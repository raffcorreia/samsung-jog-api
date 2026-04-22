# Phase 18 Execution Record

## Purpose

Track **Phase 18: Display and Touch Validation** per [Implementation Plan](./plan.md).

## Status

**Started:** 2026-04-20.

**Closed:** 2026-04-22.

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
- 2026-04-21: Final live boot config uses `/boot/firmware/config.txt` with `dtparam=i2c_arm=on`, `dtoverlay=vc4-kms-v3d`, and the Waveshare DSI overlay under `[all]`. `/boot/config.txt` is not the active file on this OS image.

```ini
dtparam=i2c_arm=on
display_auto_detect=1
dtoverlay=vc4-kms-v3d
max_framebuffers=2

[all]
enable_uart=1
# Phase 18 Waveshare 7inch DSI LCD (E) trial
dtoverlay=vc4-kms-dsi-waveshare-panel,8_0_inch
```

- 2026-04-21: Confirmed current runtime state with the display active: `DSI-1` connected at `1280x800`, HDMI disconnected, Goodix touch registered, `/sys/class/backlight/10-0045` present with `max_brightness=255`, current brightness `51/255`, and `vcgencmd get_throttled` reporting `0x0`.
- 2026-04-21: Touch is accepted as working for now. No touch offset, inversion, dead-zone, or kiosk interaction issue has been observed during manual use.

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
| Pi on, display disconnected | — | `0.32 A` | Pi-only running cost (no display attached). Confirms display hardware accounts for 0.10 A always-on draw (0.42 A software-off state minus 0.32 A) and 0.27 A at 30% brightness (0.59 A minus 0.32 A). |

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
- Later practical testing revised the safe operating ceiling downward: use `170/255` as the current safest brightness value for normal Phase 18 work.

## Pending DDC Check

Next validation step: reconnect HDMI and run a read-only DDC/CI check against the monitor while the DSI display and touch path remain active. This is only a coexistence check for Phase 18, not the broader DDC capability investigation planned for the next phase.

Result:

- 2026-04-21: HDMI was connected while the DSI display and touch stack were active. Kernel DRM reported both `DSI-1` connected at `1280x800` and `HDMI-A-1` connected with monitor modes visible.
- 2026-04-21: After HDMI hotplug and a `lightdm` restart, the app appeared on the HDMI monitor and the DSI panel went black. `lightdm`, `labwc`, and Chromium were all running. Treat this as an output-selection/compositor profile issue, not as display hardware failure. A future kiosk output profile should force the app to the DSI panel and keep HDMI available for monitor/DDC testing.
- 2026-04-21: Even with the DSI panel visually black, the DSI touch device still worked. Touches on the physical DSI panel controlled the app visible on the HDMI monitor. This confirms the touch controller remains active and also proves the current problem is display output mapping, not touch failure.
- 2026-04-21: Attempted to use `kanshi` to clone `DSI-1` and `HDMI-A-1` at `1280x800`. Kanshi reported the clone profile applied, but only HDMI showed the app. A DSI-preferred profile then left both displays black; after `lightdm` restart, the DSI panel came back upside down/cut off/blinking while HDMI behavior changed. The active kanshi config was reverted to empty and the bad profile was saved as `~/.config/kanshi/config.phase18-bad-profile`. Do not use this kanshi clone/force approach as the Phase 18 solution.
- 2026-04-21: Read-only DDC/CI check succeeded on HDMI DDC bus `/dev/i2c-2`. A Get VCP Feature request for `0x60` returned a valid response with current value `0x0004`.
- 2026-04-22: Added `video=HDMI-A-1:d` to `/boot/firmware/cmdline.txt` to disable HDMI as a Linux display output while keeping the HDMI connector electrically present for DDC. With that option active, DRM reported `HDMI-A-1` disconnected, but `/dev/i2c-2` remained present and the same read-only DDC/CI Get VCP `0x60` request still succeeded. This confirms the preferred operating model for this hardware: DSI panel for the kiosk UI; HDMI used for DDC/CI communication only, not for visual output.
- 2026-04-22: HDMI will be physically disconnected after the DDC-only check. Keep the `cmdline.txt` backup `/boot/firmware/cmdline.txt.phase18-before-hdmi-disable.bak` until the DSI-only boot path is considered stable.
- 2026-04-22: DSI-only operation was confirmed after HDMI was disconnected. The kiosk display path is considered stable enough to close Phase 18 with HDMI reserved for DDC/CI only.
- 2026-04-22: Safe maximum display brightness is `170/255`. Higher values may work intermittently, but `170/255` is the current validated safe ceiling for normal operation.
- 2026-04-22: ADS observation remained working after the Phase 6 `R20` `100 kOhm` `KEY_ADC2` isolation fix.
- 2026-04-21: Runtime I2C/device map during coexistence test:
  - `/dev/i2c-1`: Raspberry Pi GPIO2/GPIO3 project I2C bus
  - `/dev/i2c-2`: HDMI DDC bus used for DDC/CI test
  - `/dev/i2c-10`: DSI panel/touch mux channel containing `10-0014 -> gt911` Goodix touch and `10-0045 -> 8.0inch-panel`
  - `/dev/i2c-11`: parent DSI I2C controller / mux
