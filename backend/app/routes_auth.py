import uuid
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User, AuditLog
from app.auth import (
    hash_password,
    verify_password,
    issue_token,
    access_token_expires_in,
    issue_refresh_token,
    consume_refresh_token,
    revoke_refresh_token,
    current_user_id,
)
from app.schemas import RegisterIn, LoginIn, TokenOut, RefreshIn, RefreshOut, MeOut, UpdateMeIn
from app.config import MAX_UPLOAD_MB
from app import s3

router = APIRouter(prefix="/auth", tags=["auth"])
MAX_AVATAR_BYTES = min(MAX_UPLOAD_MB, 5) * 1024 * 1024  # avatar cap: 5 MB

# Разрешаем только безопасные растровые форматы. Явно исключаем image/svg+xml —
# SVG может содержать <script> и, будучи отданным браузеру напрямую через
# presigned URL (Content-Type: image/svg+xml), выполнит XSS в контексте
# S3-домена (а при некоторых конфигурациях — и того же origin).
_ALLOWED_AVATAR_MIME = {"image/png", "image/jpeg", "image/webp", "image/gif"}
# Магические байты: не доверяем клиентскому Content-Type, а проверяем сигнатуру.
def _sniff_image_mime(data: bytes) -> str | None:
    if len(data) < 12:
        return None
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _token_bundle(db: Session, user: User) -> TokenOut:
    """Общий ответ для /register, /login: access + refresh + expires_in."""
    refresh = issue_refresh_token(db, user.id)
    return TokenOut(
        id=user.id,
        username=user.username,
        token=issue_token(user.id),
        refresh_token=refresh,
        expires_in=access_token_expires_in(),
    )


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter_by(username=body.username).first():
        raise HTTPException(409, "username taken")
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
    )
    db.add(user)
    db.flush()
    db.add(AuditLog(user_id=user.id, action="register", payload={"username": user.username}))
    out = _token_bundle(db, user)
    db.commit()
    db.refresh(user)
    return out


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "invalid credentials")
    db.add(AuditLog(user_id=user.id, action="login"))
    out = _token_bundle(db, user)
    db.commit()
    return out


@router.post("/refresh", response_model=RefreshOut)
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    user_id = consume_refresh_token(db, body.refresh_token)
    new_refresh = issue_refresh_token(db, user_id)
    db.add(AuditLog(user_id=user_id, action="refresh_token"))
    db.commit()
    return RefreshOut(
        token=issue_token(user_id),
        refresh_token=new_refresh,
        expires_in=access_token_expires_in(),
    )


@router.post("/logout", status_code=204)
def logout(body: RefreshIn, db: Session = Depends(get_db)):
    user_id = revoke_refresh_token(db, body.refresh_token)
    if user_id is not None:
        db.add(AuditLog(user_id=user_id, action="logout"))
    db.commit()
    return Response(status_code=204)


# --- profile ---

def _me_out(u: User) -> MeOut:
    return MeOut(
        id=u.id,
        username=u.username,
        display_name=u.display_name,
        has_avatar=bool(u.avatar_key),
    )


@router.get("/me", response_model=MeOut)
def read_me(db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "user not found")
    return _me_out(u)


@router.patch("/me", response_model=MeOut)
def update_me(
    body: UpdateMeIn,
    db: Session = Depends(get_db),
    user_id: int = Depends(current_user_id),
):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "user not found")
    if body.display_name is not None:
        val = body.display_name.strip()
        u.display_name = val or None
    db.add(AuditLog(user_id=user_id, action="update_profile",
                    payload={"display_name": u.display_name}))
    db.commit()
    db.refresh(u)
    return _me_out(u)


@router.post("/me/avatar", response_model=MeOut)
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(current_user_id),
):
    ct = (file.content_type or "").lower()
    # Быстрый отсев по заявленному mime: только безопасные растровые форматы.
    if ct not in _ALLOWED_AVATAR_MIME:
        raise HTTPException(415, "avatar must be png, jpeg, webp or gif")

    # Читаем чанками, чтобы клиент не смог положить сервер 500-мегабайтным
    # телом (await file.read() без лимита буферизует всё в память).
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_AVATAR_BYTES:
            raise HTTPException(413, f"avatar too large (max {MAX_AVATAR_BYTES // (1024*1024)} MB)")
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise HTTPException(422, "empty file")

    # Не доверяем клиентскому Content-Type — сверяемся с реальными байтами.
    sniffed = _sniff_image_mime(data)
    if sniffed is None or sniffed != ct:
        raise HTTPException(415, "file content does not match declared image type")

    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "user not found")

    # Расширение выводим из подтверждённого mime, а не из filename — так
    # исключаем инъекции через file.filename (слэши, точки, спецсимволы).
    ext_by_mime = {
        "image/png": "png", "image/jpeg": "jpg",
        "image/webp": "webp", "image/gif": "gif",
    }
    ext = ext_by_mime[sniffed]
    new_key = f"avatars/{user_id}/{uuid.uuid4().hex}.{ext}"
    s3.put_object(new_key, data, sniffed)

    old_key = u.avatar_key
    u.avatar_key = new_key
    db.add(AuditLog(user_id=user_id, action="upload_avatar", payload={"size": len(data)}))
    db.commit()
    db.refresh(u)

    if old_key and old_key != new_key:
        try:
            s3.delete_object(old_key)
        except Exception:
            pass  # не критично — просто останется висеть в bucket

    return _me_out(u)


@router.delete("/me/avatar", response_model=MeOut)
def delete_avatar(
    db: Session = Depends(get_db),
    user_id: int = Depends(current_user_id),
):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "user not found")
    old = u.avatar_key
    u.avatar_key = None
    db.add(AuditLog(user_id=user_id, action="delete_avatar"))
    db.commit()
    db.refresh(u)
    if old:
        try:
            s3.delete_object(old)
        except Exception:
            pass
    return _me_out(u)


@router.get("/users/{user_id}/avatar")
def get_user_avatar(
    user_id: int,
    db: Session = Depends(get_db),
    _requester: int = Depends(current_user_id),  # авторизация обязательна
):
    u = db.get(User, user_id)
    if not u or not u.avatar_key:
        raise HTTPException(404, "no avatar")
    url = s3.presigned_get(u.avatar_key)
    return RedirectResponse(url, status_code=302)
