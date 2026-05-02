#!/usr/bin/env python3
"""
monitor-state.py — Live Samsung C34J79x layout state via I2C device 0x58.

Polls registers 0x3C, 0x3D, 0x3E, 0xA1, 0xA3, 0xA5 on I2C bus 13 and
matches them against known signatures to report the current display layout:
single-source or PBP (Picture by Picture) with source pair.

Usage:
    python3 scripts/monitor-state.py            # poll every 1s
    python3 scripts/monitor-state.py --interval 0.5
    python3 scripts/monitor-state.py --once     # single read, then exit
    python3 scripts/monitor-state.py --dump     # dump all 0x58 registers 0x00-0xFF

Requirements:
    pip install smbus2
    User must be in the i2c group.
"""

import argparse
import sys
import time
from dataclasses import dataclass

try:
    import smbus2
except ImportError:
    print("ERROR: smbus2 not installed. Run: pip install smbus2")
    sys.exit(1)

BUS = 13
DEVICE = 0x58
KEY_REGS = (0x3C, 0x3D, 0x3E, 0xA1, 0xA3, 0xA5)


@dataclass(frozen=True)
class Signature:
    label: str
    layout: str
    regs: dict[int, int]


SIGNATURES = [
    Signature("single_dp",    "Single DP",                {0x3C: 0x55, 0x3D: 0x3D, 0x3E: 0x06, 0xA1: 0x21, 0xA3: 0xC7, 0xA5: 0xBE}),
    Signature("single_hdmi",  "Single HDMI",              {0x3C: 0x71, 0x3D: 0x01, 0x3E: 0x02, 0xA1: 0x21, 0xA3: 0xC8, 0xA5: 0xC0}),
    Signature("single_tb",    "Single Thunderbolt/USB-C", {0x3C: 0x89, 0x3D: 0x29, 0x3E: 0x07, 0xA1: 0x22, 0xA3: 0xCB, 0xA5: 0xC0}),
    Signature("pbp_dp_hdmi",  "PBP  DP left / HDMI right",{0x3C: 0xED, 0x3D: 0x7C, 0x3E: 0x07, 0xA1: 0x21, 0xA3: 0xC9, 0xA5: 0x00}),
    Signature("pbp_hdmi_dp",  "PBP  HDMI left / DP right",{0x3C: 0x15, 0x3D: 0x1B, 0x3E: 0x00, 0xA1: 0x22, 0xA3: 0xC9, 0xA5: 0xC1}),
    Signature("pbp_dp_tb",    "PBP  DP left / TB right",  {0x3C: 0xDF, 0x3D: 0x1F, 0x3E: 0x03, 0xA1: 0x22, 0xA3: 0xC7, 0xA5: 0xC1}),
    Signature("pbp_tb_dp",    "PBP  TB left / DP right",  {0x3C: 0x76, 0x3D: 0x1B, 0x3E: 0x03, 0xA1: 0x21, 0xA3: 0xCC, 0xA5: 0xC0}),
    Signature("pbp_hdmi_tb",  "PBP  HDMI left / TB right",{0x3C: 0x52, 0x3D: 0x3D, 0x3E: 0x06, 0xA1: 0x22, 0xA3: 0xC9, 0xA5: 0x00}),
    Signature("pbp_tb_hdmi",  "PBP  TB left / HDMI right",{0x3C: 0x28, 0x3D: 0x65, 0x3E: 0x04, 0xA1: 0x21, 0xA3: 0xC8, 0xA5: 0xC0}),
]


def read_key_regs(bus: smbus2.SMBus) -> dict[int, int] | None:
    result = {}
    for reg in KEY_REGS:
        try:
            result[reg] = bus.read_byte_data(DEVICE, reg)
        except OSError as e:
            print(f"  Read error on 0x{reg:02X}: {e}", file=sys.stderr)
            return None
    return result


def match(regs: dict[int, int]) -> tuple[Signature | None, int]:
    best_sig, best_score = None, -1
    for sig in SIGNATURES:
        score = sum(1 for r in KEY_REGS if regs.get(r) == sig.regs[r])
        if score > best_score:
            best_score, best_sig = score, sig
    return best_sig, best_score


def format_regs(regs: dict[int, int]) -> str:
    return "  ".join(f"0x{r:02X}={regs[r]:02X}" for r in KEY_REGS)


def dump_all(bus: smbus2.SMBus) -> None:
    print(f"Full register dump — I2C bus {BUS}, device 0x{DEVICE:02X}\n")
    for row in range(0, 256, 16):
        vals = []
        for col in range(16):
            reg = row + col
            try:
                v = bus.read_byte_data(DEVICE, reg)
                vals.append(f"{v:02X}")
            except OSError:
                vals.append("--")
        print(f"  0x{row:02X}: {' '.join(vals)}")


def print_state(regs: dict[int, int]) -> None:
    raw = format_regs(regs)
    sig, score = match(regs)

    if score == len(KEY_REGS):
        state = f"[{sig.layout}]"
        confidence = "exact match"
    elif score >= 4:
        state = f"[{sig.layout}?]"
        confidence = f"partial match ({score}/{len(KEY_REGS)})"
    else:
        state = "[UNKNOWN — no signal or unrecognised state]"
        confidence = f"best guess: {sig.layout} ({score}/{len(KEY_REGS)})"

    print(f"  {raw}")
    print(f"  {state}  ({confidence})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Samsung C34J79x live layout state")
    parser.add_argument("--bus", type=int, default=BUS, help=f"I2C bus number (default: {BUS})")
    parser.add_argument("--interval", type=float, default=1.0,
                        help="Poll interval in seconds (default: 1.0)")
    parser.add_argument("--once", action="store_true", help="Single read then exit")
    parser.add_argument("--dump", action="store_true", help="Dump all 0x58 registers and exit")
    args = parser.parse_args()

    try:
        bus = smbus2.SMBus(args.bus)
    except Exception as e:
        print(f"ERROR: cannot open I2C bus {args.bus}: {e}")
        sys.exit(1)

    if args.dump:
        dump_all(bus)
        bus.close()
        return

    print(f"Polling I2C bus {args.bus}, device 0x{DEVICE:02X} — Ctrl+C to stop\n")
    print(f"  Registers: " + "  ".join(f"0x{r:02X}" for r in KEY_REGS))
    print()

    prev_regs = None
    try:
        while True:
            regs = read_key_regs(bus)
            if regs is None:
                time.sleep(args.interval)
                continue

            changed = regs != prev_regs
            if changed or args.once:
                ts = time.strftime("%H:%M:%S")
                marker = ">" if changed and prev_regs is not None else " "
                print(f"{marker} {ts}")
                print_state(regs)
                print()
                prev_regs = regs

            if args.once:
                break

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        bus.close()


if __name__ == "__main__":
    main()
