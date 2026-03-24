#!/usr/bin/env bash
set -euo pipefail

packages=(
  avahi-daemon
  bluez
  modemmanager
  packagekit
)

services=(
  avahi-daemon
  bluetooth
  hciuart
  ModemManager
  packagekit
)

report_line() {
  printf '%s\n' "${1:-}"
}

report_line "Conservative cleanup review"
report_line
report_line "Packages to review:"

if command -v dpkg-query >/dev/null 2>&1; then
  for package_name in "${packages[@]}"; do
    if dpkg-query -W -f='${Status}\n' "${package_name}" 2>/dev/null | grep -q "install ok installed"; then
      report_line "  installed  ${package_name}"
    else
      report_line "  absent     ${package_name}"
    fi
  done
else
  report_line "  dpkg-query not available on this host"
fi

report_line
report_line "Services to review:"

if command -v systemctl >/dev/null 2>&1; then
  for service_name in "${services[@]}"; do
    if systemctl list-unit-files "${service_name}.service" --no-legend 2>/dev/null | grep -q "${service_name}.service"; then
      enabled_state="$(systemctl is-enabled "${service_name}" 2>/dev/null || true)"
      active_state="$(systemctl is-active "${service_name}" 2>/dev/null || true)"
      report_line "  ${service_name}: enabled=${enabled_state:-unknown} active=${active_state:-unknown}"
    else
      report_line "  ${service_name}: unit not present"
    fi
  done
else
  report_line "  systemctl not available on this host"
fi

report_line
report_line "This report is intentionally conservative."
report_line "Review each package and service against the project needs before removal."
