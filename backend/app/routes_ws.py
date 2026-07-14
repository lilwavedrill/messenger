import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError
from sqlalchemy import select
from app.auth import parse_token
from app.db import SessionLocal
from app.models import ChatMember, Message, MessageStatus
from app.hub import hub

router = APIRouter()


STATUS_ORDER = {"sent": 0, "delivered": 1, "read": 2}


def _update_status(db, message_id: int, user_id: int, new_status: str) -> bool:
    """Обновить статус, только если новый выше по цепочке. Вернуть True, если поменяли."""
    row = db.get(MessageStatus, (message_id, user_id))
    if not row:
        return False
    if STATUS_ORDER[new_status] <= STATUS_ORDER[row.status]:
        return False
    row.status = new_status
    return True


@router.websocket("/ws/{chat_id}")
async def ws_chat(ws: WebSocket, chat_id: int, token: str = Query(...)):
    # WebSocket-протокол требует сначала принять handshake, а уже потом закрыть с кодом ошибки —
    # иначе Starlette кидает "WebSocket is not connected".
    await ws.accept()

    try:
        user_id = parse_token(token)
    except JWTError:
        await ws.close(code=4401)
        return

    with SessionLocal() as db:
        if not db.get(ChatMember, (chat_id, user_id)):
            await ws.close(code=4403)
            return
    await hub.join(chat_id, ws)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                ev = json.loads(raw)
            except Exception:
                continue

            kind = ev.get("type")
            if kind not in ("ack", "read"):
                continue  # heartbeat/прочее игнорируем

            ids = ev.get("message_ids") or []
            if not isinstance(ids, list) or not ids:
                continue
            new_status = "delivered" if kind == "ack" else "read"

            with SessionLocal() as db:
                # Проверим, что все сообщения из этого чата — защита от подделки
                rows = db.execute(
                    select(Message.id).where(Message.id.in_(ids), Message.chat_id == chat_id)
                ).scalars().all()
                changed: list[int] = []
                for mid in rows:
                    if _update_status(db, mid, user_id, new_status):
                        changed.append(mid)
                if changed:
                    db.commit()

            if changed:
                await hub.broadcast(chat_id, {
                    "type": "status",
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "status": new_status,
                    "message_ids": changed,
                })
    except WebSocketDisconnect:
        pass
    finally:
        await hub.leave(chat_id, ws)
