#!/usr/bin/env bash
# Knowledge Engine — SessionStart hook
# Checks infrastructure status and gathers vault context.

set -euo pipefail

# --- helpers ---
json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/}"
  s="${s//$'\t'/\\t}"
  printf '%s' "$s"
}

# --- 1+2. Knowledge host (tejo/mini2025) + Knowledge API ---
# Probe the service itself first — that is what sessions actually need — then
# diagnose transport only on failure. MagicDNS name survives IP churn; the raw
# tailnet IP is the fallback when MagicDNS is unavailable.
# (2026-08-02: replaced hardcoded 100.97.71.49 — a stale IP from tejo's old
# duplicate device registration — which made every banner report UNREACHABLE.)
KNOWLEDGE_HOST="matbookpro16.beago-quail.ts.net"
KNOWLEDGE_IP="100.69.171.35"

health_json=$(curl -sf "http://${KNOWLEDGE_HOST}:6380/health" --max-time 5 2>/dev/null \
  || curl -sf "http://${KNOWLEDGE_IP}:6380/health" --max-time 5 2>/dev/null \
  || true)

if [ -n "$health_json" ]; then
  tailscale_status="CONNECTED"
  qdrant=$(echo "$health_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('qdrant','unknown'))" 2>/dev/null || echo "unknown")
  models=$(echo "$health_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('models_loaded','unknown'))" 2>/dev/null || echo "unknown")
  api_status="UP (qdrant: ${qdrant}, models_loaded: ${models})"
elif ping -c1 -W2 "$KNOWLEDGE_IP" >/dev/null 2>&1 || ping -c1 -W2 "$KNOWLEDGE_HOST" >/dev/null 2>&1; then
  tailscale_status="CONNECTED"
  api_status="DOWN (host reachable, service not answering on :6380)"
else
  tailscale_status="UNREACHABLE — Remote RAG/ingest unavailable. Local vault search via qmd still works."
  api_status="SKIPPED (Tailscale unreachable)"
fi

# --- 3. qmd ---
qmd_bin=""
if command -v qmd >/dev/null 2>&1; then
  qmd_bin="qmd"
elif [ -x "$HOME/.npm-global/bin/qmd" ]; then
  qmd_bin="$HOME/.npm-global/bin/qmd"
fi

if [ -z "$qmd_bin" ]; then
  qmd_status="NOT INSTALLED — Run /setup"
else
  # Capture stderr too: a crashing binary (e.g. better-sqlite3 built against an
  # older Node ABI after a Homebrew Node upgrade) must report BROKEN, not be
  # silently mistaken for a missing collection. (2026-08-02: was 2>/dev/null.)
  sb_check=$($qmd_bin ls second-brain 2>&1) && sb_rc=0 || sb_rc=$?
  if [ $sb_rc -ne 0 ] && printf '%s' "$sb_check" | grep -qiE 'Error|Cannot find|dlopen|NODE_MODULE_VERSION'; then
    qmd_status="BROKEN — binary fails to run (likely Node ABI mismatch; try: npm -g rebuild better-sqlite3, or reinstall @tobilu/qmd)"
  elif [ $sb_rc -eq 0 ] && [ -n "$sb_check" ]; then
    qmd_status="OK (second-brain collection found)"
  else
    qmd_status="INSTALLED (second-brain collection not found)"
  fi
fi

# --- 4. Vault context ---
vault_dir="$HOME/second-brain"

# North Star
north_star_file="$vault_dir/A.DIVA/brain/North Star.md"
if [ -f "$north_star_file" ]; then
  north_star=$(head -20 "$north_star_file" 2>/dev/null || true)
else
  north_star="(not found)"
fi

# Inbox count
inbox_dir="$vault_dir/00-inbox"
if [ -d "$inbox_dir" ]; then
  inbox_count=$(find "$inbox_dir" -maxdepth 1 -type f | wc -l | tr -d ' ')
else
  inbox_count="0 (dir missing)"
fi

# Recent daily notes
daily_dir="$vault_dir/D.DAILY"
if [ -d "$daily_dir" ]; then
  recent_daily=$(ls -t "$daily_dir" 2>/dev/null | head -3 | tr '\n' ', ' | sed 's/,$//')
else
  recent_daily="(dir missing)"
fi

# Wiki count
wiki_dir="$vault_dir/A.DIVA/wiki"
if [ -d "$wiki_dir" ]; then
  wiki_count=$(find "$wiki_dir" -type f -name '*.md' | wc -l | tr -d ' ')
else
  wiki_count="0 (dir missing)"
fi

# --- 5. Build output ---
context="=== Knowledge Engine Status ===
Tailscale: ${tailscale_status}
Knowledge API: ${api_status}
qmd: ${qmd_status}

=== Vault Context ===
North Star (first 20 lines):
${north_star}

Inbox: ${inbox_count} items
Recent daily notes: ${recent_daily}
Wiki: ${wiki_count} notes"

escaped=$(json_escape "$context")

cat <<ENDJSON
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "${escaped}"
  }
}
ENDJSON
