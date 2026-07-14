from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User, AuditLog
from app.auth import hash_password, verify_password, issue_token
from app.schemas import RegisterIn, LoginIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


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
    db.commit()
    db.refresh(user)
    return TokenOut(id=user.id, username=user.username, token=issue_token(user.id))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "invalid credentials")
    db.add(AuditLog(user_id=user.id, action="login"))
    db.commit()
    return TokenOut(id=user.id, username=user.username, token=issue_token(user.id))
