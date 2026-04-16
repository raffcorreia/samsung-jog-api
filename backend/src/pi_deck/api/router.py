"""REST and websocket routes for Phase 10 local API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from pi_deck.api.deps import get_deck
from pi_deck.models.schemas import (
    CommandRejectedOut,
    CommandRejectedReason,
    JogHoldIn,
    JogPressIn,
    JogReleaseIn,
    LogIn,
    OperatingModeIn,
    StatusOut,
    ws_status_connected,
)
from pi_deck.services.deck_control import DeckControlService
from pi_deck.services.live_log import LiveLogService
from pi_deck.services.ws_hub import WsHub

api_v1 = APIRouter(prefix="/api/v1")


def _rejection_message(reason: CommandRejectedReason) -> str:
    return {
        CommandRejectedReason.CONCURRENT_COMMAND: "Another jog command is already running",
        CommandRejectedReason.HARDWARE_ERROR: "Hardware error while executing jog command",
        CommandRejectedReason.INVALID_DURATION: "Invalid duration for jog command",
        CommandRejectedReason.ACTIVE_HOLDS: "Active jog holds must be released before timed pulse",
    }[reason]


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


async def websocket_events(ws: WebSocket) -> None:
    deck: DeckControlService = ws.app.state.deck
    hub: WsHub = ws.app.state.ws_hub
    live_log: LiveLogService = ws.app.state.live_log
    await hub.connect(ws)
    try:
        hello = ws_status_connected(status=deck.status())
        await ws.send_json(hello.model_dump(mode="json"))
        await live_log.replay_to(ws)
        connected_log = live_log.record_event(hello.model_dump(mode="json"))
        if connected_log is not None:
            await hub.broadcast_json(connected_log.model_dump(mode="json"))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(ws)
