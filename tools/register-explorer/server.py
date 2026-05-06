#!/usr/bin/env python3
"""Serve the register explorer with a capture-delete API."""
from __future__ import annotations

import json
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TOOL_ROOT = Path(__file__).parent
REPO_ROOT = TOOL_ROOT.parents[1]
CAPTURE_ROOT = REPO_ROOT / "docs" / "investigation" / "register-captures"
BUILD_SCRIPT = REPO_ROOT / "tools" / "scripts" / "build-register-explorer-data.py"
PORT = 8765


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(TOOL_ROOT), **kwargs)

    def do_POST(self):
        if self.path != "/api/delete-capture":
            self._json(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        capture_id = body.get("capture_id", "").strip()

        if not capture_id:
            self._json(400, {"error": "missing capture_id"})
            return

        target = CAPTURE_ROOT / f"{capture_id}.json"
        if not target.exists():
            target = self._find_legacy_backing_file(capture_id)
        if target is None or not target.exists():
            self._json(404, {"error": f"No backing file found for '{capture_id}'."})
            return

        target.unlink()
        result = subprocess.run(
            [sys.executable, str(BUILD_SCRIPT)],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        if result.returncode != 0:
            self._json(500, {"error": f"Capture deleted but rebuild failed: {result.stderr[:300]}"})
            return

        self._json(200, {"ok": True})

    def _find_legacy_backing_file(self, capture_id: str):
        """Look up the source_file for old JSONL-backed captures from the built data."""
        explorer_data = TOOL_ROOT / "data" / "register-explorer.json"
        if not explorer_data.exists():
            return None
        try:
            import json as _json
            captures = _json.loads(explorer_data.read_text()).get("captures", [])
            for capture in captures:
                if capture.get("capture_id") == capture_id:
                    source_file = capture.get("source_file")
                    if source_file:
                        return REPO_ROOT / "docs" / "investigation" / source_file
        except Exception:
            pass
        return None

    def _json(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)


if __name__ == "__main__":
    with ThreadingHTTPServer(("", PORT), Handler) as httpd:
        print(f"Register Explorer → http://localhost:{PORT}/", flush=True)
        httpd.serve_forever()
