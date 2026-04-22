#!/usr/bin/env python3
"""
PreToolUse hook: blocks Bash commands that delete or modify files outside the project directory.
Reads JSON from stdin (Claude Code hook format), outputs JSON to stdout.
"""
import json
import os
import re
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

data = json.load(sys.stdin)
cmd = data.get("tool_input", {}).get("command", "")

# Match destructive commands followed by a path argument
matches = re.findall(
    r"(?:rm|rmdir|unlink|mv|chmod|chown)\s+(?:-\S+\s+)*([^\s|&;<>]+)", cmd
)

for path in matches:
    expanded = os.path.expanduser(path)
    if expanded.startswith("/") and not os.path.abspath(expanded).startswith(PROJECT_DIR):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": (
                    f'"{path}" is outside the project directory ({PROJECT_DIR}). '
                    "Proceed only if intentional."
                )
            }
        }))
        sys.exit(0)

print(json.dumps({"continue": True}))
