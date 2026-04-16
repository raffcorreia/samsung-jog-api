"""Classify KEY_ADC2 voltage (ADS1115 AIN0) into a logical direction.

Threshold midpoints use powered measurements from phase-2 execution docs
(idle 3.29 V, down 1.35, right 2.16, up 0.01, left 2.88)."""

from __future__ import annotations

from typing import Literal

Direction = Literal["up", "down", "left", "right"]


def decode_key_adc2_direction(mv: int) -> Direction | None:
    """Return direction when KEY_ADC2 is not idle, else ``None``.

    Boundaries (mV) are midpoints between documented state voltages.
    """
    if mv < 680:
        return "up"
    if mv < 1755:
        return "down"
    if mv < 2520:
        return "right"
    if mv < 3085:
        return "left"
    return None
