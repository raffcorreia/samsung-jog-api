"""Fan-out for websocket clients.

Connections are tagged as 'deck' (originating from localhost) or 'remote'.
broadcast_json()      — sends to all clients
broadcast_deck_json() — sends only to the deck client (physical kiosk)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)

_LOCALHOST = {"127.0.0.1", "::1"}


class WsHub:
    def __init__(self) -> None:
        self._clients: dict[WebSocket, bool] = {}  # ws → is_deck

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def connect(self, ws: WebSocket, *, is_deck: bool = False) -> None:
        await ws.accept()
        self._clients[ws] = is_deck
        logger.debug("ws-hub: client connected (deck=%s)", is_deck)

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.pop(ws, None)

    async def broadcast_json(self, payload: dict[str, Any]) -> None:
        await self._send_to(payload, list(self._clients))

    async def broadcast_deck_json(self, payload: dict[str, Any]) -> None:
        targets = [ws for ws, is_deck in self._clients.items() if is_deck]
        await self._send_to(payload, targets)

    async def _send_to(self, payload: dict[str, Any], targets: list[WebSocket]) -> None:
        for ws in targets:
            try:
                await ws.send_json(payload)
            except Exception as e:  # noqa: BLE001 — drop broken clients
                logger.debug("websocket send failed: %s", e)
                self.disconnect(ws)
