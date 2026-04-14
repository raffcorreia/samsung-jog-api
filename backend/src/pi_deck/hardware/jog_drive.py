"""Drive KEY_ADC1 / KEY_ADC2 resistor legs via discrete outputs (active high)."""

from __future__ import annotations

import time
from types import TracebackType

from gpiozero import OutputDevice

from pi_deck.hardware.protoboard_pins import JogAction, ProtoboardPins


class JogDrive:
    """Five low-side drive lines; HIGH asserts the corresponding jog direction."""

    def __init__(self, pins: ProtoboardPins | None = None) -> None:
        self._pins = pins or ProtoboardPins()
        self._outs: dict[JogAction, OutputDevice] = {}
        for action in JogAction:
            bcm = self._pins.drive_bcm(action)
            self._outs[action] = OutputDevice(bcm, active_high=True, initial_value=False)

    def release_all(self) -> None:
        for out in self._outs.values():
            out.off()

    def set_line(self, action: JogAction, active: bool) -> None:
        """Turn one drive line on or off without affecting other lines (multitouch / multicommand)."""
        out = self._outs[action]
        if active:
            out.on()
        else:
            out.off()

    def hold(self, action: JogAction) -> None:
        """Exclusive single-direction assert (legacy pulse path)."""
        self.release_all()
        self._outs[action].on()

    def pulse(self, action: JogAction, duration_s: float) -> None:
        """Assert one direction for ``duration_s`` seconds, then release all lines."""
        self.hold(action)
        time.sleep(duration_s)
        self.release_all()

    def close(self) -> None:
        for out in self._outs.values():
            out.close()
        self._outs.clear()

    def __enter__(self) -> JogDrive:
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _tb: TracebackType | None,
    ) -> None:
        self.close()
