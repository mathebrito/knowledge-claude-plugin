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
            [sys.executable, bundled_script],
            input=message,
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout.strip()
    except Exception:
        return

    if not output:
        return

    # Try to parse structured output from the bundled script
    try:
        classification = json.loads(output)
        category = classification.get("category", "NOTE")
        route = classification.get("route", "")
    except (json.JSONDecodeError, ValueError):
        # Plain-text output: treat the whole line as the category
        category = output.split(None, 1)[0] if output else "NOTE"
        route = output

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
