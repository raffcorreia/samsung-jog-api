"""Thread-safe coalescing for GPIO/ADS callbacks that schedule asyncio observation work.

Multiple edges can arrive while ``_observe_signals`` runs; we collapse those into at most one
extra observation round instead of queueing unbounded ``run_coroutine_threadsafe`` futures.
"""

from __future__ import annotations

import threading


class CoalesceGate:
    """Single worker loop with a pending bit (similar to Linux netif RX softirq coalescing)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._worker_running = False
        self._pending_again = False

    def request_from_thread(self) -> bool:
        """Called from a GPIO/ADS thread. Return True if this call must start the async worker."""
        with self._lock:
            if self._worker_running:
                self._pending_again = True
                return False
            self._worker_running = True
            return True

    def should_continue_after_round(self) -> bool:
        """Called from the async worker after one ``_observe_signals`` completes."""
        with self._lock:
            if self._pending_again:
                self._pending_again = False
                return True
            self._worker_running = False
            return False

    def reset(self) -> None:
        """Clear state (e.g. after worker exception or service stop)."""
        with self._lock:
            self._worker_running = False
            self._pending_again = False
