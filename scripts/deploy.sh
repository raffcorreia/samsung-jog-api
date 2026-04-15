#!/usr/bin/env bash
# Canonical deploy: build frontend, sync all code to the Pi, increment the
# persistent deploy counter, reinstall the Python package, restart pi-deck,
# and reload Chromium in kiosk mode.
#
# Run from the repository root on your dev machine (SSH key to the Pi required).
#
# Usage:
#   PI_TARGET=user@pi-hostname ./scripts/deploy.sh
#
# Environment:
#   PI_TARGET   SSH destination — required (e.g. user@pi-hostname or user@192.168.x.x)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ -z "${PI_TARGET:-}" ]; then
    echo "ERROR: PI_TARGET is not set. Example: PI_TARGET=user@pi-hostname ./scripts/deploy.sh" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# 1. Build frontend → backend/src/pi_deck/static/
# ---------------------------------------------------------------------------
echo "==> Building frontend ..."
(cd "${REPO_ROOT}/frontend" && npm run build)

# ---------------------------------------------------------------------------
# 2. Sync code to Pi (no git pull on Pi; dev machine is the source of truth)
# ---------------------------------------------------------------------------
echo "==> Ensuring remote paths exist on ${PI_TARGET} ..."
ssh -o BatchMode=yes "${PI_TARGET}" \
    'mkdir -p ~/samsung-jog-api/backend/src/pi_deck ~/samsung-jog-api/scripts/kiosk ~/samsung-jog-api/scripts/host ~/samsung-jog-api/config'

echo "==> Syncing pi_deck package (+ static/) → ${PI_TARGET}:~/samsung-jog-api/backend/src/pi_deck/ ..."
rsync -avz --delete \
    "${REPO_ROOT}/backend/src/pi_deck/" \
    "${PI_TARGET}:~/samsung-jog-api/backend/src/pi_deck/"

echo "==> Syncing backend/pyproject.toml ..."
rsync -avz \
    "${REPO_ROOT}/backend/pyproject.toml" \
    "${PI_TARGET}:~/samsung-jog-api/backend/"

echo "==> Syncing kiosk launcher ..."
rsync -avz \
    "${REPO_ROOT}/scripts/kiosk/pi-deck-chromium-kiosk.sh" \
    "${PI_TARGET}:~/samsung-jog-api/scripts/kiosk/"
ssh -o BatchMode=yes "${PI_TARGET}" \
    'chmod +x ~/samsung-jog-api/scripts/kiosk/pi-deck-chromium-kiosk.sh'

echo "==> Syncing host scripts ..."
rsync -avz \
    "${REPO_ROOT}/scripts/host/" \
    "${PI_TARGET}:~/samsung-jog-api/scripts/host/"

