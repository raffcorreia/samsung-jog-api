"""REST and websocket routes for the local API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

import asyncio

from pi_deck.api.deps import get_deck, get_display, get_recordings, get_system
from pi_deck.models.recordings import (
    RecordingLibraryOut,
    RecordingRejectedOut,
    RecordingRenameIn,
    RecordingStateOut,
)
from pi_deck.models.schemas import (
    CommandRejectedOut,
    CommandRejectedReason,
    DisplayBrightnessIn,
    DisplayBrightnessOut,
    DisplayPowerIn,
    DisplayPowerOut,
    JogHoldIn,
    JogPressIn,
    JogReleaseIn,
    LogIn,
    NetworkInfoOut,
    NetworkInterfaceOut,
    OperatingModeIn,
    StatusOut,
    SystemShutdownOut,
    ws_status_connected,
)
from pi_deck.services.display_service import DisplayService
from pi_deck.services.system_service import SystemService
from pi_deck.services.deck_control import DeckControlService
from pi_deck.services.live_log import LiveLogService
from pi_deck.services.recordings import RecordingService, RecordingServiceError
from pi_deck.services.ws_hub import WsHub

api_v1 = APIRouter(prefix="/api/v1")


def _rejection_message(reason: CommandRejectedReason) -> str:
    return {
        CommandRejectedReason.CONCURRENT_COMMAND: "Another jog command is already running",
        CommandRejectedReason.HARDWARE_ERROR: "Hardware error while executing jog command",
        CommandRejectedReason.INVALID_DURATION: "Invalid duration for jog command",
        CommandRejectedReason.ACTIVE_HOLDS: "Active jog holds must be released before timed pulse",
    }[reason]


def _recording_rejection_response(exc: RecordingServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=RecordingRejectedOut(reason=exc.reason, message=exc.message).model_dump(mode="json"),
    )


@api_v1.get("/status", response_model=StatusOut)
def api_status(deck: DeckControlService = Depends(get_deck)) -> StatusOut:
    return deck.status()


@api_v1.post("/mode", response_model=StatusOut)
async def api_set_mode(
    body: OperatingModeIn,
    deck: DeckControlService = Depends(get_deck),
) -> StatusOut:
    deck.set_operating_mode(body.mode)
    return deck.status()


@api_v1.post("/jog/press")
async def api_jog_press(
    body: JogPressIn,
    deck: DeckControlService = Depends(get_deck),
) -> JSONResponse:
    result = await deck.jog_press(body.action, body.duration_ms)
    if result is None:
        return JSONResponse({"ok": True})
    return JSONResponse(
        status_code=409,
        content=CommandRejectedOut(
            reason=result,
            message=_rejection_message(result),
        ).model_dump(mode="json"),
    )


@api_v1.post("/jog/hold")
async def api_jog_hold(
    body: JogHoldIn,
    deck: DeckControlService = Depends(get_deck),
) -> JSONResponse:
    err = await deck.jog_hold(body.action)
    if err is None:
        return JSONResponse({"ok": True})
    return JSONResponse(
        status_code=409,
        content=CommandRejectedOut(
            reason=err,
            message=_rejection_message(err),
        ).model_dump(mode="json"),
    )


@api_v1.post("/jog/release")
async def api_jog_release(
    body: JogReleaseIn,
    deck: DeckControlService = Depends(get_deck),
) -> JSONResponse:
    err, duration_ms = await deck.jog_release(body.action)
    if err is not None:
        return JSONResponse(
            status_code=409,
            content=CommandRejectedOut(
                reason=err,
                message=_rejection_message(err),
            ).model_dump(mode="json"),
        )
    return JSONResponse({"ok": True, "duration_ms": duration_ms})


@api_v1.post("/log")
async def api_log_entry_from_request(
    body: LogIn,
    deck: DeckControlService = Depends(get_deck),
) -> JSONResponse:
    live_log: LiveLogService = deck.live_log
    await live_log.publish(level=body.level, source=body.source, message=body.message)
    return JSONResponse({"ok": True})


@api_v1.delete("/log")
async def api_log_clear(deck: DeckControlService = Depends(get_deck)) -> JSONResponse:
    await deck.live_log.clear()
    return JSONResponse({"ok": True})


@api_v1.get("/recordings", response_model=RecordingLibraryOut)
def api_recordings_library(
    recordings: RecordingService = Depends(get_recordings),
) -> RecordingLibraryOut:
    return recordings.library()


@api_v1.get("/recordings/state", response_model=RecordingStateOut)
def api_recordings_state(
    recordings: RecordingService = Depends(get_recordings),
) -> RecordingStateOut:
    return recordings.state()


@api_v1.post("/recordings/start", response_model=RecordingStateOut)
async def api_recordings_start(
    recordings: RecordingService = Depends(get_recordings),
):
    try:
        return await recordings.start_recording()
    except RecordingServiceError as exc:
        return _recording_rejection_response(exc)


@api_v1.post("/recordings/stop")
async def api_recordings_stop(
    recordings: RecordingService = Depends(get_recordings),
) -> JSONResponse:
    try:
        summary = await recordings.stop_recording()
    except RecordingServiceError as exc:
        return _recording_rejection_response(exc)
    return JSONResponse({"ok": True, "item": summary.model_dump(mode="json")})


@api_v1.post("/recordings/stop-playback", response_model=RecordingStateOut)
async def api_recordings_stop_playback(
    recordings: RecordingService = Depends(get_recordings),
):
    try:
        return await recordings.stop_playback()
    except RecordingServiceError as exc:
        return _recording_rejection_response(exc)


@api_v1.post("/recordings/{recording_id}/play", response_model=RecordingStateOut)
async def api_recordings_play(
    recording_id: str,
    recordings: RecordingService = Depends(get_recordings),
):
    try:
        return await recordings.play_recording(recording_id)
    except RecordingServiceError as exc:
        return _recording_rejection_response(exc)


@api_v1.patch("/recordings/{recording_id}")
async def api_recordings_rename(
    recording_id: str,
    body: RecordingRenameIn,
    recordings: RecordingService = Depends(get_recordings),
) -> JSONResponse:
    try:
        summary = await recordings.rename_recording(recording_id, body.name)
    except RecordingServiceError as exc:
        return _recording_rejection_response(exc)
    return JSONResponse({"ok": True, "item": summary.model_dump(mode="json")})


@api_v1.delete("/recordings/{recording_id}")
async def api_recordings_delete(
    recording_id: str,
    recordings: RecordingService = Depends(get_recordings),
) -> JSONResponse:
    try:
        await recordings.delete_recording(recording_id)
    except RecordingServiceError as exc:
        return _recording_rejection_response(exc)
    return JSONResponse({"ok": True})


@api_v1.get("/recordings/{recording_id}/download", response_model=None)
def api_recordings_download(
    recording_id: str,
    recordings: RecordingService = Depends(get_recordings),
):
    try:
        path = recordings.download_path(recording_id)
    except RecordingServiceError as exc:
        return _recording_rejection_response(exc)
    return FileResponse(path, media_type="application/json", filename=path.name)


@api_v1.get("/recordings/{recording_id}/content", response_model=None)
def api_recordings_content(
    recording_id: str,
    recordings: RecordingService = Depends(get_recordings),
):
    try:
        content = recordings.read_recording_text(recording_id)
    except RecordingServiceError as exc:
        return _recording_rejection_response(exc)
    return PlainTextResponse(content, media_type="application/json")


@api_v1.put("/recordings/{recording_id}/content")
async def api_recordings_replace_content(
    recording_id: str,
    request: Request,
    recordings: RecordingService = Depends(get_recordings),
) -> JSONResponse:
    try:
        payload = (await request.body()).decode("utf-8")
        summary = await recordings.update_recording_text(recording_id, payload)
    except UnicodeDecodeError:
        return _recording_rejection_response(
            RecordingServiceError(
                RecordingRejectedReason.INVALID_RECORDING,
                "Invalid recording file",
                status_code=400,
            )
        )
    except RecordingServiceError as exc:
        return _recording_rejection_response(exc)
    return JSONResponse({"ok": True, "item": summary.model_dump(mode="json")})


@api_v1.post("/recordings/upload")
async def api_recordings_upload(
    file: UploadFile = File(...),
    recordings: RecordingService = Depends(get_recordings),
) -> JSONResponse:
    try:
        payload = await file.read()
        summary = await recordings.upload_recording(file.filename or "recording.json", payload)
    except RecordingServiceError as exc:
        return _recording_rejection_response(exc)
    return JSONResponse({"ok": True, "item": summary.model_dump(mode="json")})


@api_v1.get("/display/brightness", response_model=DisplayBrightnessOut)
def api_display_brightness_get(display: DisplayService = Depends(get_display)) -> DisplayBrightnessOut:
    from pi_deck.hardware.display_power import BRIGHTNESS_RAW_MAX

    return DisplayBrightnessOut(
        brightness_pct=display.get_brightness_pct(),
        brightness_raw=display.get_brightness_raw(),
        max_raw=BRIGHTNESS_RAW_MAX,
    )


@api_v1.put("/display/brightness", response_model=DisplayBrightnessOut)
def api_display_brightness_set(
    body: DisplayBrightnessIn,
    display: DisplayService = Depends(get_display),
) -> DisplayBrightnessOut:
    from pi_deck.hardware.display_power import BRIGHTNESS_RAW_MAX

    display.set_brightness_pct(body.brightness_pct)
    return DisplayBrightnessOut(
        brightness_pct=display.get_brightness_pct(),
        brightness_raw=display.get_brightness_raw(),
        max_raw=BRIGHTNESS_RAW_MAX,
    )


@api_v1.get("/display/power", response_model=DisplayPowerOut)
def api_display_power_get(display: DisplayService = Depends(get_display)) -> DisplayPowerOut:
    return DisplayPowerOut(on=display.is_on, brightness_pct=display.get_brightness_pct())


@api_v1.post("/display/power", response_model=DisplayPowerOut)
def api_display_power_set(
    body: DisplayPowerIn,
    display: DisplayService = Depends(get_display),
) -> DisplayPowerOut:
    if body.on:
        display.power_on()
    else:
        display.power_off()
    return DisplayPowerOut(on=display.is_on, brightness_pct=display.get_brightness_pct())


@api_v1.get("/system/network", response_model=NetworkInfoOut)
def api_system_network() -> NetworkInfoOut:
    import socket
    import subprocess
    from pathlib import Path

    hostname = socket.gethostname()
    net_root = Path("/sys/class/net")
    interfaces: list[NetworkInterfaceOut] = []

    if net_root.exists():
        for iface_path in sorted(net_root.iterdir()):
            name = iface_path.name
            if name == "lo":
                continue
            try:
                operstate = (iface_path / "operstate").read_text().strip()
                connected = operstate == "up"
            except OSError:
                connected = False

            ip: str | None = None
            try:
                result = subprocess.run(
                    ["ip", "-4", "-o", "addr", "show", name],
                    capture_output=True,
                    timeout=3,
                )
                for line in result.stdout.decode(errors="replace").splitlines():
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "inet" and i + 1 < len(parts):
                            ip = parts[i + 1].split("/")[0]
                            break
                    if ip:
                        break
            except Exception:
                pass

            interfaces.append(NetworkInterfaceOut(name=name, connected=connected, ip=ip))

    return NetworkInfoOut(hostname=hostname, interfaces=interfaces)


@api_v1.post("/system/shutdown", response_model=SystemShutdownOut)
async def api_system_shutdown(system: SystemService = Depends(get_system)) -> SystemShutdownOut:
    asyncio.create_task(system.shutdown())
    return SystemShutdownOut(ok=True, message="Shutdown initiated")


@api_v1.post("/system/restart", response_model=SystemShutdownOut)
async def api_system_restart(system: SystemService = Depends(get_system)) -> SystemShutdownOut:
    asyncio.create_task(system.restart())
    return SystemShutdownOut(ok=True, message="Restart initiated")


async def websocket_events(ws: WebSocket) -> None:
    deck: DeckControlService = ws.app.state.deck
    hub: WsHub = ws.app.state.ws_hub
    live_log: LiveLogService = ws.app.state.live_log
    recordings: RecordingService = ws.app.state.recordings
    is_deck = ws.client is not None and ws.client.host in ("127.0.0.1", "::1")
    await hub.connect(ws, is_deck=is_deck)
    try:
        hello = ws_status_connected(status=deck.status())
        await ws.send_json(hello.model_dump(mode="json"))
        await live_log.replay_to(ws)
        await recordings.websocket_sync(ws)
        connected_log = live_log.record_event(hello.model_dump(mode="json"))
        if connected_log is not None:
            await hub.broadcast_json(connected_log.model_dump(mode="json"))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(ws)
