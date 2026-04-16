"""Recording capture, storage, and replay orchestration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from pi_deck.models.recordings import (
    DelayEvent,
    PressEvent,
    RecordingFile,
    RecordingLibraryOut,
    RecordingRejectedReason,
    RecordingStateOut,
    RecordingSummary,
    WaitDdcEvent,
    WaitLedEvent,
    WaitLedMatch,
    ws_recording_library,
    ws_recording_state,
)
from pi_deck.models.schemas import SignalSnapshot
from pi_deck.services.deck_control import DeckControlService
from pi_deck.services.hardware_facade import DeckHardwareFacade
from pi_deck.services.live_log import LiveLogService
from pi_deck.services.ws_hub import WsHub
from pi_deck.storage.recordings import RecordingStore

logger = logging.getLogger(__name__)

_JOG_ACTIONS = ("up", "down", "left", "right", "center")
_MIN_DELAY_MS = 25


class RecordingServiceError(RuntimeError):
    def __init__(self, reason: RecordingRejectedReason, message: str, *, status_code: int = 409) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message
        self.status_code = status_code


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _recording_name_for_now(now: datetime) -> str:
    return now.strftime("recording_%Y-%m-%d_%H-%M-%S")


def _signals_to_held(signals: SignalSnapshot) -> dict[str, bool]:
    held = {action: False for action in _JOG_ACTIONS}
    held["center"] = signals.key_adc1_active
    direction = signals.key_adc2_direction
    if direction in ("up", "down", "left", "right"):
        held[direction] = True
    return held


def _snapshot_from_payload(payload: dict[str, Any]) -> SignalSnapshot:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    direction = data.get("key_adc2_direction")
    return SignalSnapshot(
        key_adc1_active=bool(data.get("key_adc1_active")),
        key_led_active=bool(data.get("key_led_active")),
        key_adc2_direction=direction if direction in ("up", "down", "left", "right") else None,
    )


@dataclass
class _RecordingSession:
    started_at: datetime
    base_name: str
    start_snapshot: SignalSnapshot
    prev_snapshot: SignalSnapshot
    last_semantic_at: datetime
    pending_presses: dict[str, datetime] = field(default_factory=dict)
    events: list[object] = field(default_factory=list)


class RecordingService:
    def __init__(
        self,
        *,
        store: RecordingStore,
        ws_hub: WsHub,
        live_log: LiveLogService,
        deck: DeckControlService,
        hardware: DeckHardwareFacade,
    ) -> None:
        self._store = store
        self._ws_hub = ws_hub
        self._live_log = live_log
        self._deck = deck
        self._hardware = hardware
        self._session: _RecordingSession | None = None
        self._replay_task: asyncio.Task[None] | None = None
        self._replay_stop = asyncio.Event()
        self._replaying_id: str | None = None
        self._last_error: str | None = None

    def state(self) -> RecordingStateOut:
        if self._session is not None:
            return RecordingStateOut(
                mode="recording",
                recording_started_at=self._session.started_at.isoformat().replace("+00:00", "Z"),
                active_name=self._session.base_name,
                event_count=len(self._session.events),
                last_error=self._last_error,
            )
        if self._replay_task is not None and not self._replay_task.done():
            return RecordingStateOut(
                mode="replaying",
                replaying_id=self._replaying_id,
                active_name=self._replaying_id,
                last_error=self._last_error,
            )
        return RecordingStateOut(mode="idle", last_error=self._last_error)

    def library(self) -> RecordingLibraryOut:
        return self._store.list()

    async def _broadcast(self, event: object) -> None:
        payload = event.model_dump(mode="json") if hasattr(event, "model_dump") else event
        if isinstance(payload, dict) and self._ws_hub.client_count > 0:
            await self._ws_hub.broadcast_json(payload)

    async def _broadcast_state(self) -> None:
        await self._broadcast(ws_recording_state(self.state()))

    async def _broadcast_library(self) -> None:
        await self._broadcast(ws_recording_library(self.library()))

    async def websocket_sync(self, ws) -> None:
        await ws.send_json(ws_recording_state(self.state()).model_dump(mode="json"))
        await ws.send_json(ws_recording_library(self.library()).model_dump(mode="json"))

    async def start_recording(self) -> RecordingStateOut:
        self._ensure_idle()
        now = datetime.now().astimezone()
        current = self._hardware.read_bus_snapshot()
        base_name = _recording_name_for_now(now)
        self._session = _RecordingSession(
            started_at=now,
            base_name=base_name,
            start_snapshot=current.model_copy(deep=True),
            prev_snapshot=current,
            last_semantic_at=now,
        )
        self._last_error = None
        await self._live_log.publish(level="info", source="recording", message=f"start - {base_name}")
        await self._broadcast_state()
        return self.state()

    async def stop_recording(self) -> RecordingSummary:
        session = self._session
        if session is None:
            raise RecordingServiceError(
                RecordingRejectedReason.NOT_RECORDING,
                "No active recording",
            )
        self._session = None
        stop_at = datetime.now().astimezone()
        for action, started_at in list(session.pending_presses.items()):
            self._finalize_press(session, action, started_at, stop_at)
        recording = RecordingFile(
            name=session.base_name,
            created_at=session.started_at.isoformat().replace("+00:00", "Z"),
            updated_at=stop_at.isoformat().replace("+00:00", "Z"),
            duration_ms=max(0, int((stop_at - session.started_at).total_seconds() * 1000)),
            start_state=session.start_snapshot.model_dump(mode="json"),
            end_state=self._hardware.read_bus_snapshot().model_dump(mode="json"),
            events=session.events,
        )
        summary = self._store.write_new(recording, preferred_stem=session.base_name)
        await self._live_log.publish(level="info", source="recording", message=f"saved - {summary.filename}")
        await self._broadcast_state()
        await self._broadcast_library()
        return summary

    async def rename_recording(self, recording_id: str, new_name: str) -> RecordingSummary:
        try:
            summary = self._store.rename(recording_id, new_name=new_name)
        except FileNotFoundError as exc:
            raise RecordingServiceError(
                RecordingRejectedReason.NOT_FOUND,
                f"Recording not found: {recording_id}",
                status_code=404,
            ) from exc
        await self._broadcast_library()
        return summary

    async def delete_recording(self, recording_id: str) -> None:
        try:
            self._store.delete(recording_id)
        except FileNotFoundError as exc:
            raise RecordingServiceError(
                RecordingRejectedReason.NOT_FOUND,
                f"Recording not found: {recording_id}",
                status_code=404,
            ) from exc
        await self._broadcast_library()

    async def upload_recording(self, filename: str, payload: bytes) -> RecordingSummary:
        try:
            recording = RecordingFile.model_validate_json(payload)
        except Exception as exc:
            raise RecordingServiceError(
                RecordingRejectedReason.INVALID_RECORDING,
                "Invalid recording file",
                status_code=400,
            ) from exc
        preferred = recording.name if recording.name.strip() else filename.removesuffix(".json")
        summary = self._store.write_new(recording, preferred_stem=preferred)
        await self._broadcast_library()
        return summary

    async def play_recording(self, recording_id: str) -> RecordingStateOut:
        self._ensure_idle()
        try:
            recording = self._store.read(recording_id)
        except FileNotFoundError as exc:
            raise RecordingServiceError(
                RecordingRejectedReason.NOT_FOUND,
                f"Recording not found: {recording_id}",
                status_code=404,
            ) from exc
        self._last_error = None
        self._replaying_id = recording_id
        self._replay_stop = asyncio.Event()
        self._replay_task = asyncio.create_task(self._run_playback(recording_id, recording))
        await self._broadcast_state()
        return self.state()

    async def stop_playback(self) -> RecordingStateOut:
        task = self._replay_task
        if task is None or task.done():
            raise RecordingServiceError(
                RecordingRejectedReason.NOT_REPLAYING,
                "No active replay",
            )
        self._replay_stop.set()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await self._broadcast_state()
        return self.state()

    async def observe_event(self, payload: dict[str, Any]) -> None:
        session = self._session
        if session is None:
            return
        category = payload.get("category")
        event_type = payload.get("type")
        if category == "bus" and event_type == "snapshot":
            self._handle_snapshot(session, payload)
            await self._broadcast_state()
        elif category == "bus" and event_type == "led_changed":
            self._handle_led_changed(session, payload)
            await self._broadcast_state()

    def download_path(self, recording_id: str) -> Path:
        try:
            return self._store.path_for_download(recording_id)
        except FileNotFoundError as exc:
            raise RecordingServiceError(
                RecordingRejectedReason.NOT_FOUND,
                f"Recording not found: {recording_id}",
                status_code=404,
            ) from exc

    def _ensure_idle(self) -> None:
        if self._session is not None or (
            self._replay_task is not None and not self._replay_task.done()
        ):
            raise RecordingServiceError(
                RecordingRejectedReason.BUSY,
                "Recording or replay already active",
            )

    def _append_delay_if_needed(self, session: _RecordingSession, at: datetime) -> None:
        elapsed_ms = max(0, int((at - session.last_semantic_at).total_seconds() * 1000))
        if elapsed_ms >= _MIN_DELAY_MS:
            session.events.append(DelayEvent(duration_ms=elapsed_ms))

    def _handle_snapshot(self, session: _RecordingSession, payload: dict[str, Any]) -> None:
        at = _parse_ts(str(payload.get("ts")))
        snap = _snapshot_from_payload(payload)
        prev_held = _signals_to_held(session.prev_snapshot)
        next_held = _signals_to_held(snap)
        for action in _JOG_ACTIONS:
            if prev_held[action] and not next_held[action]:
                started_at = session.pending_presses.pop(action, at)
                self._finalize_press(session, action, started_at, at)
        for action in _JOG_ACTIONS:
            if not prev_held[action] and next_held[action]:
                session.pending_presses[action] = at
        session.prev_snapshot = snap

    def _handle_led_changed(self, session: _RecordingSession, payload: dict[str, Any]) -> None:
        at = _parse_ts(str(payload.get("ts")))
        elapsed_ms = max(0, int((at - session.last_semantic_at).total_seconds() * 1000))
        timeout_ms = min(60_000, max(1_000, elapsed_ms + 800))
        active = bool((payload.get("data") or {}).get("key_led_active"))
        session.events.append(
            WaitLedEvent(
                match=WaitLedMatch(active=active),
                poll_interval_ms=50,
                timeout_ms=timeout_ms,
            )
        )
        session.last_semantic_at = at

    def _finalize_press(
        self,
        session: _RecordingSession,
        action: str,
        started_at: datetime,
        released_at: datetime,
    ) -> None:
        self._append_delay_if_needed(session, started_at)
        duration_ms = max(1, int((released_at - started_at).total_seconds() * 1000))
        session.events.append(PressEvent(action=action, duration_ms=duration_ms))
        session.last_semantic_at = released_at

    async def _run_playback(self, recording_id: str, recording: RecordingFile) -> None:
        try:
            await self._live_log.publish(
                level="info",
                source="recording",
                message=f"play - {recording.name}",
            )
            for event in recording.events:
                if self._replay_stop.is_set():
                    break
                if isinstance(event, DelayEvent):
                    await self._sleep_or_stop(event.duration_ms / 1000.0)
                    continue
                if isinstance(event, PressEvent):
                    err = await self._deck.jog_press(event.action, event.duration_ms)
                    if err is not None:
                        raise RuntimeError(f"hardware rejected press: {err.value}")
                    continue
                if isinstance(event, WaitLedEvent):
                    await self._wait_led(event)
                    continue
                if isinstance(event, WaitDdcEvent):
                    raise RecordingServiceError(
                        RecordingRejectedReason.DDC_UNAVAILABLE,
                        "wait_ddc is not available on this hardware path yet",
                    )
            if self._replay_stop.is_set():
                await self._live_log.publish(
                    level="info",
                    source="recording",
                    message=f"play stopped - {recording.name}",
                )
            else:
                await self._live_log.publish(
                    level="info",
                    source="recording",
                    message=f"play complete - {recording.name}",
                )
        except asyncio.CancelledError:
            raise
        except RecordingServiceError as exc:
            self._last_error = exc.message
            await self._live_log.publish(level="error", source="recording", message=exc.message)
        except Exception as exc:
            self._last_error = str(exc)
            logger.exception("recording playback failed")
            await self._live_log.publish(
                level="error",
                source="recording",
                message=f"play failed - {exc}",
            )
        finally:
            self._replay_task = None
            self._replaying_id = None
            self._replay_stop = asyncio.Event()
            await self._broadcast_state()

    async def _sleep_or_stop(self, seconds: float) -> None:
        if seconds <= 0:
            return
        end_at = asyncio.get_running_loop().time() + seconds
        while not self._replay_stop.is_set():
            remaining = end_at - asyncio.get_running_loop().time()
            if remaining <= 0:
                return
            await asyncio.sleep(min(remaining, 0.05))

    async def _wait_led(self, event: WaitLedEvent) -> None:
        deadline = asyncio.get_running_loop().time() + (event.timeout_ms / 1000.0)
        while not self._replay_stop.is_set():
            snap = self._hardware.read_bus_snapshot()
            if snap.key_led_active == event.match.active:
                return
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise RuntimeError(f"LED wait timed out for active={event.match.active}")
            await asyncio.sleep(min(remaining, event.poll_interval_ms / 1000.0))
