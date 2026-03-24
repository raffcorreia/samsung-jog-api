#!/usr/bin/env bash
set -euo pipefail

echo "Host smoke check"
echo

echo "System time:"
date "+%Y-%m-%dT%H:%M:%S%z"
echo

echo "Filesystem usage:"
df -h /
echo

echo "Memory:"
if command -v free >/dev/null 2>&1; then
  free -h
else
  echo "free not available on this host"
fi
echo

if command -v systemctl >/dev/null 2>&1; then
  echo "System state:"
  systemctl is-system-running || true
  echo
  echo "Failed units:"
  systemctl --failed || true
fi
