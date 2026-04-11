---
name: reduce
description: >
  Extract structured knowledge claims from source material in the inbox.
  Identifies core claims, patterns, tensions, anti-patterns, and implementation
  ideas, then creates atomic notes with proper frontmatter and wikilinks.
  Uses qmd for duplicate detection before creating notes.
version: 1.2.0
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

### Phase 2: Read FIRST, Then Ingest

**CRITICAL: Read the file BEFORE ingesting.** The ingestion pipeline may delete the
original from disk. Always follow this order:

1. **Read Content FIRST**: Read the source file with `Read` tool. Store the full text in memory.
2. **Chunk if needed**: If > 2500 lines, split into chunks for processing.
3. **Ingest to RAG**: Call `mcp__knowledge__knowledge_ingest` with the file path. This:
    - Uploads the file to the Knowledge API via multipart HTTP
    - Stores the original in MongoDB (Binary inline, up to 15MB)
    - Creates embeddings in Qdrant
    - Auto-generates a Layer 1 RAG Ficha in `B.TEJO/knowledge/` (server-side)
    - Indexes ficha summary content in Qdrant (as additional searchable chunks)
    - May delete the original from disk (files under `~/knowledge/` only; vault files are preserved)
4. **Sync vault**: Run `git -C ~/second-brain pull --rebase` to pull the Layer 1
   ficha generated on the Mac Mini to the local vault.
5. **Verify Layer 1 Ficha**: Call `mcp__knowledge__knowledge_summary` with the
   returned `document_id`. Confirm `summary` and `key_findings` are populated.
   If summary is empty, the summarization LLM may have failed — wait 30s and
   retry once. If still empty, note it and continue (claims extraction will
   compensate).

### Phase 2.5: Create Wiki Ficha (Layer 2 Bridge)

The Knowledge API auto-generates a **Layer 1 RAG Ficha** in `B.TEJO/knowledge/`
with summary, key findings, and metadata. The reduce skill creates a separate
**Layer 2 Wiki Ficha** in `A.DIVA/wiki/` that links to the Layer 1 and serves
as the wiki-layer bridge for atomic claims.

1. **Check if Layer 1 ficha exists**: Look for `~/second-brain/B.TEJO/knowledge/<slug>.md`.
   If found, read its frontmatter to get `document_id`, `summary`, `collection`.
2. **Create Wiki Ficha** in `~/second-brain/A.DIVA/wiki/ficha-<slug>.md`:
   - `type: ficha`
   - `source: "[[<layer1-ficha-filename>]]"` (wikilink to the Layer 1 RAG ficha)
   - `document_id: "<doc_id>"` (from API response or Layer 1 frontmatter)
   - `description`: 1-2 sentence summary (can reuse from Layer 1 if available).
3. **Skip if exists**: If the wiki ficha already exists, do not overwrite — just
   verify the wikilink to Layer 1 is correct.

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
