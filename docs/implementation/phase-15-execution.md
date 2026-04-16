# Phase 15 Execution Record

## Purpose

Record completion of **Phase 15: Observation Bus and Hardware Interface** per [Implementation Plan](./plan.md).

## Status

**Closed:** 2026-04-16 (merged to `main`). Telemetry design notes: [phase-15-observation-telemetry.md](./phase-15-observation-telemetry.md).

## Summary (as shipped)

- **Backend:** `DeckControlService` emits `command/held`, `command/released`, and `bus/snapshot` on REST-driven hold/release/pulse. **`ObservationBusService`** is the **single source** for physical **`bus/snapshot`**, **`bus/led_changed`**, and semantic bus log lines (`bus_delta_log_messages`). Live hardware: **~25 ms asyncio poll** plus **gpiozero** edge callbacks on KEY_ADC1, KEY_LED, and ADS1115 ALERT/RDY (`lgpio` pin factory when available); **`CoalesceGate`** limits bursts from helper threads into **`run_coroutine_threadsafe`**. ADS1115 runs in **continuous conversion** with ALERT as **conversion-ready** (not a voltage comparator); KEY_ADC2 comes from `read_conversion_mv()` + `key_adc2_decode.py`.
- **Frontend:** JogPad optimistic press after REST; reconciliation via websocket `holdCounts`. `LedIndicator` follows `key_led_active` from status / bus. OSD mock opens only from manual control.

## Host health snapshot

**Host:** `pi-deck` (deck appliance). **Captured:** 2026-04-16 (UTC in script output).

Run on the deck host anytime:

```bash
python3 scripts/pi-deck-host-health.py
```

```
pi-deck host health  |  2026-04-16T21:01:22.027726+00:00
hostname: pi-deck

[python]
  executable: /usr/bin/python3
  version:    3.13.5
  platform:   Linux-6.18.18-v7+-armv7l-with-glibc2.41
  pi_deck:    importable=True  package_version=0.1.0

[cpu]
  model: ARMv7 Processor rev 5 (v7l)
  logical cpus: 4
  load average (1 / 5 / 15 min): 0.68  0.28  0.40

[memory]
  RAM:  total 0.90 GiB  available 0.53 GiB  (MemTotal/MemAvailable KiB: 942120 / 553140)
  swap: total 0.90 GiB  free 0.90 GiB  (KiB: 942076 / 939816)

[disk]  mount /
  size 56.49 GiB  used 5.04 GiB  avail 49.12 GiB  (8.91% used)

[thermal]  sysfs zones
  thermal_zone0  cpu-thermal  46.5 °C

[raspberry_pi]  vcgencmd (SoC voltage / throttling)
  temperature: temp=47.1'C
  voltage core: volt=1.3125V
  voltage sdram_c: volt=1.2000V
  voltage sdram_i: volt=1.2000V
  voltage sdram_p: volt=1.2250V
  get_throttled: throttled=0x0
  flags set: (none)

[systemd]
  pi-deck.service: active
  lightdm.service: active

[pi-deck HTTP]
  GET http://127.0.0.1:8756/health
  ok: True  body: '{"status":"ok","version":"0.1.0"}'
```

**Review:** `get_throttled` shows no under-voltage/throttle flags; root filesystem use is low; services healthy.

## Notes

- Deploy: `PI_TARGET=user@host ./scripts/deploy.sh`
- Bench: `scripts/pi-deck-gpio-probe read-ads --channel 0` on `/dev/i2c-1` `0x48` (AIN0).
- **Follow-up (later phase):** websocket / `LiveLogService` volume and operator-facing log coalescing (see prior plan note).
