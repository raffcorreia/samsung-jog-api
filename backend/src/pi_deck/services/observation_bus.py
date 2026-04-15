"""Hardware telemetry → websocket ``bus.snapshot`` / ``bus.led_changed`` (Phase 15).

``command/held`` and ``command/released`` are emitted by ``DeckControlService`` so the UI stays
reliable even if I²C/GPIO observation glitches. This module pushes **signal** updates for KEY_ADC1 /
KEY_LED and keeps the ADS1115 conversion register fresh (AIN0 = KEY_ADC2 analog path).

Live: asyncio poll (~25 ms). Avoids GPIO edge IRQs at ~250 Hz scheduling work onto asyncio
(``run_coroutine_threadsafe``), which had starved the event loop."""

from __future__ import annotations

import asyncio
import logging
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
        self._poll_task: asyncio.Task[None] | None = None
        self._last_signals: tuple[bool, bool] | None = None
        self._led_prev: bool | None = None

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        _ = loop
        hw = self._hardware
        if getattr(hw, "kind", None) != "live":
            return
        self._poll_task = asyncio.create_task(
            self._live_telemetry_loop(),
            name="observation-telemetry",
        )

    async def stop(self) -> None:
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

    async def _live_telemetry_loop(self) -> None:
        hw = cast(LiveDeckHardware, self._hardware)

        try:
            ads = Ads1115()
            ads.start_continuous_ain0_rdy()
            self._ads = ads
        except Exception:
            logger.exception(
                "observation: ADS1115 continuous mode failed; telemetry limited to GPIO",
            )
            ads = None
            self._ads = None

        logger.info("observation: live telemetry poll started (interval=%ss)", _POLL_INTERVAL_S)
        try:
            while True:
                await asyncio.sleep(_POLL_INTERVAL_S)
                await self._poll_telemetry_once(hw, ads)
        except asyncio.CancelledError:
            raise
        finally:
            if self._ads is not None:
                try:
                    self._ads.close()
                except Exception:
                    pass
                self._ads = None

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
