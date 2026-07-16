import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Header
from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.config import JWT_SECRET, JWT_ALG, JWT_TTL_MINUTES, REFRESH_TTL_DAYS
from app.models import RefreshToken

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(p: str) -> str:
    return pwd.hash(p)


def verify_password(p: str, h: str) -> bool:
    return pwd.verify(p, h)


def issue_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_TTL_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def access_token_expires_in() -> int:
    """Seconds until a freshly issued access token expires."""
    return JWT_TTL_MINUTES * 60


def parse_token(token: str) -> int:
    data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    return int(data["sub"])


def current_user_id(authorization: str | None = Header(default=None)) -> int:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing or invalid authorization header")
    token = authorization.split(" ", 1)[1].strip()
    try:
        return parse_token(token)
    except JWTError:
        raise HTTPException(401, "invalid or expired token")


# --- Refresh tokens ---------------------------------------------------------

def _hash_refresh(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issue_refresh_token(db: Session, user_id: int) -> str:
    """Создаёт refresh-токен, кладёт его хэш в БД, возвращает сырое значение."""
    raw = secrets.token_hex(32)
    row = RefreshToken(
        user_id=user_id,
        token_hash=_hash_refresh(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TTL_DAYS),
    )
    db.add(row)
    db.flush()
    return raw


def consume_refresh_token(db: Session, raw: str) -> int:
    """Валидирует и отзывает refresh, возвращает user_id.

    Отзыв ('rotation') делает старый refresh одноразовым: попытка использовать
    его повторно после /auth/refresh даст 401.

    Используем SELECT ... FOR UPDATE, чтобы два параллельных /auth/refresh
    с одним и тем же токеном не выпустили две валидные пары (race → двойная выдача).
    """
    row = db.execute(
        select(RefreshToken)
        .where(RefreshToken.token_hash == _hash_refresh(raw))
        .with_for_update()
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(401, "invalid refresh token")
    if row.revoked_at is not None:
        raise HTTPException(401, "refresh token revoked")
    if row.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(401, "refresh token expired")
    row.revoked_at = datetime.now(timezone.utc)
    db.flush()
    return row.user_id


def revoke_refresh_token(db: Session, raw: str) -> int | None:
    """Отзывает refresh; возвращает user_id владельца, если что-то изменилось,
    иначе None (токен не найден или уже отозван).
    Блокируем строку, чтобы одновременный /logout и /refresh не пересекались."""
    row = db.execute(
        select(RefreshToken)
        .where(RefreshToken.token_hash == _hash_refresh(raw))
        .with_for_update()
    ).scalar_one_or_none()
    if row is None or row.revoked_at is not None:
        return None
    row.revoked_at = datetime.now(timezone.utc)
    db.flush()
    return row.user_id