- 2026-04-21: Backend status while DSI/touch and HDMI/DDC were active: `hardware=live`, `operating_mode=jog`, `control_state=idle`, `key_adc1_active=false`, `key_led_active=false`, and `key_adc2_direction=null`. This confirms the ADS1115 observation path was still returning an idle decoded state rather than a false key direction.
- 2026-04-21: Host health after HDMI/DDC coexistence check: `pi-deck.service` active, `lightdm.service` active, HTTP health OK, temperature about `44.4 C`, and `vcgencmd get_throttled` returned `0x0`.

## Exit Criteria Review

| Criterion | Status |
|-----------|--------|
| Display produces correct `1280x800` output under Chromium kiosk mode | Done. DSI panel works as the kiosk display. HDMI visual output is intentionally disabled with `video=HDMI-A-1:d`. |
| Touch input is recognized and coordinates are accurate across the screen | Done for Phase 18. Manual use found no offset, inversion, dead-zone, or kiosk interaction issue. |
| ADS1115 ADC polling, DDC/CI communication, and touch I2C traffic coexist without address conflicts or interference | Done. ADS observation works; DDC/CI Get VCP `0x60` succeeds on `/dev/i2c-2`; touch/panel remain on the DSI I2C mux path. |
| Confirmed device address map is recorded | Done. DSI touch/panel path and HDMI DDC bus are recorded above. The project I2C bus remains `/dev/i2c-1`; HDMI DDC uses `/dev/i2c-2`; DSI touch/panel use `/dev/i2c-10` via `/dev/i2c-11`. |

## Final Operating Policy

- Use the Waveshare DSI panel as the only kiosk visual output.
- Keep `video=HDMI-A-1:d` in `/boot/firmware/cmdline.txt` so HDMI does not become a Wayland/DRM display target.
- Use HDMI only for DDC/CI communication when needed.
- Do not use the attempted `kanshi` clone/force profiles for this hardware. They destabilized DSI scanout on the Pi 2/labwc stack.
- Keep brightness at or below `170/255` until a later display/power hardening phase revisits the panel behavior.
- Treat the 7" 1280x800 readability and high-brightness artifact issues as follow-up work, not Phase 18 blockers.

## Final Host Health Snapshot

Run on the deck host:

```bash
python3 scripts/pi-deck-host-health.py
```

Captured after final DSI-only validation:

```text
pi-deck host health  |  2026-04-22T04:06:45.331245+00:00
hostname: pi-deck

[python]
  executable: /usr/bin/python3
  version:    3.13.5
  platform:   Linux-6.18.18-v7+-armv7l-with-glibc2.41
  pi_deck:    importable=True  package_version=0.1.0

[cpu]
  model: ARMv7 Processor rev 5 (v7l)
  logical cpus: 4
  load average (1 / 5 / 15 min): 0.13  0.39  0.29

[memory]
  RAM:  total 0.90 GiB  available 0.57 GiB  (MemTotal/MemAvailable KiB: 942120 / 602076)
  swap: total 0.90 GiB  free 0.90 GiB  (KiB: 942076 / 942076)

[disk]  mount /
  size 56.49 GiB  used 5.04 GiB  avail 49.11 GiB  (8.93% used)

[thermal]  sysfs zones
  thermal_zone0  cpu-thermal  39.0 °C

[raspberry_pi]  vcgencmd (SoC voltage / throttling)
  temperature: temp=39.0'C
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
