#!/usr/bin/env python3
"""
DDC VCP brute-force scanner — Phase 24 investigation.

Scans all 256 VCP codes (0x00–0xFF) on the connected monitor, logs every
attempt (including retries) to a JSONL file, and writes a markdown summary
of all responding codes.

Retry policy: if the previous command succeeded but the current one fails,
wait 5 s and retry once before moving on. This guards against a successful
command briefly leaving the monitor unresponsive.

Usage:
    python3 scripts/ddc-scan.py [--bus N] [--delay MS] [--output DIR]

Output (written to --output, default docs/investigation/ddc-scan/):
    ddc-scan-YYYYMMDD-HHMMSS.jsonl       full event log
    ddc-scan-YYYYMMDD-HHMMSS-summary.md  markdown table of responding codes

Requirements:
    ddcutil installed on the host (sudo apt install ddcutil)
    User must be in the i2c group: sudo usermod -aG i2c $USER
"""

import argparse
import json
import random
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


# MCCS VCP code names (standard codes only; unknowns labelled at runtime)
MCCS_NAMES: dict[int, str] = {
    0x01: "Degauss",
    0x02: "New Control Value",
    0x04: "Restore Factory Defaults",
    0x05: "Restore Factory Luminance/Contrast",
    0x06: "Restore Factory Geometry",
    0x08: "Restore Factory Color",
    0x0B: "Color Temperature Increment",
    0x0C: "Color Temperature Request",
    0x0E: "Clock",
    0x10: "Brightness",
    0x12: "Contrast",
    0x14: "Select Color Preset",
    0x16: "Red Video Gain",
    0x18: "Green Video Gain",
    0x1A: "Blue Video Gain",
    0x1E: "Auto Setup",
    0x1F: "Auto Color Setup",
    0x20: "Horizontal Position",
    0x22: "Horizontal Size",
    0x30: "Vertical Position",
    0x32: "Vertical Size",
    0x3E: "Clock Phase",
    0x52: "Active Control",
    0x54: "Performance Preservation",
    0x56: "Horizontal Moire",
    0x58: "Vertical Moire",
    0x59: "Red Saturation",
    0x5A: "Yellow Saturation",
    0x5B: "Green Saturation",
    0x5C: "Cyan Saturation",
    0x5D: "Blue Saturation",
    0x5E: "Magenta Saturation",
    0x60: "Input Source",
    0x62: "Audio Speaker Volume",
    0x63: "Speaker Select",
    0x6A: "Audio Balance L/R",
    0x6C: "Video Black Level: Red",
    0x6E: "Video Black Level: Green",
    0x70: "Video Black Level: Blue",
    0x72: "Gamma",
    0x7E: "Trapezoid",
    0x82: "Display Scaling",
    0x84: "Sharpness",
    0x86: "Video Signal Interface",
    0x8A: "Color Saturation",
    0x8D: "Audio Mute",
    0x90: "Hue",
    0x9E: "Auto Setup Lock",
    0xAA: "Screen Orientation",
    0xAC: "Horizontal Frequency",
    0xAE: "Vertical Frequency",
    0xB0: "Settings",
    0xB2: "Flat Panel Sub-Pixel Layout",
    0xB6: "Display Technology Type",
    0xC0: "Display Usage Time",
    0xC6: "Application Enable Key",
    0xC8: "Display Controller ID",
    0xC9: "Display Firmware Level",
    0xCA: "OSD/Button Control",
    0xCC: "OSD Language",
    0xD6: "Power Mode",
    0xDA: "Scan Mode",
    0xDB: "Image Mode",
    0xDC: "Display Application",
    0xDF: "VCP Version",
}

RETRY_WAIT = 5.0
DEFAULT_DELAY = 0.2  # seconds between commands