# ---------------------------------------------------------------------------
# 3. Increment persistent deploy counter on the Pi (~/.pi-deck-deploy)
#    The counter is read by the backend at startup and surfaced in status.version.
# ---------------------------------------------------------------------------
echo "==> Incrementing deploy counter on ${PI_TARGET} ..."
DEPLOY_COUNTER=$(ssh -o BatchMode=yes "${PI_TARGET}" '
    n=0
    if [ -f ~/.pi-deck-deploy ]; then
        n=$(cat ~/.pi-deck-deploy 2>/dev/null || echo 0)
        n=$(echo "$n" | tr -d "[:space:]")
        [ -z "$n" ] && n=0
    fi
    n=$((n + 1))
    echo "$n" > ~/.pi-deck-deploy
    echo "$n"
')
echo "    Deploy counter: ${DEPLOY_COUNTER}"

# ---------------------------------------------------------------------------
# 4. Reinstall Python package + ensure live GPIO mode, then restart pi-deck
# ---------------------------------------------------------------------------
echo "==> Installing Python package and restarting pi-deck on ${PI_TARGET} ..."
ssh -o BatchMode=yes "${PI_TARGET}" 'set -e
cd ~/samsung-jog-api/backend
if [ ! -x .venv/bin/pip ]; then python3 -m venv .venv; fi
.venv/bin/pip install -q -U pip
.venv/bin/pip install -q -e .

# Ensure live GPIO is set in the systemd unit (idempotent)
U=/etc/systemd/system/pi-deck.service
if [ -f "$U" ]; then
    if grep -q "^Environment=PI_DECK_HARDWARE=mock" "$U"; then
        sudo sed -i "s/^Environment=PI_DECK_HARDWARE=mock/Environment=PI_DECK_HARDWARE=live/" "$U"
    fi
    if ! grep -q "^Environment=PI_DECK_HARDWARE=" "$U"; then
        sudo sed -i "/^Environment=PI_DECK_PORT=8756/a Environment=PI_DECK_HARDWARE=live" "$U"
    fi
    sudo systemctl daemon-reload
fi
sudo systemctl restart pi-deck'

# ---------------------------------------------------------------------------
# 5. Wait for the backend to be healthy, then verify status.version
# ---------------------------------------------------------------------------
echo "==> Waiting for pi-deck to become healthy ..."
ssh -o BatchMode=yes "${PI_TARGET}" 'set -e
for i in $(seq 1 15); do
    if curl -sfS --connect-timeout 3 http://127.0.0.1:8756/health >/dev/null 2>&1; then
        echo "Health OK."
        break
    fi
    if [ "$i" -eq 15 ]; then
        echo "ERROR: pi-deck did not become healthy after restart." >&2
        exit 1
    fi
    sleep 1
done
echo "--- /health ---"
curl -sS --connect-timeout 5 http://127.0.0.1:8756/health
echo
echo "--- /api/v1/status ---"
curl -sS --connect-timeout 5 http://127.0.0.1:8756/api/v1/status | head -c 400
echo'

# ---------------------------------------------------------------------------
# 6. Reload Chromium in kiosk mode (best-effort — never fails the deploy)
#    Prefer xdotool F5 (fast, no session disruption).
#    Fall back to pkill + relaunch if xdotool is absent.
# ---------------------------------------------------------------------------
echo "==> Reloading Chromium kiosk ..."
# Use a quoted heredoc so the remote script can freely mix quoting styles
# (single-quoted SSH strings cannot contain nested single quotes).
ssh -T -q -o BatchMode=yes "${PI_TARGET}" << 'REMOTE_CHROMIUM_RELOAD'
    reload_ok=0
    if command -v xdotool >/dev/null 2>&1; then
        if DISPLAY=:0 xdotool search --class chromium key F5 2>/dev/null ||
           DISPLAY=:0 xdotool search --class "chromium-browser" key F5 2>/dev/null; then
            echo "Chromium reloaded via xdotool F5."
            reload_ok=1
        else
            echo "xdotool found but no Chromium window detected; skipping reload."
        fi
    fi
    if [ "$reload_ok" -eq 0 ]; then
        echo "Attempting Chromium restart (kill + relaunch) ..."
        # Capture display env from the running Chromium process *before* killing it
        # so the relaunch can use the same session variables.
        _cpid=$(pgrep -f "chromium" 2>/dev/null | head -1 || true)
        _disp_env=""
        if [ -n "$_cpid" ] && [ -f "/proc/$_cpid/environ" ]; then
            _disp_env=$(tr '\0' '\n' < "/proc/$_cpid/environ" 2>/dev/null \
                | grep -E '^(DISPLAY|XAUTHORITY|WAYLAND_DISPLAY|XDG_RUNTIME_DIR|DBUS_SESSION_BUS_ADDRESS)=' \
                | tr '\n' ' ' || true)
        fi
        # Fall back to sensible defaults if we could not read from the process
        if [ -z "$_disp_env" ]; then
            _uid=$(id -u)
            _rt="/run/user/${_uid}"
            if [ -S "${_rt}/wayland-0" ]; then
                _disp_env="WAYLAND_DISPLAY=wayland-0 XDG_RUNTIME_DIR=${_rt}"
            else
                _disp_env="DISPLAY=:0 XAUTHORITY=${HOME}/.Xauthority"
            fi
        fi
        pkill -f chromium 2>/dev/null || true
        sleep 2
        # shellcheck disable=SC2086
        env ${_disp_env} nohup bash ~/samsung-jog-api/scripts/kiosk/pi-deck-chromium-kiosk.sh \
            >/tmp/pi-deck-kiosk-restart.log 2>&1 &
        echo "Chromium restarted in background (log: /tmp/pi-deck-kiosk-restart.log)."
    fi
REMOTE_CHROMIUM_RELOAD
# Non-zero from Chromium reload is non-fatal — code and service are already updated.
RC=$?
if [ "$RC" -ne 0 ]; then
    echo "  (Chromium reload returned $RC — deploy is still complete; refresh manually if needed)"
fi

echo ""
echo "==> Deploy complete. Counter: r${DEPLOY_COUNTER}. Pi-deck is running at http://${PI_TARGET##*@}:8756/"
