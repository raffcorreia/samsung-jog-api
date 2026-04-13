"""ASGI application: health, Phase 10 API, websocket, static UI."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from pi_deck import __version__
from pi_deck.api.router import api_v1, websocket_events
from pi_deck.services.deck_control import DeckControlService
from pi_deck.services.hardware_facade import build_hardware
from pi_deck.services.ws_hub import WsHub

logger = logging.getLogger(__name__)


def _static_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    hub = WsHub()
    hw = build_hardware()
    deck = DeckControlService(hardware=hw, ws_hub=hub, version=__version__)
    app.state.ws_hub = hub
    app.state.deck = deck
    app.state.hw = hw
    logger.info("pi-deck hardware mode: %s", hw.kind)
    yield
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
