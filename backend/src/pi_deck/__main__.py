"""`python -m pi_deck` — run the local HTTP server (Phase 9 appliance runtime)."""

from __future__ import annotations

import argparse
import logging
import os
import sys

import uvicorn

from pi_deck import __version__
from pi_deck.api.app import create_app
from pi_deck.logging_setup import setup_logging

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pi-deck",
        description="Samsung CJ791 control deck server",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--host",
        default=os.environ.get("PI_DECK_HOST", "127.0.0.1").strip() or "127.0.0.1",
        help="Bind address (default: PI_DECK_HOST or 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PI_DECK_PORT", "8756").strip() or "8756"),
        help="Listen port (default: PI_DECK_PORT or 8756)",
    )
    args = parser.parse_args()

    setup_logging()
    host = args.host
    port = args.port
    if port < 1 or port > 65535:
        print(f"Invalid port: {port}", file=sys.stderr)
        raise SystemExit(2)

    logger.info("Starting pi-deck on http://%s:%s", host, port)
    uvicorn.run(
        create_app(),
        host=host,
        port=port,
        log_config=None,
        access_log=True,
    )


if __name__ == "__main__":
    main()
