# Knowledge Engine Plugin

## Vault

Path: `~/second-brain/` (PARA+ABCD structure). Override with `VAULT_ROOT` env var if different (e.g., `~/second-brain/matheus/` on the Mac Mini).

### Zone Permissions

| Zone | Path | Who writes | Rules |
|------|------|-----------|-------|
| Inbox | `00-inbox/` | Shared | DIVA reads + appends; user captures |
| Projects | `01-projects/` | User | DIVA reads only |
| Areas | `02-areas/` | User | DIVA reads only (sacred) |
| Resources | `03-resources/` | User | DIVA reads only |
| Archive | `04-archive/` | User | DIVA reads only |
| A.DIVA | `A.DIVA/` | DIVA | Writes freely (brain, wiki, ops, context, templates) |
| B.TEJO | `B.TEJO/` | Pipeline | Immutable after creation — never edit manually |
| C.CRM | `C.CRM/` | Shared | `[DIVA]` sections auto-enriched; `[MATHEUS]` sacred |
| D.DAILY | `D.DAILY/` | Shared | DIVA pre-populates; user writes during day |

### Frontmatter Requirements

Every `.md` file written to the vault must have:
```yaml
---
tags: [category, domain]
date: YYYY-MM-DD
---
```

Wiki notes in `A.DIVA/wiki/` additionally need: `type`, `description`, `source` (or `sources`).

### 8 Canonical Note Types

`claim`, `concept`, `person`, `project`, `event`, `decision`, `document`, `synthesis`

## Vault-First Query Routing

When answering knowledge questions, search the vault FIRST:

1. Run `qmd search "query" -c second-brain`
2. Apply threshold logic:
   - Score >= 72%: Vault hit sufficient. Cite with `[[wikilinks]]`. Do NOT call knowledge_search.
   - Score 45-71%: Partial hit. Use vault + `mcp__knowledge__knowledge_search` for enrichment.
   - Score < 45%: Vault miss. Call `mcp__knowledge__knowledge_search` directly.

## Filing Loop (Dual Output Model)

When a synthesis response combines >= 2 sources and produces a new insight:
- **confidence: high** — file automatically via `/file-note`, notify user
- **confidence: medium** — propose filing to user
- **confidence: low** — do not auto-file; user can manually `/file-note`

## qmd Pitfalls

- **NEVER use `qmd query`** — crashes on macOS due to Metal reranker bug (GGML assertion failure)
- Use `qmd search` (BM25) or `qmd vsearch` (vector only) instead
- Binary location: `~/.npm-global/bin/qmd` (may not be in PATH for hooks — use absolute path)
- After bulk writes, re-index: `qmd update --collection second-brain && qmd embed`

## Scripts

All bundled scripts are at `${CLAUDE_PLUGIN_ROOT}/scripts/`:
- `validate-proposition.sh <filepath>` — exit 0 (pass), 1 (fail), 2 (error)
- `validate-write.sh <filepath>` — exit 0 (pass), 1 (fail)
- `classify-message.py "<message>"` — prints category + vault route
- `lint-vault.py [vault_path] [--json]` — vault health check
- `update-index.py [vault_path]` — update MOC indices
- `vault-commit.sh [vault_path] [message]` — git add + commit + push

## MCP Tools

The `knowledge` MCP server provides 5 tools for the remote Knowledge API:
- `knowledge_search` — semantic search across RAG collections
- `knowledge_ingest` — ingest files (multipart upload to Knowledge API over Tailscale)
- `knowledge_documents` — list documents with filters
- `knowledge_summary` — get AI summary for a document
- `knowledge_health` — check API/Qdrant status

## Language

Match the note's language (Portuguese or English) for any content you add. Tags stay in English.

## Commit Discipline

Every vault write must end with: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/vault-commit.sh`
