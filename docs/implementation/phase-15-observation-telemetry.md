# Phase 15 — Observation telemetry

**Phase 15 closed** with merge to `main` (2026-04-16). Execution record: [phase-15-execution.md](./phase-15-execution.md).

## Behavior

`ObservationBusService` emits physical bus state via `read_bus_snapshot()` only.

- **Asyncio poll (~25 ms):** always runs; full snapshot (KEY_ADC1, KEY_LED, KEY_ADC2 via ADS).
- **Edge path (live):** gpiozero `DigitalInputDevice` on KEY lines and ADS ALERT with `when_activated` / `when_deactivated`; callbacks use `run_coroutine_threadsafe` and `CoalesceGate` into the same observe path. Prefer pin factory **lgpio** when available (`build_hardware()`), else **rpigpio**.

`DeckControlService` does not emit bus telemetry.

## ADS1115

Continuous AIN0 at 250 SPS; ALERT/RDY used as conversion-ready for `read_conversion_mv()` → `decode_key_adc2_direction()`.

## Pi check

With wiring connected, exercise keys and LED; expect timely `bus/snapshot` and bus log lines when edges are active.
