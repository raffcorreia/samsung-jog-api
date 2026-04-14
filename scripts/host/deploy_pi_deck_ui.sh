#!/usr/bin/env bash
# Build the JOG UI, sync `pi_deck` (including static/) + backend metadata to the deck host,
# reinstall the Python package (RPi.GPIO / gpiozero pin factory), align systemd for live GPIO, then restart.
# Run from your dev machine (SSH key to the Pi required).
#
# Usage:
#   ./scripts/host/deploy_pi_deck_ui.sh
#   PI_TARGET=rafael@192.168.1.50 ./scripts/host/deploy_pi_deck_ui.sh
#
# Environment:
#   PI_TARGET    SSH destination (default: rafael@10.0.0.11)
#
# The repo on the Pi is expected at ~/samsung-jog-api (login user’s home).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PI_TARGET="${PI_TARGET:-rafael@10.0.0.11}"

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
ssh -o BatchMode=yes "${PI_TARGET}" \
  "sleep 3; curl -sS --connect-timeout 8 http://127.0.0.1:8756/health; echo; curl -sS --connect-timeout 8 http://127.0.0.1:8756/api/v1/status | head -c 400; echo"

echo "Done."
