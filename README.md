# Messenger — учебный проект (VK Education, кейс №1)

Реалтайм-мессенджер: авторизация, личные и групповые чаты, WebSocket-доставка,
история с пагинацией, поиск.

## Стек

- Python 3.13 · FastAPI · SQLAlchemy 2 · psycopg 3
- PostgreSQL 14 (уже установлен через Homebrew)
- Realtime — WebSocket
- Auth — JWT (HS256) + bcrypt
- Frontend — один `index.html` без сборки, отдаётся как статика

## Что работает

- `POST /auth/register`, `POST /auth/login` → JWT
- `GET/POST /chats`, `GET/POST/DELETE /chats/{id}/members`
- `POST /chats/{id}/messages` (с идемпотентностью через `client_msg_id`)
- `GET /chats/{id}/messages?before_id=&limit=` — история с пагинацией «вверх»
- `GET /chats/{id}/search?q=` — поиск по подстроке
- `WS /ws/{chat_id}?token=<JWT>` — push новых сообщений участникам
- Аудит действий → таблица `audit_log`
- Роли внутри чата: `reader` / `writer` / `owner`

## Быстрый старт

```bash
# 1) БД (Postgres 14 через Homebrew уже запущен)
brew services start postgresql@14
psql -U mac -d postgres -c "CREATE DATABASE messenger;"
psql -U mac -d messenger -f backend/schema.sql

# 2) Backend
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

- Swagger UI: http://127.0.0.1:8000/docs
- Веб-клиент: http://127.0.0.1:8000/app/
- Health-check: http://127.0.0.1:8000/healthz

## Конфигурация

Правится в `backend/.env`:

```
DATABASE_URL=postgresql+psycopg://mac@localhost:5432/messenger
JWT_SECRET=change-me-in-prod
JWT_TTL_MINUTES=1440
```

## Проверенные сценарии

| # | Сценарий | Результат |
|---|---|---|
| 1 | Регистрация alice, bob | 201, получены JWT |
| 2 | Alice создаёт групповой чат с bob | 201, чат с двумя участниками |
| 3 | Alice отправляет 3 сообщения | 201, все в БД |
| 4 | Bob читает историю | 200, все сообщения в порядке |
| 5 | Поиск по подстроке `дела` | 200, найдено 1 совпадение |
| 6 | Пустой текст | 422 |
| 7 | Без токена | 401 |
| 8 | Отправка в чат #999999 | 404 |
| 9 | WebSocket: alice шлёт REST → bob получает push | доставлено < 100 мс |

## Структура

```
messenger/
├─ backend/
│  ├─ app/
│  │  ├─ main.py           # FastAPI app + монтирование фронта
│  │  ├─ config.py         # чтение .env
│  │  ├─ db.py             # engine + SessionLocal
│  │  ├─ models.py         # SQLAlchemy-модели
│  │  ├─ schemas.py        # Pydantic-схемы
│  │  ├─ auth.py           # JWT + bcrypt + current_user_id
│  │  ├─ hub.py            # WebSocket-хаб (broadcast)
│  │  ├─ routes_auth.py
│  │  ├─ routes_chats.py
│  │  ├─ routes_messages.py
│  │  └─ routes_ws.py
│  ├─ schema.sql           # DDL PostgreSQL с индексами
│  ├─ requirements.txt
│  └─ .env
└─ frontend/
   └─ index.html           # одностраничный клиент (auth + чаты + WS)
```

## Известные ограничения

- WebSocket-хаб держит подключения в памяти → одна нода API.
  Для масштабирования нужен Redis pub/sub между инстансами.
- Нет вложений (файлы, картинки) — в схеме есть `messages.client_msg_id`,
  можно добавить таблицу `attachments`.
- Нет push-уведомлений для оффлайн-пользователей.
