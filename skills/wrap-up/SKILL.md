---
name: wrap-up
description: >
  End-of-session housekeeping — re-index vault, commit changes, update
  log, optional quick lint.
version: 1.0.0
author: knowledge-engine
---

# Wrap-Up — End-of-Session Housekeeping

Clean up after a work session: re-index search, commit changes,
log the session, and optionally run a quick lint pass.

## Triggers

- `/wrap-up` — run end-of-session housekeeping

## Workflow

### Step 1: Re-Index qmd

```bash
qmd update --collection second-brain
```

Incrementally re-indexes any new or modified files.

### Step 2: Embed New Files (Optional)

If new files were added during the session:

```bash
qmd embed --collection second-brain
```

This generates vector embeddings for new content. Skip if only existing
files were edited (update handles that).

### Step 3: Commit Vault

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/vault-commit.sh
```

Commits all vault changes with an auto-generated message.

### Step 4: Update Session Log

Append a session summary line to `~/second-brain/A.DIVA/ops/log.md`:

```
- HH:MM WRAP-UP | notas criadas: N | notas editadas: N
```

Replace `N` with actual counts from the session. Use `git diff --stat`
to determine what changed since the last commit before this session.

### Step 5: Quick Lint (Optional)

Run a quick lint check on wiki notes modified in the last hour:

```bash
find ~/second-brain/A.DIVA/wiki/ -name "*.md" -mmin -60
```

For each recently modified file, verify:
- Has YAML frontmatter with `tags` and `date`
- Contains at least one `[[wikilink]]` (if longer than 300 chars)
- No broken wikilinks to non-existent notes

Report any issues found. For a full lint, suggest running `/lint`.

### Step 6: Report Summary

Present a concise summary:

```
WRAP-UP COMPLETE

Re-indexed: qmd update OK
Committed: <commit hash> (<N files changed>)
Log updated: A.DIVA/ops/log.md
Quick lint: N files checked, N issues found

Session stats:
  - Notes created: N
  - Notes edited: N
  - Wiki pages touched: N
```
