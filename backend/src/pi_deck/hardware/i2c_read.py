"""Reliable single-byte I2C register reads with majority voting.

Raw SMBus byte reads have no checksum. A single-bit glitch returns a silently
wrong value with no indication of failure. read_byte_majority retries up to
MAX_READS times and returns the first value seen at least twice (early exit),
or None if no two reads agree (no-consensus) or all reads error.

Typical cost: 2 reads (clean bus). Worst case: MAX_READS reads.
"""

from __future__ import annotations

from smbus2 import SMBus

MAX_READS = 5


def read_byte_majority(bus: SMBus, device: int, reg: int) -> int | None:
    """Read one register byte with majority voting across up to MAX_READS attempts.

    Returns None if all reads errored or no two reads agreed.
    """
    counts: dict[int, int] = {}
    for _ in range(MAX_READS):
        try:
            val = bus.read_byte_data(device, reg)
            counts[val] = counts.get(val, 0) + 1
            if counts[val] >= 2:
                return val
        except OSError:
            pass
    if not counts:
        return None
    best = max(counts, key=lambda v: counts[v])
    if counts[best] < 2:
        return None
    return best
