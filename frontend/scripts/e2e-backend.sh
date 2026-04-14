#!/usr/bin/env bash
# Start pi-deck with mock hardware for Playwright E2E (from repo: frontend/scripts/).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}/backend"
if [[ ! -x .venv/bin/pi-deck ]]; then
  echo "e2e-backend: create venv and pip install -e '.[dev]' in backend/ first" >&2
  exit 1
fi
# shellcheck source=/dev/null
source .venv/bin/activate
export PI_DECK_HARDWARE="${PI_DECK_HARDWARE:-mock}"
export PI_DECK_HOST="${PI_DECK_HOST:-127.0.0.1}"
export PI_DECK_PORT="${PI_DECK_PORT:-8756}"
exec pi-deck
