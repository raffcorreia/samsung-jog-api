"""File logging with daily rotation and long retention (see docs/design/solution-overview.md)."""

from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path


def default_log_dir() -> Path:
    raw = os.environ.get("PI_DECK_LOG_DIR", "").strip()
    if raw and not raw.startswith("%"):
        return Path(raw).expanduser()
    return Path.home() / ".local" / "share" / "pi-deck" / "logs"


def setup_logging(log_dir: Path | None = None) -> Path:
    """Configure root logger: daily rotated file plus stderr (for systemd journal)."""
    root = logging.getLogger()
    if root.handlers:
        return log_dir or default_log_dir()

    resolved = (log_dir or default_log_dir()).resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    log_path = resolved / "pi-deck.log"

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_path,
        when="midnight",
        interval=1,
        backupCount=93,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    file_handler.suffix = "%Y-%m-%d"

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)

    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)

    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)

    return resolved
