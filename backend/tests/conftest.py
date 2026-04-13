"""Pytest defaults: mock GPIO unless a test overrides ``PI_DECK_HARDWARE``."""

from __future__ import annotations

import os

os.environ.setdefault("PI_DECK_HARDWARE", "mock")
