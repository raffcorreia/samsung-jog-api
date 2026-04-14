"""API boundary types: requests, responses, websocket envelopes."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class OperatingMode(str, Enum):
    """User-facing monitor control strategy (see docs/design/solution-overview.md)."""

    JOG = "jog"
    DDC = "ddc"
    BLIND = "blind"


class ControlState(str, Enum):
    """Whether the deck is idle or executing a software-initiated command."""

    IDLE = "idle"
    COMMANDING = "commanding"


class CommandRejectedReason(str, Enum):
    """Stable machine-readable reasons for HTTP 409 / websocket rejection events."""

    BUS_BUSY = "bus_busy"
    CONCURRENT_COMMAND = "concurrent_command"
    HARDWARE_ERROR = "hardware_error"
    INVALID_DURATION = "invalid_duration"
    ACTIVE_HOLDS = "active_holds"
    UNKNOWN_HOLD_TOKEN = "unknown_hold_token"
    HOLD_LIMIT = "hold_limit"


class JogPressIn(BaseModel):
    """Legacy: one timed assertion (duration known up front). Prefer :class:`JogDownIn` + release."""

    action: Literal["up", "down", "left", "right", "center"]
    duration_ms: int = Field(ge=1, le=60_000)


class JogDownIn(BaseModel):
    """Start asserting a jog direction until matching ``POST /jog/up`` with ``hold_token``."""

    action: Literal["up", "down", "left", "right", "center"]


class JogUpIn(BaseModel):
    """Release the hold identified by ``hold_token`` from the corresponding ``/jog/down``."""

    hold_token: str = Field(min_length=8)


class OperatingModeIn(BaseModel):
    mode: OperatingMode


class SignalSnapshot(BaseModel):
    """Observed front-panel / bus signals (best-effort; depends on hardware wiring)."""

    key_adc1_active: bool
    key_led_active: bool


class StatusOut(BaseModel):
    """Aggregated deck status for REST and initial websocket handshake."""

    version: str
    hardware: Literal["live", "mock"]
    operating_mode: OperatingMode
    control_state: ControlState
    signals: SignalSnapshot


class CommandRejectedOut(BaseModel):
    error: Literal["command_rejected"] = "command_rejected"
    reason: CommandRejectedReason
    message: str


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class WsEventV1(BaseModel):
    """Versioned websocket envelope (category + type + payload)."""

    v: Literal[1] = 1
    category: Literal["command", "bus", "control", "log", "ddc", "recording"]
    type: str
    ts: str
    data: dict[str, Any] = Field(default_factory=dict)


def ws_command_accepted(*, action: str, duration_ms: int, hold_token: str) -> WsEventV1:
    return WsEventV1(
        category="command",
        type="accepted",
        ts=utc_iso(),
        data={"action": action, "duration_ms": duration_ms, "hold_token": hold_token},
    )


def ws_command_hold_started(*, action: str, hold_token: str) -> WsEventV1:
    return WsEventV1(
        category="command",
        type="hold_started",
        ts=utc_iso(),
        data={"action": action, "hold_token": hold_token},
    )


def ws_command_rejected(*, reason: CommandRejectedReason, message: str) -> WsEventV1:
    return WsEventV1(
        category="command",
        type="rejected",
        ts=utc_iso(),
        data={"reason": reason.value, "message": message},
    )


def ws_control_state(*, control_state: ControlState, operating_mode: OperatingMode) -> WsEventV1:
    return WsEventV1(
        category="control",
        type="state",
        ts=utc_iso(),
        data={"control_state": control_state.value, "operating_mode": operating_mode.value},
    )


def ws_bus_snapshot(*, signals: SignalSnapshot) -> WsEventV1:
    return WsEventV1(
        category="bus",
        type="snapshot",
        ts=utc_iso(),
        data={"key_adc1_active": signals.key_adc1_active, "key_led_active": signals.key_led_active},
    )


def ws_status_connected(*, status: StatusOut) -> WsEventV1:
    return WsEventV1(
        category="control",
        type="connected",
        ts=utc_iso(),
        data={"status": status.model_dump(mode="json")},
    )
