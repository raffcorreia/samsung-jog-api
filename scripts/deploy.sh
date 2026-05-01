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
# Persist PI_TARGET for the session so you don't need to prefix every run:
#   export PI_TARGET=rafael@10.0.0.116
#   ./scripts/deploy.sh
#
# SSH key auth is required (BatchMode — no password prompts). One-time setup:
#   ssh-keygen -t ed25519 -C "pi-deck-deploy"
#   ssh-copy-id $PI_TARGET
#
# Environment:
#   PI_TARGET     SSH destination — required (e.g. user@hostname or user@192.168.x.x)
#   FORCE_BUILD   Set to 1 to rebuild the frontend even when no source files changed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ -z "${PI_TARGET:-}" ]; then
    echo "ERROR: PI_TARGET is not set." >&2
    echo "  Set it for this session:" >&2
    echo "    export PI_TARGET=user@hostname-or-ip" >&2
    echo "  Then re-run the deploy." >&2
    exit 1
fi

# Check connectivity before wasting time on a build or rsync.
echo "==> Checking connectivity to ${PI_TARGET} ..."
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 -o ConnectionAttempts=1 \
        "${PI_TARGET}" exit 2>/dev/null; then
    echo "ERROR: Cannot reach ${PI_TARGET}." >&2
    echo "  Verify the host is up and your SSH key is authorised, then:" >&2
    echo "    export PI_TARGET=${PI_TARGET}" >&2
    echo "  Re-run the deploy once the host is reachable." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# 1. Build frontend → backend/src/pi_deck/static/
#    Skipped when no frontend source files changed since the last build.
#    Pass FORCE_BUILD=1 to always rebuild.
# ---------------------------------------------------------------------------
_build_marker="${REPO_ROOT}/frontend/node_modules/.deploy-build-stamp"
_needs_build=1

if [ "${FORCE_BUILD:-0}" != "1" ] && [ -f "$_build_marker" ]; then
    # Any tracked change under frontend/src or frontend/public since the stamp?
    _changed=$(git -C "${REPO_ROOT}" diff --name-only HEAD \
        -- frontend/src frontend/public 2>/dev/null)
    _untracked=$(git -C "${REPO_ROOT}" ls-files --others --exclude-standard \
        frontend/src frontend/public 2>/dev/null)
    # Any file newer than the stamp (catches uncommitted edits)?
    _newer=$(find "${REPO_ROOT}/frontend/src" "${REPO_ROOT}/frontend/public" \
        -newer "$_build_marker" 2>/dev/null | head -1)
    if [ -z "$_changed" ] && [ -z "$_untracked" ] && [ -z "$_newer" ]; then
        _needs_build=0
    fi
fi

if [ "$_needs_build" -eq 1 ]; then
    echo "==> Building frontend ..."
    (cd "${REPO_ROOT}/frontend" && npm run build)
    touch "$_build_marker"
else
    echo "==> Frontend unchanged — skipping build."
fi

