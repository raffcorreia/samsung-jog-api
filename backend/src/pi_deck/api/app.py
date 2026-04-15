"""ASGI application: health, Phase 10 API, websocket, static UI."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from pi_deck import __version__
from pi_deck.api.router import api_v1, websocket_events
from pi_deck.services.deck_control import DeckControlService
from pi_deck.services.hardware_facade import build_hardware
from pi_deck.services.ws_hub import WsHub

# Path written by scripts/deploy.sh on each deployment.
_DEPLOY_COUNTER_FILE = Path.home() / ".pi-deck-deploy"


def _read_deploy_counter() -> int:
    """Return the persistent deploy counter, or 0 if absent / unreadable."""
    try:
        return int(_DEPLOY_COUNTER_FILE.read_text().strip())
    except Exception:
        return 0


def _build_version() -> str:
    """Return ``__version__`` decorated with the deploy counter when present."""
    n = _read_deploy_counter()
    return f"{__version__}+r{n}" if n > 0 else __version__

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
    hw = build_hardware()
    version = _build_version()
    deck = DeckControlService(hardware=hw, ws_hub=hub, version=version)
    app.state.ws_hub = hub
    app.state.deck = deck
    app.state.hw = hw
    logger.info("pi-deck hardware mode: %s  version: %s", hw.kind, version)
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
