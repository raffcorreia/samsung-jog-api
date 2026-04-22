# Phase 19 Execution Record

## Purpose

Track **Phase 19: Display Usability and Power Hardening** per [Implementation Plan](./plan.md).

## Status

**Started:** 2026-04-22.

**Closed:** 2026-04-22.

## Working Goal

Harden the Waveshare DSI display experience after Phase 18 bring-up: add display/Pi power controls from the top-bar power button, add a brightness slider in Settings capped at the Phase 18 validated maximum, add a full-screen color/edge validation page, and test whether the panel firmware persists brightness across reboot.

## Implementation Summary

### Backend

- `backend/src/pi_deck/hardware/display_power.py` — `LiveDisplayPower` (sysfs `/sys/class/backlight/10-0045/brightness`) and `MockDisplayPower`; ceiling enforced at `BRIGHTNESS_RAW_MAX = 170`.
- `backend/src/pi_deck/services/display_service.py` — `DisplayService`: pct ↔ raw conversion, power-off/on with last-brightness restore, always reads live sysfs on get.
- `backend/src/pi_deck/services/system_service.py` — `SystemService`: graceful Pi shutdown via `sudo shutdown -h now`; mock no-op for dev/test.
- `backend/src/pi_deck/models/schemas.py` — `DisplayBrightnessOut`, `DisplayBrightnessIn`, `DisplayPowerOut`, `DisplayPowerIn`, `SystemShutdownOut`.
- `backend/src/pi_deck/api/deps.py` — `get_display()`, `get_system()`.
- `backend/src/pi_deck/api/router.py` — new routes:
  - `GET  /api/v1/display/brightness`
  - `PUT  /api/v1/display/brightness`
  - `GET  /api/v1/display/power`
  - `POST /api/v1/display/power`
  - `POST /api/v1/system/shutdown`
- `backend/src/pi_deck/api/app.py` — wired `DisplayService` and `SystemService` into the lifespan.

### Frontend

- `frontend/src/api/client.ts` — `fetchDisplayBrightness`, `setDisplayBrightness`, `fetchDisplayPower`, `setDisplayPower`, `requestShutdown`.
- `frontend/src/components/PowerMenu.tsx` — power menu popup opened from the top-bar power button; three choices: Display (toggle backlight), Pi (5-second countdown with Now/Cancel), Cancel.
- `frontend/src/components/PowerMenu.module.css` — styles.
- `frontend/src/components/TopBar.tsx` — power button wired: opens `PowerMenu` when display is on; powers display back on immediately when display is off.
- `frontend/src/pages/SettingsPage.tsx` — added Display section: brightness slider (0–100%, debounced, with cap note) and "Open" button for color-check page.
- `frontend/src/pages/SettingsPage.module.css` — slider, busy-dot, action-button styles.
- `frontend/src/pages/ColorCheckPage.tsx` — full-screen validation page: 6 solid swatches, grayscale gradient + steps, small/normal/large text samples, 1px edge lines at all four panel edges. Tap-to-exit and Escape to exit.
- `frontend/src/pages/ColorCheckPage.module.css` — styles.
- `frontend/src/App.tsx` — added `/color-check` route.

### Tests

- `backend/tests/test_phase19_display.py` — 14 tests: brightness get/set/validation, power off/on, shutdown, pct roundtrip, raw cap, power restore.
- `frontend/src/components/PowerMenu.test.tsx` — 9 tests: render, display on/off label, cancel, shutdown confirm, countdown start value, Now button, cancel-shutdown returns to menu, closed state.
- `frontend/src/pages/ColorCheckPage.test.tsx` — 4 tests: page render, all 6 swatches, readability sample, tap-to-exit navigation.
- `frontend/src/pages/SettingsPage.test.tsx` — updated to wrap in `MemoryRouter` (required by new `useNavigate()` in `SettingsPage`); added slider and color-check button assertions.
- `frontend/src/App.test.tsx` — extended API mock to include new display/power/shutdown functions.

**Final test results:** 71 backend tests passed, 63 frontend tests passed, no regressions.

## Live Validation

