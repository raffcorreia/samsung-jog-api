#!/usr/bin/env python3
"""
backfill-test-case.py — Add test_case field to every canonical capture.

Matches each capture's attributes against the same TEST_CASES definitions
used by the register explorer and writes the matched number into the JSON.
Captures that don't match any test case get test_case: null.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CAPTURE_ROOT = REPO_ROOT / "docs" / "investigation" / "register-captures"

TEST_CASES = [
    {"num": 1,  "filters": {"power": ["standby"]}},
    {"num": 2,  "filters": {"power": ["on"], "layout": ["idle"]}},
    {"num": 3,  "filters": {"power": ["on"], "layout": ["single"], "primary": ["tb"]}},
    {"num": 4,  "filters": {"power": ["on"], "layout": ["pip"], "primary": ["tb"], "secondary": ["hdmi"], "size": ["small"]}},
    {"num": 5,  "filters": {"power": ["on"], "layout": ["pip"], "primary": ["tb"], "secondary": ["hdmi"], "size": ["medium"]}},
    {"num": 6,  "filters": {"power": ["on"], "layout": ["pip"], "primary": ["tb"], "secondary": ["hdmi"], "size": ["large"]}},
    {"num": 7,  "filters": {"power": ["on"], "layout": ["pip"], "primary": ["tb"], "secondary": ["dp"], "size": ["large"]}},
    {"num": 8,  "filters": {"power": ["on"], "layout": ["pip"], "primary": ["tb"], "secondary": ["dp"], "size": ["medium"]}},
    {"num": 9,  "filters": {"power": ["on"], "layout": ["pip"], "primary": ["tb"], "secondary": ["dp"], "size": ["small"]}},
    {"num": 10, "filters": {"power": ["on"], "layout": ["pbp"], "primary": ["tb"], "secondary": ["dp"],   "audio": ["left"]}},
    {"num": 11, "filters": {"power": ["on"], "layout": ["pbp"], "primary": ["tb"], "secondary": ["dp"],   "audio": ["right"]}},
    {"num": 12, "filters": {"power": ["on"], "layout": ["pbp"], "primary": ["tb"], "secondary": ["hdmi"], "audio": ["left"]}},
    {"num": 13, "filters": {"power": ["on"], "layout": ["pbp"], "primary": ["tb"], "secondary": ["hdmi"], "audio": ["right"]}},
    {"num": 14, "filters": {"power": ["on"], "layout": ["single"], "primary": ["hdmi"]}},
    {"num": 15, "filters": {"power": ["on"], "layout": ["pip"], "primary": ["hdmi"], "secondary": ["tb"], "size": ["small"]}},
    {"num": 16, "filters": {"power": ["on"], "layout": ["pip"], "primary": ["hdmi"], "secondary": ["tb"], "size": ["medium"]}},
    {"num": 17, "filters": {"power": ["on"], "layout": ["pip"], "primary": ["hdmi"], "secondary": ["tb"], "size": ["large"]}},
    {"num": 18, "filters": {"power": ["on"], "layout": ["pip"], "primary": ["hdmi"], "secondary": ["dp"], "size": ["large"]}},
    {"num": 19, "filters": {"power": ["on"], "layout": ["pip"], "primary": ["hdmi"], "secondary": ["dp"], "size": ["medium"]}},
    {"num": 20, "filters": {"power": ["on"], "layout": ["pip"], "primary": ["hdmi"], "secondary": ["dp"], "size": ["small"]}},
    {"num": 21, "filters": {"power": ["on"], "layout": ["pbp"], "primary": ["hdmi"], "secondary": ["dp"],   "audio": ["right"]}},
    {"num": 22, "filters": {"power": ["on"], "layout": ["pbp"], "primary": ["hdmi"], "secondary": ["dp"],   "audio": ["left"]}},
    {"num": 23, "filters": {"power": ["on"], "layout": ["pbp"], "primary": ["hdmi"], "secondary": ["tb"],   "audio": ["right"]}},
    {"num": 24, "filters": {"power": ["on"], "layout": ["pbp"], "primary": ["hdmi"], "secondary": ["tb"],   "audio": ["left"]}},
    {"num": 25, "filters": {"power": ["on"], "layout": ["single"], "primary": ["dp"]}},
    {"num": 26, "filters": {"power": ["on"], "layout": ["pip"], "primary": ["dp"], "secondary": ["tb"], "size": ["small"]}},
    {"num": 27, "filters": {"power": ["on"], "layout": ["pip"], "primary": ["dp"], "secondary": ["tb"], "size": ["medium"]}},
    {"num": 28, "filters": {"power": ["on"], "layout": ["pip"], "primary": ["dp"], "secondary": ["tb"], "size": ["large"]}},
    {"num": 29, "filters": {"power": ["on"], "layout": ["pip"], "primary": ["dp"], "secondary": ["hdmi"], "size": ["large"]}},
    {"num": 30, "filters": {"power": ["on"], "layout": ["pip"], "primary": ["dp"], "secondary": ["hdmi"], "size": ["medium"]}},
    {"num": 31, "filters": {"power": ["on"], "layout": ["pip"], "primary": ["dp"], "secondary": ["hdmi"], "size": ["small"]}},
    {"num": 32, "filters": {"power": ["on"], "layout": ["pbp"], "primary": ["dp"], "secondary": ["hdmi"], "audio": ["right"]}},
    {"num": 33, "filters": {"power": ["on"], "layout": ["pbp"], "primary": ["dp"], "secondary": ["hdmi"], "audio": ["left"]}},
    {"num": 34, "filters": {"power": ["on"], "layout": ["pbp"], "primary": ["dp"], "secondary": ["tb"],   "audio": ["right"]}},
    {"num": 35, "filters": {"power": ["on"], "layout": ["pbp"], "primary": ["dp"], "secondary": ["tb"],   "audio": ["left"]}},
]


def pip_size_label(capture: dict) -> str | None:
    size = (capture.get("pip") or {}).get("size")
    if size == 1: return "small"
    if size == 2: return "medium"
    if size == 3: return "large"
    return None


def match_test_case(capture: dict) -> int | None:
    power   = capture.get("power_state")
    layout  = capture.get("layout_mode")
    primary = capture.get("primary_input")
    secondary = capture.get("secondary_input")
    audio   = capture.get("audio_side")
    size    = pip_size_label(capture)

    for tc in TEST_CASES:
        f = tc["filters"]
        if "power"     in f and power     not in f["power"]:     continue
        if "layout"    in f and layout    not in f["layout"]:    continue
        if "primary"   in f and primary   not in f["primary"]:   continue
        if "secondary" in f and secondary not in f["secondary"]: continue
        if "audio"     in f and audio     not in f["audio"]:     continue
        if "size"      in f and size      not in f["size"]:      continue
        return tc["num"]
    return None


def main() -> None:
    paths = sorted(CAPTURE_ROOT.glob("*.json"))
    unmatched = []

    for path in paths:
        data = json.loads(path.read_text())
        if data.get("jog_button") is not None:
            # jog-button-scan.py assigns test_case directly — leave it alone
            tc = data.get("test_case")
            status = f"TC {tc:2d}" if tc is not None else "  NONE"
            print(f"  {status}  {path.name}  (jog — preserved)")
            continue
        tc = match_test_case(data)
        data["test_case"] = tc
        path.write_text(json.dumps(data, indent=2) + "\n")
        status = f"TC {tc:2d}" if tc is not None else "  NONE"
        print(f"  {status}  {path.name}")
        if tc is None:
            unmatched.append(path.name)

    print(f"\n{len(paths)} captures processed.")
    if unmatched:
        print(f"WARNING: {len(unmatched)} unmatched:")
        for name in unmatched:
            print(f"  {name}")


if __name__ == "__main__":
    main()
