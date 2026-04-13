# Phase 8 bench probe — execution definition

## Purpose

This runbook defines **how** to run the Phase 8 low-level smoke tool (`sjog-phase8-probe`) on a **Raspberry Pi** against the **Phase 6 protoboard** wiring. It is part of operational documentation, not the Phase 8 *results* record (that stays in [Phase 8 Execution Record](../implementation/phase-8-execution.md)).

## What is being executed

| Item | Location |
|------|----------|
| **Python module** | `pi_deck.cli.phase8_probe` → file `backend/src/pi_deck/cli/phase8_probe.py` |
| **Callable entry** | `main()` (invoked by `-m` or by the console script below) |
| **Console name** | `sjog-phase8-probe` — declared in **repository root** [`pyproject.toml`](../../pyproject.toml) under `[project.scripts]` |
| **Repo wrapper script** | [`scripts/sjog-phase8-probe`](../../scripts/sjog-phase8-probe) — runs the same code with `PYTHONPATH=backend/src` so you do not have to install the package first |

There is **no separate** `sjog-phase8-probe` source file: the behavior is **only** the Python module above; the shell name is packaging glue. All backend code lives under **`backend/`** so the repository root stays free for other layouts (for example a future `frontend/` tree).

## Prerequisites

- **Hardware:** Raspberry Pi (project target: **Pi 2B**) with the **Phase 6** protoboard connected per [Phase 6 Execution Record](../implementation/phase-6-execution.md) (GPIO map and harness).
- **Python:** **3.10+** (matches `requires-python` in `pyproject.toml`).
- **Dependencies:** `gpiozero`, `smbus2` (installed automatically with `pip install -e backend/`).
- **I²C:** enabled on the Pi for **ADS1115** (e.g. `raspi-config` → Interface Options → I2C). Device should appear as `/dev/i2c-1` on typical Pi OS images.
- **GPIO access:** the user running the tool must be able to access GPIO (on Raspberry Pi OS this is often via group membership such as `gpio` / `dialout`; if a command fails with permission errors on `/dev/gpiomem` or I²C, fix group membership rather than relying on `sudo` for normal use).

## Recommended execution (editable install)

From a clone of this repository on the Pi:

```bash
cd /path/to/samsung-jog-api
python3 -m venv .venv
source .venv/bin/activate
pip install -e backend/
sjog-phase8-probe --help
```

After this, `sjog-phase8-probe` is on your **`PATH`** only while the venv is activated. (The installable project is [`backend/pyproject.toml`](../../backend/pyproject.toml).)

## Execution without installing the package

Option A — **wrapper script** (sets `PYTHONPATH` for you):

```bash
cd /path/to/samsung-jog-api
chmod +x scripts/sjog-phase8-probe    # once per clone
./scripts/sjog-phase8-probe --help
```

Option B — **module** (explicit `PYTHONPATH`):

```bash
cd /path/to/samsung-jog-api
PYTHONPATH=backend/src python3 -m pi_deck.cli.phase8_probe --help
```

## Subcommands (what to run and when)

| Subcommand | Example | What it does |
|------------|---------|----------------|
| `pulse` | `sjog-phase8-probe pulse center --ms 80` | Pulses **one** Phase 6 **drive** GPIO (BCM) for the given direction. **Only use when the Pi is wired to the drive lines.** |
| `read-ins` | `sjog-phase8-probe read-ins` | One-shot read of **KEY_ADC1** and **KEY_LED** digital inputs (conditioning as built). |
| `read-alert` | `sjog-phase8-probe read-alert` | One-shot read of **ADS1115 ALERT/RDY** on **GPIO17**. |
| `read-ads` | `sjog-phase8-probe read-ads --channel 0` | One-shot **ADS1115** voltage read in **mV** (default channel **0** for current `KEY_ADC2` wiring). |

Global help: `sjog-phase8-probe -h` or any of the equivalent invocations above with `--help`.

## Safety

- **`pulse` asserts real outputs** on the monitor control path. Confirm wiring and mutual-exclusion expectations before using it on a connected monitor harness.
- Prefer **`read-ins` / `read-alert` / `read-ads`** first to confirm observation paths once the Pi is attached.

## Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| `sjog-phase8-probe: command not found` | Virtualenv not activated or `pip install -e backend/` not run; use **`./scripts/sjog-phase8-probe`** or the **`PYTHONPATH=backend/src python3 -m ...`** form instead. |
| Import errors for `gpiozero` / `smbus2` | Dependencies not installed — use **`pip install -e backend/`** from the repository root (or `cd backend && pip install -e .`). |
| Permission error on GPIO or `/dev/i2c-*` | User lacks access — add user to the correct groups or use a properly configured Pi OS image; avoid permanent `sudo` as the default fix. |
