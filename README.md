# Messenger — учебный проект (VK Education, кейс №1)

Реалтайм-мессенджер с авторизацией, чатами, WebSocket-обменом, историей,
поиском, вложениями через S3 и статусами доставки сообщений.

## Стек

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2, psycopg 3
- **БД:** PostgreSQL 14
- **Realtime:** WebSocket (`fastapi.WebSocket`)
- **Auth:** JWT (HS256) + bcrypt
- **Файлы:** S3-совместимое хранилище (MinIO локально)
- **Frontend:** одностраничный HTML/CSS/JS без сборщика

## Возможности

Обязательный минимум (MVP по ТЗ):

- [x] Регистрация/логин по паре `логин + пароль`, JWT
- [x] Личные (1-на-1) и групповые чаты с названием
- [x] Отправка и получение сообщений в реальном времени
- [x] История сообщений с пагинацией «вверх» (по `before_id`)
- [x] Добавление/удаление участников (только `owner`)
- [x] Поиск по сообщениям в рамках чата
- [x] Роли внутри чата: `reader`, `writer`, `owner`

Дополнительно:

- [x] Статусы доставки: `sent` → `delivered` → `read` (одна ✓, две ✓✓, две синих)
- [x] Идемпотентность отправки через `client_msg_id` + `UNIQUE (chat_id, client_msg_id)`
- [x] Вложения через S3-совместимое хранилище (MinIO), картинки открываются в лайтбоксе
- [x] Аудит действий пользователей → таблица `audit_log`

## Быстрый старт

Требования: macOS/Linux, Python 3.11+, PostgreSQL 14+, [MinIO](https://min.io/).

```bash
# 1) БД
brew services start postgresql@14
psql -U mac -d postgres -c "CREATE DATABASE messenger;"
psql -U mac -d messenger -f backend/schema.sql

# 2) MinIO (S3-совместимое хранилище)
brew install minio/stable/minio
mkdir -p .minio-data
minio server .minio-data --address :9000 --console-address :9001 &

# 3) Backend
cd backend
cp .env.example .env       # при необходимости поправить креды
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 4) Наполнить БД тестовыми данными (опционально)
.venv/bin/python -m scripts.seed

# 5) Запустить сервер
.venv/bin/uvicorn app.main:app --port 8000
```

После запуска:

- Веб-клиент: <http://127.0.0.1:8000/app/>
- Swagger UI: <http://127.0.0.1:8000/docs>
- Health-check: <http://127.0.0.1:8000/healthz>
- MinIO Console: <http://127.0.0.1:9001> (login `minioadmin` / `minioadmin`)

Тестовые пользователи (после `scripts/seed.py`):

| Логин | Пароль | Роль в чате «General» |
|---|---|---|
| `alice` | `secret123` | owner |
| `bob` | `secret123` | writer |
| `charlie` | `secret123` | writer |

## Структура

```
messenger/
├─ backend/
│  ├─ app/
│  │  ├─ main.py              # FastAPI приложение
│  │  ├─ config.py            # чтение .env
│  │  ├─ db.py                # engine + SessionLocal
│  │  ├─ models.py            # SQLAlchemy-модели
│  │  ├─ schemas.py           # Pydantic-схемы
│  │  ├─ auth.py              # JWT + bcrypt
│  │  ├─ hub.py               # in-memory реестр WS-подписчиков
│  │  ├─ s3.py                # клиент к MinIO/S3
│  │  ├─ routes_auth.py
│  │  ├─ routes_chats.py
│  │  ├─ routes_messages.py
│  │  ├─ routes_ws.py
│  │  └─ routes_attachments.py
│  ├─ scripts/
│  │  └─ seed.py              # наполнение тестовыми данными
│  ├─ migrations/             # инкрементальные SQL-миграции
│  ├─ schema.sql              # полная схема БД
│  ├─ requirements.txt
│  └─ .env.example
├─ frontend/
│  └─ index.html              # одностраничный клиент
└─ docs/
   ├─ er.png / er.svg / er.dot
   ├─ report.docx             # отчёт по ГОСТ 7.32-2017
   └─ report.md               # markdown-версия отчёта
```

## API (кратко)

| Метод | Путь | Описание |
|---|---|---|
| POST | `/auth/register` | Регистрация |
| POST | `/auth/login` | Вход, возвращает JWT |
| GET | `/chats` | Список моих чатов |
| POST | `/chats` | Создать чат |
| GET | `/chats/{id}/members` | Участники чата |
| POST | `/chats/{id}/members` | Добавить (только `owner`) |
| DELETE | `/chats/{id}/members/{uid}` | Удалить (только `owner`) |
| GET | `/chats/{id}/messages?before_id=&limit=` | История |
| POST | `/chats/{id}/messages` | Отправить сообщение (опц. `attachment_ids`) |
| GET | `/chats/{id}/search?q=` | Поиск по чату |
| POST | `/chats/{id}/attachments` | Загрузить файл (multipart) |
| GET | `/attachments/{id}` | Скачать (redirect на presigned URL) |
| WS | `/ws/{chat_id}?token=<JWT>` | Реалтайм-подписка |

## Известные ограничения

- Одна нода API: `Hub` держит подключения в памяти. Для масштабирования нужен
  брокер (Redis pub/sub, Kafka, NATS JetStream).
- Нет push-уведомлений для оффлайн-пользователей.
- Нет E2E-шифрования.
- Presigned URL действителен 1 час — этого хватает для скачивания, но не для
  долговременных ссылок.

## Авторы

- см. `docs/contributions.md`
