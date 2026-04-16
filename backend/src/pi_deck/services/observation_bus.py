"""Hardware telemetry → websocket ``bus.snapshot`` / ``bus/led_changed``.

Physical KEY_ADC1, KEY_ADC2 (decoded), and KEY_LED are emitted **only** from this service, driven
by ``read_bus_snapshot()`` on the hardware facade. On live hardware, KEY_ADC1 / KEY_LED use
RPi.GPIO BOTH-edge callbacks plus a ~25 ms asyncio poll as watchdog; ADS1115 uses ALERT/RDY
(``wait_for_edge``) with the same coalesced observe path as GPIO edges.

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
from pi_deck.services.live_log import LiveLogService, bus_delta_log_messages
from pi_deck.services.observation_coalesce import CoalesceGate
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
        self._observe_lock: asyncio.Lock | None = None
        self._edge_coalesce = CoalesceGate()
        self._last_signals: SignalSnapshot | None = None
        self._led_prev: bool | None = None

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._observe_lock = asyncio.Lock()
        self._edge_coalesce.reset()
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

        self._install_live_gpio_edges(live_hw)

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
        hw = self._hardware
        if getattr(hw, "kind", None) == "live":
            live = cast(LiveDeckHardware, hw)
            live.adc1_observer.disable_edge_detect()
            live.led_observer.disable_edge_detect()
        self._edge_coalesce.reset()

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
        self._observe_lock = None

    def _install_live_gpio_edges(self, hw: LiveDeckHardware) -> None:
        """RPi.GPIO edge callbacks (helper thread) only schedule asyncio work — never block the loop."""
        if sys.platform != "linux":
            return

        def _kick() -> None:
            self._schedule_observe_from_thread(hw)

        ok_adc1 = hw.adc1_observer.enable_edge_detect(_kick)
        ok_led = hw.led_observer.enable_edge_detect(_kick)
        if ok_adc1 and ok_led:
            logger.info(
                "observation: KEY_ADC1 / KEY_LED BOTH-edge detect (bouncetime) on BCM %s / %s",
                hw.pins.key_adc1_digital,
                hw.pins.key_led_digital,
            )
        else:
            logger.warning(
                "observation: GPIO edge IRQs unavailable for KEY_ADC1=%s KEY_LED=%s "
                "(common on Pi 5 / newer kernels); using asyncio poll only for those lines",
                ok_adc1,
                ok_led,
            )

    def _schedule_observe_from_thread(self, hw: LiveDeckHardware) -> None:
        loop = self._loop
        if loop is None:
            return
        if not self._edge_coalesce.request_from_thread():
            return

        fut = asyncio.run_coroutine_threadsafe(self._coalesced_edge_observe_loop(hw), loop)

        def _log_done(f: asyncio.Future[None]) -> None:
            try:
                exc = f.exception()
            except asyncio.CancelledError:
                return
            if exc is not None:
                logger.error("observation: coalesced edge observe failed", exc_info=exc)

        fut.add_done_callback(_log_done)

    async def _coalesced_edge_observe_loop(self, hw: LiveDeckHardware) -> None:
        try:
            while True:
                await self._observe_signals(hw)
                if not self._edge_coalesce.should_continue_after_round():
                    break
        except asyncio.CancelledError:
            self._edge_coalesce.reset()
            raise
        except Exception:
            logger.exception("observation: coalesced edge observe failed")
            self._edge_coalesce.reset()

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
        # ``bus/snapshot`` does not append a log row here; semantic lines use ``publish`` from
        # ``bus_delta_log_messages``. ``bus/led_changed`` and other categories still record/replay.
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
            except Exception as e:
                logger.warning(
                    "observation: wait_for_edge unsupported or failed on BCM %s (%s); "
                    "ADS telemetry uses asyncio poll only",
                    bcm,
                    e,
                )
                break
            if self._alert_stop.is_set():
                break
            if ch is None:
                continue

            self._schedule_observe_from_thread(hw)

        try:
            GPIO.cleanup(bcm)
        except Exception:
            logger.debug("observation: GPIO.cleanup(%s)", bcm, exc_info=True)

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
        lock = self._observe_lock
        if lock is None:
            return
        async with lock:
            await self._observe_signals_locked(hw)

    async def _observe_signals_locked(self, hw: DeckHardwareFacade) -> None:
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
                for msg in bus_delta_log_messages(None, snap):
                    await self._live_log.publish(level="info", source="bus", message=msg)
                await self._emit(ws_bus_snapshot(signals=snap))
                await self._emit_led_if_changed(snap.key_led_active)
            return

        if snap != self._last_signals:
            # Steady state: first iteration always returned from the ``_last_signals is None`` branch.
            prev_sig = self._last_signals
            for msg in bus_delta_log_messages(prev_sig, snap):
                await self._live_log.publish(level="info", source="bus", message=msg)
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
