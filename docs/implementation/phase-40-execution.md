# Phase 40 Execution Record

## Purpose

Track **Phase 40: Replacement Display and Final Pi 5 Host Cutover** per [Implementation Plan](./plan.md).

## Status

**Blocked.**

Phase 24's DDC capability investigation is complete. Phase 40 is an inserted platform phase to replace the defective display panel and cut the project over to the final Raspberry Pi 5 8GB host before continuing planned feature work.

## Blocker

On 2026-10-30, the replacement panel was installed and produced a working image, but its touch cable was found to be physically damaged. Live software diagnostics on the final Pi 5 host confirmed that the expected boot configuration was present, the Goodix controller probed successfully as `ID 9271`, the `Goodix-TS` driver bound to I2C device `11-0014`, and Linux created `/dev/input/event7`. A direct raw-input test produced no touch events, ruling out the kiosk UI, Chromium, Wayland coordinate mapping, and application code as the cause.

Phase 40 cannot complete touch mapping, sustained kiosk validation, or acceptance of the replacement panel while the damaged touch path remains installed. Resume the phase after the touch cable or panel assembly has been repaired or replaced, then repeat the cold-boot Goodix probe, raw input-event, coordinate-mapping, and sustained display validation checks.

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

- 2026-10-30: Replacement panel installed; DSI image output works, but touch does not.
- 2026-10-30: Final host boot configuration confirmed: `dtparam=i2c_arm=on`, `dtoverlay=vc4-kms-dsi-waveshare-panel,8_0_inch`, and `gpio=24=op,dh`.
- 2026-10-30: After a cold boot, the Goodix controller probed cleanly as `ID 9271, version 1070`, bound at I2C `11-0014`, and created `/dev/input/event7` with `ID_INPUT_TOUCHSCREEN=1`.
- 2026-10-30: A direct 20-second read from `/dev/input/event7` produced no events while the screen was tapped and dragged. The failure is below the compositor and application layers.
- 2026-10-30: Physical inspection identified damage to the replacement display's touch cable. Phase blocked pending repair or replacement.

## Host Health Snapshot

_Required before closing this phase. Paste the default text output from `python3 scripts/pi-deck-host-health.py`._
