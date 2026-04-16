#!/usr/bin/env python3
"""Standalone demo: RPi.GPIO RISING interrupt on BCM 17 with internal pull-down.

Run on the Raspberry Pi (same venv as pi-deck if you use RPi.GPIO there)::

    PI_DECK_ADS_ALERT_BCM=17 python3 scripts/pi-deck-ads-alert-rpi-demo.py

Ctrl+C exits. This does not start FastAPI — use to validate ALERT wiring in isolation.
"""

from __future__ import annotations

import os
import signal
import sys
import time

try:
    import RPi.GPIO as GPIO  # noqa: N814
except ImportError:
    print("RPi.GPIO is only available on Raspberry Pi OS / Linux with GPIO.", file=sys.stderr)
    sys.exit(1)

BCM = int(os.environ.get("PI_DECK_ADS_ALERT_BCM", "17"))


def main() -> None:
    stop = False

    def _stop(_sig: int, _frame: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BCM, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    def my_callback(channel: int) -> None:
        print("Interrupt detected on pin", channel)
        sys.stdout.flush()

    GPIO.add_event_detect(BCM, GPIO.RISING, callback=my_callback)

    print(f"Listening for RISING edges on BCM {BCM} (PUD_DOWN). Ctrl+C to exit.", flush=True)
    while not stop:
        time.sleep(0.5)

    GPIO.remove_event_detect(BCM)
    GPIO.cleanup(BCM)
    print("Done.")


if __name__ == "__main__":
    main()
