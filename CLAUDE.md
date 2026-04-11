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

## Three-Layer Architecture (LLM Wiki)

This plugin implements Andrej Karpathy's LLM Wiki pattern — a compounding
knowledge base where the AI maintains a persistent, interconnected wiki
rather than answering queries from raw sources each time.

| Layer | What | Where | Who manages |
|-------|------|-------|-------------|
| **Layer 1: Sources** | Original documents — PDFs, articles, web clips | Qdrant + MongoDB on Mac Mini (via MCP tools) | Knowledge API (automatic) |
| **Layer 2: Wiki** | Compiled knowledge — atomic claims, concepts, syntheses, linked together | `A.DIVA/wiki/` in the Obsidian vault | Claude (via /reduce, /reflect, /file-note) |
| **Layer 3: Schema** | Conventions, types, taxonomy, thresholds | `A.DIVA/SCHEMA.md` + this CLAUDE.md | Manual + plugin reference docs |

The wiki (Layer 2) is the primary knowledge surface. Layer 1 is the raw archive
searched only when the wiki doesn't have the answer. Layer 3 defines how
knowledge is structured.

## Vault Resumption Protocol

At the start of any knowledge-intensive session, orient yourself:

1. Read `A.DIVA/SCHEMA.md` (if it exists) — domain conventions, tag taxonomy, thresholds
2. Read `index.md` at vault root — auto-generated catalog of all wiki notes by type
3. Read `A.DIVA/ops/log.md` (last 20 lines) — recent pipeline operations
4. Read `A.DIVA/brain/North Star.md` (first 20 lines) — current goals and focus

This ensures you understand the vault's current state before making changes.
The session-start hook provides a summary, but for deep work, read these files directly.

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
