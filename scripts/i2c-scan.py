#!/usr/bin/env python3
"""
i2c-scan.py — Raw I2C register scan + DDC VCP scan for Phase 24 investigation.

Reads all 256 registers (0x00–0xFF) from I2C devices 0x54 and 0x58 directly,
then reads key DDC VCP codes from device 0x37 using the DDC/CI protocol.

Device 0x37 only speaks DDC/CI protocol — raw register reads return bus echo.
DDC VCP codes (0x00–0xFF) are a separate namespace accessed via protocol requests.

Usage:
    python3 scripts/i2c-scan.py                          # scan defaults
    python3 scripts/i2c-scan.py --devices 0x54,0x58
    python3 scripts/i2c-scan.py --bus 13 --output docs/investigation/i2c-scan
    python3 scripts/i2c-scan.py --no-ddc                 # skip DDC VCP scan

Requirements:
    pip install smbus2
    User must be in the i2c group.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from smbus2 import SMBus, i2c_msg
except ImportError:
    print("ERROR: smbus2 not installed. Run: pip install smbus2")
    sys.exit(1)

DEFAULT_BUS = 13
DEFAULT_DEVICES = [0x54, 0x58]  # 0x37 excluded — raw reads return only bus echo

ANNOTATIONS: dict[int, dict[int, str]] = {
    0x58: {
        0x3C: "layout key reg A (noisy)",
        0x3D: "layout key reg B (noisy)",
        0x3E: "layout key reg C (noisy)",
        0xA1: "state byte — 0x00=no signal",
        0xA3: "state byte (noisy when active)",
        0xA5: "state byte (noisy)",
        0xE0: "primary source/pipeline — unique per input",
        0xE1: "secondary source indicator",
        0xE2: "HDMI-single flag",
        0xE3: "HDMI-single flag",
    },
    0x54: {
        0x10: "HDCP state — 0x01=HDMI inactive, 0x03=HDMI port active",
        0x40: "HDCP active flag — 0x00=inactive, 0x0F=HDMI port active",
    },
}

# DDC VCP codes to read via protocol (device 0x37)
DDC_VCP_CODES: dict[int, str] = {
    0x10: "Brightness",
    0x12: "Contrast",
    0x60: "Input Source",
    0x62: "Audio Speaker Volume",
    0xD6: "Power Mode",
    0xDC: "Display Application",
}


def now_ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ddc_get_vcp(bus: SMBus, feature: int) -> dict | None:
    """Read a single DDC/CI VCP code from device 0x37 via protocol request."""
    dst_w  = 0x6E  # 0x37 << 1, write form
    src    = 0x51  # host address
    opcode = 0x01  # Get VCP Feature
    length = 2     # opcode + feature code

    pkt = [src, length | 0x80, opcode, feature]
    checksum = dst_w
    for b in pkt:
        checksum ^= b
    pkt.append(checksum)

    try:
        write_msg = i2c_msg.write(0x37, pkt)
        bus.i2c_rdwr(write_msg)
        time.sleep(0.05)

        read_msg = i2c_msg.read(0x37, 11)
        bus.i2c_rdwr(read_msg)
        reply = list(read_msg)

        # Reply: [src=0x6E, len|0x80, opcode=0x02, result, vcp_code,
        #         vcp_type, max_hi, max_lo, cur_hi, cur_lo, checksum]
        if len(reply) < 11 or reply[2] != 0x02 or reply[4] != feature:
            return {"status": "error", "error": f"unexpected reply: {[hex(b) for b in reply]}"}

        return {
            "status": "ok",
            "current": (reply[8] << 8) | reply[9],
            "max":     (reply[6] << 8) | reply[7],
            "type":    "SNC" if reply[5] == 0x01 else "C",
            "raw":     [hex(b) for b in reply],
        }
    except OSError as e:
        return {"status": "error", "error": str(e)}


def scan_ddc(bus: SMBus) -> list[dict]:
    results = []
    for code, name in DDC_VCP_CODES.items():
        entry = {
            "ts":      now_ts(),
            "device":  "0x37_ddc",
            "vcp":     f"0x{code:02X}",
            "name":    name,
        }
        result = ddc_get_vcp(bus, code)
        if result and result["status"] == "ok":
            entry["status"]  = "ok"
            entry["current"] = f"0x{result['current']:02X}"
            entry["max"]     = f"0x{result['max']:02X}"
            entry["type"]    = result["type"]
        else:
            entry["status"] = "error"
            entry["error"]  = result.get("error", "no reply") if result else "no reply"
        results.append(entry)
        time.sleep(0.1)
    return results


def scan_device(bus: SMBus, device: int) -> list[dict]:
    results = []
    for reg in range(0x00, 0x100):
        try:
            value = bus.read_byte_data(device, reg)
            entry = {
                "ts":     now_ts(),
                "device": f"0x{device:02X}",
                "reg":    f"0x{reg:02X}",
                "value":  f"0x{value:02X}",
                "status": "ok",
            }
            note = ANNOTATIONS.get(device, {}).get(reg)
            if note:
                entry["note"] = note
        except OSError as e:
            entry = {
                "ts":     now_ts(),
                "device": f"0x{device:02X}",
                "reg":    f"0x{reg:02X}",
                "status": "error",
                "error":  str(e),
            }
        results.append(entry)
        time.sleep(0.02)
    return results


def write_summary(path: Path, device: int, results: list[dict], scan_ts: str) -> None:
    ok     = [r for r in results if r["status"] == "ok"]
    errors = [r for r in results if r["status"] != "ok"]

    with path.open("w") as f:
        f.write(f"# I2C Raw Scan — Device 0x{device:02X}\n\n")
        f.write(f"- **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"- **Bus:** I2C-{DEFAULT_BUS}\n")
        f.write(f"- **Readable:** {len(ok)}/256\n\n")

        if ok:
            f.write("## Readable Registers\n\n")
            f.write("| Reg | Value | Note |\n|-----|-------|------|\n")
            for r in ok:
                f.write(f"| `{r['reg']}` | `{r['value']}` | {r.get('note', '')} |\n")

        if errors:
            f.write("\n## Unreadable Registers\n\n")
            error_regs = [int(r["reg"], 16) for r in errors]
            ranges, start, prev = [], error_regs[0], error_regs[0]
            for reg in error_regs[1:]:
                if reg != prev + 1:
                    ranges.append((start, prev))
                    start = reg
                prev = reg
            ranges.append((start, prev))
            for s, e in ranges:
                f.write(f"- `0x{s:02X}`\n" if s == e else f"- `0x{s:02X}`–`0x{e:02X}`\n")

        f.write(f"\n*Generated by `scripts/i2c-scan.py`*\n")


def write_ddc_summary(path: Path, results: list[dict]) -> None:
    with path.open("w") as f:
        f.write("# DDC VCP Scan — Device 0x37 (via DDC/CI protocol)\n\n")
        f.write(f"- **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("| VCP | Name | Current | Max | Status |\n")
        f.write("|-----|------|---------|-----|--------|\n")
        for r in results:
            if r["status"] == "ok":
                f.write(f"| `{r['vcp']}` | {r['name']} | `{r['current']}` | `{r['max']}` | ok |\n")
            else:
                f.write(f"| `{r['vcp']}` | {r['name']} | — | — | error: {r.get('error','')} |\n")
        f.write(f"\n*Generated by `scripts/i2c-scan.py`*\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="I2C register scanner + DDC VCP reader")
    parser.add_argument("--bus",      type=int,  default=DEFAULT_BUS)
    parser.add_argument("--devices",  type=str,  help="Comma-separated hex addresses (default: 0x54,0x58)")
    parser.add_argument("--output",   type=Path, default=Path("docs/investigation/i2c-scan"))
    parser.add_argument("--no-ddc",   action="store_true", help="Skip DDC VCP scan")
    args = parser.parse_args()

    devices = DEFAULT_DEVICES
    if args.devices:
        devices = [int(d.strip(), 16) for d in args.devices.split(",")]

    try:
        bus = SMBus(args.bus)
    except Exception as e:
        print(f"ERROR: cannot open I2C bus {args.bus}: {e}")
        sys.exit(1)

    args.output.mkdir(parents=True, exist_ok=True)
    scan_ts  = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = args.output / f"i2c-scan-{scan_ts}.jsonl"

    print(f"Bus: I2C-{args.bus}  Log: {log_path}\n")

    all_results: list[dict] = []

    # Raw I2C scans
    with log_path.open("w") as log_f:
        for device in devices:
            print(f"Scanning 0x{device:02X} (256 registers)...", flush=True)
            results = scan_device(bus, device)
            all_results.extend(results)
            for entry in results:
                log_f.write(json.dumps(entry) + "\n")
            log_f.flush()

            ok_count = sum(1 for r in results if r["status"] == "ok")
            print(f"  {ok_count}/256 readable")

            summary_path = args.output / f"i2c-scan-{scan_ts}-0x{device:02X}-summary.md"
            write_summary(summary_path, device, results, scan_ts)
            print(f"  Summary: {summary_path}\n")

        # DDC VCP scan
        if not args.no_ddc:
            print("Scanning DDC VCP codes on 0x37 (via DDC/CI protocol)...", flush=True)
            ddc_results = scan_ddc(bus)
            all_results.extend(ddc_results)
            for entry in ddc_results:
                log_f.write(json.dumps(entry) + "\n")

            ok_count = sum(1 for r in ddc_results if r["status"] == "ok")
            print(f"  {ok_count}/{len(DDC_VCP_CODES)} VCP codes readable")

            ddc_summary_path = args.output / f"i2c-scan-{scan_ts}-ddc-summary.md"
            write_ddc_summary(ddc_summary_path, ddc_results)
            print(f"  Summary: {ddc_summary_path}\n")

    bus.close()
    print(f"Done. Log: {log_path}")


if __name__ == "__main__":
    main()
