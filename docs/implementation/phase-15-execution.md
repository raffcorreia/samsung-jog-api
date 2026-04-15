# Phase 15 Execution Record

## Purpose

Record completion of **Phase 15: Observation Bus and Hardware Interface** per [Implementation Plan](./plan.md).

## Summary

- **Backend:** `DeckControlService` emits `command/held`, `command/released`, and `bus/snapshot` on REST-driven hold/release/pulse so the UI and logs stay reliable. `ObservationBusService` runs an asyncio **telemetry poll** on live hardware (~25 ms): refreshes **ADS1115** AIN0 reads and emits **`bus/snapshot`** / **`bus/led_changed`** when KEY_ADC1 / KEY_LED signals change, without competing with the main event loop (earlier GPIO-edge + `run_coroutine_threadsafe` storms could starve asyncio and drop all websocket progress).
- **Decode:** `KEY_ADC2` millivolt thresholds are derived from Phase 2 powered measurements (`key_adc2_decode.py`).
- **Frontend:** JogPad shows an optimistic pressed state after REST success and reconciles to observation-backed `holdCounts`. `LedIndicator` pulses on `bus/led_changed` when `KEY_LED` turns on. OSD mock can auto-open after a short post-mount delay when bus activity ticks increase.

## Host health snapshot

Run on the deck host after deploy:

```bash
python3 scripts/pi-deck-host-health.py
```

Paste the full default (text) output below when closing the phase.

```
(pending — run on deck after validating observation on live hardware)
```

## Notes

- Deploy updated code to the Pi with `PI_TARGET=user@host ./scripts/deploy.sh` so the deck runs the new `ObservationBusService` and `Ads1115.start_continuous_ain0_rdy`.
- Bench verification: `scripts/pi-deck-gpio-probe read-ads --channel 0` on `/dev/i2c-1` address `0x48` (AIN0).
