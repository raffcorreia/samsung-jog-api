#!/usr/bin/env bash
set -euo pipefail

if [[ "${OSTYPE:-}" != darwin* ]]; then
  echo "This script is intended to run on macOS." >&2
  exit 1
fi

timestamp="$(date +%Y-%m-%d)"

list_candidates() {
  diskutil list external physical | awk '
    /^\/dev\/disk/ && /external, physical/ { print $1; next }
    /^\/dev\/disk/ { current=$1; next }
    /external, physical/ { if (current != "") print current }
  '
}

show_disk_info() {
  local disk="$1"
  echo
  echo "=== ${disk} ==="
  diskutil info "${disk}" | egrep '^(   Device Node|   Media Name|   Protocol|   Disk Size|   Removable Media|   Solid State|   Virtual|   Device Location|   Total Size):' || true
  echo
  diskutil list "${disk}" || true
}

confirm() {
  local prompt="$1"
  local reply
  read -r -p "${prompt} [y/N]: " reply
  [[ "${reply}" =~ ^[Yy]([Ee][Ss])?$ ]]
}

run_backup() {
  local disk="$1"
  local raw_disk="/dev/r${disk#/dev/}"
  local default_name
  local output_path

  default_name="$(hostname -s)-${disk##*/}-${timestamp}.img"
  read -r -p "Output image path for ${disk} [${default_name}]: " output_path
  output_path="${output_path:-${default_name}}"

  if [[ -e "${output_path}" ]]; then
    echo "Output file already exists: ${output_path}" >&2
    return 1
  fi

  echo
  echo "About to image ${disk} to ${output_path}"
  echo "The disk will be unmounted first."
  if ! confirm "Continue"; then
    echo "Skipped ${disk}"
    return 0
  fi

  diskutil unmountDisk "${disk}"
  echo "Starting dd from ${raw_disk}. Press Ctrl+T in this terminal for progress."
  sudo dd if="${raw_disk}" of="${output_path}" bs=4m
  sync
  echo "Backup completed: ${output_path}"
}

candidates=()
while IFS= read -r disk; do
  [[ -n "${disk}" ]] && candidates+=("${disk}")
done < <(list_candidates)

if [[ "${#candidates[@]}" -eq 0 ]]; then
  echo "No external physical disks found."
  exit 1
fi

echo "Detected candidate external physical disks:"
for idx in "${!candidates[@]}"; do
  echo "[$((idx + 1))] ${candidates[idx]}"
  show_disk_info "${candidates[idx]}"
done

echo "Choose how to proceed:"
echo "[a] confirm all listed disks for backup"
echo "[s] select disks one by one"
echo "[q] quit"
read -r -p "Choice: " mode

case "${mode}" in
  a|A)
    if confirm "Back up all listed disks"; then
      for disk in "${candidates[@]}"; do
        run_backup "${disk}"
      done
    else
      echo "Cancelled."
      exit 0
    fi
    ;;
  s|S)
    for disk in "${candidates[@]}"; do
      show_disk_info "${disk}"
      if confirm "Back up ${disk}"; then
        run_backup "${disk}"
      else
        echo "Skipped ${disk}"
      fi
    done
    ;;
  q|Q)
    echo "Cancelled."
    exit 0
    ;;
  *)
    echo "Unknown choice: ${mode}" >&2
    exit 1
    ;;
esac
