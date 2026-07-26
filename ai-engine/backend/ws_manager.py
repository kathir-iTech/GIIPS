"""
WebSocket connection manager for real-time dashboard updates.

Maintains a set of active WebSocket connections and broadcasts
event messages (complaint:new, incident:update, etc.) to all
connected dashboard clients.  Each client receives every event —
the frontend decides which events to act on.

Thread-safe for a single asyncio event loop (all WebSocket
connections live on the same uvicorn worker).
"""

import json
import logging
from typing import Any, Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)
        logger.info("WebSocket connected  (%d active)", len(self._connections))

    async def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)
        logger.info("WebSocket disconnected  (%d active)", len(self._connections))

    async def broadcast(self, event_type: str, payload: Dict[str, Any]) -> None:
        message = json.dumps({"type": event_type, "payload": payload})
        stale: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self._connections.discard(ws)

    @property
    def active_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()
