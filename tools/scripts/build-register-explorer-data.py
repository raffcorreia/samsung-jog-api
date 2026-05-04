#!/usr/bin/env python3
"""
Build normalized investigation datasets for the Phase 24 register explorer.

This script is intentionally conservative:
- it only includes captures whose state metadata is explicit and trusted
- it preserves attempted-but-unreadable values as null
- it keeps unattempted registers absent and records the attempted scope separately
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
INVESTIGATION_ROOT = REPO_ROOT / "docs" / "investigation"
OUTPUT_ROOT = REPO_ROOT / "tools" / "register-explorer" / "data"

FULL_HEX_RANGE = [f"0x{i:02X}" for i in range(256)]
STATEFUL_DDC_CODES = ["0x10", "0x12", "0x60", "0x62", "0xD6", "0xDC"]


@dataclass(frozen=True)
class CaptureSpec:
    relative_path: str
    capture_id: str
    source_format: str
    state_label: str
    power_state: str
    signal_state: str
    layout_mode: str
    primary_input: str | None
    secondary_input: str | None
    audio_side: str | None
    pip_main_input: str | None
    pip_window_input: str | None
    pip_size: int | None
    pip_position: str | None
    notes: list[str]


INCLUDED_CAPTURE_SPECS = [
    CaptureSpec(
        relative_path="i2c-scan/i2c-0x58-on-idle-20260501-212914.jsonl",
        capture_id="idle-post-reboot-0x58-only",
        source_format="simple_0x58_only",
        state_label="Idle / no active source / post-reboot",
        power_state="on",
        signal_state="idle",
        layout_mode="idle",
        primary_input=None,
        secondary_input=None,
        audio_side=None,
        pip_main_input=None,
        pip_window_input=None,
        pip_size=None,
        pip_position=None,
        notes=[
            "Explicitly indexed in the investigation README as post-reboot idle.",
            "Only device 0x58 was captured in this file.",
        ],
    ),
    CaptureSpec(
        relative_path="i2c-scan/pip-size1-tb-small-dp-main/i2c-scan-20260501-231923.jsonl",
        capture_id="pip-size1-tb-small-dp-main",
        source_format="stateful_capture",
        state_label="PIP main: DP / window: TB / size 1 / top-left",
        power_state="on",
        signal_state="active",
        layout_mode="pip",
        primary_input="dp",
        secondary_input="tb",
        audio_side="right",
        pip_main_input="dp",
        pip_window_input="tb",
        pip_size=1,
        pip_position="top-left",
        notes=["Clean PIP capture per Phase 24 execution record."],
    ),
    CaptureSpec(
        relative_path="i2c-scan/pip-size2-tb-small-dp-main/i2c-scan-20260501-232202.jsonl",
        capture_id="pip-size2-tb-small-dp-main",
        source_format="stateful_capture",
        state_label="PIP main: DP / window: TB / size 2 / top-left",
        power_state="on",
        signal_state="active",
        layout_mode="pip",
        primary_input="dp",
        secondary_input="tb",
        audio_side="right",
        pip_main_input="dp",
        pip_window_input="tb",
        pip_size=2,
        pip_position="top-left",
        notes=["Clean PIP capture per Phase 24 execution record."],
    ),
    CaptureSpec(
        relative_path="i2c-scan/pip-size2-tb-small-dp-main/i2c-scan-20260501-232638.jsonl",
        capture_id="pip-size2-tb-small-dp-main-repeat",
        source_format="stateful_capture",
        state_label="PIP main: DP / window: TB / size 2 / top-left / repeat",
        power_state="on",
        signal_state="active",
        layout_mode="pip",
        primary_input="dp",
        secondary_input="tb",
        audio_side="right",
        pip_main_input="dp",
        pip_window_input="tb",
        pip_size=2,
        pip_position="top-left",
        notes=["Second clean capture of the same visible state."],
    ),
    CaptureSpec(
        relative_path="i2c-scan/pip-size3-tb-small-dp-main/i2c-scan-20260501-232836.jsonl",
        capture_id="pip-size3-tb-small-dp-main",
        source_format="stateful_capture",
        state_label="PIP main: DP / window: TB / size 3 / top-left",
        power_state="on",
        signal_state="active",
        layout_mode="pip",
        primary_input="dp",
        secondary_input="tb",
        audio_side="right",
        pip_main_input="dp",
        pip_window_input="tb",
        pip_size=3,
        pip_position="top-left",
        notes=["Clean PIP capture per Phase 24 execution record."],
    ),
    CaptureSpec(
        relative_path="i2c-scan/pip-size1-hdmi-small-dp-main/i2c-scan-20260502-010333.jsonl",
        capture_id="pip-size1-hdmi-small-dp-main",
        source_format="stateful_capture",
        state_label="PIP main: DP / window: HDMI / size 1 / top-left",
        power_state="on",
        signal_state="active",
        layout_mode="pip",
        primary_input="dp",
        secondary_input="hdmi",
        audio_side="right",
        pip_main_input="dp",
        pip_window_input="hdmi",
        pip_size=1,
        pip_position="top-left",
        notes=["Clean recapture after the original contaminated version was rejected."],
    ),
    CaptureSpec(
        relative_path="i2c-scan/pip-size2-hdmi-small-dp-main/i2c-scan-20260501-233908.jsonl",
        capture_id="pip-size2-hdmi-small-dp-main",
        source_format="stateful_capture",
        state_label="PIP main: DP / window: HDMI / size 2 / top-left",
        power_state="on",
        signal_state="active",
        layout_mode="pip",
        primary_input="dp",
        secondary_input="hdmi",
        audio_side="right",
        pip_main_input="dp",
        pip_window_input="hdmi",
        pip_size=2,
        pip_position="top-left",
        notes=["Clean PIP capture per Phase 24 execution record."],
    ),
    CaptureSpec(
        relative_path="i2c-scan/pip-size3-hdmi-small-dp-main/i2c-scan-20260501-233557.jsonl",
        capture_id="pip-size3-hdmi-small-dp-main",
        source_format="stateful_capture",
        state_label="PIP main: DP / window: HDMI / size 3 / top-left",
        power_state="on",
        signal_state="active",
        layout_mode="pip",
        primary_input="dp",
        secondary_input="hdmi",
        audio_side="right",
        pip_main_input="dp",
        pip_window_input="hdmi",
        pip_size=3,
        pip_position="top-left",
        notes=["Clean PIP capture per Phase 24 execution record."],
    ),
    CaptureSpec(
        relative_path="i2c-scan/pip-size1-hdmi-small-tb-main/i2c-scan-20260501-234516.jsonl",
        capture_id="pip-size1-hdmi-small-tb-main",
        source_format="stateful_capture",
        state_label="PIP main: TB / window: HDMI / size 1 / top-left",
        power_state="on",
        signal_state="active",
        layout_mode="pip",
        primary_input="tb",
        secondary_input="hdmi",
        audio_side="right",
        pip_main_input="tb",
        pip_window_input="hdmi",
        pip_size=1,
        pip_position="top-left",
        notes=["Clean PIP capture per Phase 24 execution record."],
    ),
    CaptureSpec(
        relative_path="i2c-scan/pip-size1-hdmi-small-tb-main-topright/i2c-scan-20260502-004753.jsonl",
        capture_id="pip-size1-hdmi-small-tb-main-topright",
        source_format="stateful_capture",
        state_label="PIP main: TB / window: HDMI / size 1 / top-right",
        power_state="on",
        signal_state="active",
        layout_mode="pip",
        primary_input="tb",
        secondary_input="hdmi",
        audio_side="right",
        pip_main_input="tb",
        pip_window_input="hdmi",
        pip_size=1,
        pip_position="top-right",
        notes=["Clean PIP position-variation capture."],
    ),
    CaptureSpec(
        relative_path="i2c-scan/pip-size1-hdmi-small-tb-main-bottomleft/i2c-scan-20260502-005339.jsonl",
        capture_id="pip-size1-hdmi-small-tb-main-bottomleft",
        source_format="stateful_capture",
        state_label="PIP main: TB / window: HDMI / size 1 / bottom-left",
        power_state="on",
        signal_state="active",
        layout_mode="pip",
        primary_input="tb",
        secondary_input="hdmi",
        audio_side="right",
        pip_main_input="tb",
        pip_window_input="hdmi",
        pip_size=1,
        pip_position="bottom-left",
        notes=["Clean PIP position-variation capture."],
    ),
    CaptureSpec(
        relative_path="i2c-scan/pip-size1-hdmi-small-tb-main-bottomright/i2c-scan-20260502-005519.jsonl",
        capture_id="pip-size1-hdmi-small-tb-main-bottomright",
        source_format="stateful_capture",
        state_label="PIP main: TB / window: HDMI / size 1 / bottom-right",
        power_state="on",
        signal_state="active",
        layout_mode="pip",
        primary_input="tb",
        secondary_input="hdmi",
        audio_side="right",
        pip_main_input="tb",
        pip_window_input="hdmi",
        pip_size=1,
        pip_position="bottom-right",
        notes=["Clean PIP position-variation capture."],
    ),
    CaptureSpec(
        relative_path="i2c-scan/pip-size3-hdmi-small-tb-main/i2c-scan-20260501-233414.jsonl",
        capture_id="pip-size3-hdmi-small-tb-main",
        source_format="stateful_capture",
        state_label="PIP main: TB / window: HDMI / size 3 / top-left",
        power_state="on",
        signal_state="active",
        layout_mode="pip",
        primary_input="tb",
        secondary_input="hdmi",
        audio_side="right",
        pip_main_input="tb",
        pip_window_input="hdmi",
        pip_size=3,
        pip_position="top-left",
        notes=["Clean PIP capture per Phase 24 execution record."],
    ),
    CaptureSpec(
        relative_path="i2c-scan/pip-size3-tb-small-hdmi-main/i2c-scan-20260501-233134.jsonl",
        capture_id="pip-size3-tb-small-hdmi-main",
        source_format="stateful_capture",
        state_label="PIP main: HDMI / window: TB / size 3 / top-left",
        power_state="on",
        signal_state="active",
        layout_mode="pip",
        primary_input="hdmi",
        secondary_input="tb",
        audio_side="right",
        pip_main_input="hdmi",
        pip_window_input="tb",
        pip_size=3,
        pip_position="top-left",
        notes=["Clean PIP capture per Phase 24 execution record."],
    ),
]


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


EXCLUSION_RULES = [
    ("i2c-scan/i2c-0x58-tb-active-20260501-214114.jsonl", "Excluded: early single-source capture; contamination risk documented."),
    ("i2c-scan/i2c-all-tb-active-20260501-215231.jsonl", "Excluded: early single-source capture; contamination risk documented."),
    ("i2c-scan/i2c-all-dp-active-20260501-220136.jsonl", "Excluded: early single-source capture; contamination risk documented."),
    ("i2c-scan/i2c-all-hdmi-active-20260501-222201.jsonl", "Excluded: early single-source capture; HDMI source was Pi at incompatible resolution."),
    ("i2c-scan/i2c-all-pbp-hdmi-tb-20260501-223036.jsonl", "Excluded: PBP capture; PBP E0-E3 contamination documented."),
    ("i2c-scan/i2c-all-pbp-tb-dp-20260501-223357.jsonl", "Excluded: PBP capture; PBP E0-E3 contamination documented."),
    ("i2c-scan/i2c-all-pbp-tb-hdmi-20260501-222706.jsonl", "Excluded: PBP capture; PBP E0-E3 contamination documented."),
    ("i2c-scan/i2c-scan-20260501-210013.jsonl", "Excluded: filename/index mismatch and old raw 0x37 reads only; idle is represented by the explicit post-reboot idle capture instead."),
    ("i2c-scan/i2c-scan-20260501-224313.jsonl", "Excluded: source state is not explicit in the investigation index."),
]


def parse_hex_value(value: str) -> int:
    return int(value, 16)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def infer_timestamp_from_path(path: Path) -> str | None:
    stem = path.stem
    for token in stem.split("-"):
        if len(token) == 8 and token.isdigit():
            return None
    text = path.stem
    for i in range(len(text) - 14):
        chunk = text[i : i + 15]
        if len(chunk) == 15 and chunk[8] == "-" and chunk[:8].isdigit() and chunk[9:].isdigit():
            return f"{chunk[:4]}-{chunk[4:6]}-{chunk[6:8]}T{chunk[9:11]}:{chunk[11:13]}:{chunk[13:15]}"
    return None


def empty_full_register_map() -> dict[str, int | None]:
    return {reg: None for reg in FULL_HEX_RANGE}


def normalize_stateful_capture(spec: CaptureSpec) -> dict[str, Any]:
    path = INVESTIGATION_ROOT / spec.relative_path
    items = load_jsonl(path)
    ts = items[0].get("ts") if items and "ts" in items[0] else infer_timestamp_from_path(path)

    devices: dict[str, Any] = {
        "0x54": {
            "kind": "i2c_registers",
            "scan_scope": "full_256",
            "attempted_registers": FULL_HEX_RANGE,
            "values": empty_full_register_map(),
        },
        "0x58": {
            "kind": "i2c_registers",
            "scan_scope": "full_256",
            "attempted_registers": FULL_HEX_RANGE,
            "values": empty_full_register_map(),
        },
        "0x37_ddc": {
            "kind": "ddc_vcp",
            "scan_scope": "subset",
            "attempted_registers": STATEFUL_DDC_CODES,
            "values": {},
            "details": {},
        },
    }

    for item in items:
        device = item.get("device")
        status = item.get("status", "ok")

        if device in {"0x54", "0x58"}:
            reg = f"0x{int(item['reg'], 16):02X}"
            devices[device]["values"][reg] = parse_hex_value(item["value"]) if status == "ok" and "value" in item else None
        elif device == "0x37_ddc":
            reg = f"0x{int(item['vcp'], 16):02X}"
            value = parse_hex_value(item["current"]) if status == "ok" and "current" in item else None
            devices[device]["values"][reg] = value
            devices[device]["details"][reg] = {
                "name": item.get("name"),
                "status": status,
                "value": value,
                "max": parse_hex_value(item["max"]) if status == "ok" and "max" in item else None,
                "type": item.get("type"),
                "error": item.get("error"),
            }

    return {
        "capture_id": spec.capture_id,
        "source_file": spec.relative_path,
        "source_format": spec.source_format,
        "captured_at": ts,
        "monitor_bus": "/dev/i2c-13",
        "state_label": spec.state_label,
        "power_state": spec.power_state,
        "signal_state": spec.signal_state,
        "layout_mode": spec.layout_mode,
        "primary_input": spec.primary_input,
        "secondary_input": spec.secondary_input,
        "audio_side": spec.audio_side,
        "pip": {
            "main_input": spec.pip_main_input,
            "window_input": spec.pip_window_input,
            "size": spec.pip_size,
            "position": spec.pip_position,
        },
        "flags": {
            "contaminated": False,
            "metadata_certainty": "high",
        },
        "notes": spec.notes,
        "devices": devices,
    }


def normalize_simple_0x58_capture(spec: CaptureSpec) -> dict[str, Any]:
    path = INVESTIGATION_ROOT / spec.relative_path
    items = load_jsonl(path)
    values = empty_full_register_map()
    for item in items:
        reg = f"0x{int(item['reg'], 16):02X}"
        values[reg] = parse_hex_value(item["value"])

    return {
        "capture_id": spec.capture_id,
        "source_file": spec.relative_path,
        "source_format": spec.source_format,
        "captured_at": infer_timestamp_from_path(path),
        "monitor_bus": "/dev/i2c-13",
        "state_label": spec.state_label,
        "power_state": spec.power_state,
        "signal_state": spec.signal_state,
        "layout_mode": spec.layout_mode,
        "primary_input": spec.primary_input,
        "secondary_input": spec.secondary_input,
        "audio_side": spec.audio_side,
        "pip": {
            "main_input": spec.pip_main_input,
            "window_input": spec.pip_window_input,
            "size": spec.pip_size,
            "position": spec.pip_position,
        },
        "flags": {
            "contaminated": False,
            "metadata_certainty": "high",
        },
        "notes": spec.notes,
        "devices": {
            "0x58": {
                "kind": "i2c_registers",
                "scan_scope": "full_256",
                "attempted_registers": FULL_HEX_RANGE,
                "values": values,
            }
        },
    }


def normalize_capture(spec: CaptureSpec) -> dict[str, Any]:
    if spec.source_format == "stateful_capture":
        return normalize_stateful_capture(spec)
    if spec.source_format == "simple_0x58_only":
        return normalize_simple_0x58_capture(spec)
    raise ValueError(f"Unsupported source format: {spec.source_format}")


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


def build_inventory(included_capture_paths: set[str], ddc_paths: set[str]) -> list[dict[str, str]]:
    decisions: dict[str, str] = {path: "Included in stateful explorer dataset." for path in included_capture_paths}
    decisions.update({path: "Included as brute-force DDC capability scan." for path in ddc_paths})
    decisions.update(dict(EXCLUSION_RULES))

    all_jsonl = {
        str(path.relative_to(INVESTIGATION_ROOT))
        for path in INVESTIGATION_ROOT.glob("**/*.jsonl")
    }
    for path in sorted(all_jsonl):
        if path not in decisions:
            decisions[path] = "Excluded: no explicit allowlist entry for this source."

    return [{"path": path, "decision": decisions[path]} for path in sorted(decisions)]


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    captures = [normalize_capture(spec) for spec in INCLUDED_CAPTURE_SPECS]
    ddc_scans = [normalize_bruteforce_ddc(INVESTIGATION_ROOT / relative_path) for relative_path in BRUTE_FORCE_DDC_FILES]
    inventory = build_inventory(
        included_capture_paths={spec.relative_path for spec in INCLUDED_CAPTURE_SPECS},
        ddc_paths=set(BRUTE_FORCE_DDC_FILES),
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
