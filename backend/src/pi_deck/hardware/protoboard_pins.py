"""BCM GPIO map for the discrete-component protoboard validation build.

Pin map source: docs/implementation/phase-6-execution.md. When integrated PCBs
replace this wiring, add another pin module and select it via configuration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class JogAction(Enum):
    """Logical JOG actions; each maps to one drive transistor on the protoboard."""

    CENTER = "center"
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


_DRIVE_BCM: dict[JogAction, int] = {
    JogAction.CENTER: 5,
    JogAction.UP: 6,
    JogAction.DOWN: 13,
    JogAction.LEFT: 19,
    JogAction.RIGHT: 26,
}


@dataclass(frozen=True, slots=True)
class ProtoboardPins:
    """BCM numbers for the discrete protoboard (board numbering)."""

    i2c_sda: int = 2
    i2c_scl: int = 3
    # ADS1115 ALERT/RDY → ``wait_for_edge`` in observation_bus + I²C poll backup.
    ads_alert: int = 17
    key_adc1_digital: int = 27
    key_led_digital: int = 22
    drive_center: int = 5
    drive_up: int = 6
    drive_down: int = 13
    drive_left: int = 19
    drive_right: int = 26

    def drive_bcm(self, action: JogAction) -> int:
        return _DRIVE_BCM[action]
