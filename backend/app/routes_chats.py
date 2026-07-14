from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from app.db import get_db
from app.models import Chat, ChatMember, User, AuditLog
from app.auth import current_user_id
from app.schemas import ChatCreateIn, ChatOut, MemberIn, UserOut

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("", response_model=list[ChatOut])
def list_my_chats(db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    q = (
        select(Chat)
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .where(ChatMember.user_id == user_id)
        .order_by(Chat.created_at.desc())
    )
    return list(db.execute(q).scalars())


@router.post("", response_model=ChatOut, status_code=201)
def create_chat(body: ChatCreateIn, db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    if body.type == "group" and not body.title:
        raise HTTPException(422, "group chat requires title")
    if body.type == "direct" and len(body.member_ids) != 1:
        raise HTTPException(422, "direct chat requires exactly 1 other member")

    chat = Chat(type=body.type, title=body.title, created_by=user_id)
    db.add(chat)
    db.flush()

    db.add(ChatMember(chat_id=chat.id, user_id=user_id, role="owner"))
    for mid in body.member_ids:
        if mid == user_id:
            continue
        if not db.get(User, mid):
            raise HTTPException(404, f"user {mid} not found")
        db.add(ChatMember(chat_id=chat.id, user_id=mid, role="writer"))

    db.add(AuditLog(user_id=user_id, action="create_chat", payload={"chat_id": chat.id, "type": chat.type}))
    db.commit()
    db.refresh(chat)
    return chat


def _require_owner(db: Session, chat_id: int, user_id: int) -> ChatMember:
    m = db.get(ChatMember, (chat_id, user_id))
    if not m:
        raise HTTPException(404, "chat not found")
    if m.role != "owner":
        raise HTTPException(403, "owner only")
    return m


@router.get("/{chat_id}/members", response_model=list[UserOut])
def list_members(chat_id: int, db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    if not db.get(ChatMember, (chat_id, user_id)):
        raise HTTPException(404, "chat not found")
    q = select(User).join(ChatMember, ChatMember.user_id == User.id).where(ChatMember.chat_id == chat_id)
    return list(db.execute(q).scalars())


@router.post("/{chat_id}/members", status_code=201)
def add_member(chat_id: int, body: MemberIn, db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    _require_owner(db, chat_id, user_id)
    if not db.get(User, body.user_id):
        raise HTTPException(404, "user not found")
    if db.get(ChatMember, (chat_id, body.user_id)):
        raise HTTPException(409, "already a member")
    db.add(ChatMember(chat_id=chat_id, user_id=body.user_id, role=body.role))
    db.add(AuditLog(user_id=user_id, action="add_member",
                    payload={"chat_id": chat_id, "target": body.user_id, "role": body.role}))
    db.commit()
    return {"ok": True}


@router.delete("/{chat_id}/members/{target_id}")
def remove_member(chat_id: int, target_id: int, db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    _require_owner(db, chat_id, user_id)
    m = db.get(ChatMember, (chat_id, target_id))
    if not m:
        raise HTTPException(404, "member not found")
    if m.role == "owner":
        raise HTTPException(409, "cannot remove owner")
    db.delete(m)
    db.add(AuditLog(user_id=user_id, action="remove_member",
                    payload={"chat_id": chat_id, "target": target_id}))
    db.commit()
    return {"ok": True}
