# Phase 18 Execution Record

## Purpose

Track **Phase 18: Display and Touch Validation** per [Implementation Plan](./plan.md).

## Status

**Started:** 2026-04-20.

## Working Goal

Install the Waveshare 7" DSI display in the development fixture, validate touch input under Chromium kiosk mode, and confirm that the touch controller coexists with the existing ADS1115 and DDC/CI devices on the shared I2C bus.

## Initial Checklist

- Mount the Waveshare 7" DSI display into the temporary Phase 17 support.
- Connect DSI ribbon and display power.
- Boot the Pi with the display attached and confirm 1280x800 output.
- Confirm Chromium kiosk mode renders correctly on the installed display.
- Validate touch coordinates across the screen.
- Enumerate the I2C bus with the display/touch stack attached.
- Record confirmed addresses for ADS1115, DDC/CI, and the touch controller.
- Confirm ADS1115 polling and DDC/CI communication still work while touch is active.
- Document required `/boot/config.txt` or `dtoverlay` changes, if any.
- Run and document the host health benchmark before closing the phase, with special attention to voltage, throttling flags, thermals, and memory/CPU impact after the display is attached.

## Open Risks

- Phase 16 remains parked because hardware access is currently unavailable for recording/replay validation.
- The intermittent `KEY_ADC2` observation-stall defect remains open and can affect trust in long-running hardware validation.
- The Phase 17 support is crude; display installation may expose new strain-relief or connector-clearance constraints.
- Reconnecting or disturbing the display power pin can restart the Raspberry Pi. Treat the display power wiring as a live power-integrity risk during bring-up; avoid hot-plugging it casually and document the final power path.
- The display and touch stack may add enough load to expose power-margin problems. The phase cannot close until `vcgencmd get_throttled`, voltage, temperature, and host health output are captured after display installation.
- Touch capability remains a Phase 18 requirement. The first bring-up should use the display's default touch path rather than disabling touch or moving it onto the project GPIO2/GPIO3 I2C bus prematurely.
- The physical 7" 1280x800 panel has high pixel density for the viewing distance. The UI is functionally sized for 1280x800 but some small text is not comfortably readable on the actual display. Treat this as a product/UI readability issue before changing global OS scaling.

## Bring-Up Notes

- 2026-04-20: Confirmed the deck host is `Raspberry Pi 2 Model B Rev 1.1`.
- 2026-04-20: Active boot config is `/boot/firmware/config.txt`; `/boot/config.txt` is only a redirect notice.
- 2026-04-20: Backed up the boot config on the Pi as `/boot/firmware/config.txt.phase18-dsi.bak`.
- 2026-04-20: Added a first DSI trial overlay under `[all]`:

```ini
# Phase 18 Waveshare 7inch DSI LCD (E) trial
dtoverlay=vc4-kms-dsi-waveshare-panel,8_0_inch
```

- 2026-04-20: Do not start with the `dsi0` parameter on Pi 2B. That parameter is intended for boards with multiple DSI ports; Pi 2B has a single DSI connector.
- 2026-04-20: For the Waveshare touch setting, use the display's default `I2C0`/DSI touch path for initial bring-up. Do not wire or configure the panel for `I2C1`/GPIO2/GPIO3 until the display and default touch path are proven, because GPIO2/GPIO3 are already the project bus for ADS1115 and DDC/CI.
- 2026-04-20: Display and touch are working on the Waveshare panel.
- 2026-04-20: First visual usability finding: several small-text regions are hard to read on the physical panel. Candidate areas for a later UI pass include the live log, calendar detail text, notes metadata, OSD mock labels, recording workspace metadata, and version/status badge.
- 2026-04-20: First display-quality finding: colors appear somewhat washed out and horizontal lines are visible. Do not classify this as panel quality yet.
- 2026-04-20: Power diagnostics after display bring-up showed an active/recorded undervoltage and throttling condition: `vcgencmd get_throttled` returned `0x50005`, and `dmesg` reported `Undervoltage detected!` during boot. Treat power integrity as a primary suspect for visual artifacts and Pi resets before blaming the DSI panel or UI.
- 2026-04-20: The panel registers a Linux backlight device at `/sys/class/backlight/10-0045` with `max_brightness=255`.
- 2026-04-20: Reduced brightness to 20% before reboot by writing `51` to `/sys/class/backlight/10-0045/brightness`. `actual_brightness` also reported `51`. After reducing brightness, `dmesg` logged `Voltage normalised`, but `vcgencmd get_throttled` still reported the sticky prior fault state `0x50005`.
- 2026-04-20: Restored brightness to 100% by writing `255` to `/sys/class/backlight/10-0045/brightness`; `actual_brightness` reported `255`.
- 2026-04-20: At 100% brightness the display grayed out. Immediately reducing brightness back to 20% (`51/255`) showed new `dmesg` undervoltage events around the brightness test. Keep brightness below full until the power path is improved and revalidated.
- 2026-04-20: After the 100% brightness test, the panel showed high-frequency flicker even at reduced brightness. Display and touch remained detected (`DSI-1` connected at `1280x800`; Goodix touch input registered), but undervoltage events continued intermittently. Brightness was lowered to 5% (`13/255`) as a temporary stabilization test. Power path remains the leading suspect.

