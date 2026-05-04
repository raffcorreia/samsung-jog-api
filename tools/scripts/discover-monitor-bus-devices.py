#!/usr/bin/env python3
"""
discover-monitor-bus-devices.py — discovery pass for the Phase 24 bus hypothesis.

Purpose:
- probe the full 7-bit I2C address range on the monitor-facing bus
- identify which addresses acknowledge
- attempt a full 0x00-0xFF raw register sweep for each responding address
- save raw evidence for later comparison across monitor states

This is discovery tooling, not the default repeated capture workflow.
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from smbus2 import SMBus
except ImportError:
    print("ERROR: smbus2 not installed. Run: pip install smbus2")
    sys.exit(1)


REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = REPO_ROOT / "docs" / "investigation" / "bus-discovery"
DEFAULT_BUS = 13
ADDRESS_RANGE = range(0x03, 0x78)
REGISTER_RANGE = range(0x100)


def now_utc() -> datetime:
    return datetime.now(UTC)


def hex_byte(value: int) -> str:
    return f"0x{value:02X}"


def prompt_choice(label: str, options: list[tuple[str, str]], *, allow_blank: bool = False) -> str | None:
    option_text = " / ".join(f"{key}={value}" for key, value in options)
    while True:
        raw = input(f"{label} [{option_text}]: ").strip().lower()
        if not raw and allow_blank:
            return None
        for key, value in options:
            if raw == key:
                return value
        print("Invalid choice.")


def prompt_text(label: str, *, allow_blank: bool = True) -> str | None:
    raw = input(f"{label}: ").strip()
    if not raw and allow_blank:
        return None
    return raw


def prompt_int(label: str, *, allow_blank: bool = False) -> int | None:
    while True:
        raw = input(f"{label}: ").strip()
        if not raw and allow_blank:
            return None
        try:
            return int(raw)
        except ValueError:
            print("Enter an integer.")


def slugify(text: str) -> str:
    return "-".join(part for part in "".join(c.lower() if c.isalnum() else "-" for c in text).split("-") if part) or "discovery"


def build_state_metadata() -> dict[str, Any]:
    print("Enter the observed monitor state for this discovery pass.")
    power_state = prompt_choice("Power state", [("on", "on"), ("standby", "standby")])
    if power_state == "standby":
        signal_state = "none"
        layout_mode = "standby"
        primary_input = None
        secondary_input = None
        audio_side = None
        pip = {"main_input": None, "window_input": None, "size": None, "position": None}
        state_label = "Standby"
    else:
        signal_state = prompt_choice("Signal state", [("active", "active"), ("idle", "idle")])
        if signal_state == "idle":
            layout_mode = "idle"
            primary_input = None
            secondary_input = None
            audio_side = None
            pip = {"main_input": None, "window_input": None, "size": None, "position": None}
            state_label = "Idle / no active source"
        else:
            layout_mode = prompt_choice("Layout mode", [("single", "single"), ("pbp", "pbp"), ("pip", "pip")])
            primary_input = prompt_choice("Primary/main input", [("hdmi", "hdmi"), ("dp", "dp"), ("tb", "tb")])
            secondary_input = None
            audio_side = None
            pip = {"main_input": None, "window_input": None, "size": None, "position": None}
            if layout_mode == "single":
                state_label = f"Single source: {primary_input.upper()}"
            elif layout_mode == "pbp":
                secondary_input = prompt_choice("Secondary/right input", [("hdmi", "hdmi"), ("dp", "dp"), ("tb", "tb")])
                audio_side = prompt_choice("Audio side", [("left", "left"), ("right", "right")])
                state_label = f"PBP left: {primary_input.upper()} / right: {secondary_input.upper()} / audio {audio_side}"
            else:
                secondary_input = prompt_choice("PIP window input", [("hdmi", "hdmi"), ("dp", "dp"), ("tb", "tb")])
                audio_side = prompt_choice("Audio side", [("left", "left"), ("right", "right")])
                pip_size = prompt_int("PIP size (1/2/3)")
                pip_position = prompt_text("PIP position", allow_blank=False)
                pip = {
                    "main_input": primary_input,
                    "window_input": secondary_input,
                    "size": pip_size,
                    "position": pip_position,
                }
                state_label = (
                    f"PIP main: {primary_input.upper()} / window: {secondary_input.upper()} / "
                    f"size {pip_size} / {pip_position}"
                )

    notes = prompt_text("Notes (optional)")
    return {
        "state_label": state_label,
        "power_state": power_state,
        "signal_state": signal_state,
        "layout_mode": layout_mode,
        "primary_input": primary_input,
        "secondary_input": secondary_input,
        "audio_side": audio_side,
        "pip": pip,
        "notes": [notes] if notes else [],
    }


def probe_address(bus: SMBus, address: int) -> dict[str, Any]:
    readable = 0
    errors = 0
    values: dict[str, int | None] = {}
    error_map: dict[str, str] = {}

    for reg_num in REGISTER_RANGE:
        reg = hex_byte(reg_num)
        try:
            value = bus.read_byte_data(address, reg_num)
            values[reg] = value
            readable += 1
        except OSError as exc:
            values[reg] = None
            error_map[reg] = str(exc)
            errors += 1
        time.sleep(0.01)

    non_null_values = [value for value in values.values() if value is not None]
    classification = classify_address(address, readable, non_null_values)

    return {
        "address": hex_byte(address),
        "attempted_registers": [hex_byte(reg) for reg in REGISTER_RANGE],
        "values": values,
        "errors": error_map,
        "readable_count": readable,
        "error_count": errors,
        "classification": classification,
    }


def classify_address(address: int, readable: int, non_null_values: list[int]) -> str:
    if readable == 0:
        return "no_response"
    if readable == 256:
        unique_values = set(non_null_values)
        if len(unique_values) == 1:
            return "uniform_full_map"
        if address == 0x37 and unique_values == {0x37}:
            return "echo_only"
        return "full_map"
    return "partial_map"


def write_outputs(capture: dict[str, Any]) -> tuple[Path, Path]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    ts = datetime.fromisoformat(capture["captured_at"].replace("Z", "+00:00")).strftime("%Y%m%d-%H%M%S")
    slug = slugify(capture["state_label"])
    json_path = OUTPUT_ROOT / f"{ts}-{slug}.json"
    md_path = OUTPUT_ROOT / f"{ts}-{slug}-summary.md"

    json_path.write_text(json.dumps(capture, indent=2) + "\n")

    responding = [entry for entry in capture["addresses"] if entry["classification"] != "no_response"]
    with md_path.open("w") as f:
        f.write("# Monitor Bus Discovery Summary\n\n")
        f.write(f"- **Captured at:** {capture['captured_at']}\n")
        f.write(f"- **Bus:** {capture['monitor_bus']}\n")
        f.write(f"- **State:** {capture['state_label']}\n")
        f.write(f"- **Responding addresses:** {len(responding)}\n\n")
        f.write("| Address | Classification | Readable | Errors |\n")
        f.write("|---------|----------------|----------|--------|\n")
        for entry in responding:
            f.write(
                f"| `{entry['address']}` | {entry['classification']} | "
                f"{entry['readable_count']}/256 | {entry['error_count']} |\n"
            )

    return json_path, md_path


def main() -> None:
    metadata = build_state_metadata()
    try:
        bus = SMBus(DEFAULT_BUS)
    except Exception as exc:
        print(f"ERROR: cannot open I2C bus {DEFAULT_BUS}: {exc}")
        sys.exit(1)

    captured_at = now_utc().isoformat(timespec="seconds")
    addresses = []
    print("\nStarting bus discovery sweep...")
    for address in ADDRESS_RANGE:
        print(f"Probing {hex_byte(address)}...", flush=True)
        addresses.append(probe_address(bus, address))
    bus.close()

    capture = {
        "capture_id": f"{datetime.fromisoformat(captured_at).strftime('%Y%m%d-%H%M%S')}-{slugify(metadata['state_label'])}",
        "captured_at": captured_at,
        "monitor_bus": f"/dev/i2c-{DEFAULT_BUS}",
        "source": {
            "tool": "tools/scripts/discover-monitor-bus-devices.py",
            "tool_version": 1,
        },
        **metadata,
        "addresses": addresses,
    }

    json_path, md_path = write_outputs(capture)
    counts = Counter(entry["classification"] for entry in addresses)
    print(f"\nRaw discovery written to {json_path}")
    print(f"Summary written to {md_path}")
    print(f"Classification counts: {dict(counts)}")


if __name__ == "__main__":
    main()
