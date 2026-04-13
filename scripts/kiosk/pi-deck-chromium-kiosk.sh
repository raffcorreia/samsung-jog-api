#!/usr/bin/env bash
# Launch Chromium in kiosk mode pointed at the local pi-deck server.
# Intended for ~/.config/autostart via pi-deck-kiosk.desktop (graphical session).

set -euo pipefail

PORT="${PI_DECK_PORT:-8756}"
URL="${PI_DECK_URL:-http://127.0.0.1:${PORT}/}"

wait_for_health() {
  local i
  for i in $(seq 1 120); do
    if command -v curl >/dev/null 2>&1; then
      curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null && return 0
    else
      python3 - "$PORT" <<'PY' && return 0
import sys, urllib.request
port = sys.argv[1]
try:
    urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1).read()
except OSError:
    raise SystemExit(1)
PY
    fi
    sleep 1
  done
  echo "pi-deck-chromium-kiosk: backend did not become ready on port ${PORT}" >&2
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

# Hide idle cursor on X11 (Wayland: rely on kiosk fullscreen; optional: wlrctl if available)
if [[ -z "${WAYLAND_DISPLAY:-}" ]] && command -v unclutter >/dev/null 2>&1; then
  unclutter -idle 0 -root &
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
  "${URL}"
)

if [[ -n "${WAYLAND_DISPLAY:-}" ]]; then
  exec "${BROWSER[@]}" --ozone-platform=wayland "${CHROME_ARGS[@]}"
fi

exec "${BROWSER[@]}" "${CHROME_ARGS[@]}"
