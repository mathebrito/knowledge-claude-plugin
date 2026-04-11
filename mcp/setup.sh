#!/usr/bin/env bash
# Bootstrap the MCP server venv
set -euo pipefail

cd "$(dirname "$0")"

echo "Creating Python venv for knowledge-engine MCP server..."
python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt

echo "Done. MCP server ready at: $(pwd)/.venv/bin/python3 server.py"
