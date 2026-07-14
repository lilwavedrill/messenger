from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Header
from passlib.context import CryptContext
from jose import jwt, JWTError
from app.config import JWT_SECRET, JWT_ALG, JWT_TTL_MINUTES

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
