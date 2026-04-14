"""REST and websocket routes for Phase 10 local API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from pi_deck.api.deps import get_deck
from pi_deck.models.schemas import (
    CommandRejectedOut,
    CommandRejectedReason,
    JogDownIn,
    JogPressIn,
    JogUpIn,
    OperatingModeIn,
    StatusOut,
    ws_status_connected,
)
from pi_deck.services.deck_control import DeckControlService
from pi_deck.services.ws_hub import WsHub

api_v1 = APIRouter(prefix="/api/v1")


def _rejection_message(reason: CommandRejectedReason) -> str:
    return {
        CommandRejectedReason.BUS_BUSY: "Monitor jog bus reports activity; command refused",
        CommandRejectedReason.CONCURRENT_COMMAND: "Another jog command is already running",
        CommandRejectedReason.HARDWARE_ERROR: "Hardware error while executing jog command",
        CommandRejectedReason.INVALID_DURATION: "Invalid duration for jog command",
        CommandRejectedReason.ACTIVE_HOLDS: "Active jog holds must be released before timed pulse",
        CommandRejectedReason.UNKNOWN_HOLD_TOKEN: "Unknown or expired hold_token",
        CommandRejectedReason.HOLD_LIMIT: "Too many simultaneous jog holds",
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


@api_v1.post("/jog/down")
async def api_jog_down(
    body: JogDownIn,
    deck: DeckControlService = Depends(get_deck),
) -> JSONResponse:
    err, hold_token = await deck.jog_down(body.action)
    if err is None and hold_token is not None:
        return JSONResponse({"ok": True, "hold_token": hold_token})
    assert err is not None
    return JSONResponse(
        status_code=409,
        content=CommandRejectedOut(
            reason=err,
            message=_rejection_message(err),
        ).model_dump(mode="json"),
    )


@api_v1.post("/jog/up")
async def api_jog_up(
    body: JogUpIn,
    deck: DeckControlService = Depends(get_deck),
) -> JSONResponse:
    err, duration_ms = await deck.jog_up(body.hold_token)
    if err is not None:
        return JSONResponse(
            status_code=409,
            content=CommandRejectedOut(
                reason=err,
                message=_rejection_message(err),
            ).model_dump(mode="json"),
        )
    return JSONResponse({"ok": True, "duration_ms": duration_ms})


async def websocket_events(ws: WebSocket) -> None:
    deck: DeckControlService = ws.app.state.deck
    hub: WsHub = ws.app.state.ws_hub
    await hub.connect(ws)
    try:
        hello = ws_status_connected(status=deck.status())
        await ws.send_json(hello.model_dump(mode="json"))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(ws)
