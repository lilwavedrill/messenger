"""Интеграционные тесты API мессенджера.

Требуют запущенный Postgres с загруженной схемой (см. backend/schema.sql
и миграции). БД: `messenger`, пользователь `postgres/postgres` — то же
окружение, где живёт uvicorn.
"""
import uuid
from tests.conftest import auth_headers


# --- auth -------------------------------------------------------------------

def test_register_and_login_happy_path(client, unique_username):
    # register возвращает access + refresh
    r = client.post("/auth/register", json={"username": unique_username, "password": "secret123"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["username"] == unique_username
    assert body["token"]
    assert body["refresh_token"]
    assert body["expires_in"] > 0

    # login тем же паролем — тоже успех
    r = client.post("/auth/login", json={"username": unique_username, "password": "secret123"})
    assert r.status_code == 200, r.text
    body2 = r.json()
    assert body2["id"] == body["id"]
    assert body2["token"]
    assert body2["refresh_token"] != body["refresh_token"]


def test_login_with_wrong_password_returns_401(client, user):
    r = client.post("/auth/login", json={"username": user["username"], "password": "WRONG"})
    assert r.status_code == 401


# --- chats / messages -------------------------------------------------------

def test_create_chat_send_message_history_search(client, user, user_factory):
    # два пользователя — создатель и участник
    other = user_factory()

    r = client.post(
        "/chats",
        headers=auth_headers(user),
        json={"type": "group", "title": f"grp_{uuid.uuid4().hex[:8]}", "member_ids": [other["id"]]},
    )
    assert r.status_code == 201, r.text
    chat_id = r.json()["id"]

    # отправка
    r = client.post(
        f"/chats/{chat_id}/messages",
        headers=auth_headers(user),
        json={"text": "Первое сообщение с полнотекстовым поиском"},
    )
    assert r.status_code == 201, r.text
    msg = r.json()

    # история
    r = client.get(f"/chats/{chat_id}/messages", headers=auth_headers(user))
    assert r.status_code == 200
    history = r.json()
    assert any(m["id"] == msg["id"] for m in history)

    # search: точное вхождение
    r = client.get(f"/chats/{chat_id}/search", headers=auth_headers(user), params={"q": "поиск"})
    assert r.status_code == 200
    hits = r.json()
    assert any(m["id"] == msg["id"] for m in hits), f"search 'поиск' didn't find msg {msg['id']}"

    # search: стемминг ("поисков" -> тот же lexeme)
    r = client.get(f"/chats/{chat_id}/search", headers=auth_headers(user), params={"q": "поисков"})
    assert r.status_code == 200
    assert any(m["id"] == msg["id"] for m in r.json())

    # search: заведомо отсутствующая строка
    r = client.get(f"/chats/{chat_id}/search", headers=auth_headers(user), params={"q": "zzznotpresent"})
    assert r.status_code == 200
    assert r.json() == []


# --- roles ------------------------------------------------------------------

def test_reader_gets_403_on_send(client, user, user_factory):
    reader = user_factory()

    r = client.post(
        "/chats",
        headers=auth_headers(user),
        json={"type": "group", "title": f"grp_{uuid.uuid4().hex[:8]}", "member_ids": []},
    )
    assert r.status_code == 201
    chat_id = r.json()["id"]

    # добавим reader'а с ролью reader
    r = client.post(
        f"/chats/{chat_id}/members",
        headers=auth_headers(user),
        json={"user_id": reader["id"], "role": "reader"},
    )
    assert r.status_code == 201, r.text

    # reader пытается отправить — должен получить 403
    r = client.post(
        f"/chats/{chat_id}/messages",
        headers=auth_headers(reader),
        json={"text": "не должно пройти"},
    )
    assert r.status_code == 403


# --- refresh / logout -------------------------------------------------------

def test_refresh_rotates_and_old_is_revoked(client, user):
    refresh1 = user["refresh_token"]

    # первое обновление — успех
    r = client.post("/auth/refresh", json={"refresh_token": refresh1})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token"] and body["refresh_token"] and body["expires_in"] > 0
    refresh2 = body["refresh_token"]
    assert refresh2 != refresh1

    # повторная попытка старым — 401 (rotation)
    r = client.post("/auth/refresh", json={"refresh_token": refresh1})
    assert r.status_code == 401

    # logout свежим — 204
    r = client.post("/auth/logout", json={"refresh_token": refresh2})
    assert r.status_code == 204

    # после logout — refresh больше не работает
    r = client.post("/auth/refresh", json={"refresh_token": refresh2})
    assert r.status_code == 401


def test_refresh_with_garbage_returns_401(client):
    r = client.post("/auth/refresh", json={"refresh_token": "definitely-not-a-real-token"})
    assert r.status_code == 401


# --- idempotency ------------------------------------------------------------

def test_send_same_client_msg_id_twice_returns_same_message(client, user):
    r = client.post(
        "/chats",
        headers=auth_headers(user),
        json={"type": "group", "title": f"grp_{uuid.uuid4().hex[:8]}", "member_ids": []},
    )
    chat_id = r.json()["id"]

    cid = str(uuid.uuid4())
    payload = {"text": "идемпотентно", "client_msg_id": cid}
    r1 = client.post(f"/chats/{chat_id}/messages", headers=auth_headers(user), json=payload)
    assert r1.status_code == 201, r1.text
    r2 = client.post(f"/chats/{chat_id}/messages", headers=auth_headers(user), json=payload)
    assert r2.status_code == 201, r2.text
    assert r1.json()["id"] == r2.json()["id"], "same client_msg_id must map to same message id"