def now_ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def check_ddcutil() -> None:
    result = subprocess.run(["which", "ddcutil"], capture_output=True)
    if result.returncode != 0:
        print("ERROR: ddcutil not found. Install it with:")
        print("  sudo apt install ddcutil")
        print("  sudo usermod -aG i2c $USER  # then log out and back in")
        sys.exit(1)


def detect_bus() -> int | None:
    result = subprocess.run(
        ["ddcutil", "detect"],
        capture_output=True, text=True, timeout=15,
    )
    match = re.search(r"/dev/i2c-(\d+)", result.stdout)
    if match:
        return int(match.group(1))
    return None


def get_capabilities(bus: int) -> str | None:
    result = subprocess.run(
        ["ddcutil", f"--bus={bus}", "capabilities"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def query_vcp(bus: int, code: int) -> dict:
    hex_code = f"0x{code:02X}"
    cmd = ["ddcutil", f"--bus={bus}", "getvcp", "--terse", hex_code]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return _parse_terse(result.stdout.strip())
        return {
            "status": "error",
            "error": (result.stderr.strip() or result.stdout.strip() or "non-zero exit")[:200],
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "timeout"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _parse_terse(output: str) -> dict:
    # ddcutil --terse getvcp output formats:
    #   VCP <HEX> C <current> <max>      Continuous
    #   VCP <HEX> NC <sl_hex>            Non-Continuous
    #   VCP <HEX> T <bytes...>           Table
    parts = output.split()
    if len(parts) < 3 or parts[0] != "VCP":
        return {"status": "error", "error": f"unexpected output: {output!r}"}
    vtype = parts[2]
    if vtype == "C" and len(parts) >= 5:
        try:
            return {"status": "ok", "type": "C", "current": int(parts[3]), "max": int(parts[4])}
        except ValueError:
            return {"status": "error", "error": f"parse error: {output!r}"}
    if vtype == "NC":
        return {"status": "ok", "type": "NC", "sl": parts[3] if len(parts) > 3 else "?"}
    if vtype == "T":
        return {"status": "ok", "type": "T", "raw": " ".join(parts[3:])}
    return {"status": "ok", "type": vtype, "raw": output}


def _summary_row(r: dict) -> str:
    vtype = r.get("type", "?")
    if vtype == "C":
        current, maxsl = str(r.get("current", "")), str(r.get("max", ""))
    elif vtype == "NC":
        current, maxsl = "", r.get("sl", "")
    else:
        current, maxsl = "", r.get("raw", "")[:40]
    retried = " *(retried)*" if r.get("attempt", 1) > 1 else ""
    return f"| `{r['code']}` | {r['name']}{retried} | {vtype} | {current} | {maxsl} |"


def main() -> None:
    parser = argparse.ArgumentParser(description="DDC VCP brute-force scanner")
    parser.add_argument("--bus", type=int, help="I2C bus number (auto-detect if omitted)")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY,
                        help=f"Delay between commands in seconds (default: {DEFAULT_DELAY})")
    parser.add_argument("--output", type=Path, default=Path("docs/investigation/ddc-scan"),
                        help="Output directory")
    parser.add_argument("--codes", type=str,
                        help="Comma-separated hex codes to scan instead of full 0x00-0xFF range")
    parser.add_argument("--reverse", action="store_true",
                        help="Scan in descending order")
    parser.add_argument("--random", action="store_true",
                        help="Scan in random order")
    args = parser.parse_args()

    check_ddcutil()

    # Detect display
    bus = args.bus
    if bus is None:
        print("Detecting display...", flush=True)
        bus = detect_bus()
        if bus is None:
            print("ERROR: No display detected by ddcutil.")
            print("Check the HDMI connection and run:  ddcutil detect")
            print("If the monitor is connected but not found, check /boot/config.txt")
            print("for 'video=HDMI-A-1:d' — it may need to be temporarily removed.")
            sys.exit(1)
        print(f"Display found on I2C bus {bus}.")
    else:
        print(f"Using I2C bus {bus} (specified).")

    # Prepare output
    args.output.mkdir(parents=True, exist_ok=True)
    scan_ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = args.output / f"ddc-scan-{scan_ts}.jsonl"
    summary_path = args.output / f"ddc-scan-{scan_ts}-summary.md"

    print(f"Log:     {log_path}")
    print(f"Summary: {summary_path}")

    # Read capability string first
    print("\nReading capability string...", flush=True)
    capabilities = get_capabilities(bus)
    cap_entry = {
        "ts": now_ts(),
        "event": "capabilities",
        "bus": bus,
        "output": capabilities or "none",
    }

    responding: list[dict] = []
    prev_succeeded = False

    with log_path.open("w") as log_f:
        log_f.write(json.dumps(cap_entry) + "\n")
        log_f.flush()

        if capabilities:
            print(f"Capabilities: {capabilities[:120]}{'...' if len(capabilities) > 120 else ''}")
        else:
            print("No capability string returned.")

        if args.codes:
            code_list = [int(c.strip(), 16) for c in args.codes.split(",")]
        else:
            code_list = list(range(0x00, 0x100))

        if args.reverse:
            code_list = list(reversed(code_list))
        elif args.random:
            random.shuffle(code_list)

        if args.random:
            order = "random"
        elif args.reverse:
            order = "descending"
        else:
            order = "ascending"

        print(f"\nScanning {len(code_list)} VCP codes ({order})...\n")

        for code in code_list:
            name = MCCS_NAMES.get(code, f"Unknown (0x{code:02X})")
            time.sleep(args.delay)

            result = query_vcp(bus, code)
            attempt = 1
            succeeded = result["status"] == "ok"

            if not succeeded and prev_succeeded:
                print(
                    f"  0x{code:02X}  {name:<42}  -- (retrying in {RETRY_WAIT:.0f}s...)",
                    flush=True,
                )
                time.sleep(RETRY_WAIT)
                result = query_vcp(bus, code)
                attempt = 2
                succeeded = result["status"] == "ok"

            entry = {
                "ts": now_ts(),
                "code": f"0x{code:02X}",
                "name": name,
                "attempt": attempt,
                **result,
            }
            log_f.write(json.dumps(entry) + "\n")
            log_f.flush()

            if succeeded:
                responding.append(entry)
                detail = ""
                if result.get("type") == "C":
                    detail = f"  current={result['current']}  max={result['max']}"
                elif result.get("type") == "NC":
                    detail = f"  sl={result['sl']}"
                retry_note = " [retried]" if attempt > 1 else ""
                print(f"  0x{code:02X}  {name:<42}  OK{retry_note}{detail}", flush=True)
            else:
                # Print failures only if they were retried (interesting) or every 16 codes
                if attempt > 1 or code % 16 == 0:
                    print(f"  0x{code:02X}  {name:<42}  --", flush=True)

            prev_succeeded = succeeded

    # Write markdown summary
    with summary_path.open("w") as md_f:
        md_f.write("# DDC VCP Scan Summary\n\n")
        md_f.write(f"- **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        md_f.write(f"- **Bus:** I2C-{bus}\n")
        md_f.write(f"- **Codes scanned:** 256 (0x00–0xFF)\n")
        md_f.write(f"- **Codes responding:** {len(responding)}\n")
        md_f.write(f"- **Log:** `{log_path.name}`\n\n")

        if capabilities:
            md_f.write("## Capability String\n\n")
            md_f.write(f"```\n{capabilities}\n```\n\n")

        md_f.write("## Responding Codes\n\n")
        md_f.write("| Code | Name | Type | Current | Max / SL |\n")
        md_f.write("|------|------|------|---------|----------|\n")
        for r in responding:
            md_f.write(_summary_row(r) + "\n")

        md_f.write("\n*Generated by `scripts/ddc-scan.py`*\n")

    print(f"\nDone. {len(responding)}/256 codes responded.")
    print(f"Log:     {log_path}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
