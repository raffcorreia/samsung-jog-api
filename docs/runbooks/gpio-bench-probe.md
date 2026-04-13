# GPIO bench probe (protoboard)

## Purpose

This runbook defines how to run the **bring-up script** for GPIO and I²C smoke tests on a **Raspberry Pi** wired to the **discrete protoboard** (pin map in [Phase 6 Execution Record](../implementation/phase-6-execution.md)). The script lives under **`scripts/`** — it is **not** part of the installable `pi_deck` API.

Historical validation notes for the low-level prototype phase are in [Phase 8 Execution Record](../implementation/phase-8-execution.md).

## What is being executed

| Item | Location |
|------|----------|
| **Script** | [`scripts/pi_deck_gpio_probe.py`](../../scripts/pi_deck_gpio_probe.py) |
| **Shell wrapper** | [`scripts/pi-deck-gpio-probe`](../../scripts/pi-deck-gpio-probe) — sets `PYTHONPATH=backend/src` and invokes the script |

There is **no** `pip` console entry for this tool; use the wrapper or set `PYTHONPATH` yourself.

## Prerequisites

- **Hardware:** Raspberry Pi (project target: **Pi 2B**) with the protoboard connected per [Phase 6 Execution Record](../implementation/phase-6-execution.md).
- **Python:** **3.10+** (`backend/pyproject.toml` → `requires-python`).
- **Dependencies:** `gpiozero`, `smbus2` — install with **`pip install -e backend/`** if you import `pi_deck` from a venv (needed for the script’s imports).
- **I²C:** enabled for **ADS1115** (`/dev/i2c-1` on typical images).
- **GPIO access:** user must have access to GPIO and I²C devices (e.g. `gpio` / `dialout` groups).

## Recommended execution

**Option A — wrapper (no install, sets `PYTHONPATH`):**

```bash
cd /path/to/samsung-jog-api
chmod +x scripts/pi-deck-gpio-probe    # once per clone
./scripts/pi-deck-gpio-probe --help
```

**Option B — venv + editable install** (same imports as the future app server):

```bash
cd /path/to/samsung-jog-api
python3 -m venv .venv
source .venv/bin/activate
pip install -e backend/
python3 scripts/pi_deck_gpio_probe.py --help
```

**Option C — explicit `PYTHONPATH`:**

```bash
cd /path/to/samsung-jog-api
PYTHONPATH=backend/src python3 scripts/pi_deck_gpio_probe.py --help
```

## Subcommands

| Subcommand | Example | What it does |
|------------|---------|----------------|
| `pulse` | `./scripts/pi-deck-gpio-probe pulse center --ms 80` | Pulses **one** drive GPIO (BCM) for the given direction. **Only when the Pi is wired to the drive lines.** |
| `read-ins` | `./scripts/pi-deck-gpio-probe read-ins` | One-shot read of **KEY_ADC1** and **KEY_LED** digital inputs. |
| `read-alert` | `./scripts/pi-deck-gpio-probe read-alert` | One-shot read of **ADS1115 ALERT/RDY**. |
| `read-ads` | `./scripts/pi-deck-gpio-probe read-ads --channel 0` | One-shot **ADS1115** voltage in **mV** (default AIN **0**). |

## Safety

- **`pulse` drives real outputs** on the monitor control path. Confirm wiring before use.
- Prefer **`read-ins` / `read-alert` / `read-ads`** first when bringing up observation paths.

## Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| `ModuleNotFoundError: pi_deck` | Run via **`./scripts/pi-deck-gpio-probe`** or set **`PYTHONPATH=backend/src`**, or **`pip install -e backend/`**. |
| Import errors for `gpiozero` / `smbus2` | **`pip install -e backend/`** from the repository root. |
| Permission errors on GPIO or `/dev/i2c-*` | Fix user groups on Raspberry Pi OS; avoid defaulting to `sudo`. |
