#!/usr/bin/env python3
"""
jog-button-scan.py — Capture register state on each JOG button press.

Monitors the Pi WebSocket for JOG button events and immediately scans all
register state after each press, writing captures with test_case numbers
starting from --start-tc (default 50).

Button → TC offset (from --start-tc):
  center → +0
  up     → +1
  down   → +2
  left   → +3
  right  → +4

Usage (run on the Pi):
    python3 tools/scripts/jog-button-scan.py --base-tc 3
    python3 tools/scripts/jog-button-scan.py --base-tc 14 --start-tc 55

Press Ctrl+C to stop.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from smbus2 import SMBus, i2c_msg
except ImportError:
    print("ERROR: smbus2 not installed. Run: pip install smbus2")
    sys.exit(1)

try:
    import websockets
except ImportError:
    print("ERROR: websockets not installed. Run: pip install websockets")
    sys.exit(1)


REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_CAPTURE_ROOT = REPO_ROOT / "docs" / "investigation" / "register-captures"
DEFAULT_BUS = 13
DEFAULT_DEVICES = [0x58]
DEFAULT_HOST = "10.0.0.116"
DEFAULT_PORT = 8756

BUTTON_TC_OFFSET: dict[str, int] = {
    "center": 0,
    "up":     1,
    "down":   2,
    "left":   3,
    "right":  4,
}

KNOWN_DDC_VCP_NAMES: dict[int, str] = {
    0x10: "Brightness",
    0x12: "Contrast",
    0x60: "Input Source",
    0x62: "Audio Speaker Volume",
    0xD6: "Power Mode",
    0xDC: "Display Application",
}

_MAX_READS = 5
REG_DELAY = 0.02

# Monitor state attributes keyed by TC number (matches backfill-test-case.py TEST_CASES)
TC_STATES: dict[int, dict[str, Any]] = {
    1:  {"power": "standby", "layout": None,     "primary": None,   "secondary": None,  "audio": None,    "pip_size": None},
    2:  {"power": "on",      "layout": "idle",   "primary": None,   "secondary": None,  "audio": None,    "pip_size": None},
    3:  {"power": "on",      "layout": "single", "primary": "tb",   "secondary": None,  "audio": None,    "pip_size": None},
    4:  {"power": "on",      "layout": "pip",    "primary": "tb",   "secondary": "hdmi","audio": None,    "pip_size": 1},
    5:  {"power": "on",      "layout": "pip",    "primary": "tb",   "secondary": "hdmi","audio": None,    "pip_size": 2},
    6:  {"power": "on",      "layout": "pip",    "primary": "tb",   "secondary": "hdmi","audio": None,    "pip_size": 3},
    7:  {"power": "on",      "layout": "pip",    "primary": "tb",   "secondary": "dp",  "audio": None,    "pip_size": 3},
    8:  {"power": "on",      "layout": "pip",    "primary": "tb",   "secondary": "dp",  "audio": None,    "pip_size": 2},
    9:  {"power": "on",      "layout": "pip",    "primary": "tb",   "secondary": "dp",  "audio": None,    "pip_size": 1},
    10: {"power": "on",      "layout": "pbp",    "primary": "tb",   "secondary": "dp",  "audio": "left",  "pip_size": None},
    11: {"power": "on",      "layout": "pbp",    "primary": "tb",   "secondary": "dp",  "audio": "right", "pip_size": None},
    12: {"power": "on",      "layout": "pbp",    "primary": "tb",   "secondary": "hdmi","audio": "left",  "pip_size": None},
    13: {"power": "on",      "layout": "pbp",    "primary": "tb",   "secondary": "hdmi","audio": "right", "pip_size": None},
    14: {"power": "on",      "layout": "single", "primary": "hdmi", "secondary": None,  "audio": None,    "pip_size": None},
    15: {"power": "on",      "layout": "pip",    "primary": "hdmi", "secondary": "tb",  "audio": None,    "pip_size": 1},
    16: {"power": "on",      "layout": "pip",    "primary": "hdmi", "secondary": "tb",  "audio": None,    "pip_size": 2},
    17: {"power": "on",      "layout": "pip",    "primary": "hdmi", "secondary": "tb",  "audio": None,    "pip_size": 3},
    18: {"power": "on",      "layout": "pip",    "primary": "hdmi", "secondary": "dp",  "audio": None,    "pip_size": 3},
    19: {"power": "on",      "layout": "pip",    "primary": "hdmi", "secondary": "dp",  "audio": None,    "pip_size": 2},
    20: {"power": "on",      "layout": "pip",    "primary": "hdmi", "secondary": "dp",  "audio": None,    "pip_size": 1},
    21: {"power": "on",      "layout": "pbp",    "primary": "hdmi", "secondary": "dp",  "audio": "right", "pip_size": None},
    22: {"power": "on",      "layout": "pbp",    "primary": "hdmi", "secondary": "dp",  "audio": "left",  "pip_size": None},
    23: {"power": "on",      "layout": "pbp",    "primary": "hdmi", "secondary": "tb",  "audio": "right", "pip_size": None},
    24: {"power": "on",      "layout": "pbp",    "primary": "hdmi", "secondary": "tb",  "audio": "left",  "pip_size": None},
    25: {"power": "on",      "layout": "single", "primary": "dp",   "secondary": None,  "audio": None,    "pip_size": None},
    26: {"power": "on",      "layout": "pip",    "primary": "dp",   "secondary": "tb",  "audio": None,    "pip_size": 1},
    27: {"power": "on",      "layout": "pip",    "primary": "dp",   "secondary": "tb",  "audio": None,    "pip_size": 2},
    28: {"power": "on",      "layout": "pip",    "primary": "dp",   "secondary": "tb",  "audio": None,    "pip_size": 3},
    29: {"power": "on",      "layout": "pip",    "primary": "dp",   "secondary": "hdmi","audio": None,    "pip_size": 3},
    30: {"power": "on",      "layout": "pip",    "primary": "dp",   "secondary": "hdmi","audio": None,    "pip_size": 2},
    31: {"power": "on",      "layout": "pip",    "primary": "dp",   "secondary": "hdmi","audio": None,    "pip_size": 1},
    32: {"power": "on",      "layout": "pbp",    "primary": "dp",   "secondary": "hdmi","audio": "right", "pip_size": None},
    33: {"power": "on",      "layout": "pbp",    "primary": "dp",   "secondary": "hdmi","audio": "left",  "pip_size": None},
    34: {"power": "on",      "layout": "pbp",    "primary": "dp",   "secondary": "tb",  "audio": "right", "pip_size": None},
    35: {"power": "on",      "layout": "pbp",    "primary": "dp",   "secondary": "tb",  "audio": "left",  "pip_size": None},
}


def tc_state_label(tc: int) -> str:
    s = TC_STATES[tc]
    if s["power"] == "standby":
        return "Standby"
    if s["layout"] == "idle":
        return "Idle / no active source"
    if s["layout"] == "single":
        return f"Single source: {s['primary'].upper()}"
    if s["layout"] == "pip":
        return f"PIP main: {s['primary'].upper()} / window: {s['secondary'].upper()} / size {s['pip_size']}"
    if s["layout"] == "pbp":
        return f"PBP left: {s['primary'].upper()} / right: {s['secondary'].upper()} / audio {s['audio']}"
    return f"TC{tc}"


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "capture"


def full_hex_range() -> list[str]:
    return [f"0x{i:02X}" for i in range(256)]


def empty_register_map() -> dict[str, int | None]:
    return {reg: None for reg in full_hex_range()}


def _read_majority_detail(bus: SMBus, device: int, reg_num: int) -> tuple[int | None, int, bool, str | None]:
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

    return {
        "kind": "i2c_registers",
        "scan_scope": "full_256",
        "attempted_registers": full_hex_range(),
        "values": values,
        "errors": errors,
        "read_stats": {
            "total_reads": total_reads,
            "registers_with_retries": sum(1 for d in retry_detail.values() if d["attempts"] > 2),
            "registers_no_consensus": sum(1 for d in retry_detail.values() if d["no_consensus"]),
            "retry_detail": retry_detail,
        },
    }


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
        reg = f"0x{code_num:02X}"
        name = KNOWN_DDC_VCP_NAMES.get(code_num, f"Unknown (0x{code_num:02X})")
        result = ddc_get_vcp(bus, code_num)
        if result["status"] == "ok":
            values[reg] = result["current"]
            details[reg] = {"name": name, "status": "ok", "value": result["current"],
                            "max": result["max"], "type": result["type"], "raw": result["raw"]}
        else:
            values[reg] = None
            details[reg] = {"name": name, "status": "error", "value": None,
                            "max": None, "type": None, "raw": None, "error": result["error"]}
        time.sleep(0.1)
    return {
        "kind": "ddc_vcp",
        "scan_scope": "full_256",
        "attempted_registers": attempted,
        "values": values,
        "details": details,
    }


def do_capture(button: str, base_tc: int, test_case: int, include_ddc: bool) -> Path:
    captured_at = datetime.now(UTC).isoformat(timespec="seconds")
    state = TC_STATES[base_tc]
    label = f"JOG {button} | {tc_state_label(base_tc)}"
    capture_id = f"{datetime.fromisoformat(captured_at).strftime('%Y%m%d-%H%M%S')}-{slugify(label)}"

    signal_state: str
    if state["power"] == "standby":
        signal_state = "none"
    elif state["layout"] == "idle":
        signal_state = "idle"
    else:
        signal_state = "active"

    pip_size = state["pip_size"]
    capture: dict[str, Any] = {
        "capture_id": capture_id,
        "captured_at": captured_at,
        "monitor_bus": f"/dev/i2c-{DEFAULT_BUS}",
        "source": {
            "tool": "tools/scripts/jog-button-scan.py",
            "tool_version": 1,
        },
        "state_label": label,
        "power_state": state["power"],
        "signal_state": signal_state,
        "layout_mode": state["layout"],
        "connected_inputs": [],
        "signal_present_inputs": [],
        "primary_input": state["primary"],
        "secondary_input": state["secondary"],
        "audio_side": state["audio"],
        "pip": {
            "main_input": state["primary"] if state["layout"] == "pip" else None,
            "window_input": state["secondary"] if state["layout"] == "pip" else None,
            "size": pip_size,
            "position": None,
        },
        "flags": {
            "osd_visible": False,
            "contaminated": False,
            "include_in_explorer": True,
            "metadata_certainty": "high",
        },
        "notes": [f"JOG button scan: {button} press from TC{base_tc} state"],
        "jog_button": button,
        "base_test_case": base_tc,
        "test_case": test_case,
        "devices": {},
    }

    bus = SMBus(DEFAULT_BUS)
    try:
        for device in DEFAULT_DEVICES:
            print(f"    Scanning 0x{device:02X}...")
            capture["devices"][f"0x{device:02X}"] = scan_device(bus, device)
        if include_ddc:
            print("    Scanning DDC (0x37)...")
            capture["devices"]["0x37_ddc"] = scan_ddc(bus)
    finally:
        bus.close()

    RAW_CAPTURE_ROOT.mkdir(parents=True, exist_ok=True)
    ts = datetime.fromisoformat(captured_at).strftime("%Y%m%d-%H%M%S")
    path = RAW_CAPTURE_ROOT / f"{ts}-{slugify(label)}.json"
    path.write_text(json.dumps(capture, indent=2) + "\n")
    return path


def refresh_explorer_data() -> None:
    script = REPO_ROOT / "tools" / "scripts" / "build-register-explorer-data.py"
    subprocess.run([sys.executable, str(script)], check=True, cwd=REPO_ROOT)


async def main_async(args: argparse.Namespace) -> None:
    base_tc: int = args.base_tc
    start_tc: int = args.start_tc
    include_ddc: bool = not args.no_ddc
    ws_url = f"ws://{args.host}:{args.port}/ws/events"

    if base_tc not in TC_STATES:
        print(f"ERROR: --base-tc must be 1–35, got {base_tc}")
        sys.exit(1)

    print(f"Base monitor state : TC{base_tc} — {tc_state_label(base_tc)}")
    print(f"TC assignments     :")
    for button, offset in BUTTON_TC_OFFSET.items():
        print(f"  {button:<8} → TC{start_tc + offset}")
    if not include_ddc:
        print("DDC scan           : skipped (--no-ddc)")
    print(f"\nConnecting to {ws_url} ...")

    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=1)

    async with websockets.connect(ws_url) as ws:
        print("Connected. Press any JOG button to capture. Ctrl+C to stop.\n")

        async for raw_msg in ws:
            try:
                msg = json.loads(raw_msg)
            except json.JSONDecodeError:
                continue

            if msg.get("category") != "bus" or msg.get("type") != "snapshot":
                continue

            data = msg.get("data", {})
            center: bool = data.get("key_adc1_active", False)
            direction: str | None = data.get("key_adc2_direction")

            button: str | None = None
            if center:
                button = "center"
            elif direction in BUTTON_TC_OFFSET:
                button = direction

            if button is None:
                continue

            tc = start_tc + BUTTON_TC_OFFSET[button]
            ts_now = datetime.now(UTC).strftime("%H:%M:%S")
            print(f"[{ts_now}] {button} → TC{tc}  scanning...")

            try:
                path = await loop.run_in_executor(
                    executor, do_capture, button, base_tc, tc, include_ddc
                )
                print(f"    Saved: {path.name}")
                await loop.run_in_executor(executor, refresh_explorer_data)
                print(f"    Explorer updated. Ready.\n")
            except Exception as exc:
                print(f"    ERROR during capture: {exc}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capture register state on each JOG button press.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help=f"Pi hostname or IP (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"Pi API port (default: {DEFAULT_PORT})")
    parser.add_argument("--base-tc", type=int, required=True, metavar="N",
                        help="Monitor TC number describing current state (1–35)")
    parser.add_argument("--start-tc", type=int, default=50, metavar="N",
                        help="First TC number to assign; center=N, up=N+1, … (default: 50)")
    parser.add_argument("--no-ddc", action="store_true",
                        help="Skip DDC VCP scan (~26s) — I2C devices only")
    args = parser.parse_args()

    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
