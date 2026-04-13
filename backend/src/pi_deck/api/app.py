"""ASGI application: health route and static UI (served until the Vite frontend exists)."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)


def _static_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(
        title="pi-deck",
        version="0.1.0",
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )

    @app.get("/health")
    def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    static = _static_dir()
    if not static.is_dir():
        logger.warning("static directory missing at %s", static)
    else:
        app.mount("/", StaticFiles(directory=str(static), html=True), name="static")

    return app