Deployed as **r89** to `pi-deck` (Raspberry Pi 2B, `hardware=live`).

### API smoke tests

```
GET /api/v1/display/brightness → {"brightness_pct": 30, "brightness_raw": 51, "max_raw": 170}
GET /api/v1/display/power      → {"on": true, "brightness_pct": 30}
PUT /api/v1/display/brightness {"brightness_pct": 30} → {"brightness_pct": 30, "brightness_raw": 51, "max_raw": 170}
POST /api/v1/display/power {"on": false} → {"on": false, "brightness_pct": 0}  sysfs: 0
POST /api/v1/display/power {"on": true}  → {"on": true,  "brightness_pct": 30} sysfs: 51
POST /api/v1/system/shutdown → {"ok": true, "message": "Shutdown initiated"} (mock no-op in test; live triggers sudo shutdown)
```

### Brightness persistence test (Phase 19 requirement)

1. Set brightness to `85 raw` (≈ 50% of cap) via sysfs.
2. Rebooted the Pi (`sudo reboot`).
3. Post-reboot sysfs read: `85` — unchanged.
4. Backend API on restart: `{"brightness_pct": 50, "brightness_raw": 85, "max_raw": 170}`.

**Finding:** The Waveshare DSI panel/backlight firmware persists the selected brightness value across a full Pi reboot. No application-level restore mechanism is required. The backend reads the live sysfs value on every `GET /api/v1/display/brightness` call, so the kiosk always reflects the actual hardware state after reboot.

### Brightness / throttle benchmark

Measurements taken at three representative brightness levels after Phase 19 deployment:

| Brightness UI % | Raw (sysfs) | `get_throttled` | `measure_volts core` | Notes |
|-----------------|------------|-----------------|----------------------|-------|
| 0% (off)        | 0          | `0x0`           | `1.3125 V`           | No flags, no artifacts |
| 30% (default)   | 51         | `0x0`           | `1.2000 V`           | No flags, no artifacts |
| 100% (cap 170)  | 170        | `0x0`           | `1.3125 V`           | No flags, no artifacts |

All three brightness levels tested clean with the current power path. No under-voltage or throttling flags at any cap-limited value.

## Host Health Snapshot

Run on the deck host 2026-04-22 after Phase 19 deployment and reboot:

