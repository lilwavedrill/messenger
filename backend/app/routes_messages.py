from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func, literal_column, Text, cast
from app.db import get_db
from app.models import Message, MessageStatus, ChatMember, AuditLog, Attachment
from app.auth import current_user_id
from app.schemas import SendMessageIn, MessageOut, StatusOut, AttachmentOut
from app.hub import hub

router = APIRouter(prefix="/chats", tags=["messages"])


def _require_member(db: Session, chat_id: int, user_id: int) -> ChatMember:
    m = db.get(ChatMember, (chat_id, user_id))
    if not m:
        raise HTTPException(404, "chat not found")
    return m


def _statuses_for(db: Session, message_ids: list[int]) -> dict[int, list[StatusOut]]:
    if not message_ids:
        return {}
    rows = db.execute(
        select(MessageStatus).where(MessageStatus.message_id.in_(message_ids))
    ).scalars()
    out: dict[int, list[StatusOut]] = {}
    for r in rows:
        out.setdefault(r.message_id, []).append(StatusOut(user_id=r.user_id, status=r.status))
    return out


def _attachments_for(db: Session, message_ids: list[int]) -> dict[int, list[AttachmentOut]]:
    if not message_ids:
        return {}
    rows = db.execute(
        select(Attachment).where(Attachment.message_id.in_(message_ids))
    ).scalars()
    out: dict[int, list[AttachmentOut]] = {}
    for r in rows:
        out.setdefault(r.message_id, []).append(
            AttachmentOut(id=r.id, filename=r.filename, mime_type=r.mime_type, size_bytes=r.size_bytes)
        )
    return out


def _to_out(msg: Message, statuses: list[StatusOut], atts: list[AttachmentOut] | None = None) -> MessageOut:
    return MessageOut(
        id=msg.id, chat_id=msg.chat_id, sender_id=msg.sender_id,
        text=msg.text, created_at=msg.created_at, statuses=statuses,
        attachments=atts or [],
    )


@router.post("/{chat_id}/messages", response_model=MessageOut, status_code=201)
async def send_message(
    chat_id: int,
    body: SendMessageIn,
    db: Session = Depends(get_db),
    user_id: int = Depends(current_user_id),
):
    member = _require_member(db, chat_id, user_id)
    if member.role == "reader":
        raise HTTPException(403, "read-only in this chat")

    # Идемпотентность
    if body.client_msg_id:
        existing = db.execute(
            select(Message).where(
                Message.chat_id == chat_id, Message.client_msg_id == body.client_msg_id
            )
        ).scalar_one_or_none()
        if existing:
            st = _statuses_for(db, [existing.id]).get(existing.id, [])
            at = _attachments_for(db, [existing.id]).get(existing.id, [])
            return _to_out(existing, st, at)

    msg = Message(chat_id=chat_id, sender_id=user_id, text=body.text, client_msg_id=body.client_msg_id)
    db.add(msg)
    db.flush()

    # Привязка ранее загруженных вложений к сообщению
    if body.attachment_ids:
        atts = db.execute(
            select(Attachment).where(Attachment.id.in_(body.attachment_ids))
        ).scalars().all()
        for a in atts:
            if a.uploader_id != user_id or a.message_id is not None:
                raise HTTPException(403, "attachment not owned or already used")
            a.message_id = msg.id

    # Начальные статусы: 'sent' для всех участников чата
    members = db.execute(
        select(ChatMember.user_id).where(ChatMember.chat_id == chat_id)
    ).scalars().all()
    for uid in members:
        db.add(MessageStatus(message_id=msg.id, user_id=uid, status="sent"))

    db.add(AuditLog(user_id=user_id, action="send_message", payload={"chat_id": chat_id}))
    db.commit()
    db.refresh(msg)

    st = _statuses_for(db, [msg.id]).get(msg.id, [])
    at = _attachments_for(db, [msg.id]).get(msg.id, [])
    payload = _to_out(msg, st, at).model_dump(mode="json")
    payload["type"] = "message"
    await hub.broadcast(chat_id, payload)
    return _to_out(msg, st, at)


@router.get("/{chat_id}/messages", response_model=list[MessageOut])
def history(
    chat_id: int,
    before_id: int | None = Query(None, description="сообщения с id < before_id"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user_id: int = Depends(current_user_id),
):
    _require_member(db, chat_id, user_id)
    q = select(Message).where(Message.chat_id == chat_id)
    if before_id is not None:
        q = q.where(Message.id < before_id)
    q = q.order_by(desc(Message.id)).limit(limit)
    rows = list(reversed(list(db.execute(q).scalars())))
    ids = [m.id for m in rows]
    st_map = _statuses_for(db, ids)
    at_map = _attachments_for(db, ids)
    return [_to_out(m, st_map.get(m.id, []), at_map.get(m.id, [])) for m in rows]


@router.get("/{chat_id}/search", response_model=list[MessageOut])
def search(
    chat_id: int,
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user_id: int = Depends(current_user_id),
):
    _require_member(db, chat_id, user_id)

    # Полнотекстовый поиск через GIN-индекс (idx_messages_text_search).
    # plainto_tsquery корректно превращает "поиск" / "поисков" в один и тот же lexeme.
    # Первый аргумент — regconfig, поэтому передаём его как literal_column
    # (иначе SQLAlchemy отправит его как VARCHAR и Postgres не найдёт функцию).
    russian = literal_column("'russian'")
    tsquery = func.plainto_tsquery(russian, q)
    tsvector = func.to_tsvector(russian, Message.text)

    # Если tsquery пустая (например q состоит только из стоп-слов) — fallback на ILIKE,
    # иначе пользователь получит пустой список и подумает, что ничего не найдено.
    is_empty = db.execute(select(cast(tsquery, Text))).scalar() == ""

    if is_empty:
        rows = list(db.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .where(Message.text.ilike(f"%{q}%"))
            .order_by(desc(Message.id))
            .limit(limit)
        ).scalars())
    else:
        rank = func.ts_rank_cd(tsvector, tsquery)
        rows = list(db.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .where(tsvector.op("@@")(tsquery))
            .order_by(desc(rank), desc(Message.id))
            .limit(limit)
        ).scalars())

    ids = [m.id for m in rows]
    st_map = _statuses_for(db, ids)
    at_map = _attachments_for(db, ids)
    return [_to_out(m, st_map.get(m.id, []), at_map.get(m.id, [])) for m in rows]
