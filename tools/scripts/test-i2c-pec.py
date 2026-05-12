#!/usr/bin/env python3
"""
test-i2c-pec.py — Probe whether I2C device 0x58 supports SMBus PEC.

Reads a handful of known-stable registers first without PEC (baseline),
then with PEC enabled. If the device doesn't support PEC the kernel will
either return an error or silently mis-frame the response (the slave's last
data byte gets treated as the CRC byte, so the actual value byte is missing).

Expected baseline for 0x58 register 0x02 = 0x79 (Novatek scaler sanity byte).

Usage:
    python3 tools/scripts/test-i2c-pec.py
    python3 tools/scripts/test-i2c-pec.py --bus 13 --device 0x58
"""

import argparse
import sys
import time

try:
    from smbus2 import SMBus
except ImportError:
    print("ERROR: smbus2 not installed. Run: pip install smbus2")
    sys.exit(1)

# Registers with known stable values when monitor has an active source.
# Format: (register, expected_value, label)
PROBE_REGS: list[tuple[int, int | None, str]] = [
    (0x02, 0x79, "scaler sanity"),
    (0xA7, 0xF8, "pipeline flags"),
    (0x3C, None, "layout byte 0"),
    (0x3D, None, "layout byte 1"),
    (0x3E, None, "layout byte 2"),
]


def read_reg(bus: SMBus, device: int, reg: int) -> int | None:
    try:
        return bus.read_byte_data(device, reg)
    except OSError as exc:
        return None, str(exc)


def probe(bus_num: int, device: int) -> None:
    print(f"Bus: /dev/i2c-{bus_num}  Device: {hex(device)}\n")

    # --- baseline (PEC off) ---
    print("=== Without PEC ===")
    baseline: dict[int, int | None] = {}
    with SMBus(bus_num) as bus:
        bus.pec = 0
        for reg, expected, label in PROBE_REGS:
            result = read_reg(bus, device, reg)
            if isinstance(result, tuple):
                val, err = result
                status = f"ERROR: {err}"
            else:
                val = result
                match = ""
                if expected is not None:
                    match = " ✓" if val == expected else f" ✗ (expected {hex(expected)})"
                status = f"{hex(val) if val is not None else 'null'}{match}"
            baseline[reg] = val
            print(f"  0x{reg:02X}  {label:<20} {status}")
            time.sleep(0.02)

    print()
    time.sleep(0.1)

    # --- with PEC ---
    print("=== With PEC ===")
    pec_ok = True
    with SMBus(bus_num) as bus:
        bus.pec = 1
        for reg, expected, label in PROBE_REGS:
            result = read_reg(bus, device, reg)
            if isinstance(result, tuple):
                val, err = result
                status = f"ERROR: {err}"
                pec_ok = False
            else:
                val = result
                agrees = val == baseline[reg]
                match = " ✓ agrees" if agrees else f" ✗ MISMATCH (baseline={hex(baseline[reg]) if baseline[reg] is not None else 'null'})"
                status = f"{hex(val) if val is not None else 'null'}{match}"
                if not agrees:
                    pec_ok = False
            print(f"  0x{reg:02X}  {label:<20} {status}")
            time.sleep(0.02)

    print()
    if pec_ok:
        print("RESULT: PEC reads agree with baseline — device likely supports PEC.")
    else:
        print("RESULT: PEC reads differ from baseline or errored — device does NOT support PEC.")
        print("        The mismatch is expected: without PEC support the slave sends N bytes,")
        print("        but the master reads N+1 expecting a trailing CRC, shifting the frame.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bus", type=int, default=13, metavar="N")
    parser.add_argument("--device", type=lambda x: int(x, 16), default=0x58, metavar="HEX")
    args = parser.parse_args()
    probe(args.bus, args.device)


if __name__ == "__main__":
    main()
