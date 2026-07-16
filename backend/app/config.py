import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://mac@localhost:5432/messenger")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_TTL_MINUTES = int(os.getenv("JWT_TTL_MINUTES", "30"))
JWT_ALG = "HS256"
REFRESH_TTL_DAYS = int(os.getenv("REFRESH_TTL_DAYS", "30"))

S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "http://127.0.0.1:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadmin")
S3_BUCKET = os.getenv("S3_BUCKET", "messenger-attachments")
S3_PUBLIC_URL = os.getenv("S3_PUBLIC_URL", "http://127.0.0.1:9000")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "100"))
