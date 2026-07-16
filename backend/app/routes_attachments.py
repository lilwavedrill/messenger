"""Загрузка и скачивание вложений через S3-совместимое хранилище."""
import re
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Attachment, ChatMember, AuditLog
from app.auth import current_user_id
from app.config import MAX_UPLOAD_MB
from app import s3

router = APIRouter(tags=["attachments"])

MAX_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# Разрешаем в имени только буквы/цифры/точку/подчёркивание/дефис.
# Всё остальное (слэши, обратные слэши, NUL, управляющие символы, юникод-хитрости)
# режем — иначе можно испортить S3-ключ или подсунуть неожиданный Content-Disposition.
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]")


def _sanitize_filename(name: str | None) -> str:
    if not name:
        return "file"
    # NUL-байты и путь: берём только базовое имя
    base = name.replace("\x00", "").replace("\\", "/").split("/")[-1]
    base = _SAFE_NAME_RE.sub("_", base).strip("._") or "file"
    # ограничиваем длину, чтобы уложиться в лимит s3_key (VARCHAR(512))
    if len(base) > 128:
        stem, dot, ext = base.rpartition(".")
        if dot and 1 <= len(ext) <= 8:
            base = stem[: 128 - len(ext) - 1] + "." + ext
        else:
            base = base[:128]
    return base


@router.post("/chats/{chat_id}/attachments")
async def upload_attachment(
    chat_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(current_user_id),
):
    """Загрузить файл и получить attachment_id для последующей отправки в сообщении."""
    if not db.get(ChatMember, (chat_id, user_id)):
        raise HTTPException(404, "chat not found")

    # Читаем чанками с проверкой лимита — иначе клиент может выесть память,
    # прислав файл сильно больше MAX_BYTES.
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_BYTES:
            raise HTTPException(413, f"file too large (max {MAX_UPLOAD_MB} MB)")
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise HTTPException(422, "empty file")

    safe_name = _sanitize_filename(file.filename)
    key = f"chat/{chat_id}/{uuid.uuid4().hex}/{safe_name}"
    s3.put_object(key, data, file.content_type or "application/octet-stream")

    att = Attachment(
        uploader_id=user_id,
        s3_key=key,
        filename=safe_name,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(data),
    )
    db.add(att)
    db.add(AuditLog(
        user_id=user_id, action="upload_attachment",
        payload={"chat_id": chat_id, "filename": safe_name, "size": len(data)},
    ))
    db.commit()
    db.refresh(att)

    return {
        "id": att.id,
        "filename": att.filename,
        "mime_type": att.mime_type,
        "size_bytes": att.size_bytes,
    }


@router.get("/attachments/{att_id}")
def download_attachment(
    att_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(current_user_id),
):
    """Редиректим на presigned URL в S3 (временная ссылка на 1 час)."""
    att = db.get(Attachment, att_id)
    if not att:
        raise HTTPException(404, "attachment not found")

    # Проверка доступа: если вложение прикреплено к сообщению — проверяем членство в чате
    if att.message_id:
        from app.models import Message
        msg = db.get(Message, att.message_id)
        if not msg or not db.get(ChatMember, (msg.chat_id, user_id)):
            raise HTTPException(403, "access denied")
    elif att.uploader_id != user_id:
        # Ещё не привязано к сообщению — доступ только у загрузившего
        raise HTTPException(403, "access denied")

    url = s3.presigned_get(att.s3_key)
    return RedirectResponse(url, status_code=302)
