# Phase 15 — Observation telemetry (IRQ-first follow-up)

## Problem (Phase 15 hybrid)

Phase 15 shipped a hybrid: `ObservationBusService` runs a ~25 ms asyncio poll and (originally) a dedicated thread on ADS1115 ALERT/RDY. KEY_ADC1 and KEY_LED were level-sampled in `read_bus_snapshot()` so transitions could be delayed by up to one poll interval unless another signal caused a snapshot.

ADS1115 was configured in **continuous conversion** mode with **COMP_QUE = 11** so ALERT/RDY asserts on **conversion ready** (not a voltage comparator against KEY_ADC2 thresholds).

## Follow-up — IRQ path (gpiozero + lgpio)

Live hardware uses **one gpiozero pin factory** for outputs (`JogDrive`) and inputs (`KeyAdc1Observe`, `KeyLedObserve`, `AdsAlertPin`):

1. **`build_hardware()`** prefers **`GPIOZERO_PIN_FACTORY=lgpio`** when `import lgpio` succeeds (Pi 5 / Bookworm). Otherwise **`rpigpio`** (RPi.GPIO). Override with the environment variable if needed.

2. **KEY_ADC1 / KEY_LED** — `DigitalInputDevice` with `when_activated` + `when_deactivated` (logical both-edge). Callbacks run on gpiozero’s helper thread; they only **`run_coroutine_threadsafe`** into `ObservationBusService` via **`CoalesceGate`** so bursts coalesce.

3. **ADS ALERT** — `AdsAlertPin` is a `DigitalInputDevice` on the ALERT BCM (open-drain, **active_low**). Same coalesced observe path; **no** `RPi.GPIO.wait_for_edge` thread.

4. **Asyncio poll** — ~25 ms loop remains as **watchdog** and backup if edge hooks fail.

5. **Semantics** — `bus/snapshot`, `bus/led_changed`, and `bus_delta_log_messages` unchanged; `asyncio.Lock` serializes poll vs IRQ-driven observation.

## RPi.GPIO vs lgpio

Raw **RPi.GPIO** `add_event_detect` / `wait_for_edge` often **fail** on Pi 5 / newer kernels (`NOTIMPLEMENTED`). The IRQ implementation is **gpiozero with lgpio**, not RPi.GPIO edges.

## ADS1115 mode (unchanged)

Continuous AIN0 at 250 SPS with ALERT as conversion-ready feeds `read_conversion_mv()` → `decode_key_adc2_direction()`.

## Hardware verification (Pi)

With ALERT and GPIO wiring connected, exercise KEY1 / KEY2 and LED: expect timely `bus/snapshot` and bus log lines. Confirm `GPIOZERO_PIN_FACTORY` in logs / env (`lgpio` vs `rpigpio`).

## Revision history

| When | Notes |
|------|--------|
| Phase 15 ship | Poll + ADS `wait_for_edge` only; KEY lines level-polled in snapshot |
| IRQ-first (RPi.GPIO) | BOTH-edge + coalesced path — failed on Pi 5 |
| gpiozero + lgpio | Real IRQs via `DigitalInputDevice`; ADS ALERT same pattern; poll watchdog |
