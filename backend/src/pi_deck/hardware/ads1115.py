"""Minimal ADS1115 access over I2C (e.g. KEY_ADC2 on the protoboard)."""

from __future__ import annotations

import time
from dataclasses import dataclass

from smbus2 import SMBus


@dataclass(frozen=True, slots=True)
class Ads1115Config:
    """Default address with ADDR pin to GND."""

    bus_id: int = 1
    address: int = 0x48


class Ads1115:
    """Single-shot reads for bench and bring-up."""

    REG_POINTER = 0x00
    REG_CONFIG = 0x01

    def __init__(self, config: Ads1115Config | None = None) -> None:
        self._cfg = config or Ads1115Config()
        self._bus = SMBus(self._cfg.bus_id)

    def close(self) -> None:
        self._bus.close()

    def read_single_ended_mv(self, channel: int) -> int:
        """Return millivolts for single-ended input AIN``channel`` (0–3), FSR ±4.096 V."""
        if channel not in (0, 1, 2, 3):
            raise ValueError("channel must be 0..3")

        mux = 0x4000 + (channel << 12)
        pga = 0x0200  # ±4.096 V → 0.125 mV per count
        mode_dr_comp = 0x0100 | 0x0080 | 0x0003
        config = 0x8000 | mux | pga | mode_dr_comp

        data = [(config >> 8) & 0xFF, config & 0xFF]
        self._bus.write_i2c_block_data(self._cfg.address, self.REG_CONFIG, data)
        time.sleep(0.01)
        raw = self._bus.read_i2c_block_data(self._cfg.address, self.REG_POINTER, 2)
        value = (raw[0] << 8) | raw[1]
        if value & 0x8000:
            value -= 0x10000
        return int(value * 0.125)
