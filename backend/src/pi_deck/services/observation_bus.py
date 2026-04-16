"""Hardware telemetry → websocket ``bus.snapshot`` / ``bus/led_changed`` (Phase 15).

``command/held`` and ``command/released`` are emitted by ``DeckControlService`` so the UI stays
reliable. This service reports KEY_ADC1 / KEY_LED and refreshes ADS1115 AIN0 (KEY_ADC2 analog path).

Live: **BCM 17** (ADS ALERT): ``wait_for_edge`` in a daemon thread, one async sample per edge.
A **~25 ms poll** backs up KEY1/LED.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import threading
from typing import cast

from pi_deck.hardware.ads1115 import Ads1115
from pi_deck.models.schemas import (
    SignalSnapshot,
    ws_bus_led_changed,
    ws_bus_snapshot,
)
from pi_deck.services.hardware_facade import LiveDeckHardware
from pi_deck.services.live_log import LiveLogService
from pi_deck.services.ws_hub import WsHub

logger = logging.getLogger(__name__)

_POLL_INTERVAL_S = 0.025
_ALERT_EDGE_TIMEOUT_MS = 500


class ObservationBusService:
    """Background telemetry: ``bus/snapshot`` and ``bus/led_changed`` on live hardware."""

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
        self._ads: Ads1115 | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._poll_task: asyncio.Task[None] | None = None
        self._alert_thread: threading.Thread | None = None
        self._alert_stop = threading.Event()
        self._last_signals: tuple[bool, bool] | None = None
        self._led_prev: bool | None = None

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        hw = self._hardware
        if getattr(hw, "kind", None) != "live":
            return
        live_hw = cast(LiveDeckHardware, hw)

        try:
            ads = Ads1115()
            ads.start_continuous_ain0_rdy()
            self._ads = ads
        except Exception:
            logger.exception(
                "observation: ADS1115 continuous mode failed; telemetry limited to GPIO",
            )
            self._ads = None

        self._poll_task = asyncio.create_task(
            self._live_telemetry_loop(live_hw, self._ads),
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

        if self._ads is not None:
            try:
                self._ads.close()
            except Exception:
                logger.debug("observation: ads close failed", exc_info=True)
            self._ads = None
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
        if log_event is not None:
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
        await self._poll_telemetry_once(hw, self._ads)

    async def _live_telemetry_loop(self, hw: LiveDeckHardware, ads: Ads1115 | None) -> None:
        logger.info("observation: live telemetry poll started (interval=%ss)", _POLL_INTERVAL_S)
        try:
            while True:
                await asyncio.sleep(_POLL_INTERVAL_S)
                await self._poll_telemetry_once(hw, ads)
        except asyncio.CancelledError:
            raise

    async def _poll_telemetry_once(self, hw: LiveDeckHardware, ads: Ads1115 | None) -> None:
        if ads is not None:
            try:
                await asyncio.to_thread(ads.read_conversion_mv)
            except Exception:
                logger.exception("observation: ADS read failed")

        try:
            adc1, led = hw.read_signals()
        except Exception:
            logger.exception("observation: read_signals failed")
            return

        snap = (adc1, led)
        if self._last_signals is None:
            self._last_signals = snap
            if self._led_prev is None:
                self._led_prev = led
            return

        if snap != self._last_signals:
            self._last_signals = snap
            await self._emit(
                ws_bus_snapshot(
                    signals=SignalSnapshot(key_adc1_active=adc1, key_led_active=led),
                ),
            )

        await self._emit_led_if_changed(led)

    async def _emit_led_if_changed(self, led: bool) -> None:
        if self._led_prev is None:
            self._led_prev = led
            return
        if led == self._led_prev:
            return
        self._led_prev = led
        await self._emit(ws_bus_led_changed(active=led))
