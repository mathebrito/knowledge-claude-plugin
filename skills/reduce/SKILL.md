---
name: reduce
description: >
  Extract structured knowledge claims from source material in the inbox.
  Identifies core claims, patterns, tensions, anti-patterns, and implementation
  ideas, then creates atomic notes with proper frontmatter and wikilinks.
  Uses qmd for duplicate detection before creating notes.
version: 1.1.0
author: knowledge-engine plugin (adapted from arscontexta/reduce)
---

# Knowledge Reduce — Extract Claims from Sources

Extract atomic knowledge claims from source material and create structured notes
in the second-brain vault.

## Triggers

- `/reduce` — process next item from inbox or queue
- `/reduce [filename]` — process a specific file from inbox
- `extract insights from ...` — natural language trigger

## Paths (hardcoded)

| Path | Purpose |
|------|---------|
| `~/second-brain/00-inbox/` | Source material awaiting processing |
| `~/second-brain/A.DIVA/wiki/` | Output — atomic claim notes AND Wiki document fichas |
| `~/second-brain/B.TEJO/knowledge/` | Layer 1 RAG fichas (managed by Knowledge API) |
| `~/second-brain/A.DIVA/wiki/MOCs/` | Maps of Content (hub.md is index) |
| `~/second-brain/A.DIVA/ops/queue.yaml` | Pipeline state |
| `~/second-brain/A.DIVA/ops/log.md` | Operations log (append) |

## Workflow

### Phase 1: Orient

1. Check `~/second-brain/A.DIVA/ops/queue.yaml` or list files in `~/second-brain/00-inbox/`.
2. Pick the oldest unprocessed file.
3. Show the user and ask for confirmation.

### Phase 2: Ingest & Read

1. **Ingest to RAG**: Call `mcp__knowledge__knowledge_ingest` for the file. This ensures:
    - Original is stored in MongoDB (Binary).
    - Layer 1 RAG Ficha is created in `B.TEJO/knowledge/`.
    - Original is deleted from the vault/disk.
    - Note: the MCP tool rsync's the file to Mac Mini before ingesting.
2. **Read Content**: Read the source file with `read_file` BEFORE it is deleted, or use `mcp__knowledge__knowledge_search` if already processed.
3. Chunk if > 2500 lines.

### Phase 2.5: Create Wiki Ficha (Layer 2 Bridge)

**CRITICAL:** Before extracting individual claims, create a "Wiki Ficha" in `~/second-brain/A.DIVA/wiki/ficha-<slug>.md`.
- `type: ficha`
- `source: "[[ficha-<doc_id>]]"` (Link to the Layer 1 RAG ficha)
- `description`: 1-2 sentence summary.

### Phase 3: Categorize & Extract

Extract Claims: Core claims, Patterns, Tensions, Anti-patterns, Enrichments, Implementation ideas, Validations.
Language Rule: Match source language.

### Phase 4: Search for Duplicates

Use `qmd search "claim title" -c second-brain`. Classify as New, Enrichment, or Duplicate.

**IMPORTANT:** Use `qmd search` (BM25 only), NEVER `qmd query` (crashes due to Metal reranker bug on macOS).

### Phase 5: Present Findings

Present ALL findings (Ficha + Claims) to user. Wait for approval.

### Phase 6: Create Notes

Create notes in `~/second-brain/A.DIVA/wiki/`. Include `agent`, `model`, `provider`, and `origin: reduce`.

### Phase 7: Update MOCs

Add Ficha and Claims to relevant MOCs in `~/second-brain/A.DIVA/wiki/MOCs/`.

### Phase 8: Cleanup & Update Queue

1. **Original Retention**: Ensure original is removed (handled by `mcp__knowledge__knowledge_ingest`). NEVER move to `04-archive/`.
2. Update `~/second-brain/A.DIVA/ops/queue.yaml` and `~/second-brain/A.DIVA/ops/log.md`.
3. **Git commit**:
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/scripts/vault-commit.sh
   ```
4. **Update QMD index**:
   ```bash
   qmd update --collection second-brain
   ```
5. **Update index.md**:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/update-index.py
   ```

### Phase 9: Report

Show final summary:
```
## Reduce Complete
Source: <filename> → Ingested to RAG & MongoDB (Original deleted)
RAG Ficha: [[ficha-<doc_id>]] in B.TEJO/knowledge/
Wiki Ficha: [[ficha-<slug>]] in A.DIVA/wiki/
Notes created: N
```

## Quality Gates

- Frontmatter completeness.
- Wikilink minimum (source, MOC, related).
- Title as proposition.
- Standalone body.
- No original files in vault.
