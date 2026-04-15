"""Backend-owned live log buffer and websocket log event creation."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Literal

from fastapi import WebSocket

from pi_deck.models.schemas import WsEventV1, utc_iso, ws_log_entry
from pi_deck.services.ws_hub import WsHub

LogLevel = Literal["debug", "info", "warning", "error"]


def _event_message(event: dict[str, Any]) -> tuple[LogLevel, str, str]:
    category = str(event.get("category", "?"))
    event_type = str(event.get("type", "?"))
    data = event.get("data") if isinstance(event.get("data"), dict) else {}

    if category == "control" and event_type == "connected":
        status = data.get("status") if isinstance(data.get("status"), dict) else {}
        hw = status.get("hardware", "?")
        state = status.get("control_state", "?")
        return "info", "control", f"connected - hardware={hw} control={state}"
    if category == "command" and event_type == "held":
        return "info", "command", f"hold - {data.get('action', '?')}"
    if category == "command" and event_type == "released":
        return (
            "info",
            "command",
            f"release - {data.get('action', '?')} {int(data.get('duration_ms', 0))}ms",
        )
    if category == "command" and event_type == "pulse":
        return (
            "info",
            "command",
            f"pulse - {data.get('action', '?')} {int(data.get('duration_ms', 0))}ms",
        )
    if category == "command" and event_type == "rejected":
        reason = data.get("reason", "?")
        message = data.get("message", "")
        return "warning", "command", f"command rejected - {reason}: {message}"
    if category == "control" and event_type == "state":
        state = data.get("control_state", "?")
        mode = data.get("operating_mode", "?")
        return "info", "control", f"control - state={state} mode={mode}"
    if category == "bus" and event_type == "snapshot":
        adc1 = bool(data.get("key_adc1_active"))
        led = bool(data.get("key_led_active"))
        return "info", "bus", f"signals - adc1_active={adc1} key_led_active={led}"

    return "info", category, f"{category}/{event_type}"


@dataclass
class LiveLogService:
    """Bounded backend log history with websocket replay support."""

    ws_hub: WsHub
    max_entries: int = 220
    _entries: deque[WsEventV1] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._entries = deque(maxlen=self.max_entries)

    @property
    def entries(self) -> tuple[WsEventV1, ...]:
        return tuple(self._entries)

    def record(
        self,
        *,
        level: LogLevel,
        source: str,
        message: str,
        ts: str | None = None,
    ) -> WsEventV1:
        event = ws_log_entry(
            level=level,
            source=source,
            message=message,
            ts=ts or utc_iso(),
        )
        self._entries.append(event)
        return event

    def record_event(self, event: dict[str, Any]) -> WsEventV1 | None:
        if event.get("category") == "log":
            return None
        level, source, message = _event_message(event)
        ts = event.get("ts") if isinstance(event.get("ts"), str) else None
        return self.record(level=level, source=source, message=message, ts=ts)

    async def publish(self, *, level: LogLevel, source: str, message: str) -> WsEventV1:
        event = self.record(level=level, source=source, message=message)
        await self.ws_hub.broadcast_json(event.model_dump(mode="json"))
        return event

    async def replay_to(self, ws: WebSocket) -> None:
        for entry in self.entries:
            await ws.send_json(entry.model_dump(mode="json"))
