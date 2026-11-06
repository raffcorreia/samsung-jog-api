#!/usr/bin/env bash
# Build the JOG UI, sync `pi_deck` (including static/) + backend metadata to the deck host,
# reinstall the Python package (RPi.GPIO / gpiozero pin factory), align systemd for live GPIO, then restart.
# Run from your dev machine (SSH key to the Pi required).
#
# Usage:
#   PI_DECK_IP=192.168.x.x ./scripts/host/deploy_pi_deck_ui.sh
#
# Environment:
#   PI_DECK_IP    Deck IP address — required (or set it in .env.local)
#   PI_DECK_USER  SSH user — optional; defaults to rafael
#
# The repo on the Pi is expected at ~/samsung-jog-api (login user’s home).
#
# Note: scripts/deploy.sh is the canonical full deploy; this script is kept for
# partial (UI-only) deploys during active frontend development.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [ -z "${PI_DECK_IP:-}" ] && [ -f "${REPO_ROOT}/.env.local" ]; then
    set -a
    # shellcheck disable=SC1091
    . "${REPO_ROOT}/.env.local"
    set +a
fi

if [ -z "${PI_DECK_IP:-}" ]; then
    echo "ERROR: PI_DECK_IP is not set. Ask for the current deck IP before deploying." >&2
    exit 1
fi

PI_DECK_USER="${PI_DECK_USER:-rafael}"
PI_TARGET="${PI_DECK_USER}@${PI_DECK_IP}"

echo "Building frontend → ${REPO_ROOT}/backend/src/pi_deck/static ..."
(cd "${REPO_ROOT}/frontend" && npm run build)

echo "Ensure repo paths exist on ${PI_TARGET} ..."
ssh -o BatchMode=yes "${PI_TARGET}" 'mkdir -p ~/samsung-jog-api/backend/src/pi_deck'

echo "Rsync pi_deck → ${PI_TARGET}:~/samsung-jog-api/backend/src/pi_deck/"
rsync -avz --delete \
  "${REPO_ROOT}/backend/src/pi_deck/" \
  "${PI_TARGET}:~/samsung-jog-api/backend/src/pi_deck/"

echo "Rsync backend/pyproject.toml → ${PI_TARGET}:~/samsung-jog-api/backend/"
rsync -avz "${REPO_ROOT}/backend/pyproject.toml" "${PI_TARGET}:~/samsung-jog-api/backend/"

echo "Rsync kiosk launcher → ${PI_TARGET}:~/samsung-jog-api/scripts/kiosk/"
ssh -o BatchMode=yes "${PI_TARGET}" 'mkdir -p ~/samsung-jog-api/scripts/kiosk'
rsync -avz "${REPO_ROOT}/scripts/kiosk/pi-deck-chromium-kiosk.sh" "${PI_TARGET}:~/samsung-jog-api/scripts/kiosk/"
ssh -o BatchMode=yes "${PI_TARGET}" 'chmod +x ~/samsung-jog-api/scripts/kiosk/pi-deck-chromium-kiosk.sh'

echo "Editable install + systemd (live GPIO) on ${PI_TARGET} ..."
ssh -o BatchMode=yes "${PI_TARGET}" 'set -e
cd ~/samsung-jog-api/backend
if [ ! -x .venv/bin/pip ]; then python3 -m venv .venv; fi
.venv/bin/pip install -q -U pip
.venv/bin/pip install -q -e .
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

echo "Verifying (localhost on Pi) ..."
ssh -o BatchMode=yes "${PI_TARGET}" 'set -e
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sfS --connect-timeout 4 http://127.0.0.1:8756/health >/dev/null 2>&1; then
    curl -sS --connect-timeout 8 http://127.0.0.1:8756/health
    echo
    curl -sS --connect-timeout 8 http://127.0.0.1:8756/api/v1/status | head -c 400
    echo
    exit 0
  fi
  sleep 1
done
echo "health check failed after restart" >&2
exit 1'

echo "Done."
