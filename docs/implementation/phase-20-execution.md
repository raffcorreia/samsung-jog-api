# Phase 20 Execution Record

## Purpose

Track **Phase 20: Raspberry Pi 5 Rebuild and Display Performance Validation** per [Implementation Plan](./plan.md).

## Status

**Started:** 2026-04-28.

**Closed:** 2026-04-29. Partial close — display quality items deferred to replacement panel arrival.

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

## Execution Log

- 2026-04-28: Full `apt-get full-upgrade` + `autoremove` run. Packages updated: ntfs-3g, libntfs-3g89t64, libngtcp2-16, libngtcp2-crypto-gnutls8. Initramfs regenerated. 0 packages remaining after upgrade.
- 2026-04-28: EEPROM bootloader updated from `1746713597` (2025-05-08) to `1765222194` (2025-12-08) via `rpi-eeprom-update -a`. Verified up to date after reboot. pi-deck service healthy post-reboot.
- 2026-04-28: Full `apt-get upgrade` run after initial setup. Packages updated: ntfs-3g, libntfs-3g89t64, libngtcp2-16, libngtcp2-crypto-gnutls8. Initramfs regenerated. Pi healthy post-upgrade, 0 packages remaining.
- 2026-04-28: Phase 1 host cleanup completed on Pi 5 (hostname `pi-deck5`, Debian 13 Trixie, kernel 6.12.75). Removed avahi-daemon, bluez, cloud-init, rpi-connect-lite, udisks2 and their deps. Package count reduced from 645 → 583.
- 2026-04-28: IPv6 connectivity absent on Pi 5 network. Fixed by adding `/etc/apt/apt.conf.d/99force-ipv4` (`Acquire::ForceIPv4 "true"`). Required before any apt operation.
- 2026-04-28: Phase 9 desktop stack installed (lightdm, rpd-wayland-core, Chromium, unclutter, python3-venv). `lgpio` build required `swig`, `python3-dev`, and `liblgpio-dev` — installed via apt before pip succeeded.
- 2026-04-28: Phase 12 deploy completed via `scripts/deploy.sh`. Version `0.1.0+r2`, `PI_DECK_HARDWARE=live`, service active.
- 2026-04-28: DSI display enabled. Added to `/boot/firmware/config.txt` under `[all]`: `dtparam=i2c_arm=on` and `dtoverlay=vc4-kms-dsi-waveshare-panel,8_0_inch`. Added `video=HDMI-A-1:d video=HDMI-A-2:d` to `/boot/firmware/cmdline.txt`. After reboot: `card2-DSI-2` connected at `1280x800`, Goodix touch ID 9271 registered, backlight at `/sys/class/backlight/11-0045`. Note: display connector name on Pi 5 is `DSI-2`, not `DSI-1` as on Pi 2 — update any scripts that reference `DSI-1` by name.
- 2026-04-28: I2C bring-up: `dtparam=i2c_arm=on` was present in config.txt but `i2c-dev` kernel module was not loaded, so no `/dev/i2c-*` devices appeared. Fixed by `sudo modprobe i2c-dev` and adding `i2c-dev` to `/etc/modules`. Installed `i2c-tools` (binary at `/usr/sbin/i2cdetect` — not in default SSH PATH, use full path or `sudo`). Scan results: i2c-1 (project bus) shows ADS1115 at `0x48`; i2c-11 (display bus) shows Goodix touch at `0x14` and backlight controller at `0x45` (both `UU` — owned by kernel driver, correct).
- 2026-04-28: Kiosk autostart `.desktop` file was not installed to `~/.config/autostart/` (install script ran as root, wrote to root's home). Fixed manually: `pi-deck-kiosk.desktop` copied to `/home/rafael/.config/autostart/` with `@REPO_ROOT@` substituted. Chromium kiosk launched successfully in current session.
- 2026-04-29: GPIO backend confirmed: `hardware_facade._gpiozero_pin_factory_for_live()` auto-selects `lgpio` on Pi 5 (lgpio available in venv → `GPIOZERO_PIN_FACTORY=lgpio`). Falls back to `rpigpio` only if lgpio is absent. No manual override required.
- 2026-04-29: Jog key observation (KEY_ADC2) validated end-to-end on Pi 5 — physical key presses register correctly in the UI via the running service.
- 2026-04-29: DDC bus confirmed available on Pi 5.
- 2026-04-29: Touch input validated on Pi 5 — touch events received and mapped correctly in Chromium kiosk.
- 2026-04-29: Sustained kiosk run — Pi 5 ran the full kiosk all day with no observed instability, crashes, or throttling. `get_throttled=0x0` throughout.
- 2026-04-29: WS responsiveness confirmed excellent — bus events appear in the kiosk UI with no perceptible lag, indistinguishable from a desktop or phone browser. This directly resolves the primary Pi 2 performance complaint.

## Known Issues and Observations

### DSI backlight reset on DRM takeover (resolved)
During boot the kernel framebuffer driver initializes the Waveshare LP8557 backlight controller at full brightness — the boot terminal is visible. When labwc starts and takes over the DRM/KMS output, the DSI panel is re-initialized and the backlight controller's brightness register is reset to 0. The sysfs file (`/sys/class/backlight/11-0045/brightness`) retains its cached value, so `display_power.read_brightness_raw()` reports the old number while the screen is physically black. Writing any value to sysfs sends a fresh I2C command to the LP8557 and wakes the backlight.

**Fix:** `~/.config/labwc/autostart` writes the persisted brightness value to sysfs 4 seconds after labwc starts (after the DRM takeover settles). Brightness is now persisted to `~/.pi-deck-brightness` (raw int) by `DisplayService` on every `set_brightness_pct()` call and on `power_off()`. On reboot the autostart reads that file and restores the exact level the user last set.

### Backlight path differs from Pi 2 (resolved)
Pi 2 exposes the backlight at `/sys/class/backlight/10-0045/`; Pi 5 at `/sys/class/backlight/11-0045/`. `display_power.py` and `display_service.py` were hardcoded to the Pi 2 path. Fixed by auto-discovery: scan `/sys/class/backlight/` for any entry ending in `-0045`.

### DSI output name differs from Pi 2 (resolved)
Pi 2 reports the DSI connector as `DSI-1`; Pi 5 as `DSI-2`. `display_power.py` was hardcoded to `DSI-1` for both wlr-randr power control and power state parsing. Fixed by auto-discovery: parse `wlr-randr` output for the first `DSI-*` entry at runtime.



### Small circle rendering quality — deferred

Small circular UI elements (LED indicator ~28px, record button ~48px) show a visible mesh/grid texture on the physical panel. Two causes are likely contributing:

1. **Display defect:** the damaged panel (see below) creates horizontal banding along pixel rows that is more visible on smooth gradient surfaces than on high-contrast text. This may resolve with the replacement unit.
2. **Pixel density:** at 28–48px on a 216 PPI panel with 1:1 DPR, there are too few physical pixels for clean anti-aliasing on curves. The center power button (~108px CSS circle) looks fine — size is the key variable.

Approaches evaluated during Phase 20: CSS `border-radius`, SVG with radial gradients + blur filters, SVG with flat fills + CSS `drop-shadow`. None fully resolved the texture at these sizes.

Candidates for a later polish pass:
- Supersampling: render SVG at 2× inside a clipped container, scale down with `transform: scale(0.5)`
- Increase element sizes (LED → ~40px, record button → ~64px)
- Redesign to shapes that read cleanly at small sizes (rounded-square LED, stroke-only ring for record)

**Hold judgment until the replacement display arrives.** If the mesh texture is primarily the panel defect, it may resolve without any code change.

### Click events too brief for monitor recognition on Pi 5 (not observed on Pi 2)

The Pi 5's faster CPU causes browser click events to complete too quickly for the monitor's JOG key debounce logic to register them. A brief hold (~100–200 ms) is required for the monitor to recognise a click. This was not observed on the Pi 2. Root cause is likely that the Pi 5 dispatches and resolves the pointer event faster than the Pi 2, shortening the effective contact time seen by the JOG drive circuit. Needs investigation to determine whether the fix is a software-side click duration floor, a pulse duration adjustment in the drive code, or both.

### Display unit defective — invalidates display quality comparison

The display unit received for Phase 20 has a physical crack/damage causing multiple confirmed symptoms:

**Horizontal banding across the full panel:** Regular, evenly-spaced dark horizontal bands run across the entire active area — through color swatches, text, black regions, and white regions equally. This is characteristic of horizontal LCD electrode rows failing from physical damage. Visible on the color/edge validation page (`/color-check`) and on the main UI. This is not a rendering or software artifact.

**Dead zone at the top:** A large dark band at the very top of the panel corresponds to the crack site. A black spot is also present in the top-right corner.

**Color quality degraded:** All colors appear undersaturated and washed out because the horizontal dark bands are overlaid on every pixel, averaging down perceived brightness and saturation across the full panel. This makes it impossible to draw meaningful conclusions about the Pi 5 display color quality or compare it against Pi 2.

**Full brightness instability:** Setting brightness to 100% (255 raw) destabilizes the panel on Pi 5, the same failure mode seen on Pi 2 at high brightness. This is attributed to the physical damage causing irregular power draw in the affected areas rather than a Pi 5 power delivery limitation.

**Conclusion:** The current display unit is too damaged to evaluate Pi 5 display quality, validate color rendering, or compare brightness behavior against Pi 2 findings. All display quality observations from Phase 20 are invalidated by the panel defect. A replacement unit has been requested. The Pi 5 vs Pi 2 display comparison must be repeated on a healthy panel before any conclusions can be drawn.

### Display 5V reconnect causes shutdown on Pi 5 (worse than Pi 2)

Disconnecting and reconnecting the display's 5V power while the Pi is running causes a **full shutdown** on Pi 5, not just a reset as observed on Pi 2. The Pi 5 does not recover — it powers off completely and requires a manual power cycle.

The root cause is the same: display power inrush on reconnect pulls the shared 5V rail, but the Pi 5 appears more sensitive to the transient, interpreting it as an under-voltage fault and triggering a clean shutdown rather than a brown-out reset.

**Consequence:** physical display power cycling is completely unusable with the current wiring on Pi 5. Backlight-only software off (`brightness=0` + `wlr-randr --off`) remains the only safe display power-saving mechanism.

**Required for true display power-off:** an external 5V supply for the display, independent of the Pi GPIO header. This is a PCB-phase requirement — see Phase 19 hardware limitation note for the GPIO-controlled high-side switch design. Until the PCB phase, do not disconnect the display's 5V connector while the Pi is running.

## Power Measurements

Measured on Pi 5 (`pi-deck5`) with the active cooler (fan) **off**. Display brightness at "100%" refers to the capped maximum of `170/255` raw (the Phase 18 cap was still in place during these measurements).

| State | Voltage | Current | Power | Notes |
|-------|---------|---------|-------|-------|
| Display on, 100% brightness (170/255 raw), fan off | 5.02 V | 0.98 A | 4.92 W | Kiosk running, idle |
| Display off (backlight 0 + wlr-randr --off), fan off | 5.05 V | 0.60 A | 3.03 W | Software display-off |

**Delta:** software display-off saves **0.38 A / 1.91 W** on Pi 5 at capped brightness.

| State | Voltage | Current | Power | Notes |
|-------|---------|---------|-------|-------|
| Pi halted (`sudo shutdown -h now`), no display, USB-C still connected | 5.09 V | 0.34 A | 1.73 W | Pi powered off but supply connected |

**Standby concern:** the Pi 5 has no hardware power switch. After a software halt the board draws **0.34 A / 1.73 W** continuously as long as the USB-C supply is connected. There is no idle-zero state without physically unplugging the supply. For a desk installation that runs 24/7 this is a long-term energy concern; for a device left unattended for days it is also a thermal concern. A hardware power switch or a smart-plug arrangement will be required for a fully power-managed installation — noted as a future hardware consideration.

### Pi 2 vs Pi 5 comparison

| State | Pi 2 (Phase 18) | Pi 5 (Phase 20) |
|-------|-----------------|-----------------|
| Display off / brightness 0 | 4.93 V / 0.53 A | 5.05 V / 0.60 A |
| Display on at safe brightness ceiling | 4.90 V / 0.60 A (51/255, ~30%) | 5.02 V / 0.98 A (170/255, 100% capped) |

Pi 5 idle draw is higher than Pi 2 (~0.60 A vs ~0.53 A display-off), consistent with the Pi 5 SoC being significantly more capable. The Pi 5 supply voltage holds steadier under load (5.02 V at nearly 1 A vs Pi 2 sagging to 4.78 V at 0.93 A), confirming better power delivery.

**Note:** these measurements used a defective display unit. Repeat on the replacement panel, and re-test at uncapped full brightness (255/255) once a healthy panel is available to establish the true Pi 5 ceiling.

## GPIO Schema

Use [Phase 20 Raspberry Pi 5 GPIO Schema](../hardware/pi5-gpio-schema.md).

## Evidence Checklist

- ✅ Pi 5 hardware, storage, OS image, power supply, and hostname recorded (`pi-deck5`, Pi 5 Model B Rev 1.1, 16 GiB RAM)
- ✅ `pi-deck.service` active on Pi 5
- ✅ Chromium kiosk starts automatically after reboot (via `~/.config/labwc/autostart`)
- ✅ `scripts/deploy.sh` targets the Pi 5 and increments the visible version (r14 at close)
- ✅ `PI_DECK_HARDWARE=live` works on Pi 5
- ✅ GPIO backend confirmed: `lgpio` auto-selected by `hardware_facade`
- ✅ Project I2C bus (i2c-1, ADS1115 at 0x48), DSI touch/panel bus (i2c-11), and backlight sysfs path (`/sys/class/backlight/11-0045/brightness`) recorded
- ✅ DDC bus confirmed available on Pi 5
- ✅ `video=HDMI-A-1:d video=HDMI-A-2:d` confirmed required for Pi 5 (two HDMI ports)
- ✅ Xwayland mode confirmed required (`--disable-gpu-vsync` needed on Pi 5)
- ✅ Color/edge validation page inspected — defective panel; see Known Issues
- ✅ Sustained kiosk run completed — full day, no instability or throttling
- ✅ Final host health snapshot recorded
- ⏳ Phase 1 host-prep artifacts under `docs/investigation/host-prep/` — not captured (non-blocking)
- ⏳ Brightness range and artifact threshold re-test — deferred to replacement panel
- ⏳ Touch re-validation on healthy panel — deferred to replacement panel

## Pi 2 Baseline to Compare

Use the Phase 18 and Phase 19 execution records as the baseline:

| Area | Pi 2 baseline | Pi 5 result |
| --- | --- | --- |
| Kiosk resolution | `1280x800` DSI | ✅ `1280x800` DSI — confirmed |
| Touch | working, no observed offset | ✅ Confirmed working — re-validation on healthy panel deferred |
| Safe brightness cap | `170/255` through UI/API | ⏳ Cap removed (255/255 now); full validation deferred to healthy panel |
| High-brightness artifacts | artifacts above the validated safe range | ⏳ Defective panel — cannot conclude |
| Chromium mode | Xwayland selected for subpixel rendering | ✅ Xwayland confirmed; `--disable-gpu-vsync` additionally required on Pi 5 |
| Display power off | backlight `0` plus `wlr-randr DSI-1 --off` | ✅ Same via `DSI-2` (auto-discovered); physical 5V reconnect causes full shutdown |
| HDMI policy | visual output disabled, DDC retained | ✅ Both `HDMI-A-1` and `HDMI-A-2` disabled; DDC confirmed available |
| Idle host health | no active throttle at Phase 19 close | ✅ `get_throttled=0x0`; runs ~5 °C hotter at idle — expected, within safe range |
| Perceived responsiveness | unsatisfactory on Pi 2 | ✅ **Resolved — indistinguishable from desktop browser** |

## Host Health Snapshot

Run on Pi 5 (`pi-deck5`) 2026-04-29 after full day of kiosk operation (deploy r11):

```text
temperature:    49.4°C
get_throttled:  0x0  (no flags)
uptime:         8 min (after reboot)
load average:   0.01 / 0.04 / 0.01
RAM:            15 GiB total, 831 MiB used, 15 GiB available
swap:           2.0 GiB total, 0 used
disk (/):       58 GiB total, 5.6 GiB used (11%)
pi-deck:        0.1.0+r11, hardware=live, control_state=idle
```

### Earlier snapshot — 2026-04-28 after Phase 20 bring-up (deploy r6, post-reboot idle):

```text
pi-deck host health  |  2026-04-29T03:08:25.530055+00:00
hostname: pi-deck5

[python]
  executable: /usr/bin/python3
  version:    3.13.5
  platform:   Linux-6.12.75+rpt-rpi-2712-aarch64-with-glibc2.41
  pi_deck:    importable=False  package_version=None

[cpu]
  model: Raspberry Pi 5 Model B Rev 1.1
  logical cpus: 4
  load average (1 / 5 / 15 min): 0.02  0.04  0.03

[memory]
  RAM:  total 15.84 GiB  available 15.08 GiB  (MemTotal/MemAvailable KiB: 16608176 / 15815504)
  swap: total 2.00 GiB  free 2.00 GiB  (KiB: 2097136 / 2097136)

[disk]  mount /
  size 57.97 GiB  used 5.61 GiB  avail 49.95 GiB  (9.68% used)

[thermal]  sysfs zones
  thermal_zone0  cpu-thermal  48.5 °C

[raspberry_pi]  vcgencmd (SoC voltage / throttling)
  temperature: temp=48.8'C
  voltage core: volt=0.8559V
  voltage sdram_c: volt=0.6000V
  voltage sdram_i: volt=0.6000V
  voltage sdram_p: volt=1.1000V
  get_throttled: throttled=0x0
  flags set: (none)

[systemd]
  pi-deck.service: active
  lightdm.service: active

[pi-deck HTTP]
  GET http://127.0.0.1:8756/health
  ok: True  body: '{"status":"ok","version":"0.1.0"}'
```

**Pi 2 baseline comparison (Phase 19):** CPU 44.4 °C / 0.90 GiB RAM / load ~0.86. Pi 5: CPU 48.8 °C / 15.84 GiB RAM / load ~0.03. Pi 5 runs ~5 °C hotter at near-zero load compared to Pi 2 under moderate load — the Pi 5 SoC dissipates more heat even at idle due to its higher transistor count and base power consumption. The Pi 5 throttle threshold is 85 °C; no throttle flags were observed. The active cooler (fan) was off during all Phase 20 measurements — enabling it will reduce temperatures further. The perceived warmth when touching the cooler is real and expected.

## Pi 5 vs Pi 2 Comparison Summary

| Area | Pi 2 baseline | Pi 5 result |
|------|---------------|-------------|
| Kiosk resolution | `1280x800` DSI | `1280x800` DSI |
| Touch | Working, no observed offset | Not yet re-validated on healthy panel |
| Safe brightness ceiling | `170/255` via UI/API (power-path limited) | `170/255` measured; full `255/255` not validated on healthy panel |
| High-brightness artifacts | Artifacts above ~220/255 even on good supply | Defective panel — cannot conclude |
| Display color quality | Baseline | Defective panel — cannot conclude |
| Chromium mode | Xwayland for subpixel rendering | Same — Xwayland required + `--disable-gpu-vsync` |
| Display power off | Backlight `0` + `wlr-randr DSI-1 --off` | Same via DSI-2; physical 5V reconnect causes full shutdown (worse than Pi 2 reset) |
| HDMI policy | Visual output disabled, DDC retained | Same; both `HDMI-A-1` and `HDMI-A-2` must be disabled |
| Idle temperature | ~44–47 °C (moderate load) | ~49 °C (near-zero load) — runs hotter at idle; active cooler off |
| Throttling | `0x0` at Phase 19 close | `0x0` — no throttle flags observed |
| RAM | 0.90 GiB total | 15.84 GiB total |
| **UI / WS responsiveness** | **Noticeably sluggish — lag between hardware events and UI updates** | **Indistinguishable from desktop browser — no perceptible lag on bus WS messages** |
| Perceived kiosk responsiveness | Unsatisfactory on Pi 2 | Resolved on Pi 5 |

## Decision

The Pi 5 resolves the primary performance complaint from Phase 19: WebSocket bus event responsiveness is now indistinguishable from a desktop or phone browser. This was the key open question for the Pi 5 upgrade and it is answered positively.

Remaining open items before the Pi 5 comparison can be fully closed:
- Repeat display quality, brightness ceiling, and color validation on the replacement panel
- Validate touch on the replacement panel
- Decide whether future phases proceed on Pi 5 as the primary target
