#!/usr/bin/env python3
"""
Build normalized investigation datasets for the Phase 24 register explorer.

Sources:
- docs/investigation/register-captures/*.json  — canonical stateful captures
- docs/investigation/ddc-scan/*.jsonl           — brute-force DDC capability scans
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
INVESTIGATION_ROOT = REPO_ROOT / "docs" / "investigation"
OUTPUT_ROOT = REPO_ROOT / "tools" / "register-explorer" / "data"
CANONICAL_CAPTURE_ROOT = INVESTIGATION_ROOT / "register-captures"

FULL_HEX_RANGE = [f"0x{i:02X}" for i in range(256)]

BRUTE_FORCE_DDC_FILES = [
    "ddc-scan/ddc-scan-20260501-153903.jsonl",
    "ddc-scan/ddc-scan-20260501-161242.jsonl",
    "ddc-scan/ddc-scan-20260501-161655.jsonl",
]

ANNOTATIONS = {
    "0x58": {
        "noisy_registers": ["0x0B", "0x0C", "0x0D", "0x1F", "0x3C", "0x3D", "0x3E", "0xA0", "0xA3", "0xA5"],
        "notes": {
            "0x02": "Scaler sanity check; clean captures should read 0x79.",
            "0x48": "Display mode byte; interpretation still under investigation.",
            "0x4A": "Audio side selector; 0x00=left, 0x02=right.",
            "0xA1": "Signal presence; 0x00 is the reliable idle indicator.",
            "0xE1": "Menu1 OSD guard; 0xFA indicates the scan should be discarded.",
        },
    },
    "0x37_ddc": {
        "notes": {
            "0x60": "Primary source in PBP, main source in PIP.",
            "0xD6": "Power mode VCP.",
        },
    },
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def load_canonical_capture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def include_canonical_capture(capture: dict[str, Any]) -> bool:
    return bool(capture.get("flags", {}).get("include_in_explorer"))


def load_canonical_captures() -> tuple[list[dict[str, Any]], list[tuple[str, str]]]:
    captures: list[dict[str, Any]] = []
    decisions: list[tuple[str, str]] = []
    if not CANONICAL_CAPTURE_ROOT.exists():
        return captures, decisions
    for path in sorted(CANONICAL_CAPTURE_ROOT.glob("*.json")):
        capture = load_canonical_capture(path)
        relative_path = str(path.relative_to(INVESTIGATION_ROOT))
        if include_canonical_capture(capture):
            captures.append(capture)
            decisions.append((relative_path, "Included: canonical capture marked include_in_explorer=true."))
        else:
            decisions.append((relative_path, "Excluded: canonical capture marked include_in_explorer=false."))
    return captures, decisions


def normalize_bruteforce_ddc(path: Path) -> dict[str, Any]:
    items = load_jsonl(path)
    scan = {
        "scan_id": path.stem,
        "source_file": str(path.relative_to(INVESTIGATION_ROOT)),
        "captured_at": items[0].get("ts"),
        "monitor_bus": f"/dev/i2c-{items[0].get('bus')}" if items and items[0].get("bus") is not None else None,
        "attempted_registers": FULL_HEX_RANGE,
        "values": {reg: None for reg in FULL_HEX_RANGE},
        "details": {reg: {"status": "not_attempted"} for reg in FULL_HEX_RANGE},
        "capabilities": items[0].get("output"),
    }
    for item in items[1:]:
        reg = f"0x{int(item['code'], 16):02X}"
        status = item.get("status")
        value: int | str | None = None
        if status == "ok":
            if "current" in item and isinstance(item["current"], int):
                value = item["current"]
            elif "sl" in item and isinstance(item["sl"], str) and item["sl"].startswith("x"):
                try:
                    value = int(item["sl"][1:], 16)
                except ValueError:
                    value = None
            elif "raw" in item:
                value = item["raw"]
        scan["values"][reg] = value
        scan["details"][reg] = {
            "name": item.get("name"),
            "status": status,
            "attempt": item.get("attempt"),
            "type": item.get("type"),
            "value": value,
            "max": item.get("max"),
            "sl": item.get("sl"),
            "raw": item.get("raw"),
            "error": item.get("error"),
        }
    return scan


def build_inventory(
    ddc_paths: set[str],
    canonical_decisions: list[tuple[str, str]],
) -> list[dict[str, str]]:
    decisions: dict[str, str] = {path: "Included as brute-force DDC capability scan." for path in ddc_paths}
    decisions.update(dict(canonical_decisions))
    all_sources = {
        str(path.relative_to(INVESTIGATION_ROOT))
        for path in CANONICAL_CAPTURE_ROOT.glob("*.json")
    }
    for path in sorted(all_sources):
        if path not in decisions:
            decisions[path] = "Excluded: no explicit allowlist entry for this source."
    return [{"path": path, "decision": decisions[path]} for path in sorted(decisions)]


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    captures, canonical_decisions = load_canonical_captures()
    ddc_scans = [normalize_bruteforce_ddc(INVESTIGATION_ROOT / p) for p in BRUTE_FORCE_DDC_FILES]
    inventory = build_inventory(
        ddc_paths=set(BRUTE_FORCE_DDC_FILES),
        canonical_decisions=canonical_decisions,
    )

    register_explorer = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source_root": "docs/investigation",
        "notes": [
            "Null means the register or VCP code was attempted but did not produce a readable value.",
            "Unattempted registers are omitted from subset scans and listed in attempted_registers instead.",
            "Only captures with explicit high-confidence state metadata are included here.",
        ],
        "annotations": ANNOTATIONS,
        "captures": captures,
    }

    ddc_capabilities = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "notes": [
            "These scans are global capability probes, not state-tagged monitor captures.",
            "Values are normalized conservatively: scalar current/SL values are exposed when available, otherwise null.",
        ],
        "scans": ddc_scans,
    }

    source_inventory = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "notes": [
            "This inventory records which investigation sources were promoted into explorer data and which were intentionally excluded.",
        ],
        "files": inventory,
    }

    (OUTPUT_ROOT / "register-explorer.json").write_text(json.dumps(register_explorer, indent=2) + "\n")
    (OUTPUT_ROOT / "ddc-capabilities.json").write_text(json.dumps(ddc_capabilities, indent=2) + "\n")
    (OUTPUT_ROOT / "source-inventory.json").write_text(json.dumps(source_inventory, indent=2) + "\n")

    print(f"Wrote {OUTPUT_ROOT / 'register-explorer.json'}")
    print(f"Wrote {OUTPUT_ROOT / 'ddc-capabilities.json'}")
    print(f"Wrote {OUTPUT_ROOT / 'source-inventory.json'}")


if __name__ == "__main__":
    main()
