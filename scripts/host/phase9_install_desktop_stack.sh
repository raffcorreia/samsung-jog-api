#!/usr/bin/env bash
# Install a minimal Raspberry Pi OS graphical stack, Chromium, and helpers for kiosk bring-up.
# Run once on the Pi with sudo. Reboot after completion.
#
# This pulls Wayland desktop packages (rpd-wayland-core) and lightdm. Adjust if you use a
# different session stack.

set -euo pipefail

if [[ $(id -u) -ne 0 ]]; then
  echo "Run with sudo: sudo $0" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y \
  lightdm \
  rpd-wayland-core \
  chromium \
  unclutter \
  curl \
  python3-venv

systemctl set-default graphical.target

# Desktop autologin as the invoking non-root user (sudo preserves SUDO_USER).
TARGET_USER="${SUDO_USER:-${USER:-root}}"
if [[ "${TARGET_USER}" == "root" ]]; then
  echo "Run this script with sudo from a normal user account so SUDO_USER is set." >&2
  exit 1
fi

# raspi-config must run as root; it uses $USER for lightdm autologin — force the deck user.
env USER="${TARGET_USER}" HOME="/home/${TARGET_USER}" raspi-config nonint do_boot_behaviour B4

echo "Desktop stack installed. Reboot to start the graphical session: sudo reboot"