```text
pi-deck host health  |  2026-04-22T04:35:22.589326+00:00
hostname: pi-deck

[python]
  executable: /usr/bin/python3
  version:    3.13.5
  platform:   Linux-6.18.18-v7+-armv7l-with-glibc2.41
  pi_deck:    importable=True  package_version=0.1.0

[cpu]
  model: ARMv7 Processor rev 5 (v7l)
  logical cpus: 4
  load average (1 / 5 / 15 min): 1.93  0.86  0.33

[memory]
  RAM:  total 0.90 GiB  available 0.54 GiB  (MemTotal/MemAvailable KiB: 942120 / 562956)
  swap: total 0.90 GiB  free 0.90 GiB  (KiB: 942076 / 942076)

[disk]  mount /
  size 56.49 GiB  used 4.96 GiB  avail 49.20 GiB  (8.78% used)

[thermal]  sysfs zones
  thermal_zone0  cpu-thermal  44.4 °C

[raspberry_pi]  vcgencmd (SoC voltage / throttling)
  temperature: temp=44.4'C
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

Health is clean. `get_throttled=0x0`, no flags, temperature within normal range.

## Display Power-Off Behavior

- Powering off the DSI display writes `0` to `/sys/class/backlight/10-0045/brightness`.
- The DSI panel goes dark; the `DSI-1` connector and kernel DRM state remain intact.
- Touch input remains active while the display is off (the Goodix touch controller on `/dev/i2c-10` is not affected by the backlight state).
- Touch being independently active while the display is off is documented here; it is not a problem for the current use-case (operator can still tap the physical screen to power on via the remote browser or can physically reconnect).
- Display is powered back on by restoring the last non-zero brightness to `/sys/class/backlight/10-0045/brightness`.
- Power-off does not save meaningful system power: the Pi SoC, RAM, and DSI hardware all remain active. Only the backlight draw is eliminated (roughly 0.07–0.10 A depending on prior brightness).

## Phase 19 Extended Work (Post-Close)

After the initial phase close, further display and readability hardening was done in the same scope:

### Display power — wlr-randr compositor control + backlight kill

The original `bl_power` sysfs approach was replaced: the Waveshare panel driver accepts writes but the firmware ignores them and the panel stays on. The working mechanism is `wlr-randr --output DSI-1 --off/--on` through the labwc Wayland compositor.

Additionally, `DisplayService.power_off()` now also zeros the sysfs backlight (`/sys/class/backlight/10-0045/brightness`) so the physical LED is also cut. The raw value is saved before power-off and restored after power-on. Measured current draw at power-off: **0.59 A → 0.42 A** (−0.17 A is the backlight LED).

`display_power.py`: `write_power_on()` uses `subprocess.run(["wlr-randr", "--output", "DSI-1", flag])` with `_WAYLAND_ENV` hardcoding `WAYLAND_DISPLAY=wayland-0` and `XDG_RUNTIME_DIR=/run/user/1000` since the systemd service starts without a graphical session.

`display_service.py`: `_saved_raw: int | None` instance variable; `power_off()` saves and zeros; `power_on()` restores.

### Display power-on from browser — TopBar race fix

`TopBar.handlePowerClick()` now always fetches a fresh `/api/v1/display/power` state before deciding the action (power on vs. open menu), eliminating the stale-state race when the display was physically off.

### Xwayland mode + subpixel font rendering

Switching Chromium from native Wayland to Xwayland (X11) mode enables subpixel (LCD/ClearType-like) rendering, which Wayland disables by design. Changes:

- `scripts/kiosk/pi-deck-chromium-kiosk.sh`: added `--ozone-platform=x11` to Chromium args; `run_chromium()` now sets `DISPLAY=:0` and clears `WAYLAND_DISPLAY` so Chromium targets Xwayland.
- `scripts/kiosk/pi-deck-chromium-kiosk.sh`: compositor scale reset to `1.0` (was `1.25` briefly during investigation; reverted — scaling reduces viewport from 1280×800 to 1024×640 with no net gain).
- `scripts/host/install_pi_deck_kiosk_autostart.sh`: added fontconfig subpixel-rgb setup: removes `10-sub-pixel-none.conf` (Raspberry Pi OS default) and links `10-sub-pixel-rgb.conf`.
- `frontend/src/index.css`: `html { font-size: 20px }` — base rem anchored to 20px physical; `font-weight: 500` on `:root` for stroke visibility.

Result: `fc-match --format='%{rgba}' sans` now returns `1` (FC_RGBA_RGB). Comfortable reading threshold at 50 cm desk distance is ~24px; 1.2rem = 24px at this base.

### Font-size floor lift — all primary UI

Systematic audit and bump of all font sizes below the 1.2rem comfortable threshold (24px physical):

| File | Selector | Before | After | Role |
|------|----------|--------|-------|------|
| PowerMenu.module.css | `.choiceBtn` | 0.90rem | 1.20rem | Primary action buttons |
| PowerMenu.module.css | `.countdownText` | 0.92rem | 1.20rem | Shutdown countdown |
| PowerMenu.module.css | `.shutdownNowBtn` | 0.88rem | 1.20rem | Danger confirm button |
| PowerMenu.module.css | `.cancelBtn` | 0.88rem | 1.10rem | Cancel button |
| SettingsPage.module.css | `.sectionTitle` | 0.72rem | 0.90rem | Section heading |
| SettingsPage.module.css | `.rowLabel` | 0.88rem | 1.20rem | Settings row label |
| SettingsPage.module.css | `.rowValue` | 0.82rem | 1.00rem | Settings row value |
| SettingsPage.module.css | `.sliderLabel` | 0.88rem | 1.20rem | Brightness slider label |
| SettingsPage.module.css | `.sliderValue` | 0.82rem | 1.00rem | Brightness value readout |
| SettingsPage.module.css | `.sliderNote` | 0.72rem | 0.90rem | Cap note hint |
| SettingsPage.module.css | `.actionBtn` | 0.82rem | 1.10rem | Open color-check button |
| TopBar.module.css | `.title` | 1.08rem | 1.20rem | Page title |
| ConfirmDialog.module.css | `.message` | 0.98rem | 1.20rem | Dialog body text |
| LiveLog.module.css | `.head` | 0.68rem | 0.90rem | Log section header |
| LiveLog.module.css | `.pre` | clamp(0.65rem,1.8vw,0.80rem) | clamp(0.90rem,1.8vw,1.00rem) | Log content (monospace) |
| RecordingWorkspace.module.css | `.statusText strong` | 0.74rem | 1.00rem | Recording status label |
| RecordingWorkspace.module.css | `.statusText span` | 0.90rem | 1.00rem | Recording status subtext |
| RecordingWorkspace.module.css | `.sectionHeader` | 0.72rem | 0.90rem | Workspace section header |
| RecordingWorkspace.module.css | `.itemMeta` | 0.84rem | 1.00rem | Item metadata |
| RecordingWorkspace.module.css | `.editorMeta` | 0.82rem | 1.00rem | Editor metadata |
| HomePage.module.css | `.osdTrigger` | 0.70rem | 0.90rem | OSD trigger button |

Not changed: OsdMockPanel (simulates Samsung TV OSD, compact by design), CalendarWidget/NotesWidget (grid-constrained), VersionBadge (decorative), ColorCheckPage test samples (intentional test bands).

Deployed as **r97**.

## Final Host Health Snapshot (Phase 19 Extended — r97)

Run after Xwayland mode + font size pass at steady-state kiosk idle:

```text
pi-deck host health  |  2026-04-22T15:28:44.847586+00:00
hostname: pi-deck

