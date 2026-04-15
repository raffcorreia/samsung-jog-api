#!/usr/bin/env bash
# Install pi-deck as a system service (systemd). Run on the Raspberry Pi after cloning the repo.
# Must run with sudo (writes /etc/systemd/system/pi-deck.service). Uses SUDO_USER for @SERVICE_USER@.
#
# Usage:
#   sudo ./scripts/host/install_pi_deck_systemd.sh [REPO_ROOT]
#
# Default REPO_ROOT: parent of scripts/ (repository root), resolved to an absolute path.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO_ROOT="$(realpath "${1:-$DEFAULT_ROOT}")"
UNIT_SRC="${REPO_ROOT}/config/systemd/pi-deck.service"
UNIT_DST="/etc/systemd/system/pi-deck.service"
SERVICE_USER="${PI_DECK_SERVICE_USER:-${SUDO_USER:-$USER}}"
if [[ "${SERVICE_USER}" == "root" ]]; then
  echo "Refusing to install pi-deck as root: set PI_DECK_SERVICE_USER to the deck login" \
    "(e.g. export PI_DECK_SERVICE_USER=deck-user) or run with sudo from that account." >&2
  exit 1
fi
SERVICE_HOME="$(getent passwd "${SERVICE_USER}" | cut -d: -f6)"

if [[ ! -f "${UNIT_SRC}" ]]; then
  echo "Missing unit template: ${UNIT_SRC}" >&2
  exit 1
fi

if [[ "${REPO_ROOT}" != /* ]]; then
  echo "REPO_ROOT must be absolute: ${REPO_ROOT}" >&2
  exit 1
fi

if [[ -z "${SERVICE_HOME}" ]]; then
  echo "Could not resolve home for user: ${SERVICE_USER}" >&2
  exit 1
fi

BACKEND="${REPO_ROOT}/backend"
if [[ ! -d "${BACKEND}" ]]; then
  echo "Expected backend at ${BACKEND}" >&2
  exit 1
fi

(
  cd "${BACKEND}"
  if [[ ! -x .venv/bin/pip ]]; then
    python3 -m venv .venv
  fi
  .venv/bin/pip install -U pip
  .venv/bin/pip install -e ".[dev]"
)

sed \
  -e "s|@REPO_ROOT@|${REPO_ROOT}|g" \
  -e "s|@SERVICE_USER@|${SERVICE_USER}|g" \
  -e "s|@SERVICE_HOME@|${SERVICE_HOME}|g" \
  "${UNIT_SRC}" | sudo tee "${UNIT_DST}" >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable pi-deck.service
sudo systemctl restart pi-deck.service
echo "Installed ${UNIT_DST} — status:"
sudo systemctl --no-pager -l status pi-deck.service || true
echo "Health check:"
curl -sf "http://127.0.0.1:8756/health" && echo || echo "curl failed (service may still be starting)"
echo "Listening on all interfaces (PI_DECK_HOST=0.0.0.0). Try: curl -sf http://$(hostname -I | awk '{print $1}'):8756/health"
