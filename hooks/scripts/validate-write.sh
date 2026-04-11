#!/usr/bin/env bash
# Knowledge Engine — PostToolUse hook for Write|Edit
# Validates vault .md writes via the bundled validate-write.sh script.

set -euo pipefail

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
VAULT_DIR="$HOME/second-brain"

# Read stdin (tool call JSON)
input=$(cat)

# Extract file_path from tool_input using python3
file_path=$(echo "$input" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    # PostToolUse provides tool_input with the tool's parameters
    ti = data.get('tool_input', {})
    print(ti.get('file_path', ''))
except Exception:
    print('')
" 2>/dev/null || true)

# Exit silently if no file path extracted
[ -z "$file_path" ] && exit 0

# Check if this is a .md file under ~/second-brain/
case "$file_path" in
  "${VAULT_DIR}"/*.md|"${VAULT_DIR}"/**/*.md)
    # Run the bundled validation script
    bundled_script="${PLUGIN_ROOT}/scripts/validate-write.sh"
    if [ ! -x "$bundled_script" ]; then
      exit 0
    fi

    result=$("$bundled_script" "$file_path" 2>&1 || true)

    if echo "$result" | grep -q "FAIL"; then
      # Escape for JSON
      escaped=$(python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))" <<< "$result")
      cat <<ENDJSON
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": ${escaped}
  }
}
ENDJSON
    fi
    ;;
  *)
    # Not a vault file — no output
    ;;
esac
