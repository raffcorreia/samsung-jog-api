"""System-level controls: Pi shutdown and restart.

The shutdown command requires ``sudo`` because the ``pi-deck`` systemd unit
runs as a non-root user.  The Pi image must have a sudoers rule that allows
the service user to run ``shutdown`` without a password:

    pi-deck ALL=(ALL) NOPASSWD: /sbin/shutdown

On mock hardware the call is logged only — no actual shutdown or restart is issued.
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


class SystemService:
    """Pi shutdown helper with live/mock behaviour."""

    def __init__(self, hw_mode: str) -> None:
        self._live = hw_mode == "live"

    async def shutdown(self) -> None:
        """Initiate a graceful Pi shutdown (async so the HTTP response can be flushed first)."""
        if not self._live:
            logger.info("system: shutdown requested (mock — no-op)")
            return
        logger.info("system: shutdown initiated via sudo shutdown -h now")
        await asyncio.sleep(0.3)
        proc = await asyncio.create_subprocess_exec(
            "sudo", "shutdown", "-h", "now",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode and proc.returncode != 0:
            logger.error(
                "system: shutdown command returned %d: %s",
                proc.returncode,
                stderr.decode(errors="replace").strip(),
            )

    async def restart(self) -> None:
        """Initiate a graceful Pi restart (async so the HTTP response can be flushed first)."""
        if not self._live:
            logger.info("system: restart requested (mock — no-op)")
            return
        logger.info("system: restart initiated via sudo shutdown -r now")
        await asyncio.sleep(0.3)
        proc = await asyncio.create_subprocess_exec(
            "sudo", "shutdown", "-r", "now",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode and proc.returncode != 0:
            logger.error(
                "system: restart command returned %d: %s",
                proc.returncode,
                stderr.decode(errors="replace").strip(),
            )