## Brightness / Power Measurements

Manual measurements taken during Phase 18 display bring-up:

First power-supply / power-path test:

| Brightness value | Voltage | Current | Observed behavior | `get_throttled` |
|------------------|---------|---------|-------------------|-----------------|
| `0` | `4.93 V` | `0.53 A` | no artifacts, no weird behavior | `0x50000` |
| `13` | `4.92 V` | `0.55 A` | no artifacts, no weird behavior | `0x50000` |
| `51` | `4.90 V` | `0.60 A` | no artifacts, no weird behavior | `0x50005` |
| `127` | `4.86 V` | `0.71 A` | no artifacts, no weird behavior | `0x50005` |
| `200` | `4.80 V` | `0.87 A` | no artifacts, no weird behavior | `0x50005` |
| `220` | `4.82 V` | `0.82 A` | artifacts and weird behavior; screen blinked in blocks | `0x50005` |
| `255` | `4.78 V` | `0.93 A` | artifacts and weird behavior; block blinking, but better than `220` | `0x50005` |

Second power-supply test:

| Brightness value | Voltage | Current | Observed behavior | `get_throttled` |
|------------------|---------|---------|-------------------|-----------------|
| `220` | `5.12 V` | `0.96 A` | no artifacts, no weird behavior | `0x0` |
| `230` | `5.12 V` | `0.91 A` | artifacts and weird behavior; screen blinked in blocks | `0x0` |
| `255` | `5.12 V` | `0.97 A` | artifacts and weird behavior; screen blinked in blocks | `0x0` |

Additional baseline / off-state measurements:

| State | Voltage | Current | Notes |
|-------|---------|---------|-------|
| Pi off, display connected | `5.04 V` | `0.21 A` | Display/backlight path still draws some standby/off-state current. |
| Pi off, display disconnected | `5.10 V` | `0.07 A` | Pi off-state / supply path baseline without display load. |
| Pi and display disconnected | `5.12 V` | `0.00 A` | Open/no-load supply measurement. |

Initial interpretation:

- Brightness values up to `200/255` were visually stable during this test, even though voltage had sagged to about `4.80 V`.
- Artifacts began at `220/255` and remained present at `255/255`.
- Current draw rises materially with backlight level, from about `0.53 A` at brightness `0` to about `0.93 A` at brightness `255`.
- The no-load supply is about `5.12 V`, but loaded display operation pulls the measured voltage down as far as `4.78 V`. This points to voltage drop under load somewhere in the supply/cable/connector/display-power path, not merely an inability to source the measured current.
- The `220/255` measurement showed slightly higher voltage and lower current than `200/255` while also showing artifacts; that is likely because block blinking reduced average current during the measurement rather than because `220/255` is electrically healthier.
- The second power-supply test changed the conclusion: with a stronger supply/path, `220/255` was stable at `5.12 V` and `throttled=0x0`, confirming the earlier instability was at least partly power-path related.
- However, `230/255` and `255/255` still produced block-blinking artifacts even at `5.12 V` and `throttled=0x0`. That means high-brightness artifacts are not explained solely by Raspberry Pi undervoltage; the panel/backlight driver, display power input path, DSI/panel timing, or Pi 2 compatibility may still be limiting full-brightness operation.
- The `0x50005` throttle state contains active or historical undervoltage/throttle flags; use fresh boot measurements and `dmesg` timestamps when deciding whether a specific brightness level is currently safe.
- With the improved supply/path, `220/255` is the highest tested artifact-free brightness. Keep the panel at or below `220/255` until the `230+` artifact threshold is understood.
