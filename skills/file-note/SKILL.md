---
name: file-note
description: >
  Archive a synthesis response as a permanent note in the wiki.
  Detects cross-ficha synthesis, deduplicates via qmd search, and creates
  structured notes with proper frontmatter and wikilinks.
  Implements the dual output model for the LLM Wiki.
version: 1.0.0
author: knowledge-engine plugin
---

# Knowledge File — Archive Synthesis to Wiki

Archive the last synthesis response as a permanent note in the LLM Wiki.
Implements the dual output model: every synthesis query produces a response
to the user AND a permanent note in the vault.

## Triggers

- `/file-note` — archive the last synthesis from this conversation
- `/file-note confirm` — confirm a pending filing proposal
- `/file-note skip` — skip a pending filing proposal

## Paths

| Path | Purpose |
|------|---------|
| `~/second-brain/A.DIVA/wiki/` | Output — synthesis notes |
| `~/second-brain/A.DIVA/wiki/MOCs/` | Maps of Content |
| `~/second-brain/A.DIVA/templates/wiki-synthesis.md` | Template reference |
| `~/second-brain/A.DIVA/ops/log.md` | Operations log (append) |

## Workflow

### Phase 1: Identify Synthesis

1. Look back at the most recent knowledge response in this conversation
2. Verify it qualifies as a synthesis:
   - Combined information from >= 2 distinct notes or documents
   - Produced a conclusion, comparison, trade-off analysis, or recommendation
   - Generated a new claim not textually present in any source note
3. If not a synthesis, tell the user: "A ultima resposta nao e uma sintese cross-ficha. Nada a arquivar."

### Phase 2: Draft Note

1. Generate title as lowercase prose-as-proposition (claim test: "this note argues that [title]")
2. Generate slug from title: `YYYY-MM-DD-<slug>.md` (lowercase, hyphens, max 80 chars)
3. Extract claims derivados (atomic propositions from the synthesis)
4. List source notes with their role in the synthesis
5. Assess confidence:
   - **high**: strong evidence from multiple vault notes, clear logical chain
   - **medium**: reasonable inference, some gaps in evidence
   - **low**: speculative, limited evidence, novel territory
6. Select primary MOC domain from: Tech, Climate, Business, People, Methodology

### Phase 3: Deduplication Gate

Search the wiki for similar existing notes:

```bash
# IMPORTANT: Use 'qmd search', NOT 'qmd query' (query crashes due to Metal reranker bug on macOS)
qmd search "<proposed title>" -c second-brain
```

Apply dedup thresholds:

| Score | Action |
|-------|--------|
| >= 85% | **APPEND** — add new claims to existing note, update sources list. Update `origin` field if mixing file+reduce: `origin: [reduce, file]` |
| 70-84% | **MERGE PROPOSED** — show user: "Nota similar existe: [[slug]]. Fundir? /file-note confirm \| /file-note skip" |
| < 70% | **CREATE** new note |

### Phase 4: Create/Update Note

**For new notes:**

1. Create file at `~/second-brain/A.DIVA/wiki/YYYY-MM-DD-<slug>.md`
2. Write using this template:

```markdown
---
title: "<proposicao em prosa>"
date: YYYY-MM-DD
type: synthesis
origin: file
tags: [<dominio-1>, synthesis]
description: "<1 frase resumindo o insight>"
sources: ["[[<nota-1>]]", "[[<nota-2>]]"]
query_origin: "<query original do usuario>"
confidence: <high|medium|low>
moc: "[[MOC-<dominio>]]"
agent: DIVA (knowledge-engine plugin)
model: <current model id>
provider: <current provider>
---

# <titulo como proposicao>

## Sintese

<Corpo da sintese: 2-5 paragrafos. Prosa direta. Apenas o raciocinio
cross-ficha que conecta as fontes — nao repetir o que as notas ja dizem.>

## Claims derivados

- <claim atomico 1>
- <claim atomico 2>

## Fontes

- [[<nota-1>]] — <papel na sintese>
- [[<nota-2>]] — <papel na sintese>

## Contrapontos potenciais

<!-- Preenchido pelo divergence check (lint) ou manualmente -->

## Historico de revisoes

- YYYY-MM-DD: criado por sintese automatica (filing loop)
```

**For appends (score >= 85%):**

1. Read existing note
2. Add new claims under `## Claims derivados`
3. Add new sources under `## Fontes`
4. If origin changes (e.g., adding `file` to a `reduce` note): `origin: [reduce, file]`
5. Add revision entry under `## Historico de revisoes`

### Phase 5: Post-Filing

Execute these steps in order:

1. **Update MOC** — add entry to relevant MOC in `~/second-brain/A.DIVA/wiki/MOCs/` if new note:
   ```
   - [[<note title>]] — <one-line description>
   ```

2. **Append to log.md** at `~/second-brain/A.DIVA/ops/log.md`:
   ```
   - HH:MM FILE sintese `[[YYYY-MM-DD-slug]]` | fontes: N notas | trigger: manual | confidence: high|medium|low
   ```

3. **Git commit**:
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/scripts/vault-commit.sh
   ```

4. **Re-index QMD**:
   ```bash
   qmd update --collection second-brain
   ```

5. **Update index.md**:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/update-index.py
   ```

6. **Report to user**: Include in response:
   ```
   Insight arquivado: [[YYYY-MM-DD-slug]]
   ```

## Quality Gates

1. **Title must pass claim test** — "this note argues that [title]"
2. **Minimum 2 source notes** referenced in `sources` frontmatter
3. **Synthesis body must not repeat source content** — only cross-ficha reasoning
4. **Dedup gate must run** before any file creation
5. **Log.md entry required** before declaring success

## Language

Match the language of the synthesis response. If the conversation was in
Portuguese, write the note in Portuguese. Tags stay in English.

## Auto-Filing Rules

When a knowledge query produces a synthesis (combines >= 2 sources, produces new
insight), assess confidence and act accordingly:

| Confidence | Action |
|-----------|--------|
| **high** | File automatically via this workflow. Notify user: "Insight arquivado: [[slug]]" |
| **medium** | Propose filing: "Gerei uma sintese. Arquivar? /file-note confirm \| /file-note skip" |
| **low** | Do not auto-file. User can manually invoke `/file-note` |

These rules apply during normal conversation, not just when `/file-note` is
explicitly invoked. The filing loop is a core part of the LLM Wiki pattern —
every synthesis is a candidate for permanent knowledge.

## Error Handling

- **qmd unavailable**: Skip dedup gate, warn user, create note anyway
- **vault-commit.sh fails**: Report error, note is still saved locally
- **log.md doesn't exist**: Create it with header, then append
- **MOC file not found**: Suggest creating a new MOC, skip MOC update
