-- Добавляем поле для ключа аватара в S3
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_key VARCHAR(512);
