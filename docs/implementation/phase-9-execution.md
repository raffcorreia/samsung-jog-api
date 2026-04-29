# Phase 9 Execution Record

**Status:** complete (repository + Pi bring-up scripts; kiosk verified after graphical stack is installed).

**Date:** 2026-04-13

## Summary

Phase 9 delivers a supervised local runtime aligned with [Solution Overview — Host platform design](../design/solution-overview.md):

- **`pi-deck` process:** FastAPI serves `/health`, static UI at `/` (Phase 11+ **JOG console** built from `frontend/` into `pi_deck/static`), default bind on the appliance is `0.0.0.0:8756` via `PI_DECK_HOST` in the unit; launched via `pi-deck` console script.
- **`systemd`:** `config/systemd/pi-deck.service` template (`@REPO_ROOT@`) installed by `scripts/host/install_pi_deck_systemd.sh` (creates venv, editable install, enables service).
- **Logging:** `pi_deck.logging_setup` uses `TimedRotatingFileHandler` (midnight rotation, 93 backups) plus stderr for `journalctl`; default directory `~/.local/share/pi-deck/logs`.
- **Kiosk:** `scripts/kiosk/pi-deck-chromium-kiosk.sh` opens fullscreen to the JOG UI, waits for `/health`, optional pointer hide (`unclutter` / `wlrctl`), Wayland uses `--ozone-platform=wayland`; `pi-deck-kiosk.desktop` autostart via `scripts/host/install_pi_deck_kiosk_autostart.sh`.
- **Desktop stack (optional on headless images):** `scripts/host/phase9_install_desktop_stack.sh` installs `lightdm`, `rpd-wayland-core`, `chromium`, sets `graphical.target`, runs `raspi-config nonint do_boot_behaviour B4` with `USER` set to the deck account.

## Operational entry points

| Document / script | Role |
|-------------------|------|
| [Phase 9 platform bring-up runbook](../runbooks/phase-9-platform-bring-up.md) | End-to-end steps |
| `scripts/host/install_pi_deck_systemd.sh` | Venv + systemd unit |
| `scripts/host/phase9_install_desktop_stack.sh` | Desktop + Chromium (sudo) |
| `scripts/host/install_pi_deck_kiosk_autostart.sh` | XDG autostart for kiosk |
| [`scripts/pi-deck-host-health.py`](../../scripts/pi-deck-host-health.py) | Host + Python snapshot (CPU, memory, disk, thermals, Pi `vcgencmd`, throttling, `pi-deck` / `lightdm`, HTTP health) |

## Exit criteria (from plan)

| Criterion | Evidence |
|-----------|----------|
| Deck boots into application without manual intervention | After desktop install + autostart, graphical login launches Chromium to localhost; backend starts at boot via `pi-deck.service`. |
| Kiosk runtime recovers from process failures | `Restart=on-failure` on `pi-deck.service`; kiosk relaunches on session restart if Chromium exits. |

## On-device verification (2026-04-13)

- Deployed to the deck host via `rsync` to `~/samsung-jog-api` and `sudo ./scripts/host/install_pi_deck_systemd.sh`.
- `curl http://127.0.0.1:8756/health` returns `{"status":"ok"}`; `systemctl restart pi-deck` restores the listener.
- The host was initially **console-only** (`multi-user.target`); full-screen Chromium kiosk requires `scripts/host/phase9_install_desktop_stack.sh` (or equivalent) plus `install_pi_deck_kiosk_autostart.sh` — see the runbook.

## Host health snapshot (baseline)

Recorded by running on the deck host **`pi-deck`**:

```bash
python3 ~/samsung-jog-api/scripts/pi-deck-host-health.py
```

The script adds `backend/src` to `sys.path` when run from a repo clone so **`import pi_deck`** works without installing. **Documentation** in execution records uses the **default plain-text** output below (paste into Markdown, e.g. inside a fenced block). **`--json`** is optional for scripts or archives only — **not** the primary format for phase write-ups.

**Captured output (2026-04-13):**

