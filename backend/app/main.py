from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.routes_auth import router as auth_router
from app.routes_chats import router as chats_router
from app.routes_messages import router as messages_router
from app.routes_ws import router as ws_router
from app.routes_attachments import router as attachments_router
from app import s3

app = FastAPI(title="Messenger API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chats_router)
app.include_router(messages_router)
app.include_router(ws_router)
app.include_router(attachments_router)


@app.on_event("startup")
def _init_s3():
    try:
        s3.ensure_bucket()
    except Exception as e:
        print(f"[warn] S3 bucket init failed: {e}")


@app.get("/healthz", tags=["meta"])
def healthz():
    return {"status": "ok"}


# Отдаём минимальный HTML-клиент как статику
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