# ---------------------------------------------------------------------------
# 2. Auto-tag on main + compute version
#    Format on main:   0.1.0+r64
#    Format on branch: 0.1.0+r64-phase-x-implementation
# ---------------------------------------------------------------------------
_branch=$(git -C "${REPO_ROOT}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

# On main: auto-tag HEAD if not already tagged, then push the tag.
if [ "$_branch" = "main" ]; then
    _head_tag=$(git -C "${REPO_ROOT}" tag --points-at HEAD 2>/dev/null \
        | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | head -1 || true)
    if [ -z "$_head_tag" ]; then
        _latest_tag=$(git -C "${REPO_ROOT}" tag --sort=-version:refname 2>/dev/null \
            | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | head -1 || true)
        if [ -z "$_latest_tag" ]; then
            _new_tag="v0.1.0"
        else
            IFS='.' read -r _maj _min _pat <<< "${_latest_tag#v}"
            _new_tag="v${_maj}.${_min}.$((_pat + 1))"
        fi
        echo "==> Auto-tagging HEAD as ${_new_tag} ..."
        git -C "${REPO_ROOT}" tag "${_new_tag}"
        git -C "${REPO_ROOT}" push origin "${_new_tag}" 2>/dev/null && echo "    Tagged and pushed." || echo "    Tagged locally (push skipped — no remote auth)."
    else
        echo "==> HEAD already tagged as ${_head_tag} — skipping auto-tag."
    fi
fi

_git_desc=$(git -C "${REPO_ROOT}" describe --tags --always --long 2>/dev/null || echo "untagged")

# Parse describe output: vX.Y.Z-N-gHASH
if [[ "$_git_desc" =~ ^v?([0-9]+\.[0-9]+\.[0-9]+)-([0-9]+)-g([0-9a-f]+)$ ]]; then
    _tag="${BASH_REMATCH[1]}"
else
    _tag="0.0.0"
fi

if [ "$_branch" = "main" ]; then
    _BRANCH_SUFFIX=""
else
    _branch_slug="${_branch//\//-}"
    _BRANCH_SUFFIX="-${_branch_slug}"
fi

_APP_VERSION_BASE="${_tag}"

# ---------------------------------------------------------------------------
# 3. Sync code to Pi (no git pull on Pi; dev machine is the source of truth)
# ---------------------------------------------------------------------------
echo "==> Ensuring remote paths exist on ${PI_TARGET} ..."
# (Step 3 continues below — _version.py is written after deploy counter is incremented)
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
# 4. Increment persistent deploy counter on the Pi (~/.pi-deck-deploy)
#    Write _version.py with the full version string before the next rsync.
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

APP_VERSION="${_APP_VERSION_BASE}+r${DEPLOY_COUNTER}${_BRANCH_SUFFIX}"
echo "    App version:    ${APP_VERSION}"

# Write _version.py locally so the rsync picks it up.
cat > "${REPO_ROOT}/backend/src/pi_deck/_version.py" << EOF
# Auto-generated by scripts/deploy.sh — do not edit or commit
__version__ = "${APP_VERSION}"
EOF

# Push _version.py to Pi immediately (it was already rsynced above but counter
# was not known yet; send the final file now before the package install step).
rsync -avz \
    "${REPO_ROOT}/backend/src/pi_deck/_version.py" \
    "${PI_TARGET}:~/samsung-jog-api/backend/src/pi_deck/_version.py"

# ---------------------------------------------------------------------------
# 5. Reinstall Python package + ensure live GPIO mode, then restart pi-deck
# ---------------------------------------------------------------------------
echo "==> Installing Python package and restarting pi-deck on ${PI_TARGET} ..."
ssh -o BatchMode=yes "${PI_TARGET}" 'set -e
cd ~/samsung-jog-api/backend
if [ ! -x .venv/bin/pip ]; then python3 -m venv .venv; fi
.venv/bin/pip install -q -U pip
.venv/bin/pip install -q -e .

U=/etc/systemd/system/pi-deck.service
if [ ! -f "$U" ]; then
    echo "ERROR: ${U} is missing — systemd was never set up for pi-deck on this host." >&2
    echo "On the Pi, run once (from repo root):" >&2
    echo "  sudo ./scripts/host/install_pi_deck_systemd.sh \"\$(pwd)\"" >&2
    echo "Or: sudo ./scripts/host/install_pi_deck_systemd.sh \$HOME/samsung-jog-api" >&2
    exit 1
fi

# Ensure live GPIO is set in the systemd unit (idempotent)
if grep -q "^Environment=PI_DECK_HARDWARE=mock" "$U"; then
    sudo sed -i "s/^Environment=PI_DECK_HARDWARE=mock/Environment=PI_DECK_HARDWARE=live/" "$U"
fi
if ! grep -q "^Environment=PI_DECK_HARDWARE=" "$U"; then
    sudo sed -i "/^Environment=PI_DECK_PORT=8756/a Environment=PI_DECK_HARDWARE=live" "$U"
fi
sudo systemctl daemon-reload

sudo systemctl restart pi-deck
_ok=0
for _w in $(seq 1 20); do
    if sudo systemctl is-active --quiet pi-deck; then
        _ok=1
        break
    fi
    if sudo systemctl is-failed --quiet pi-deck 2>/dev/null; then
        break
    fi
    sleep 0.5
done
if [ "$_ok" != "1" ]; then
    echo "ERROR: pi-deck.service is not active after restart (unit failed or exited immediately)." >&2
    echo "--- systemctl status pi-deck.service ---" >&2
    sudo systemctl --no-pager -l status pi-deck.service || true
    echo "--- journalctl -u pi-deck (last 80 lines) ---" >&2
    sudo journalctl -u pi-deck -n 80 --no-pager || true
    exit 1
fi'

# ---------------------------------------------------------------------------
# 6. Wait for the backend to be healthy, then verify status.version
# ---------------------------------------------------------------------------
echo "==> Waiting for pi-deck to become healthy ..."
ssh -o BatchMode=yes "${PI_TARGET}" 'set -e
for i in $(seq 1 30); do
    if curl -sfS --connect-timeout 3 http://127.0.0.1:8756/health >/dev/null 2>&1; then
        echo "Health OK."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "ERROR: /health on 127.0.0.1:8756 did not respond (app may have crashed after systemd start)." >&2
        echo "--- systemctl status pi-deck.service ---" >&2
        sudo systemctl --no-pager -l status pi-deck.service || true
        echo "--- journalctl -u pi-deck (last 80 lines) ---" >&2
        sudo journalctl -u pi-deck -n 80 --no-pager || true
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
# 7. Reload Chromium in kiosk mode (best-effort — never fails the deploy)
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
