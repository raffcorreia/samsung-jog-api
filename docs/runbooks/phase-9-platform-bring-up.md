# Phase 9: Local Platform Bring-Up

## Purpose

Bring the control-deck host to the [Solution Overview — Host platform design](../design/solution-overview.md) baseline:

- `systemd`-supervised `pi-deck` HTTP server (serves the React **JOG console** from `pi_deck/static`; build via `frontend/npm run build`)
- daily rotated file logs with long retention
- Chromium kiosk pointed at `http://127.0.0.1:8756/` — the **JOG console** UI (after a graphical session exists)
- documented recovery: `Restart=on-failure` on the service; kiosk restarts with session login

## Prerequisites

- Raspberry Pi OS with network access
- Repository clone on the Pi (this document assumes `~/samsung-jog-api`, matching the systemd unit template)
- SSH access for setup

## 1. Install the backend service

From the repository root on the Pi:

```bash
chmod +x scripts/host/install_pi_deck_systemd.sh scripts/kiosk/pi-deck-chromium-kiosk.sh
sudo ./scripts/host/install_pi_deck_systemd.sh
```

Run the installer with `sudo` so it can write `/etc/systemd/system/pi-deck.service`. The script substitutes `@REPO_ROOT@`, `@SERVICE_USER@`, and `@SERVICE_HOME@` in `config/systemd/pi-deck.service`. By default it uses `SUDO_USER` (the account that invoked `sudo`) as the service user. To override:

```bash
sudo PI_DECK_SERVICE_USER=pi ./scripts/host/install_pi_deck_systemd.sh
```

The unit sets `HOME` and `PI_DECK_LOG_DIR` to explicit paths under that user’s home so logging never tries to create `/root/.local/...` when the process drops privileges.

This creates `backend/.venv`, installs `pi-deck` in editable mode, installs `/etc/systemd/system/pi-deck.service`, enables and starts the unit.

Check:

```bash
systemctl status pi-deck
curl -sf http://127.0.0.1:8756/health
journalctl -u pi-deck -n 50 --no-pager
```

Logs on disk (daily rotation, ~93 retained files):

```text
~/.local/share/pi-deck/logs/pi-deck.log
```

Environment overrides (optional):

| Variable | Default | Meaning |
|----------|---------|---------|
| `PI_DECK_HOST` | `0.0.0.0` | Bind address (`0.0.0.0` = LAN + localhost; use `127.0.0.1` only if you refuse non-local connections) |
| `PI_DECK_PORT` | `8756` | Listen port |
| `PI_DECK_LOG_DIR` | `~/.local/share/pi-deck/logs` | Directory for `pi-deck.log` |
| `PI_DECK_HARDWARE` | `mock` (default in `config/systemd/pi-deck.service`) | **`live`** only after GPIO init works on this Pi. If `live` fails during startup, **`pi-deck` never listens on 8756**, **`/health` never succeeds**, and the [kiosk script](../../scripts/kiosk/pi-deck-chromium-kiosk.sh) **exits without launching Chromium** (it waits up to ~120s for `/health`). Use `sudo systemctl edit pi-deck` to set `Environment=PI_DECK_HARDWARE=live` when ready. |

Edit the unit with `sudo systemctl edit pi-deck` to add `Environment=` lines, then `sudo systemctl daemon-reload && sudo systemctl restart pi-deck`.

## 2. Graphical session and kiosk (deck display)

**Kiosk cannot work** while the Pi boots to the text console only (`multi-user.target`). There must be a graphical session, Chromium, and an autostart entry. Symptoms: blank display, no Chromium, `systemctl is-active display-manager` → `inactive`.

If the Pi currently boots to multi-user (console only), install a desktop stack once:

```bash
sudo ./scripts/host/phase9_install_desktop_stack.sh
sudo reboot
```

After reboot, the system should land in a graphical session logged in as your user.

Install the autostart entry so Chromium opens fullscreen to the local app:

```bash
chmod +x scripts/host/install_pi_deck_kiosk_autostart.sh
./scripts/host/install_pi_deck_kiosk_autostart.sh
```

Log out and back in, or reboot, to verify Chromium loads the **JOG console** (hero, controls, live log).

The kiosk script (`scripts/kiosk/pi-deck-chromium-kiosk.sh`) waits for `/health` before launching. **Pointer hiding:** on X11 it runs `unclutter` when installed; on **Wayland** it runs `wlrctl pointer hide` when that tool is available ([Phase 11](../implementation/phase-11-execution.md) polish). If the pointer still shows, install `wlrctl` or use X11 — see the [implementation plan](../implementation/plan.md#phase-9-local-platform-bring-up) history.

After changing the React UI, rebuild `frontend/` and restart `pi-deck` (or rsync `backend/src/pi_deck/static/`); refresh the kiosk session if Chromium cached an old bundle.

## 3. Recovery checks

- **Backend crash:** `systemctl status pi-deck` should show automatic restart (`Restart=on-failure`).
- **Reboot:** after `sudo reboot`, `curl http://127.0.0.1:8756/health` should succeed once networking is up (service starts after `network-online.target`).
- **Kiosk:** if Chromium dies, restarting the graphical session (logout/login) relaunches autostart; the backend keeps running independently.

## 4. “Default Keyring” / GNOME Keyring password prompt (autologin)

With **LightDM autologin**, PAM does not unlock **GNOME Keyring**, so you may see a dialog asking to set or unlock the default keyring.

For an appliance/kiosk host you usually want to avoid that prompt:

1. Run once as the graphical user (not `root`):

   ```bash
   chmod +x scripts/kiosk/pi-deck-disable-gnome-keyring-autostart.sh
   ./scripts/kiosk/pi-deck-disable-gnome-keyring-autostart.sh
   ```

2. The kiosk launcher already passes **`--password-store=basic`** to Chromium so it does not rely on the GNOME keyring for its password store.

3. **Reboot** or log out and back in.

If a prompt is already on screen, you can **Cancel** it after applying the steps above; the next session should not start the keyring components the same way.

## 5. Changing the clone path

`config/systemd/pi-deck.service` uses `@REPO_ROOT@` placeholders. Re-run `install_pi_deck_systemd.sh` with the absolute path to the repository root, or edit the installed unit under `/etc/systemd/system/pi-deck.service`.

## Host health snapshot

After bring-up, capture a baseline on the deck with:

```bash
python3 scripts/pi-deck-host-health.py
```

Use the **default text output** in Markdown execution records. `--json` is optional (tooling/archives only), not the main documentation format.

See [Phase 9 execution record](../implementation/phase-9-execution.md#host-health-snapshot-baseline) for an example. Feature phases (**10–19**) must record an updated snapshot when closing the phase ([Host health gate](../implementation/plan.md#host-health-gate-feature-phases-1019)).

## Related documents

- [Implementation plan — Phase 9](../implementation/plan.md#phase-9-local-platform-bring-up)
- [Code guidelines — lifecycle](../development/code-guidelines.md#lifecycle-across-implementation-phases)
- [Prepare Raspberry Pi](prepare-raspberry-pi.md) (Phase 1 baseline)
