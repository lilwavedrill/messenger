-- Статусы сообщений: отправлено / доставлено / прочитано
-- Одна запись на пару (message, user) — по каждому получателю.

CREATE TABLE IF NOT EXISTS message_status (
    message_id BIGINT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status     VARCHAR(16) NOT NULL
               CHECK (status IN ('sent', 'delivered', 'read')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (message_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_message_status_msg ON message_status(message_id);
