#!/usr/bin/env bash
# Disable GNOME Keyring autostart entries for the current user (typical kiosk / autologin setup).
# Without this, autologin often triggers "Default Keyring" password prompts because the keyring
# is not unlocked by PAM.
#
# Usage: run once as the graphical login user (not with sudo):
#   ./scripts/kiosk/pi-deck-disable-gnome-keyring-autostart.sh

set -euo pipefail

AUTOSTART="${HOME}/.config/autostart"
mkdir -p "${AUTOSTART}"

disable_one() {
  local name="$1"
  local dst="${AUTOSTART}/${name}"
  if [[ -f "${dst}" ]] && grep -q '^Hidden=true' "${dst}" 2>/dev/null; then
    return 0
  fi
  cat >"${dst}" <<EOF
[Desktop Entry]
Type=Application
Name=disable-${name}
Hidden=true
EOF
  echo "Wrote ${dst} (overrides /etc/xdg/autostart/${name})"
}

for f in gnome-keyring-secrets.desktop gnome-keyring-ssh.desktop gnome-keyring-pkcs11.desktop; do
  if [[ -f "/etc/xdg/autostart/${f}" ]]; then
    disable_one "${f}"
  fi
done

echo "Log out and back in (or reboot) for the change to take effect."
