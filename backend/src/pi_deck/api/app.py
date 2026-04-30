"""ASGI application: health, Phase 10 API, websocket, static UI."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from pi_deck import __version__
from pi_deck.models.schemas import (
    ws_display_open_power_menu,
    ws_display_power_button_held,
    ws_display_power_button_released,
    ws_display_power_changed,
)
from pi_deck.api.router import api_v1, websocket_events
from pi_deck.hardware.display_button import DisplayButton
from pi_deck.hardware.display_power import build_display_power
from pi_deck.services.deck_control import DeckControlService
from pi_deck.services.display_service import DisplayService
from pi_deck.services.hardware_facade import build_hardware
from pi_deck.services.live_log import LiveLogService
from pi_deck.services.observation_bus import ObservationBusService
from pi_deck.services.recordings import RecordingService
from pi_deck.services.status_led_service import StatusLedService
from pi_deck.services.system_service import SystemService
from pi_deck.services.ws_hub import WsHub
from pi_deck.storage.recordings import RecordingStore


logger = logging.getLogger(__name__)


def _static_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "static"


class _StaticCacheControlMiddleware(BaseHTTPMiddleware):
    """Avoid stale index.html in kiosk / remote browsers (hashed assets change each build)."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path == "/" or path.endswith(".html"):
            # Kiosk browsers may still reuse a cached shell without Pragma/Expires.
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        elif "/assets/" in path:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    hub = WsHub()
    live_log = LiveLogService(hub)
    hw = build_hardware()
    version = __version__
    deck = DeckControlService(hardware=hw, ws_hub=hub, live_log=live_log, version=version)
    recordings = RecordingService(
        store=RecordingStore(),
        ws_hub=hub,
        live_log=live_log,
        deck=deck,
        hardware=hw,
    )
    observation = ObservationBusService(ws_hub=hub, live_log=live_log, hardware=hw)
    observation.add_listener(recordings.observe_event)
    observation.start(asyncio.get_running_loop())
    display_hw = build_display_power(hw.kind)
    display = DisplayService(display_hw)
    display.power_on()
    loop = asyncio.get_running_loop()
    status_led = StatusLedService(hw.kind)
    status_led.start()

    def _on_power_changed(on: bool) -> None:
        status_led.set_panel_on(on)
        asyncio.run_coroutine_threadsafe(
            hub.broadcast_json(ws_display_power_changed(on=on).model_dump(mode="json")),
            loop,
        )

    display.set_power_listener(_on_power_changed)

    hw.led_observer.set_state_callback(lambda active: status_led.set_monitor_led(active))

    def _btn_short_press() -> None:
        if not display.is_on:
            display.power_on()
        else:
            asyncio.run_coroutine_threadsafe(
                hub.broadcast_json(ws_display_open_power_menu().model_dump(mode="json")),
                loop,
            )

    def _btn_hold() -> None:
        if display.is_on:
            display.power_off()

    def _btn_press() -> None:
        status_led.set_button_held(True)
        asyncio.run_coroutine_threadsafe(
            hub.broadcast_json(ws_display_power_button_held().model_dump(mode="json")),
            loop,
        )

    def _btn_release() -> None:
        status_led.set_button_held(False)
        asyncio.run_coroutine_threadsafe(
            hub.broadcast_json(ws_display_power_button_released().model_dump(mode="json")),
            loop,
        )

    display_btn = DisplayButton()
    display_btn.set_callback(
        _btn_short_press,
        _btn_hold,
        on_press=_btn_press,
        on_release_any=_btn_release,
    )
    system = SystemService(hw.kind)
    app.state.ws_hub = hub
    app.state.live_log = live_log
    app.state.deck = deck
    app.state.hw = hw
    app.state.observation = observation
    app.state.recordings = recordings
    app.state.display = display
    app.state.display_btn = display_btn
    app.state.system = system
    app.state.status_led = status_led
    logger.info("pi-deck hardware mode: %s  version: %s", hw.kind, version)
    yield
    display_btn.close()
    status_led.stop()
    await observation.stop()
    hw.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="pi-deck",
        version=__version__,
        lifespan=lifespan,
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )
    app.add_middleware(_StaticCacheControlMiddleware)

    @app.get("/health")
    def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "version": __version__})

    app.include_router(api_v1)

    @app.websocket("/ws/events")
    async def deck_ws(ws: WebSocket) -> None:
        await websocket_events(ws)

    static = _static_dir()
    if not static.is_dir():
        logger.warning("static directory missing at %s", static)
    else:
        app.mount("/", StaticFiles(directory=str(static), html=True), name="static")

    return app
