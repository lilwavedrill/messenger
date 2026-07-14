"""Клиент к S3-совместимому хранилищу (MinIO для разработки).
Bucket создаётся автоматически при старте приложения.
"""
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from app.config import (
    S3_ENDPOINT_URL, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET, S3_PUBLIC_URL,
)


_s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT_URL,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    config=Config(signature_version="s3v4"),
    region_name="us-east-1",
)


def ensure_bucket():
    try:
        _s3.head_bucket(Bucket=S3_BUCKET)
    except ClientError:
        _s3.create_bucket(Bucket=S3_BUCKET)


def put_object(key: str, data: bytes, content_type: str) -> None:
    _s3.put_object(Bucket=S3_BUCKET, Key=key, Body=data, ContentType=content_type)


def presigned_get(key: str, expires_in: int = 3600) -> str:
    """Временная ссылка на скачивание, действительна expires_in секунд."""
    url = _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )
    # MinIO подписывает по внутреннему хосту; подменяем на публичный
    if S3_PUBLIC_URL and S3_PUBLIC_URL != S3_ENDPOINT_URL:
        url = url.replace(S3_ENDPOINT_URL, S3_PUBLIC_URL, 1)
    return url


def delete_object(key: str) -> None:
    _s3.delete_object(Bucket=S3_BUCKET, Key=key)
