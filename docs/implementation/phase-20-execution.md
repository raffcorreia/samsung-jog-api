# Phase 20 Execution Record

## Purpose

Track **Phase 20: Raspberry Pi 5 Rebuild and Display Performance Validation** per [Implementation Plan](./plan.md).

## Status

**Started:** not started.

**Closed:** not closed.

## Working Goal

Rebuild the control deck on the Raspberry Pi 5 16GB, repeat the infrastructure and display-preparation phases without new product-code development, deploy the current application through the canonical deploy script, and decide whether the display quality and Chromium performance issues are Raspberry Pi 2-specific.

## Required Execution Sequence

Run these in order:

1. **Phase 1 repeat:** fresh Pi 5 host preparation and conservative cleanup; capture pre-cleanup and post-cleanup host state.
2. **Phase 9 repeat:** install service, desktop stack, Chromium kiosk, autostart, and keyring suppression on the Pi 5.
3. **Phase 12 repeat:** deploy current code using `scripts/deploy.sh`; confirm version increments and kiosk reloads.
4. **Phase 8 / Phase 15 hardware repeat:** validate Phase 6 protoboard GPIO drive and observation on Pi 5.
5. **Phase 18 repeat:** validate DSI display, touch, I2C map, and DDC-only HDMI policy.
6. **Phase 19 repeat:** validate display power, brightness cap behavior, color/edge page, reboot persistence, and brightness/power measurements.
7. **Pi 5 comparison:** measure display quality, Chromium responsiveness, resource usage, thermals, throttling, and sustained kiosk behavior against the Pi 2 baseline.
8. **Decision:** record whether future phases proceed on Pi 5 and what earlier assumptions changed.

## GPIO Schema

Use [Phase 20 Raspberry Pi 5 GPIO Schema](../hardware/phase-20-pi5-gpio-schema.md).

## Evidence Checklist

- Pi 5 hardware, storage, OS image, power supply, and hostname recorded
- Phase 1 host-prep artifacts captured under `artifacts/host-prep/`
- `pi-deck.service` active on Pi 5
- Chromium kiosk starts automatically after reboot
- `scripts/deploy.sh` targets the Pi 5 and increments the visible version
- `PI_DECK_HARDWARE=live` works on Pi 5
- actual `GPIOZERO_PIN_FACTORY` or equivalent GPIO backend recorded
- project I2C bus, ADS1115, DDC bus, DSI touch/panel bus, and backlight sysfs path recorded
- `video=HDMI-A-1:d` behavior confirmed or revised for Pi 5
- brightness range and artifact threshold re-tested
- Xwayland/native Wayland Chromium mode compared with evidence
- color/edge validation page inspected on the physical panel
- 30-minute sustained kiosk run completed
- final host health snapshot pasted below

## Pi 2 Baseline to Compare

Use the Phase 18 and Phase 19 execution records as the baseline:

| Area | Pi 2 baseline | Pi 5 result |
| --- | --- | --- |
| Kiosk resolution | `1280x800` DSI | TBD |
| Touch | working, no observed offset | TBD |
| Safe brightness cap | `170/255` through UI/API | TBD |
| High-brightness artifacts | artifacts above the validated safe range | TBD |
| Chromium mode | Xwayland selected for subpixel rendering | TBD |
| Display power off | backlight `0` plus `wlr-randr DSI-1 --off` | TBD |
| HDMI policy | visual output disabled, DDC retained | TBD |
| Idle host health | no active throttle at Phase 19 close | TBD |
| Perceived responsiveness | unsatisfactory on Pi 2 | TBD |

## Host Health Snapshot

Paste the final default text output from:

```bash
python3 scripts/pi-deck-host-health.py
```

```text
TBD
```

## Decision

TBD.
