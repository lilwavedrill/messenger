"""Наполняет базу тестовыми данными: 3 пользователя, один личный чат, один групповой,
пара сообщений в каждом. Идемпотентно — повторный запуск не создаёт дубли.

Запуск:
    .venv/bin/python -m scripts.seed
"""
from sqlalchemy import select
from app.db import SessionLocal
from app.models import User, Chat, ChatMember, Message, MessageStatus
from app.auth import hash_password


def get_or_create_user(db, username, password, display_name):
    u = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if u:
        return u
    u = User(username=username, password_hash=hash_password(password), display_name=display_name)
    db.add(u)
    db.flush()
    print(f"  + user {username} (id={u.id})")
    return u


def get_or_create_chat(db, chat_type, title, creator, members):
    """Ищем чат по названию (для group) или по составу участников (для direct)."""
    if chat_type == "group":
        existing = db.execute(select(Chat).where(Chat.type == "group", Chat.title == title)).scalar_one_or_none()
        if existing:
            return existing
    else:
        # для direct — ищем чат, где ровно эти двое
        member_ids = sorted(u.id for u in members)
        q = select(Chat).where(Chat.type == "direct")
        for c in db.execute(q).scalars():
            ids = sorted(m.user_id for m in db.execute(
                select(ChatMember).where(ChatMember.chat_id == c.id)
            ).scalars())
            if ids == member_ids:
                return c

    chat = Chat(type=chat_type, title=title, created_by=creator.id)
    db.add(chat)
    db.flush()
    db.add(ChatMember(chat_id=chat.id, user_id=creator.id, role="owner"))
    for m in members:
        if m.id != creator.id:
            db.add(ChatMember(chat_id=chat.id, user_id=m.id, role="writer"))
    print(f"  + chat {chat_type} '{title or 'direct'}' (id={chat.id})")
    return chat


def send_if_empty(db, chat, sender, texts):
    """Отправляет тексты, только если в чате ещё нет сообщений."""
    existing = db.execute(select(Message).where(Message.chat_id == chat.id).limit(1)).scalar_one_or_none()
    if existing:
        return
    member_ids = [m.user_id for m in db.execute(
        select(ChatMember).where(ChatMember.chat_id == chat.id)
    ).scalars()]
    for t in texts:
        msg = Message(chat_id=chat.id, sender_id=sender.id, text=t)
        db.add(msg)
        db.flush()
        for uid in member_ids:
            db.add(MessageStatus(message_id=msg.id, user_id=uid, status="sent"))
    print(f"  + {len(texts)} messages in chat {chat.id}")


def main():
    with SessionLocal() as db:
        print("Seeding users...")
        alice = get_or_create_user(db, "alice", "secret123", "Алиса")
        bob = get_or_create_user(db, "bob", "secret123", "Боб")
        charlie = get_or_create_user(db, "charlie", "secret123", "Чарли")

        print("Seeding chats...")
        general = get_or_create_chat(db, "group", "General", alice, [alice, bob, charlie])
        dm = get_or_create_chat(db, "direct", None, alice, [alice, bob])

        print("Seeding messages...")
        send_if_empty(db, general, alice, [
            "Привет всем!",
            "Это наш общий чат.",
            "Тут можно обсуждать что угодно.",
        ])
        send_if_empty(db, dm, alice, [
            "Привет, Боб!",
            "Как дела?",
        ])

        db.commit()
        print("Done.")


if __name__ == "__main__":
    main()