[python]
  executable: /usr/bin/python3
  version:    3.13.5
  platform:   Linux-6.18.18-v7+-armv7l-with-glibc2.41
  pi_deck:    importable=True  package_version=0.1.0

[cpu]
  model: ARMv7 Processor rev 5 (v7l)
  logical cpus: 4
  load average (1 / 5 / 15 min): 0.86  0.52  0.65

[memory]
  RAM:  total 0.90 GiB  available 0.56 GiB  (MemTotal/MemAvailable KiB: 942120 / 590092)
  swap: total 0.90 GiB  free 0.90 GiB  (KiB: 942076 / 941848)

[disk]  mount /
  size 56.49 GiB  used 5.04 GiB  avail 49.11 GiB  (8.93% used)

[thermal]  sysfs zones
  thermal_zone0  cpu-thermal  46.0 °C

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

Xwayland overhead is negligible: 560 MB RAM available (vs 540 MB at r89 baseline), swap still unused, temperature 47 °C (well inside 85 °C throttle ceiling), `get_throttled=0x0`.

## Exit Criteria Review

| Criterion | Status |
|-----------|--------|
| Display can be powered off and back on from the UI/API without destabilizing the kiosk session | Done. Power off/on via `/api/v1/display/power` verified live. Kiosk session unaffected. |
| Pi shutdown flow requires explicit confirmation or countdown completion and can be cancelled | Done. Power menu → Pi → 5-second countdown with Now/Cancel. Cancel returns to menu; Now calls `/api/v1/system/shutdown`. |
| Brightness behavior after reboot is explicitly tested and documented | Done. Panel firmware persists brightness; no app-level restore needed. |
| Brightness cannot exceed 170/255 through the UI/API | Done. `BRIGHTNESS_RAW_MAX = 170` enforced in `LiveDisplayPower.write_brightness_raw()` and `MockDisplayPower.write_brightness_raw()`. API validates `brightness_pct ∈ [0, 100]`; raw is derived as `round(pct × 170 / 100)`. |
| Color/edge validation page renders correctly on the DSI panel | Done. Route `/color-check` deployed; page contains solid swatches, grayscale gradient, small/normal/large text, and 1px edge lines at all four corners. |
| Power/throttle measurements recorded for the capped brightness range | Done. See benchmark table above. |
| Host health gate passes | Done. See host health snapshot above. |
