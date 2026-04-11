---
name: lint
description: >
  Full vault health check — broken wikilinks, orphan notes, stale claims,
  divergence analysis. Run manually or weekly.
version: 1.0.0
author: knowledge-engine
---

# Knowledge Lint — Vault Health Check

Run a comprehensive health check on the second-brain vault. Combines
deterministic checks (Python script) with LLM-powered divergence
analysis.

## Triggers

- `/lint` — full lint
- Weekly cron: Sunday 06:00

## Workflow

### Phase 1: Run Deterministic Checks

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/lint-vault.py ~/second-brain --json
```

Parse the JSON output. This covers:
1. **Broken wikilinks** — `[[links]]` pointing to non-existent notes
2. **Orphan notes** — notes with zero inbound links (excluding MOCs)
3. **Stale claims** — notes older than 18 months without update
4. **Fichas vs RAG sync** — fichas whose source collection no longer exists in the vector store

### Phase 2: Divergence Check (LLM-powered)

For the top 5 MOC domains (by note count):

1. Pick the 3 most-linked notes in each domain (via `qmd search` for MOC topic)
2. Read each note's claims
3. Generate 2-3 substantive counterarguments
4. Check if any existing note already addresses the counterpoint (`qmd search`)
5. If not covered, add `## Contrapontos potenciais` section to the note:
   ```markdown
   ## Contrapontos potenciais

   - <contraponto 1> — gerado por lint YYYY-MM-DD
   - <contraponto 2> — gerado por lint YYYY-MM-DD
   ```

**Quality bar for counterarguments:**
- Must be substantive (not trivial "but what if wrong?")
- Must be domain-specific
- Must challenge the claim's core logic, not peripheral details
- Skip if the note already has a populated Contrapontos section

**Token budget:** Max 5 clusters (one per MOC domain), 3 notes per cluster.

**IMPORTANT:** NEVER use `qmd query` — crashes on macOS due to Metal reranker bug. Use `qmd search` (BM25) or `qmd vsearch` (vector only).

### Phase 3: Generate Report

Save report to `~/second-brain/B.TEJO/reports/YYYY-MM-DD-lint-report.md`:

```markdown
---
title: "Lint Report YYYY-MM-DD"
date: YYYY-MM-DD
type: report
tags: [lint, vault-health]
---

# Lint Report — YYYY-MM-DD

## Resumo

| Check | Total | Issues |
|---|---|---|
| Wikilinks verificados | N | N quebrados |
| Notas verificadas | N | N orfas |
| Claims stale | N revisados | N flagged |
| Fichas vs RAG | N | N desincronizadas |
| Divergence check | N clusters | N contrapontos adicionados |

## Acoes necessarias (requer humano)

1. [[nota-X]] — <descricao do problema e accao sugerida>
2. ...

## Acoes tomadas automaticamente

- N seccoes de "Contrapontos potenciais" adicionadas
- N fichas marcadas status: archived (se aplicavel)
- index.md atualizado
```

### Phase 4: Post-Lint

1. **Update index.md**:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/update-index.py ~/second-brain
   ```

2. **Git commit**:
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/scripts/vault-commit.sh
   ```

## Cron Setup

Weekly lint on Sunday 06:00. Configure via launchd or crontab.
The cron triggers this skill which runs the full pipeline.

## Quality Constraints

- Divergence check: max 5 clusters per run (token budget)
- Counterarguments must be substantive, not trivial objections
- Never modify notes in PARA directories (00-04) — read only
- Never delete notes — only flag, archive, or annotate
- Report always saved even if zero issues found