```
pi-deck host health  |  2026-04-13T17:00:23.811076+00:00
hostname: pi-deck

[python]
  executable: /usr/bin/python3
  version:    3.13.5
  platform:   Linux-6.18.18-v7+-armv7l-with-glibc2.41
  pi_deck:    importable=True  package_version=0.1.0

[cpu]
  model: ARMv7 Processor rev 5 (v7l)
  logical cpus: 4
  load average (1 / 5 / 15 min): 0.09  0.08  0.07

[memory]
  RAM:  total 0.90 GiB  available 0.57 GiB  (MemTotal/MemAvailable KiB: 942120 / 600164)
  swap: total 0.90 GiB  free 0.90 GiB  (KiB: 942076 / 942076)

[disk]  mount /
  size 56.49 GiB  used 4.97 GiB  avail 49.18 GiB  (8.79% used)

[thermal]  sysfs zones
  thermal_zone0  cpu-thermal  47.6 °C

[raspberry_pi]  vcgencmd (SoC voltage / throttling)
  temperature: temp=48.7'C
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
  ok: True  body: '{"status":"ok"}'
```

**Review:** `get_throttled` is **`0x0`** (no under-voltage, frequency cap, or thermal throttle flags). Root filesystem **~8.8%** used. RAM available **0.57 GiB** of 0.90 GiB. SoC **~48°C** at idle with **`pi-deck`** and **`lightdm`** active.

Later feature phases (**10–28**) should append a fresh snapshot to their execution records per the [Host health gate](plan.md#host-health-gate-feature-phases-1028).

## Pi 5 Differences (Phase 20 findings — 2026-04-28)

When repeating Phase 9 on a Raspberry Pi 5 running `rpd-labwc` (Raspberry Pi Desktop Wayland session), the following differences apply:

### lgpio build dependencies

`lgpio` (the GPIO backend) requires native code to compile. On Pi 5 the pip build fails unless these are installed first:

```bash
sudo apt-get install -y swig python3-dev liblgpio-dev
```

Run this before `install_pi_deck_systemd.sh` or any `pip install` step.

### Venv root ownership after install script

`install_pi_deck_systemd.sh` must be run with `sudo` to install the systemd unit. On Pi 5 this leaves the virtualenv owned by root. After the install script completes, fix ownership:

```bash
sudo chown -R rafael:rafael ~/samsung-jog-api/backend/.venv
```

Without this, subsequent `pip install` calls in the venv fail with permission errors.

### Kiosk autostart location — labwc, not XDG

The `rpd-labwc` desktop session does **not** process `~/.config/autostart/` (XDG autostart). The install script (`install_pi_deck_kiosk_autostart.sh`) writes the `.desktop` file to that path, which is ignored. On Pi 5 the kiosk launcher must be placed in the labwc autostart file instead:

```bash
cat > ~/.config/labwc/autostart << 'EOF'
#!/bin/sh
# DSI panel backlight resets to 0 when DRM/labwc takes over.
# Re-apply the persisted brightness value 4s after compositor init.
(sleep 4 && brightness=$(cat ~/.pi-deck-brightness 2>/dev/null || echo 170) && bl=$(ls /sys/class/backlight/*-0045/brightness 2>/dev/null | head -1) && [ -n "$bl" ] && echo "$brightness" > "$bl") &
/home/rafael/samsung-jog-api/scripts/kiosk/pi-deck-chromium-kiosk.sh &
EOF
chmod +x ~/.config/labwc/autostart
```

The brightness restore line (line 4) is also required — see Phase 19 Pi 5 differences.

### Install script writes .desktop to root's home

When `install_pi_deck_kiosk_autostart.sh` runs under sudo, it writes `pi-deck-kiosk.desktop` to root's home directory instead of the user's. On Pi 5 the labwc autostart approach above replaces the `.desktop` file mechanism entirely, so this is not a blocking issue — but be aware the `.desktop` file at `~/.config/autostart/pi-deck-kiosk.desktop` under the user account will not be auto-created.

## Deferred from Phase 9

- **Kiosk pointer hiding:** the visible cursor on Wayland (labwc) was intentionally not finalized here; see [Phase 11 — Low-Level JOG Console UI](./plan.md#phase-11-low-level-jog-console-ui) (touch / kiosk polish).

## Follow-on (Phase 10+)

- Replace placeholder static UI with Vite/React build served by the same app.
- Extend API per implementation plan; keep `hardware/` as the integration layer per [Code Guidelines](../development/code-guidelines.md).
