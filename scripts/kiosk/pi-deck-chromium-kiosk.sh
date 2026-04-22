#!/usr/bin/env bash
# Launch Chromium in kiosk mode to the pi-deck **JOG console** (Phase 11+ UI).
#
# The backend serves the React bundle from pi_deck/static at GET / (same UI as on the LAN).
# This script waits for GET /health, optionally hides the idle pointer (X11: unclutter;
# Wayland: wlrctl when installed), then starts Chromium fullscreen.
#
# Used by ~/.config/autostart via pi-deck-kiosk.desktop (see install_pi_deck_kiosk_autostart.sh).
#
# Environment (optional):
#   PI_DECK_PORT   Listen port (default 8756). Must match pi-deck.service.
#   PI_DECK_URL    Full URL to open (default http://127.0.0.1:${PI_DECK_PORT}/).
#                  Override only if you proxy or split HTTP vs WS (normally unnecessary).
#
# CPU priority — cannot create CPU out of thin air; this nudges the scheduler toward Chromium.
#   PI_DECK_KIOSK_NICE  e.g. -5 (higher priority than default 0). Values below ~-10 often need
#                        root or CAP_SYS_NICE; unprivileged users are typically limited (see `man nice`).
#
# Memory — the Pi has one RAM pool; “giving more” to the browser means not starving it (swap/zram,
# fewer background services) or slightly raising the V8 heap (example only; test on device):
#   PI_DECK_CHROMIUM_EXTRA_ARGS='--js-flags=--max-old-space-size=256'
#   (Add more Chromium flags separated by spaces; use the desktop file or export before this script.)
#
# Complementary (often better than raising Chromium): lower pi-deck’s priority so the UI wins under load.
# In systemd unit for pi-deck:  Nice=5  or  CPUWeight=50

set -euo pipefail

PORT="${PI_DECK_PORT:-8756}"
URL="${PI_DECK_URL:-http://127.0.0.1:${PORT}/}"

# Autostart often runs without WAYLAND_DISPLAY set even on Wayland sessions; Chromium needs it for --ozone-platform=wayland.
_uid="$(id -u)"
_rt="${XDG_RUNTIME_DIR:-/run/user/${_uid}}"
if [[ -z "${WAYLAND_DISPLAY:-}" && -S "${_rt}/wayland-0" ]]; then
  export WAYLAND_DISPLAY=wayland-0
fi
if [[ -z "${XDG_RUNTIME_DIR:-}" && -d "/run/user/${_uid}" ]]; then
  export XDG_RUNTIME_DIR="/run/user/${_uid}"
fi

wait_for_health() {
  local i max_attempts
  max_attempts="${PI_DECK_HEALTH_WAIT_SECONDS:-600}"
  for i in $(seq 1 "${max_attempts}"); do
    if command -v curl >/dev/null 2>&1; then
      curl -sf --connect-timeout 2 "http://127.0.0.1:${PORT}/health" >/dev/null && return 0
    else
      python3 - "$PORT" <<'PY' && return 0
import sys, urllib.request
port = sys.argv[1]
try:
    urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2).read()
except OSError:
    raise SystemExit(1)
PY
    fi
    if (( i % 60 == 0 )); then
      echo "pi-deck-chromium-kiosk: still waiting for /health on port ${PORT} (${i}s)..." >&2
    fi
    sleep 1
  done
  echo "pi-deck-chromium-kiosk: backend did not become ready on port ${PORT} after ${max_attempts}s" >&2
  exit 1
}

if command -v chromium >/dev/null 2>&1; then
  BROWSER=(chromium)
elif command -v chromium-browser >/dev/null 2>&1; then
  BROWSER=(chromium-browser)
else
  echo "pi-deck-chromium-kiosk: no chromium binary found" >&2
  exit 1
fi

wait_for_health

# Hide idle cursor on X11 only (not Wayland — unclutter needs X11 DISPLAY).
if [[ -z "${WAYLAND_DISPLAY:-}" && -n "${DISPLAY:-}" ]] && command -v unclutter >/dev/null 2>&1; then
  unclutter -idle 0 -root &
elif [[ -n "${WAYLAND_DISPLAY:-}" ]] && command -v wlrctl >/dev/null 2>&1; then
  wlrctl pointer hide 2>/dev/null || true
fi

# Reset compositor scale to 1:1 — Chromium runs via Xwayland (X11 mode) which
# handles its own DPI and does not use the Wayland output scale.
if [[ -n "${WAYLAND_DISPLAY:-}" ]]; then
  wlr-randr --output DSI-1 --scale 1.0 2>/dev/null || true
fi

CHROME_ARGS=(
  --password-store=basic
  --kiosk
  --noerrdialogs
  --disable-infobars
  --disable-session-crashed-bubble
  --disable-restore-session-state
  --check-for-update-interval=31536000
  --no-first-run
  --no-default-browser-check
  # Localhost appliance: avoid stale index / hashed bundles after deploy (disk cache is aggressive).
  --disable-http-cache
  # Appliance UX: no translate bar on first load; kiosk is a known single origin.
  --disable-features=Translate
  # X11 mode via Xwayland: enables subpixel (LCD) font rendering which is disabled
  # on native Wayland. labwc starts Xwayland on demand; DISPLAY=:0 is the socket
  # labwc pre-creates at /tmp/.X11-unix/X0.
  --ozone-platform=x11
)

# Optional extra flags (e.g. --js-flags=--max-old-space-size=256); split on spaces — avoid spaces inside one flag.
if [[ -n "${PI_DECK_CHROMIUM_EXTRA_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  CHROME_ARGS+=(${PI_DECK_CHROMIUM_EXTRA_ARGS})
fi

CHROME_ARGS+=("${URL}")

run_chromium() {
  # Run under Xwayland: set DISPLAY, clear WAYLAND_DISPLAY so Chromium uses X11.
  # labwc pre-creates /tmp/.X11-unix/X0 and starts Xwayland on first connection.
  if [[ -n "${PI_DECK_KIOSK_NICE:-}" ]]; then
    exec nice -n "${PI_DECK_KIOSK_NICE}" env DISPLAY=:0 WAYLAND_DISPLAY= "${BROWSER[@]}" "$@"
  fi
  exec env DISPLAY=:0 WAYLAND_DISPLAY= "${BROWSER[@]}" "$@"
}

run_chromium "${CHROME_ARGS[@]}"
