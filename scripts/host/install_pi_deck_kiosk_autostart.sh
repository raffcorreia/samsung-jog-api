#!/usr/bin/env bash
# Install XDG autostart entry for Chromium kiosk → pi-deck **JOG console** (Phase 11 UI).
# Graphical session required.
#
# Usage:
#   ./scripts/host/install_pi_deck_kiosk_autostart.sh [REPO_ROOT]
#
# Requires: desktop session, chromium package, pi-deck systemd service (or manual backend).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO_ROOT="$(realpath "${1:-$DEFAULT_ROOT}")"
DESKTOP_SRC="${REPO_ROOT}/scripts/kiosk/pi-deck-kiosk.desktop"
AUTOSTART_DIR="${HOME}/.config/autostart"
AUTOSTART_DST="${AUTOSTART_DIR}/pi-deck-kiosk.desktop"
KIOSK_SCRIPT="${REPO_ROOT}/scripts/kiosk/pi-deck-chromium-kiosk.sh"

if [[ ! -f "${DESKTOP_SRC}" ]]; then
  echo "Missing ${DESKTOP_SRC}" >&2
  exit 1
fi

chmod +x "${KIOSK_SCRIPT}"

mkdir -p "${AUTOSTART_DIR}"
sed "s|@REPO_ROOT@|${REPO_ROOT}|g" "${DESKTOP_SRC}" >"${AUTOSTART_DST}"
echo "Wrote ${AUTOSTART_DST}"
echo "Log out and back in (or reboot) for Chromium to open fullscreen on the JOG console."
