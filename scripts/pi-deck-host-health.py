#!/usr/bin/env python3
"""
Collect Python runtime and host metrics for the control deck (Raspberry Pi–aware).

Not part of the installable pi_deck package — run from the repo or copy to the Pi:
  python3 scripts/pi-deck-host-health.py          # default: paste this into Markdown execution records
  python3 scripts/pi-deck-host-health.py --json   # optional: machine-readable only

Exit code 0 always unless --strict-throttle (exit 1 if throttling flags set).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Repo layout: allow `import pi_deck` when run from a clone without installing (editable backend/src).
_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_SRC = _REPO_ROOT / "backend" / "src"
if _BACKEND_SRC.is_dir():
    sys.path.insert(0, str(_BACKEND_SRC))

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
from datetime import UTC, datetime
from typing import Any

# Raspberry Pi get_throttled bitmask (see official docs)
_THROTTLE_BITS = {
    0: "under_voltage_detected_now",
    1: "arm_frequency_capped_now",
    2: "currently_throttled",
    3: "soft_temp_limit_active_now",
    16: "under_voltage_occurred_since_boot",
    17: "arm_frequency_capped_occurred",
    18: "throttling_occurred",
    19: "soft_temp_limit_occurred",
}


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _vcgencmd(*args: str) -> str | None:
    exe = Path("/usr/bin/vcgencmd")
    if not exe.is_file():
        return None
    try:
        r = subprocess.run(
            [str(exe), *args],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if r.returncode != 0:
            return None
        return r.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return None


def _parse_throttled(line: str | None) -> dict[str, Any]:
    out: dict[str, Any] = {"raw": line, "hex": None, "flags": {}, "any_current": False}
    if not line or "=" not in line:
        return out
    m = re.search(r"throttled=(0x[0-9a-fA-F]+)", line)
    if not m:
        return out
    val = int(m.group(1), 16)
    out["hex"] = m.group(1)
    for bit, name in _THROTTLE_BITS.items():
        if val & (1 << bit):
            out["flags"][name] = True
            if bit <= 3:
                out["any_current"] = True
    return out


def _meminfo() -> dict[str, int]:
    data = _read(Path("/proc/meminfo"))
    out: dict[str, int] = {}
    for line in data.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].endswith(":"):
            key = parts[0][:-1]
            try:
                out[key] = int(parts[1])
            except ValueError:
                pass
    return out


def _cpu_model() -> str:
    text = _read(Path("/proc/cpuinfo"))
    for line in text.splitlines():
        if line.startswith("Model") or line.startswith("model name"):
            return line.split(":", 1)[-1].strip()
    return "unknown"


def _loadavg() -> tuple[float, float, float] | None:
    if hasattr(os, "getloadavg"):
        try:
            return os.getloadavg()
        except OSError:
            pass
    text = _read(Path("/proc/loadavg")).split()
    if len(text) < 3:
        return None
    try:
        return (float(text[0]), float(text[1]), float(text[2]))
    except ValueError:
        return None


def _thermal_zones() -> list[dict[str, str]]:
    zones = []
    base = Path("/sys/class/thermal")
    if not base.is_dir():
        return zones
    for z in sorted(base.glob("thermal_zone*")):
        t = _read(z / "temp").strip()
        typ = _read(z / "type").strip()
        if t.isdigit():
            zones.append({"zone": z.name, "type": typ or "?", "temp_c": f"{int(t) / 1000.0:.1f}"})
    return zones


def _disk(path: str = "/") -> dict[str, Any]:
    try:
        u = shutil.disk_usage(path)
        return {
            "path": path,
            "total_bytes": u.total,
            "used_bytes": u.used,
            "free_bytes": u.free,
            "used_percent": round(100.0 * u.used / u.total, 2) if u.total else None,
        }
    except OSError as e:
        return {"path": path, "error": str(e)}


def _python_block() -> dict[str, Any]:
    block: dict[str, Any] = {
        "version": sys.version.split()[0],
        "full_version": sys.version.replace("\n", " "),
        "executable": sys.executable,
        "prefix": sys.prefix,
        "platform": platform.platform(),
        "machine": platform.machine(),
    }
    try:
        import pi_deck  # noqa: PLC0415

        block["pi_deck_importable"] = True
        block["pi_deck_version"] = getattr(pi_deck, "__version__", "?")
    except ImportError:
        block["pi_deck_importable"] = False
        block["pi_deck_version"] = None
    return block


def _pi_metrics() -> dict[str, Any]:
    m: dict[str, Any] = {}
    temp = _vcgencmd("measure_temp")
    if temp:
        m["cpu_temp_c"] = temp
    volts: dict[str, str] = {}
    for component in ("core", "sdram_c", "sdram_i", "sdram_p"):
        v = _vcgencmd("measure_volts", component)
        if v:
            volts[component] = v
    if volts:
        m["voltages"] = volts
    th = _parse_throttled(_vcgencmd("get_throttled"))
    if th.get("raw"):
        m["throttle"] = th
    return m


def _systemd_unit(name: str) -> str | None:
    try:
        r = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return r.stdout.strip() if r.returncode == 0 else r.stdout.strip() or "unknown"
    except OSError:
        return None


def _curl_health(url: str, timeout: float = 2.0) -> dict[str, Any]:
    try:
        r = subprocess.run(
            ["curl", "-sf", "--connect-timeout", str(timeout), url],
            capture_output=True,
            text=True,
            timeout=timeout + 1,
            check=False,
        )
        return {
            "url": url,
            "ok": r.returncode == 0,
            "body": (r.stdout.strip()[:200] if r.stdout else ""),
        }
    except OSError:
        return {"url": url, "ok": False, "error": "curl not available"}


def collect() -> dict[str, Any]:
    mem = _meminfo()
    mem_avail = mem.get("MemAvailable")
    mem_total = mem.get("MemTotal")
    swap_free = mem.get("SwapFree")
    swap_total = mem.get("SwapTotal")
    report: dict[str, Any] = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "hostname": platform.node(),
        "python": _python_block(),
        "cpu": {
            "model": _cpu_model(),
            "count_logical": os.cpu_count(),
            "loadavg_1_5_15": _loadavg(),
        },
        "memory_kib": {
            "MemTotal": mem_total,
            "MemAvailable": mem_avail,
            "SwapTotal": swap_total,
            "SwapFree": swap_free,
        },
        "disk_root": _disk("/"),
        "thermal_zones": _thermal_zones(),
        "raspberry_pi": _pi_metrics(),
        "services": {
            "pi-deck": _systemd_unit("pi-deck.service"),
            "lightdm": _systemd_unit("lightdm.service"),
        },
        "pi_deck_http": _curl_health("http://127.0.0.1:8756/health"),
    }
    return report


def _fmt_gib(n: int | None) -> str:
    if n is None:
        return "?"
    return f"{n / (1024**3):.2f} GiB"


def _format_human(data: dict[str, Any]) -> str:
    """Plain-text report suitable for pasting into markdown execution records."""
    lines: list[str] = []
    lines.append(f"pi-deck host health  |  {data.get('timestamp_utc', '')}")
    lines.append(f"hostname: {data.get('hostname', '?')}")
    py = data.get("python") or {}
    lines.append("")
    lines.append("[python]")
    lines.append(f"  executable: {py.get('executable')}")
    lines.append(f"  version:    {py.get('version')}")
    lines.append(f"  platform:   {py.get('platform')}")
    lines.append(
        f"  pi_deck:    importable={py.get('pi_deck_importable')}  "
        f"package_version={py.get('pi_deck_version')}",
    )
    cpu = data.get("cpu") or {}
    lines.append("")
    lines.append("[cpu]")
    lines.append(f"  model: {cpu.get('model')}")
    lines.append(f"  logical cpus: {cpu.get('count_logical')}")
    la = cpu.get("loadavg_1_5_15")
    if isinstance(la, tuple) and len(la) == 3:
        lines.append(f"  load average (1 / 5 / 15 min): {la[0]:.2f}  {la[1]:.2f}  {la[2]:.2f}")
    else:
        lines.append(f"  load average: {la!s}")
    mem = data.get("memory_kib") or {}
    mt, ma = mem.get("MemTotal"), mem.get("MemAvailable")
    st, sf = mem.get("SwapTotal"), mem.get("SwapFree")
    lines.append("")
    lines.append("[memory]")
    if mt is not None:
        lines.append(
            f"  RAM:  total {_fmt_gib(mt * 1024)}  available {_fmt_gib(ma * 1024) if ma else '?'}  (MemTotal/MemAvailable KiB: {mt} / {ma})",
        )
    else:
        lines.append("  RAM:  (not available on this OS)")
    if st is not None:
        lines.append(
            f"  swap: total {_fmt_gib(st * 1024)}  free {_fmt_gib(sf * 1024) if sf is not None else '?'}  (KiB: {st} / {sf})",
        )
    disk = data.get("disk_root") or {}
    lines.append("")
    lines.append("[disk]  mount /")
    if disk.get("error"):
        lines.append(f"  error: {disk.get('error')}")
    else:
        total = disk.get("total_bytes")
        used = disk.get("used_bytes")
        free = disk.get("free_bytes")
        pct = disk.get("used_percent")
        lines.append(
            f"  size {_fmt_gib(total)}  used {_fmt_gib(used)}  avail {_fmt_gib(free)}  ({pct}% used)",
        )
    tz = data.get("thermal_zones") or []
    lines.append("")
    lines.append("[thermal]  sysfs zones")
    if not tz:
        lines.append("  (none — e.g. not Linux or no sensors)")
    for z in tz:
        lines.append(f"  {z.get('zone')}  {z.get('type')}  {z.get('temp_c')} °C")
    rpi = data.get("raspberry_pi") or {}
    lines.append("")
    lines.append("[raspberry_pi]  vcgencmd (SoC voltage / throttling)")
    if not rpi:
        lines.append("  (not available — not a Pi or vcgencmd missing)")
    else:
        if rpi.get("cpu_temp_c"):
            lines.append(f"  temperature: {rpi['cpu_temp_c']}")
        for comp, val in (rpi.get("voltages") or {}).items():
            lines.append(f"  voltage {comp}: {val}")
        th = rpi.get("throttle") or {}
        if th.get("raw"):
            lines.append(f"  get_throttled: {th.get('raw')}")
            flags = th.get("flags") or {}
            if flags:
                lines.append(f"  flags set: {', '.join(sorted(flags))}")
            else:
                lines.append("  flags set: (none)")
    svc = data.get("services") or {}
    lines.append("")
    lines.append("[systemd]")
    lines.append(f"  pi-deck.service: {svc.get('pi-deck')}")
    lines.append(f"  lightdm.service: {svc.get('lightdm')}")
    http = data.get("pi_deck_http") or {}
    lines.append("")
    lines.append("[pi-deck HTTP]")
    lines.append(f"  GET {http.get('url')}")
    lines.append(f"  ok: {http.get('ok')}  body: {http.get('body')!r}")
    if http.get("error"):
        lines.append(f"  error: {http.get('error')}")
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description="Host health snapshot for pi-deck / Raspberry Pi")
    p.add_argument("--json", action="store_true", help="print JSON only")
    p.add_argument(
        "--strict-throttle",
        action="store_true",
        help="exit 1 if get_throttled reports current under-voltage or throttling",
    )
    args = p.parse_args()
    data = collect()
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(_format_human(data), end="")

    if args.strict_throttle:
        rpi = data.get("raspberry_pi") or {}
        th = rpi.get("throttle") or {}
        flags = th.get("flags") or {}
        bad = any(
            k in flags
            for k in (
                "under_voltage_detected_now",
                "currently_throttled",
                "arm_frequency_capped_now",
            )
        )
        if bad:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
