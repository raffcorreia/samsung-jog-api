"""Hardware telemetry → websocket ``bus.snapshot`` / ``bus/led_changed``.

Physical KEY_ADC1, KEY_ADC2 (decoded), and KEY_LED are emitted **only** from this service, driven
by ``read_bus_snapshot()`` on the hardware facade (poll + ADS ALERT edge on live hardware).

``DeckControlService`` sends commands to GPIO only; it does **not** emit jog ``command/*`` events.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import threading
from typing import cast

from pi_deck.models.schemas import SignalSnapshot, ws_bus_led_changed, ws_bus_snapshot
from pi_deck.services.hardware_facade import DeckHardwareFacade, LiveDeckHardware, MockDeckHardware
from pi_deck.services.live_log import LiveLogService
from pi_deck.services.ws_hub import WsHub

logger = logging.getLogger(__name__)

_POLL_INTERVAL_S = 0.025
_ALERT_EDGE_TIMEOUT_MS = 500


class ObservationBusService:
    """Background telemetry: ``bus/snapshot`` and ``bus/led_changed`` (live and mock)."""

    def __init__(
        self,
        *,
        ws_hub: WsHub,
        live_log: LiveLogService,
        hardware: object,
    ) -> None:
        self._ws_hub = ws_hub
        self._live_log = live_log
        self._hardware = hardware
        self._loop: asyncio.AbstractEventLoop | None = None
        self._poll_task: asyncio.Task[None] | None = None
        self._alert_thread: threading.Thread | None = None
        self._alert_stop = threading.Event()
        self._last_signals: SignalSnapshot | None = None
        self._led_prev: bool | None = None

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        hw = self._hardware
        kind = getattr(hw, "kind", None)

        if kind == "mock":
            mock_hw = cast(MockDeckHardware, hw)
            mock_hw.set_change_notifier(lambda: self._schedule_sample_from_notifier())
            self._poll_task = asyncio.create_task(
                self._mock_telemetry_loop(mock_hw),
                name="observation-mock-telemetry",
            )
            return

        if kind != "live":
            return
        live_hw = cast(LiveDeckHardware, hw)

        self._poll_task = asyncio.create_task(
            self._live_telemetry_loop(live_hw),
            name="observation-telemetry",
        )

        self._alert_stop.clear()
        self._alert_thread = threading.Thread(
            target=self._alert_gpio_loop,
            args=(live_hw,),
            name="ads-alert",
            daemon=True,
        )
        self._alert_thread.start()

    def _schedule_sample_from_notifier(self) -> None:
        loop = self._loop
        if loop is None:
            return
        mock_hw = cast(MockDeckHardware, self._hardware)

        async def _once() -> None:
            await self._observe_signals(mock_hw)

        fut = asyncio.run_coroutine_threadsafe(_once(), loop)

        def _log_done(f: asyncio.Future[None]) -> None:
            try:
                exc = f.exception()
            except asyncio.CancelledError:
                return
            if exc is not None:
                logger.error("observation: mock notifier sample failed", exc_info=exc)

        fut.add_done_callback(_log_done)

    async def stop(self) -> None:
        self._alert_stop.set()
        if self._alert_thread is not None:
            self._alert_thread.join(timeout=3.0)
            self._alert_thread = None

        if self._poll_task is not None:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None

        hw = self._hardware
        if getattr(hw, "kind", None) == "mock":
            cast(MockDeckHardware, hw).set_change_notifier(None)

        self._loop = None

    async def _emit(self, event: object) -> None:
        payload = (
            event.model_dump(mode="json") if hasattr(event, "model_dump") else event  # type: ignore[assignment]
        )
        if not isinstance(payload, dict):
            return
        log_event = self._live_log.record_event(payload)
        if self._ws_hub.client_count == 0:
            return
        await self._ws_hub.broadcast_json(payload)
        # One wire event per observation: ``bus/*`` updates UI; ``record_event`` still appends
        # matching ``log/entry`` to the replay buffer, but we do not broadcast that again (avoids
        # duplicate messages). The UI derives the visible log line from ``bus/led_changed``.
        if log_event is not None and payload.get("category") != "bus":
            await self._ws_hub.broadcast_json(log_event.model_dump(mode="json"))

    def _alert_gpio_loop(self, hw: LiveDeckHardware) -> None:
        """Block on ALERT/RDY edges; schedule one async telemetry sample per edge."""
        if sys.platform != "linux":
            return
        loop = self._loop
        if loop is None:
            return

        import RPi.GPIO as GPIO  # noqa: N814

        bcm = hw.pins.ads_alert
        try:
            GPIO.setup(bcm, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        except Exception:
            logger.exception("observation: cannot setup ALERT BCM %s", bcm)
            return

        logger.info("observation: ADS ALERT monitoring on BCM %s (wait_for_edge)", bcm)

        while not self._alert_stop.is_set():
            try:
                ch = GPIO.wait_for_edge(bcm, GPIO.BOTH, timeout=_ALERT_EDGE_TIMEOUT_MS)
            except Exception:
                logger.exception("observation: wait_for_edge on BCM %s", bcm)
                break
            if self._alert_stop.is_set():
                break
            if ch is None:
                continue

            fut = asyncio.run_coroutine_threadsafe(self._sample_after_alert(hw), loop)

            def _log_alert_done(f: asyncio.Future[None]) -> None:
                try:
                    exc = f.exception()
                except asyncio.CancelledError:
                    return
                if exc is not None:
                    logger.error("observation: alert telemetry sample failed", exc_info=exc)

            fut.add_done_callback(_log_alert_done)

        try:
            GPIO.cleanup(bcm)
        except Exception:
            logger.debug("observation: GPIO.cleanup(%s)", bcm, exc_info=True)

    async def _sample_after_alert(self, hw: LiveDeckHardware) -> None:
        await self._observe_signals(hw)

    async def _mock_telemetry_loop(self, hw: MockDeckHardware) -> None:
        logger.info("observation: mock telemetry poll (interval=%ss)", _POLL_INTERVAL_S)
        try:
            while True:
                await asyncio.sleep(_POLL_INTERVAL_S)
                await self._observe_signals(hw)
        except asyncio.CancelledError:
            raise

    async def _live_telemetry_loop(self, hw: LiveDeckHardware) -> None:
        logger.info("observation: live telemetry poll started (interval=%ss)", _POLL_INTERVAL_S)
        try:
            while True:
                await asyncio.sleep(_POLL_INTERVAL_S)
                await self._observe_signals(hw)
        except asyncio.CancelledError:
            raise

    async def _observe_signals(self, hw: DeckHardwareFacade) -> None:
        try:
            snap = hw.read_bus_snapshot()
        except Exception:
            logger.exception("observation: read_bus_snapshot failed")
            return

        if self._last_signals is None:
            self._last_signals = snap
            if self._led_prev is None:
                self._led_prev = snap.key_led_active
            observed_idle = (
                not snap.key_adc1_active
                and not snap.key_led_active
                and snap.key_adc2_direction is None
            )
            # Avoid duplicate idle snapshot vs ``control/connected``; but if something is
            # asserted before the first poll interval (e.g. mock notifier), publish once.
            if not observed_idle:
                await self._emit(ws_bus_snapshot(signals=snap))
                await self._emit_led_if_changed(snap.key_led_active)
            return

        if snap != self._last_signals:
            self._last_signals = snap
            await self._emit(ws_bus_snapshot(signals=snap))

        await self._emit_led_if_changed(snap.key_led_active)

    async def _emit_led_if_changed(self, led: bool) -> None:
        if self._led_prev is None:
            self._led_prev = led
            return
        if led == self._led_prev:
            return
        self._led_prev = led
        await self._emit(ws_bus_led_changed(active=led))
