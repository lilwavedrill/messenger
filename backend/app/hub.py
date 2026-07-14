"""WebSocket-хаб: держит подключения и рассылает события участникам чата."""
import asyncio
import json
from collections import defaultdict
from fastapi import WebSocket


class Hub:
    def __init__(self):
        self._chats: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def join(self, chat_id: int, ws: WebSocket):
        async with self._lock:
            self._chats[chat_id].add(ws)

    async def leave(self, chat_id: int, ws: WebSocket):
        async with self._lock:
            self._chats[chat_id].discard(ws)

    async def broadcast(self, chat_id: int, event: dict):
        data = json.dumps(event, ensure_ascii=False, default=str)
        dead: list[WebSocket] = []
        for ws in list(self._chats.get(chat_id, ())):
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.leave(chat_id, ws)


hub = Hub()
