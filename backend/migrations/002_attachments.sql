-- Вложения: файлы хранятся в S3-совместимом хранилище (MinIO),
-- в БД — только метаданные и ссылка на объект.

CREATE TABLE IF NOT EXISTS attachments (
    id         BIGSERIAL PRIMARY KEY,
    message_id BIGINT REFERENCES messages(id) ON DELETE CASCADE,
    uploader_id BIGINT NOT NULL REFERENCES users(id),
    s3_key     VARCHAR(512) NOT NULL,
    filename   VARCHAR(255) NOT NULL,
    mime_type  VARCHAR(128) NOT NULL,
    size_bytes BIGINT NOT NULL CHECK (size_bytes >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_attachments_message ON attachments(message_id);
