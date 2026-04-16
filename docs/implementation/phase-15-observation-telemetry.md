# Phase 15 — Observation telemetry (IRQ-first follow-up)

## Problem (Phase 15 hybrid)

Phase 15 shipped a hybrid: `ObservationBusService` runs a ~25 ms asyncio poll and a dedicated thread that blocks on ADS1115 ALERT/RDY (`wait_for_edge`). Both paths called `read_bus_snapshot()`. KEY_ADC1 and KEY_LED were sampled only when that poll ran (`GPIO.input` inside `KeyAdc1Observe` / `KeyLedObserve`), so physical transitions could be delayed by up to one poll interval unless another signal caused a snapshot.

ADS1115 was configured in **continuous conversion** mode with **COMP_QUE = 11** so ALERT/RDY asserts on **conversion ready** (not a voltage comparator against KEY_ADC2 thresholds).

## Follow-up (this change)

1. **KEY_ADC1 (BCM 27) and KEY_LED (BCM 22)** — After the usual `GPIO.setup(..., IN)`, register RPi.GPIO **BOTH**-edge detection with a small bouncetime. Callbacks run on RPi.GPIO’s helper thread; they only call into `ObservationBusService` via the same pattern as ADS: **`run_coroutine_threadsafe`** into a **coalesced** async loop (see `CoalesceGate` in `observation_coalesce.py`), not unbounded per-edge futures.

2. **ADS ALERT** — The ALERT thread still uses `wait_for_edge`; it now shares that **coalesced** scheduler with GPIO edges so bursts collapse to extra observation rounds instead of stacking many `run_coroutine_threadsafe` calls.

3. **Asyncio poll** — The ~25 ms poll remains as a **watchdog**: catches missed edges, startup races, and any path where IRQs are unavailable. It is not removed.

4. **Semantics** — `bus/snapshot`, `bus/led_changed`, and `bus_delta_log_messages` are unchanged; observation work is serialized with an `asyncio.Lock` so poll and IRQ-driven paths cannot corrupt `_last_signals`.

## ADS1115 mode (unchanged)

Continuous AIN0 at 250 SPS with ALERT as conversion-ready is appropriate for feeding `read_conversion_mv()` → `decode_key_adc2_direction()`. Comparator mode would be a different product decision (hardware thresholds vs firmware thresholds) and is **not** switched here.

## Hardware verification (Pi)

With ALERT and GPIO wiring connected, exercise KEY1 / KEY2 and LED: expect timely `bus/snapshot` and bus log lines. If anything still depends on the slow poll alone, it will show up as a delay of ~25 ms worst case rather than IRQ-limited latency.

## RPi.GPIO edge limitations (Pi 5 / newer stacks)

On some images, ``add_event_detect`` / ``wait_for_edge`` raise at runtime (e.g. ``Failed to add edge detection``, ``Error waiting for edge``). The service **does not fail startup**: KEY lines and ADS ALERT fall back to the asyncio ~25 ms poll path only. For full IRQ support on newer Pis, investigate ``lgpio`` / libgpiod-based factories (separate from this fallback).

## Revision history

| When | Notes |
|------|--------|
| Phase 15 ship | Poll + ADS `wait_for_edge` only; KEY lines level-polled in snapshot |
| IRQ-first follow-up | BOTH-edge on KEY_ADC1 / KEY_LED + coalesced observe path shared with ALERT |
| Graceful fallback | If RPi.GPIO edges are unavailable, log warning and use poll-only (no crash) |
