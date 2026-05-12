#!/usr/bin/env python3
"""
collect-register-capture.py — one-command Phase 24 capture workflow.

Workflow:
1. Prompt for the observed monitor state.
2. Read the full repeated register set from the monitor-facing bus.
3. Write one canonical raw capture JSON under docs/investigation/register-captures/.
4. Regenerate tools/register-explorer/data/.

No command-line parameters are required for the normal repeated workflow.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from smbus2 import SMBus, i2c_msg
except ImportError:
    print("ERROR: smbus2 not installed. Run: pip install smbus2")
    sys.exit(1)


REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_CAPTURE_ROOT = REPO_ROOT / "docs" / "investigation" / "register-captures"
DEFAULT_BUS = 13
DEFAULT_DEVICES = [0x3A, 0x50, 0x54, 0x58]
KNOWN_DDC_VCP_NAMES: dict[int, str] = {
    0x10: "Brightness",
    0x12: "Contrast",
    0x60: "Input Source",
    0x62: "Audio Speaker Volume",
    0xD6: "Power Mode",
    0xDC: "Display Application",
}


def now_utc() -> datetime:
    return datetime.now(UTC)


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


def prompt_input_list(label: str) -> list[str]:
    valid = {"hdmi", "dp", "tb"}
    while True:
        raw = input(f"{label} [comma-separated: hdmi,dp,tb or none]: ").strip().lower()
        if not raw or raw == "none":
            return []
        values = [item.strip() for item in raw.split(",") if item.strip()]
        if values and all(value in valid for value in values) and len(set(values)) == len(values):
            return values
        print("Enter a comma-separated list using only hdmi, dp, tb, or none.")


def prompt_bool(label: str, *, default: bool = False) -> bool:
    suffix = "Y/n" if default else "y/N"
    while True:
        raw = input(f"{label} [{suffix}]: ").strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("Enter y or n.")


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "capture"


def parse_hex_value(value: str) -> int:
    return int(value, 16)


def full_hex_range() -> list[str]:
    return [f"0x{i:02X}" for i in range(256)]


def empty_register_map() -> dict[str, int | None]:
    return {reg: None for reg in full_hex_range()}


def ddc_vcp_name(code: int) -> str:
    return KNOWN_DDC_VCP_NAMES.get(code, f"Unknown (0x{code:02X})")


def ddc_get_vcp(bus: SMBus, feature: int) -> dict[str, Any]:
    dst_w = 0x6E
    src = 0x51
    opcode = 0x01
    length = 2

    pkt = [src, length | 0x80, opcode, feature]
    checksum = dst_w
    for byte in pkt:
        checksum ^= byte
    pkt.append(checksum)

    try:
        bus.i2c_rdwr(i2c_msg.write(0x37, pkt))
        time.sleep(0.05)
        read_msg = i2c_msg.read(0x37, 11)
        bus.i2c_rdwr(read_msg)
        reply = list(read_msg)
        if len(reply) < 11 or reply[2] != 0x02 or reply[4] != feature:
            return {"status": "error", "error": f"unexpected reply: {[hex(b) for b in reply]}"}
        return {
            "status": "ok",
            "current": (reply[8] << 8) | reply[9],
            "max": (reply[6] << 8) | reply[7],
            "type": "SNC" if reply[5] == 0x01 else "C",
            "raw": [hex(b) for b in reply],
        }
    except OSError as exc:
        return {"status": "error", "error": str(exc)}


def scan_ddc(bus: SMBus) -> dict[str, Any]:
    values: dict[str, int | None] = {}
    details: dict[str, Any] = {}
    attempted = full_hex_range()
    for code_num in range(256):
        code = code_num
        name = ddc_vcp_name(code)
        reg = f"0x{code:02X}"
        result = ddc_get_vcp(bus, code)
        if result["status"] == "ok":
            values[reg] = result["current"]
            details[reg] = {
                "name": name,
                "status": "ok",
                "value": result["current"],
                "max": result["max"],
                "type": result["type"],
                "raw": result["raw"],
            }
        else:
            values[reg] = None
            details[reg] = {
                "name": name,
                "status": "error",
                "value": None,
                "max": None,
                "type": None,
                "raw": None,
                "error": result["error"],
            }
        time.sleep(0.1)
    return {
        "kind": "ddc_vcp",
        "scan_scope": "full_256",
        "attempted_registers": attempted,
        "values": values,
        "details": details,
    }


_MAX_READS = 5
REG_DELAY = 0.02  # between different registers


def _read_majority_detail(bus: SMBus, device: int, reg_num: int) -> tuple[int | None, int, bool, str | None]:
    """Read with majority voting, returning (value, attempts, no_consensus, last_error)."""
    counts: dict[int, int] = {}
    last_error: str | None = None
    for i in range(_MAX_READS):
        try:
            val = bus.read_byte_data(device, reg_num)
            counts[val] = counts.get(val, 0) + 1
            if counts[val] >= 2:
                return val, i + 1, False, None
        except OSError as exc:
            last_error = str(exc)

    if not counts:
        return None, _MAX_READS, True, last_error

    best = max(counts, key=lambda v: counts[v])
    return best, _MAX_READS, counts[best] < 2, last_error


def scan_device(bus: SMBus, device: int) -> dict[str, Any]:
    values = empty_register_map()
    errors: dict[str, str] = {}
    retry_detail: dict[str, Any] = {}
    total_reads = 0
    for reg_num in range(256):
        reg = f"0x{reg_num:02X}"
        val, attempts, no_consensus, last_error = _read_majority_detail(bus, device, reg_num)
        total_reads += attempts
        values[reg] = val
        if last_error and val is None:
            errors[reg] = last_error
        if attempts > 2 or no_consensus:
            retry_detail[reg] = {"attempts": attempts, "no_consensus": no_consensus}
        time.sleep(REG_DELAY)

    read_stats = {
        "total_reads": total_reads,
        "registers_with_retries": sum(1 for d in retry_detail.values() if d["attempts"] > 2),
        "registers_no_consensus": sum(1 for d in retry_detail.values() if d["no_consensus"]),
        "retry_detail": retry_detail,
    }
    if read_stats["registers_no_consensus"]:
        print(f"  WARNING: {read_stats['registers_no_consensus']} register(s) never reached consensus after {_MAX_READS} reads.")

    return {
        "kind": "i2c_registers",
        "scan_scope": "full_256",
        "attempted_registers": full_hex_range(),
        "values": values,
        "errors": errors,
        "read_stats": read_stats,
    }


def build_state_metadata() -> dict[str, Any]:
    print("Enter the observed monitor state.")
    power_state = prompt_choice("Power state", [("on", "on"), ("standby", "standby")])
    connected_inputs = prompt_input_list("Connected inputs")
    signal_present_inputs = prompt_input_list("Inputs currently sending usable images")
    if power_state == "standby":
        signal_state = "none"
        layout_mode = None
        primary_input = None
        secondary_input = None
        audio_side = None
        pip = {"main_input": None, "window_input": None, "size": None, "position": None}
    else:
        signal_state = prompt_choice("Signal state", [("active", "active"), ("idle", "idle")])
        if signal_state == "idle":
            layout_mode = "idle"
            primary_input = None
            secondary_input = None
            audio_side = None
            pip = {"main_input": None, "window_input": None, "size": None, "position": None}
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
            if layout_mode != "single":
                state_label = locals().get("state_label")
            else:
                state_label = f"Single source: {primary_input.upper()}"

    osd_visible = prompt_bool("OSD visible at capture time?", default=False)
    contaminated = prompt_bool("Capture contaminated or otherwise untrusted?", default=False)
    include_in_explorer = prompt_bool("Include this capture in regenerated explorer data?", default=not contaminated)
    notes_text = prompt_text("Notes (optional)")

    if power_state == "standby":
        state_label = "Standby"
    elif signal_state == "idle":
        state_label = "Idle / no active source"

    metadata = {
        "state_label": state_label,
        "power_state": power_state,
        "signal_state": signal_state,
        "layout_mode": layout_mode,
        "connected_inputs": connected_inputs,
        "signal_present_inputs": signal_present_inputs,
        "primary_input": primary_input,
        "secondary_input": secondary_input,
        "audio_side": audio_side,
        "pip": pip,
        "flags": {
            "osd_visible": osd_visible,
            "contaminated": contaminated,
            "include_in_explorer": include_in_explorer,
            "metadata_certainty": "high" if include_in_explorer else "unknown",
        },
        "notes": [notes_text] if notes_text else [],
    }
    return metadata


def write_capture_file(capture: dict[str, Any]) -> Path:
    RAW_CAPTURE_ROOT.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.fromisoformat(capture["captured_at"].replace("Z", "+00:00")).strftime("%Y%m%d-%H%M%S")
    filename = f"{timestamp}-{slugify(capture['state_label'])}.json"
    path = RAW_CAPTURE_ROOT / filename
    path.write_text(json.dumps(capture, indent=2) + "\n")
    return path


def refresh_register_explorer_data() -> None:
    script = REPO_ROOT / "tools" / "scripts" / "build-register-explorer-data.py"
    subprocess.run([sys.executable, str(script)], check=True, cwd=REPO_ROOT)


def main() -> None:
    metadata = build_state_metadata()

    try:
        bus = SMBus(DEFAULT_BUS)
    except Exception as exc:
        print(f"ERROR: cannot open I2C bus {DEFAULT_BUS}: {exc}")
        sys.exit(1)

    captured_at = now_utc().isoformat(timespec="seconds")
    capture_id = f"{datetime.fromisoformat(captured_at).strftime('%Y%m%d-%H%M%S')}-{slugify(metadata['state_label'])}"

    scanned_devices: dict[str, Any] = {}
    for device in DEFAULT_DEVICES:
        print(f"\nCapturing {hex(device)}...")
        scanned_devices[f"0x{device:02X}"] = scan_device(bus, device)
    print("Capturing DDC subset on 0x37...")
    device_ddc = scan_ddc(bus)
    bus.close()

    capture = {
        "capture_id": capture_id,
        "captured_at": captured_at,
        "monitor_bus": f"/dev/i2c-{DEFAULT_BUS}",
        "source": {
            "tool": "tools/scripts/collect-register-capture.py",
            "tool_version": 1,
        },
        **metadata,
        "devices": {
            **scanned_devices,
            "0x37_ddc": device_ddc,
        },
    }

    path = write_capture_file(capture)
    print(f"\nRaw capture written to {path}")

    print("Refreshing tools/register-explorer/data/ ...")
    refresh_register_explorer_data()
    print("Done.")


if __name__ == "__main__":
    main()
