#!/usr/bin/env python3
"""Knowledge Engine — UserPromptSubmit hook.

Reads the user's message from stdin JSON, runs the bundled
classify-message.py, and emits vault-routing context if the
classification is something other than the default NOTE type.
"""

import json
import os
import subprocess
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    # Extract user message text
    message = data.get("message", "")
    if not message:
        # Fallback: some hook formats nest under prompt / content
        message = data.get("prompt", data.get("content", ""))
    if not message:
        return

    plugin_root = os.environ.get(
        "CLAUDE_PLUGIN_ROOT",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
    )
    bundled_script = os.path.join(plugin_root, "scripts", "classify-message.py")

    if not os.path.isfile(bundled_script):
        return

    try:
        result = subprocess.run(
            [sys.executable, bundled_script, message],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout.strip()
    except Exception:
        return

    if not output:
        return

    # Bundled script outputs two lines:
    #   CATEGORY
    #   [vault-route: path/to/destination]
    lines = output.splitlines()
    category = lines[0].strip() if lines else "NOTE"
    route = ""
    if len(lines) > 1:
        # Extract path from "[vault-route: X]"
        route_line = lines[1].strip()
        if route_line.startswith("[vault-route:"):
            route = route_line.split(":", 1)[1].rstrip("]").strip()
        else:
            route = route_line

    if category == "NOTE":
        return

    if route:
        hint = f"[vault-route: {route}] — classified as {category}"
    else:
        hint = f"classified as {category}"

    payload = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": hint,
        }
    }
    json.dump(payload, sys.stdout)


if __name__ == "__main__":
    main()
