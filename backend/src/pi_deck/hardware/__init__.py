"""Low-level hardware only: GPIO, I2C, DDC adapters — no HTTP or workflow logic."""

from pi_deck.hardware.protoboard_pins import JogAction, ProtoboardPins

__all__ = ["JogAction", "ProtoboardPins"]
