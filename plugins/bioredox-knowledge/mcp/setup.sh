#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
command -v uv >/dev/null 2>&1 || {
  echo "uv is required: https://docs.astral.sh/uv/" >&2
  exit 1
}

uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
printf 'BioRedox Knowledge MCP dependencies are installed.\n'
