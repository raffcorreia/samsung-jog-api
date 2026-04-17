"""Domain models for recording capture, storage, and replay."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from pi_deck.models.schemas import WsEventV1, utc_iso

CURRENT_RECORDING_VERSION = "V1"
SUPPORTED_UPLOAD_RECORDING_VERSIONS = {CURRENT_RECORDING_VERSION}


class HoldEvent(BaseModel):
    type: Literal["hold"] = "hold"
    action: Literal["up", "down", "left", "right", "center"]


class ReleaseEvent(BaseModel):
    type: Literal["release"] = "release"
    action: Literal["up", "down", "left", "right", "center"]


class DelayEvent(BaseModel):
    type: Literal["delay"] = "delay"
    duration_ms: int = Field(ge=1, le=60_000)


class WaitLedMatch(BaseModel):
    active: bool


class LedEvent(BaseModel):
    type: Literal["led"] = "led"
    active: bool
    blocking: bool = False
    poll_interval_ms: int | None = Field(default=None, ge=10, le=1_000)
    timeout_ms: int | None = Field(default=None, ge=100, le=60_000)


class WaitLedEvent(BaseModel):
    type: Literal["wait_led"] = "wait_led"
    match: WaitLedMatch
    poll_interval_ms: int = Field(ge=10, le=1_000)
    timeout_ms: int = Field(ge=100, le=60_000)


class WaitDdcEvent(BaseModel):
    type: Literal["wait_ddc"] = "wait_ddc"
    match: dict[str, Any] = Field(default_factory=dict)
    poll_interval_ms: int = Field(ge=10, le=5_000)
    timeout_ms: int = Field(ge=100, le=60_000)


RecordingEvent = Annotated[
    HoldEvent | ReleaseEvent | DelayEvent | LedEvent | WaitLedEvent | WaitDdcEvent,
    Field(discriminator="type"),
]


def recording_duration_ms(events: list[RecordingEvent]) -> int:
    total = 0
    for event in events:
        if isinstance(event, DelayEvent):
            total += event.duration_ms
    return total


def is_supported_upload_version(version: str | int) -> bool:
    return version in SUPPORTED_UPLOAD_RECORDING_VERSIONS


class RecordingFile(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    version: Literal["V1", 1] = CURRENT_RECORDING_VERSION
    description: str | None = Field(default=None, max_length=240)
    source: Literal["observation"] = "observation"
    created_at: str
    updated_at: str
    # Always derived from events on load/save; the stored value is overwritten and never trusted.
    duration_ms: int = Field(ge=0, le=3_600_000)
    events: list[RecordingEvent] = Field(default_factory=list)


class RecordingSummary(BaseModel):
    id: str
    filename: str
    name: str
    created_at: str
    updated_at: str
    event_count: int
    duration_ms: int
    size_bytes: int


class RecordingLibraryOut(BaseModel):
    items: list[RecordingSummary] = Field(default_factory=list)


class RecordingStateOut(BaseModel):
    mode: Literal["idle", "recording", "replaying"] = "idle"
    recording_started_at: str | None = None
    replay_started_at: str | None = None
    replay_total_duration_ms: int | None = None
    replaying_id: str | None = None
    active_name: str | None = None
    event_count: int = 0
    last_error: str | None = None


class RecordingRenameIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class RecordingRejectedReason(str, Enum):
    BUSY = "busy"
    NOT_RECORDING = "not_recording"
    NOT_REPLAYING = "not_replaying"
    INVALID_RECORDING = "invalid_recording"
    NOT_FOUND = "not_found"
    DDC_UNAVAILABLE = "ddc_unavailable"


class RecordingRejectedOut(BaseModel):
    error: Literal["recording_rejected"] = "recording_rejected"
    reason: RecordingRejectedReason
    message: str


def ws_recording_state(state: RecordingStateOut) -> WsEventV1:
    return WsEventV1(
        category="recording",
        type="state",
        ts=utc_iso(),
        data=state.model_dump(mode="json"),
    )


def ws_recording_library(library: RecordingLibraryOut) -> WsEventV1:
    return WsEventV1(
        category="recording",
        type="library",
        ts=utc_iso(),
        data=library.model_dump(mode="json"),
    )
