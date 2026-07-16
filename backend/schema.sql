-- Схема БД мессенджера

DROP TABLE IF EXISTS refresh_tokens  CASCADE;
DROP TABLE IF EXISTS audit_log       CASCADE;
DROP TABLE IF EXISTS attachments     CASCADE;
DROP TABLE IF EXISTS message_status  CASCADE;
DROP TABLE IF EXISTS messages        CASCADE;
DROP TABLE IF EXISTS chat_members    CASCADE;
DROP TABLE IF EXISTS chats           CASCADE;
DROP TABLE IF EXISTS users           CASCADE;

CREATE TABLE users (
    id            BIGSERIAL PRIMARY KEY,
    username      VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name  VARCHAR(128),
    avatar_key    VARCHAR(512),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE chats (
    id         BIGSERIAL PRIMARY KEY,
    type       VARCHAR(16) NOT NULL CHECK (type IN ('direct', 'group')),
    title      VARCHAR(128),
    created_by BIGINT NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE chat_members (
    chat_id   BIGINT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    user_id   BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role      VARCHAR(16) NOT NULL DEFAULT 'writer'
              CHECK (role IN ('reader', 'writer', 'owner')),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (chat_id, user_id)
);

CREATE TABLE messages (
    id            BIGSERIAL PRIMARY KEY,
    chat_id       BIGINT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    sender_id     BIGINT NOT NULL REFERENCES users(id),
    text          TEXT NOT NULL CHECK (char_length(text) BETWEEN 1 AND 4000),
    client_msg_id UUID,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (chat_id, client_msg_id)
);

CREATE TABLE message_status (
    message_id BIGINT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status     VARCHAR(16) NOT NULL
               CHECK (status IN ('sent', 'delivered', 'read')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (message_id, user_id)
);

CREATE TABLE attachments (
    id          BIGSERIAL PRIMARY KEY,
    message_id  BIGINT REFERENCES messages(id) ON DELETE CASCADE,
    uploader_id BIGINT NOT NULL REFERENCES users(id),
    s3_key      VARCHAR(512) NOT NULL,
    filename    VARCHAR(255) NOT NULL,
    mime_type   VARCHAR(128) NOT NULL,
    size_bytes  BIGINT NOT NULL CHECK (size_bytes >= 0),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE audit_log (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT REFERENCES users(id),
    action     VARCHAR(64) NOT NULL,
    payload    JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE refresh_tokens (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_attachments_message ON attachments(message_id);
CREATE INDEX idx_message_status_msg ON message_status(message_id);
CREATE INDEX idx_messages_chat_created ON messages(chat_id, id DESC);
CREATE INDEX idx_messages_text_search  ON messages USING gin(to_tsvector('russian', text));
CREATE INDEX idx_chat_members_user     ON chat_members(user_id);
CREATE INDEX idx_refresh_tokens_user   ON refresh_tokens(user_id);
