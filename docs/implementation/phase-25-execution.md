# Phase 25 Execution Record

## Purpose

Track **Phase 25: Replacement Display and Final Pi 5 Host Cutover** per [Implementation Plan](./plan.md).

## Status

**Planned / next.**

Phase 24's DDC capability investigation is complete. Phase 25 is an inserted platform phase to replace the defective display panel and cut the project over to the final Raspberry Pi 5 8GB host before continuing planned feature work.

## Working Goal

Install the replacement DSI panel, move the control deck baseline to the final Raspberry Pi 5 8GB, and re-run the hardware/display validation that Phase 20 could not close because the previous panel was defective.

## Initial Checklist

- Record final host identity: Raspberry Pi model/RAM, OS, kernel, storage, power supply, active cooling state, and hostname.
- Prepare the final Pi 5 host with the current host-prep and platform bring-up runbooks.
- Deploy current code with `scripts/deploy.sh`.
- Verify `pi-deck.service`, kiosk autostart, and visible version.
- Verify Phase 6 protoboard wiring on the Pi 5 GPIO map.
- Validate `JOG`, `KEY_ADC1`, `KEY_ADC2`, `KEY_LED`, `ADS1115`, display power GPIO, and status LED paths.
- Install replacement DSI panel.
- Validate DSI output at `1280x800`, touch mapping, backlight path, brightness read/write, and brightness persistence.
- Confirm both HDMI outputs are disabled as Linux displays while HDMI/DDC remains usable.
- Confirm DDC/CI reads for `VCP 0x60`, `0x10`, and `0xD6`.
- Re-run color/edge validation on the healthy panel.
- Re-test brightness ceiling, including the previous `170/255` cap and higher values if safe.
- Re-test display power off/on behavior.
- Run sustained kiosk validation and host health snapshot.
- Decide whether the Raspberry Pi 5 8GB plus replacement panel is accepted as the baseline for subsequent phases.

## Open Risks

- The replacement panel may still have visible defects or a different brightness/artifact threshold.
- The final Raspberry Pi 5 8GB may differ from the temporary Pi 5 validation unit in OS image, storage, power supply, cooling, or boot configuration.
- Display power cycling and inrush behavior must be re-validated on the actual final wiring.
- Phase 24 DDC work proved HDMI video can be disabled while DDC remains usable; this must be confirmed again after final host/display setup.

## Evidence Log

_To be filled during execution._

## Host Health Snapshot

_Required before closing this phase. Paste the default text output from `python3 scripts/pi-deck-host-health.py`._
