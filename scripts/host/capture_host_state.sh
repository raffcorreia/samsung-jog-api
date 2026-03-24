#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"

timestamp="$(date +%Y%m%d-%H%M%S)"
host_name="$(hostname -s 2>/dev/null || hostname)"
output_root="${1:-${repo_root}/artifacts/host-prep}"
output_dir="${output_root}/${host_name}-${timestamp}"

mkdir -p "${output_dir}"

run_to_file() {
  local file="$1"
  shift

  if "$@" >"${output_dir}/${file}" 2>&1; then
    return 0
  fi

  printf 'command failed: %q' "$1" >"${output_dir}/${file}"
  shift || true
  for arg in "$@"; do
    printf ' %q' "${arg}" >>"${output_dir}/${file}"
  done
  printf '\n' >>"${output_dir}/${file}"
}

maybe_run_to_file() {
  local file="$1"
  local command_name="$2"
  shift 2

  if command -v "${command_name}" >/dev/null 2>&1; then
    run_to_file "${file}" "${command_name}" "$@"
  else
    printf 'missing command: %s\n' "${command_name}" >"${output_dir}/${file}"
  fi
}

cat >"${output_dir}/README.txt" <<EOF
Host preparation baseline capture

Created: ${timestamp}
Host: ${host_name}

This directory may contain machine-specific details such as private IP
addresses, package inventories, and enabled services. Do not commit it.
EOF

run_to_file "date.txt" date "+%Y-%m-%dT%H:%M:%S%z"
run_to_file "uname.txt" uname -a
maybe_run_to_file "os-release.txt" cat /etc/os-release
maybe_run_to_file "hostnamectl.txt" hostnamectl
maybe_run_to_file "uptime.txt" uptime
maybe_run_to_file "disk-usage.txt" df -h
maybe_run_to_file "memory.txt" free -h
maybe_run_to_file "block-devices.txt" lsblk
maybe_run_to_file "network.txt" ip -brief address
maybe_run_to_file "routes.txt" ip route
maybe_run_to_file "enabled-services.txt" systemctl list-unit-files --type=service --state=enabled
maybe_run_to_file "running-services.txt" systemctl list-units --type=service --state=running
maybe_run_to_file "failed-services.txt" systemctl --failed
maybe_run_to_file "packages.txt" dpkg-query -W -f='${binary:Package}\t${Version}\n'
maybe_run_to_file "manual-packages.txt" apt-mark showmanual
maybe_run_to_file "apt-sources.txt" grep -R -n '^deb ' /etc/apt/sources.list /etc/apt/sources.list.d
maybe_run_to_file "vcgencmd-version.txt" vcgencmd version
maybe_run_to_file "vcgencmd-measure-temp.txt" vcgencmd measure_temp

printf '%s\n' "${output_dir}"
