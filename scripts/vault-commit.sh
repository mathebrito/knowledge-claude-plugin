#!/usr/bin/env bash
set -euo pipefail

# vault-commit.sh — Auto-commit of Second Brain vault.
# Usage: bash vault-commit.sh [vault_path] [commit_message]

VAULT="${1:-${VAULT_ROOT:-$HOME/second-brain}}"
MSG="${2:-chore: vault auto-commit $(date -u +%Y-%m-%dT%H:%M:%SZ)}"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

if [ ! -d "$VAULT/.git" ]; then
  log "ERROR: Vault not found or not a git repo at $VAULT"
  exit 1
fi

cd "$VAULT"

log "Vault commit: checking for changes..."

# Pull remote changes first to avoid divergence
if git remote get-url origin &>/dev/null; then
  git pull --rebase origin main 2>/dev/null && log "Pulled from origin." || log "WARNING: Pull failed (non-fatal), continuing."
fi

git add -A

if git diff --cached --quiet; then
  log "No vault changes to commit."
  exit 0
fi

git commit -m "$MSG"

if git remote get-url origin &>/dev/null; then
  git push origin HEAD 2>/dev/null && log "Vault pushed to origin." || log "WARNING: Push failed (non-fatal)."
fi

log "Vault auto-committed."
