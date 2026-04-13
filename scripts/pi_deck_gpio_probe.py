#!/usr/bin/env python3
"""Bench script: GPIO + ADS1115 smoke tests for the discrete protoboard (run on Raspberry Pi).

Run via `./scripts/pi-deck-gpio-probe` or with ``PYTHONPATH=backend/src`` set. Not part of the
installable API — kept under ``scripts/`` for bring-up.
"""

from __future__ import annotations

import argparse
import logging
import sys

from pi_deck.hardware.ads1115 import Ads1115
from pi_deck.hardware.ads_alert_observe import AdsAlertObserve
from pi_deck.hardware.jog_drive import JogDrive
from pi_deck.hardware.jog_observe import KeyAdc1Observe
from pi_deck.hardware.led_observe import KeyLedObserve
from pi_deck.hardware.protoboard_pins import JogAction

_LOG = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(description="GPIO / ADS1115 bench probe (protoboard).")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("pulse", help="Pulse one drive line for a few milliseconds.")
    sp.add_argument(
        "action",
        type=str,
        choices=[a.name.lower() for a in JogAction],
        help="Jog direction to assert",
    )
    sp.add_argument("--ms", type=float, default=80.0, help="Pulse width in milliseconds")

    sub.add_parser("read-ins", help="Print KEY_ADC1 and KEY_LED digital levels once.")

    sub.add_parser("read-alert", help="Print ADS1115 ALERT/RDY digital level once.")

    sa = sub.add_parser("read-ads", help="Read ADS1115 single-ended channel in mV.")
    sa.add_argument("--channel", type=int, default=0, help="AIN channel 0–3 (KEY_ADC2 wiring)")

    args = p.parse_args(argv)

    if args.cmd == "pulse":
        action = JogAction[args.action.upper()]
        duration_s = args.ms / 1000.0
        with JogDrive() as drive:
            _LOG.info("Pulsing %s for %.2f ms", action.value, args.ms)
            drive.pulse(action, duration_s)
        return 0

    if args.cmd == "read-ins":
        k1 = KeyAdc1Observe()
        led = KeyLedObserve()
        try:
            _LOG.info("KEY_ADC1 (digital) active=%s", k1.is_active)
            _LOG.info("KEY_LED (digital) active=%s", led.is_active)
        finally:
            k1.close()
            led.close()
        return 0

    if args.cmd == "read-alert":
        alert = AdsAlertObserve()
        try:
            _LOG.info("ADS1115 ALERT/RDY active=%s", alert.is_active)
        finally:
            alert.close()
        return 0

    if args.cmd == "read-ads":
        adc = Ads1115()
        try:
            mv = adc.read_single_ended_mv(args.channel)
            _LOG.info("AIN%d ≈ %d mV", args.channel, mv)
        finally:
            adc.close()
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
