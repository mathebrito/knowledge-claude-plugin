---
name: knowledge-search
description: >
  Vault-first knowledge query — search qmd locally, fall back to RAG
  over Tailscale if needed.
version: 1.0.0
author: knowledge-engine
---

# Knowledge Search — Vault-First Query

Search the local vault first via qmd (BM25), then fall back to the
Knowledge MCP server (RAG over Tailscale) when local results are
insufficient.

## Triggers

- `/knowledge-search <query>` — explicit search
- Also invoked implicitly when answering knowledge questions

## Workflow

### Step 1: Local Search via qmd

```bash
qmd search "<user query>" -c second-brain
```

This runs BM25 keyword search over the indexed vault (A.DIVA/wiki/,
PARA notes, daily notes, CRM, etc.).

**CRITICAL:** NEVER use `qmd query` — it crashes on macOS due to a Metal
reranker bug. Always use:
- `qmd search` — BM25 keyword search (fast, reliable)
- `qmd vsearch` — vector-only search (when semantic matching needed)

### Step 2: Evaluate Results and Route

Apply threshold logic on the top result score:

| Score | Action |
|---|---|
| >= 72% | **Vault hit sufficient.** Present results with `[[wikilinks]]`. STOP. |
| 45-71% | **Partial hit.** Use vault results as base + call `mcp__knowledge__knowledge_search` for enrichment. |
| < 45% | **Vault miss.** Call `mcp__knowledge__knowledge_search` directly. |

### Step 3: Enrich via Knowledge MCP (if needed)

When score is below 72%, call the Knowledge MCP server:

```
mcp__knowledge__knowledge_search(query="<user query>")
```

This searches the RAG pipeline over Tailscale (Qdrant vector store with
ingested documents, papers, meeting transcripts, etc.).

Combine local vault results with RAG results for a comprehensive answer.

### Step 4: Suggest Filing (if synthesis)

If the combined answer:
- Draws from >= 2 distinct sources (vault notes or RAG documents)
- Produces a NEW conclusion, comparison, or trade-off analysis

Then suggest: "This looks like a cross-source synthesis. Run `/file-note`
to save it to the wiki."

### Step 5: Always Cite with Wikilinks

When referencing vault notes in the response, always use `[[wikilinks]]`:
- `[[note-title]]` for vault notes
- Include source attribution for RAG results

## Notes

- For navigation queries ("what do we have about X"), just list results — no filing
- For factual lookups (single source, no reasoning), present directly — no filing
- The Knowledge MCP server requires Tailscale connectivity to `100.97.71.49`
