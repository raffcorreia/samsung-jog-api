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

# ── Font rendering ────────────────────────────────────────────────────────────
# Enable RGB subpixel (LCD) font rendering for the 7" Waveshare DSI panel.
# Raspberry Pi OS ships with sub-pixel-none active; replacing it with rgb makes
# text noticeably sharper in Chromium X11/Xwayland mode.
_FC_AVAIL=/usr/share/fontconfig/conf.avail
_FC_CONF=/etc/fonts/conf.d
if [[ -f "${_FC_CONF}/10-sub-pixel-none.conf" ]]; then
  sudo rm "${_FC_CONF}/10-sub-pixel-none.conf"
  echo "Removed 10-sub-pixel-none.conf"
fi
if [[ ! -e "${_FC_CONF}/10-sub-pixel-rgb.conf" ]]; then
  sudo ln -s "${_FC_AVAIL}/10-sub-pixel-rgb.conf" "${_FC_CONF}/10-sub-pixel-rgb.conf"
  echo "Enabled 10-sub-pixel-rgb.conf"
fi
fc-cache -f
echo "Font cache updated (rgba=$(fc-match --format='%{rgba}' sans))"

mkdir -p "${AUTOSTART_DIR}"
sed "s|@REPO_ROOT@|${REPO_ROOT}|g" "${DESKTOP_SRC}" >"${AUTOSTART_DST}"
echo "Wrote ${AUTOSTART_DST}"
echo "Log out and back in (or reboot) for Chromium to open fullscreen on the JOG console."
