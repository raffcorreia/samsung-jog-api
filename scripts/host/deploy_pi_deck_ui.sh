#!/usr/bin/env bash
# Build the JOG UI and sync `pi_deck` (including static/) to the deck host, then restart the service.
# Run from your dev machine (SSH key to the Pi required).
#
# Usage:
#   ./scripts/host/deploy_pi_deck_ui.sh
#   PI_TARGET=rafael@192.168.1.50 PI_REPO=~/samsung-jog-api ./scripts/host/deploy_pi_deck_ui.sh
#
# Environment:
#   PI_TARGET   SSH destination (default: rafael@10.0.0.11)
#   PI_REPO     Path to repo clone on the Pi (default: ~/samsung-jog-api)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PI_TARGET="${PI_TARGET:-rafael@10.0.0.11}"
PI_REPO="${PI_REPO:-~/samsung-jog-api}"
REMOTE_DECK="${PI_REPO}/backend/src/pi_deck"

echo "Building frontend → ${REPO_ROOT}/backend/src/pi_deck/static ..."
(cd "${REPO_ROOT}/frontend" && npm run build)

echo "Rsync pi_deck → ${PI_TARGET}:${REMOTE_DECK}/"
rsync -avz --delete \
  "${REPO_ROOT}/backend/src/pi_deck/" \
  "${PI_TARGET}:${REMOTE_DECK}/"

echo "Restarting pi-deck on ${PI_TARGET} ..."
ssh -o BatchMode=yes "${PI_TARGET}" "sudo systemctl restart pi-deck"

echo "Verifying (localhost on Pi, then LAN) ..."
ssh -o BatchMode=yes "${PI_TARGET}" \
  "sleep 2; curl -sS --connect-timeout 5 http://127.0.0.1:8756/health; echo; curl -sS --connect-timeout 5 http://127.0.0.1:8756/ | grep -E 'index-.*\\.(js|css)' | head -2"

echo "Done."
