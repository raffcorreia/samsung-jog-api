#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  apply_conservative_cleanup.sh --config /path/to/cleanup.conf [--apply]

Behavior:
  - without --apply, prints the commands it would run
  - with --apply, disables services and purges packages from the config
EOF
}

config_path=""
apply_changes="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)
      config_path="${2:-}"
      shift 2
      ;;
    --apply)
      apply_changes="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${config_path}" ]]; then
  printf 'missing required --config\n' >&2
  usage >&2
  exit 1
fi

if [[ ! -f "${config_path}" ]]; then
  printf 'config not found: %s\n' "${config_path}" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${config_path}"

if ! declare -p PACKAGES_TO_PURGE >/dev/null 2>&1; then
  PACKAGES_TO_PURGE=()
fi

if ! declare -p SERVICES_TO_DISABLE >/dev/null 2>&1; then
  SERVICES_TO_DISABLE=()
fi

sudo_prefix=()
if [[ "${EUID}" -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    sudo_prefix=(sudo)
  else
    printf 'sudo is required when not running as root\n' >&2
    exit 1
  fi
fi

if ! command -v systemctl >/dev/null 2>&1; then
  printf 'systemctl is required on the target Raspberry Pi host\n' >&2
  exit 1
fi

if ! command -v dpkg-query >/dev/null 2>&1; then
  printf 'dpkg-query is required on the target Raspberry Pi host\n' >&2
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  printf 'apt-get is required on the target Raspberry Pi host\n' >&2
  exit 1
fi

run_or_print() {
  if [[ "${apply_changes}" == "true" ]]; then
    "$@"
  else
    printf 'DRY RUN:'
    printf ' %q' "$@"
    printf '\n'
  fi
}

for service_name in "${SERVICES_TO_DISABLE[@]}"; do
  if systemctl list-unit-files "${service_name}.service" --no-legend 2>/dev/null | grep -q "${service_name}.service"; then
    run_or_print "${sudo_prefix[@]}" systemctl disable --now "${service_name}"
  fi
done

packages_present=()
for package_name in "${PACKAGES_TO_PURGE[@]}"; do
  if dpkg-query -W -f='${Status}\n' "${package_name}" 2>/dev/null | grep -q "install ok installed"; then
    packages_present+=("${package_name}")
  fi
done

if [[ "${#packages_present[@]}" -gt 0 ]]; then
  run_or_print "${sudo_prefix[@]}" apt-get purge -y "${packages_present[@]}"
  run_or_print "${sudo_prefix[@]}" apt-get autoremove -y
fi
