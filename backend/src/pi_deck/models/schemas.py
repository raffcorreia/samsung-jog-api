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

    CONCURRENT_COMMAND = "concurrent_command"
    HARDWARE_ERROR = "hardware_error"
    INVALID_DURATION = "invalid_duration"
    ACTIVE_HOLDS = "active_holds"


class JogPressIn(BaseModel):
    """Legacy: one timed assertion (duration known up front). Prefer hold + release."""

    action: Literal["up", "down", "left", "right", "center"]
    duration_ms: int = Field(ge=1, le=60_000)


class JogHoldIn(BaseModel):
    """Assert a jog direction until ``POST /jog/release`` with the same ``action``."""

    action: Literal["up", "down", "left", "right", "center"]


class JogReleaseIn(BaseModel):
    """Release the hold for ``action`` (idempotent if nothing held)."""

    action: Literal["up", "down", "left", "right", "center"]


class OperatingModeIn(BaseModel):
    mode: OperatingMode


class LogIn(BaseModel):
    """UI-originated event to append to the backend-owned live log."""

    level: Literal["debug", "info", "warning", "error"] = "info"
    source: str = Field(min_length=1, max_length=40)
    message: str = Field(min_length=1, max_length=240)


class SignalSnapshot(BaseModel):
    """Observed front-panel / bus signals (best-effort; depends on hardware wiring).

    ``key_adc1_active`` is **not** an ADS1115 reading. It is the **digital** observation of the
    monitor ``KEY_ADC1`` line (center / enter on this product), after conditioning: ``True`` when
    center is physically asserted. On the current protoboard observation path that means the Pi GPIO
    is pulled **low** during press and remains **high** at idle.
    Direction keys are decoded from ``KEY_ADC2`` (ADS1115 AIN0 mV thresholds) on live hardware;
    mock hardware derives them from asserted drive lines for parity with observation.
    """

    key_adc1_active: bool
    key_led_active: bool
    key_adc2_direction: Literal["up", "down", "left", "right"] | None = None


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


def ws_command_held(*, action: str) -> WsEventV1:
    return WsEventV1(
        category="command",
        type="held",
        ts=utc_iso(),
        data={"action": action},
    )


def ws_command_released(*, action: str, duration_ms: int) -> WsEventV1:
    return WsEventV1(
        category="command",
        type="released",
        ts=utc_iso(),
        data={"action": action, "duration_ms": duration_ms},
    )


def ws_command_pulse(*, action: str, duration_ms: int) -> WsEventV1:
    return WsEventV1(
        category="command",
        type="pulse",
        ts=utc_iso(),
        data={"action": action, "duration_ms": duration_ms},
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
    data = {
        "key_adc1_active": signals.key_adc1_active,
        "key_led_active": signals.key_led_active,
        "key_adc2_direction": signals.key_adc2_direction,
    }
    return WsEventV1(
        category="bus",
        type="snapshot",
        ts=utc_iso(),
        data=data,
    )


def ws_bus_led_changed(*, active: bool) -> WsEventV1:
    return WsEventV1(
        category="bus",
        type="led_changed",
        ts=utc_iso(),
        data={"key_led_active": active},
    )


def ws_status_connected(*, status: StatusOut) -> WsEventV1:
    return WsEventV1(
        category="control",
        type="connected",
        ts=utc_iso(),
        data={"status": status.model_dump(mode="json")},
    )


def ws_log_entry(
    *,
    level: Literal["debug", "info", "warning", "error"],
    source: str,
    message: str,
    ts: str | None = None,
) -> WsEventV1:
    return WsEventV1(
        category="log",
        type="entry",
        ts=ts or utc_iso(),
        data={"level": level, "source": source, "message": message},
    )


def ws_log_cleared() -> WsEventV1:
    """Notify clients that the server-side live log buffer was wiped."""
    return WsEventV1(
        category="log",
        type="cleared",
        ts=utc_iso(),
        data={},
    )


# ── Phase 19: display brightness / power ──────────────────────────────────────

class DisplayBrightnessOut(BaseModel):
    """Current and capped brightness state (Phase 19)."""

    brightness_pct: int = Field(ge=0, le=100)
    brightness_raw: int = Field(ge=0, le=255)
    max_raw: int = Field(default=170)


class DisplayBrightnessIn(BaseModel):
    """Set display brightness by percentage."""

    brightness_pct: int = Field(ge=0, le=100)


class DisplayPowerOut(BaseModel):
    """Current display power state (Phase 19)."""

    on: bool
    brightness_pct: int = Field(ge=0, le=100)


class DisplayPowerIn(BaseModel):
    """Set display power state."""

    on: bool


class SystemShutdownOut(BaseModel):
    """Shutdown acknowledgement (Phase 19)."""

    ok: bool
    message: str
