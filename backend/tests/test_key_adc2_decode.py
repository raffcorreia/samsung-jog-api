"""KEY_ADC2 voltage classification (Phase 2 measurements)."""

from __future__ import annotations

import pytest

from pi_deck.hardware.key_adc2_decode import decode_key_adc2_direction


@pytest.mark.parametrize(
    ("mv", "expected"),
    [
        (0, "up"),
        (500, "up"),
        (1200, "down"),
        (2000, "right"),
        (2600, "left"),
        (3200, None),
        (3300, None),
    ],
)
def test_decode_key_adc2_direction(mv: int, expected: str | None) -> None:
    assert decode_key_adc2_direction(mv) == expected
