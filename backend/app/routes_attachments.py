"""Загрузка и скачивание вложений через S3-совместимое хранилище."""
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

    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, f"file too large (max {MAX_UPLOAD_MB} MB)")
    if not data:
        raise HTTPException(422, "empty file")

    key = f"chat/{chat_id}/{uuid.uuid4().hex}/{file.filename}"
    s3.put_object(key, data, file.content_type or "application/octet-stream")

    att = Attachment(
        uploader_id=user_id,
        s3_key=key,
        filename=file.filename or "unnamed",
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(data),
    )
    db.add(att)
    db.add(AuditLog(
        user_id=user_id, action="upload_attachment",
        payload={"chat_id": chat_id, "filename": file.filename, "size": len(data)},
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
