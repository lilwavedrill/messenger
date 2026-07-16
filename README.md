# Messenger

Учебный мессенджер для практики VK Education (кейс № 1). Личные и групповые
чаты, обмен сообщениями в реальном времени по WebSocket, история и поиск,
вложения через S3, статусы доставки и полный набор ролей внутри чата.

## Стек

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2, psycopg 3
- **БД:** PostgreSQL 14
- **Realtime:** WebSocket
- **Auth:** JWT (access + refresh) + bcrypt
- **Хранилище файлов:** S3-совместимое (MinIO для локальной разработки)
- **Frontend:** одностраничное HTML/CSS/JS-приложение без сборщика
- **Тесты:** pytest + httpx

## Реализованные функции

Обязательный минимум по ТЗ:

- [x] Регистрация/логин, JWT + refresh, bcrypt для паролей
- [x] Личные (1-на-1) и групповые чаты с названием
- [x] Реалтайм-обмен сообщениями через WebSocket
- [x] История сообщений с пагинацией «вверх» (по `before_id`)
- [x] Добавление/удаление участников (только `owner`)
- [x] Поиск по сообщениям (полнотекстовый на GIN-индексе)
- [x] Роли внутри чата: `reader`, `writer`, `owner`

Дополнительно:

- [x] Статусы доставки: `sent` → `delivered` → `read`
      (одна ✓ — отправлено, две ✓✓ — доставлено, две синих — прочитано)
- [x] Идемпотентность отправки через `client_msg_id`
      и уникальный ключ `(chat_id, client_msg_id)`
- [x] Вложения через S3 (MinIO): загрузка, presigned-URL для скачивания,
      лайтбокс для изображений
- [x] Пользовательский профиль: `display_name`, аватар
- [x] Ротация refresh-токенов (одноразовые, revoke через `/auth/logout`)
- [x] Аудит действий пользователей (таблица `audit_log`)
- [x] Автоматические тесты API (7 сценариев, включая негативные)

## Быстрый старт

Требования: macOS/Linux, Python 3.11+, PostgreSQL 14+,
[MinIO](https://min.io/), `graphviz` для перегенерации ER-диаграммы
(опционально).

```bash
# 1) PostgreSQL
brew services start postgresql@14
psql -U mac -d postgres -c "CREATE DATABASE messenger;"
psql -U mac -d messenger -f backend/schema.sql

# 2) MinIO
brew install minio/stable/minio
mkdir -p .minio-data
minio server .minio-data --address :9000 --console-address :9001 &

# 3) Backend
cd backend
cp .env.example .env
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 4) Тестовые данные (опционально)
.venv/bin/python -m scripts.seed

# 5) Запуск
.venv/bin/uvicorn app.main:app --port 8000
```

После запуска доступны:

- Веб-клиент: <http://127.0.0.1:8000/app/>
- Swagger UI: <http://127.0.0.1:8000/docs>
- Health-check: <http://127.0.0.1:8000/healthz>
- MinIO Console: <http://127.0.0.1:9001> (`minioadmin` / `minioadmin`)

Тестовые аккаунты после `scripts/seed.py`:

| Логин | Пароль | Роль в чате «General» |
|---|---|---|
| `alice`   | `secret123` | owner  |
| `bob`     | `secret123` | writer |
| `charlie` | `secret123` | writer |

## Автоматические тесты

```bash
cd backend
.venv/bin/pytest -q
```

Покрывают happy-path регистрации/логина, отказ на неверном пароле, полный
цикл «создать чат — отправить — получить — найти», проверку прав `reader`
на отправку, ротацию refresh-токенов, идемпотентность отправки.

## Структура

```
messenger/
├─ backend/
│  ├─ app/
│  │  ├─ main.py              # FastAPI-приложение, монтирование фронта
│  │  ├─ config.py            # чтение .env
│  │  ├─ db.py                # SQLAlchemy engine и SessionLocal
│  │  ├─ models.py            # ORM-модели
│  │  ├─ schemas.py           # Pydantic-схемы request/response
│  │  ├─ auth.py              # JWT, bcrypt, refresh-токены
│  │  ├─ hub.py               # in-memory реестр WS-подписчиков
│  │  ├─ s3.py                # клиент MinIO/S3, presigned URLs
│  │  ├─ routes_auth.py       # /auth/*, профиль, аватар
│  │  ├─ routes_chats.py      # чаты и участники
│  │  ├─ routes_messages.py   # отправка, история, поиск
│  │  ├─ routes_ws.py         # WebSocket + ack/read
│  │  └─ routes_attachments.py# загрузка/раздача файлов
│  ├─ migrations/             # инкрементальные SQL-миграции
│  ├─ scripts/seed.py         # тестовые данные
│  ├─ tests/                  # pytest + httpx
│  ├─ schema.sql              # полная схема БД
│  ├─ requirements.txt
│  └─ .env.example
├─ frontend/
│  └─ index.html              # одностраничный клиент
└─ docs/
   ├─ er.png / er.svg / er.dot
   ├─ report.docx             # отчёт по ГОСТ 7.32-2017
   ├─ report.md               # markdown-версия отчёта
   ├─ contributions.md        # вклад участников
   └─ build_report.js         # генератор отчёта (docx-js)
```

## API

Полная интерактивная документация — Swagger UI по адресу `/docs`.
Кратко:

| Метод   | Путь                                     | Описание |
|---------|------------------------------------------|-----------|
| POST    | `/auth/register`                         | Регистрация |
| POST    | `/auth/login`                            | Вход (access + refresh) |
| POST    | `/auth/refresh`                          | Обмен refresh на новый access |
| POST    | `/auth/logout`                           | Отзыв refresh-токена |
| GET     | `/auth/me`                               | Профиль |
| PATCH   | `/auth/me`                               | Обновить `display_name` |
| POST    | `/auth/me/avatar`                        | Загрузить аватар |
| DELETE  | `/auth/me/avatar`                        | Удалить аватар |
| GET     | `/auth/users/{id}/avatar`                | Аватар (redirect на presigned) |
| GET     | `/chats`                                 | Список моих чатов |
| POST    | `/chats`                                 | Создать чат |
| GET     | `/chats/{id}/members`                    | Участники |
| POST    | `/chats/{id}/members`                    | Добавить (только owner) |
| DELETE  | `/chats/{id}/members/{uid}`              | Удалить (только owner) |
| GET     | `/chats/{id}/messages?before_id=&limit=` | История |
| POST    | `/chats/{id}/messages`                   | Отправить |
| GET     | `/chats/{id}/search?q=`                  | Поиск |
| POST    | `/chats/{id}/attachments`                | Загрузить файл |
| GET     | `/attachments/{id}`                      | Скачать (redirect) |
| WS      | `/ws/{chat_id}?token=<JWT>`              | Реалтайм-подписка |

## Известные ограничения

- Одна нода API — `Hub` держит подключения в памяти. При масштабировании на
  несколько инстансов нужен внешний брокер (например, Redis pub/sub).
- Нет push-уведомлений для оффлайн-пользователей.
- Нет E2E-шифрования переписки.
- Presigned URL действителен 1 час.

## Авторы

См. [docs/contributions.md](docs/contributions.md).
