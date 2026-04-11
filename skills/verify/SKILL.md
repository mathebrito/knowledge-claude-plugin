---
name: verify
description: >
  Quality gate between /reduce and /reflect. Runs 6 structural and semantic
  checks on wiki notes: propositional title, duplicate detection, source
  presence, valid type, outbound wikilinks, and note length. Two modes:
  interactive (recent notes) and batch (full wiki scan with JSON report).
version: 1.0.0
author: knowledge-engine plugin (adapted from arscontexta)
---

# Knowledge Verify — Quality Gate for Wiki Notes

Validates wiki notes against 6 quality checks before they enter the
`/reflect` phase. Catches structural and semantic issues early so that
`/reflect` operates on clean, well-formed notes.

## Triggers

- `/verify` — interactive mode, runs on notes from the most recent `/reduce`
- `/verify [filepath]` — verify a specific note
- `/verify --all` — batch scan of all A.DIVA/wiki/ notes, writes JSON report

## Pipeline Position

```
/reduce → notes draft → /verify → notes validated → /reflect
```

## Paths (hardcoded)

| Path | Purpose |
|------|---------|
| `~/second-brain/A.DIVA/wiki/` | Notes to verify |
| `~/second-brain/A.DIVA/SCHEMA.md` | Canonical types reference |
| `~/second-brain/A.DIVA/ops/queue.yaml` | Pipeline state (last reduce) |
| `~/second-brain/A.DIVA/ops/verify-report.json` | Batch mode output |
| `${CLAUDE_PLUGIN_ROOT}/scripts/validate-proposition.sh` | Proposition validator |
| `qmd` | Search tool for duplicate detection (assume in PATH after /setup) |

---

## Workflow — Interactive Mode (`/verify`)

### Step 1: Identify Target Notes

If a specific filepath is given, use that note.

Otherwise, find notes from the most recent `/reduce` run:

```bash
# Check queue.yaml for last reduce timestamp
cat ~/second-brain/A.DIVA/ops/queue.yaml
```

Use the `last_reduce` timestamp to find recently created notes:

```bash
# Find notes modified since last reduce
find ~/second-brain/A.DIVA/wiki/ -name '*.md' -not -path '*/MOCs/*' -not -name '_log.md' -newer ~/second-brain/A.DIVA/ops/queue.yaml | sort
```

If no recent notes found, ask the user which notes to verify.

### Step 2: Run All 6 Checks

For each target note, run the checks in order. Read the note first:

```bash
cat "<note-path>"
```

#### Check 1: Titulo proposicional

Reuse the existing validation script:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/validate-proposition.sh "<note-path>"
```

**Exit codes:**
- `0` = PASS (title is a proposition)
- `1` = FAIL (title looks like a topic label)
- `2` = ERROR (file not found, no heading)

**If FAIL:** Propose a rewritten title that passes the claim test:
"This note argues that [title]" must read as a complete sentence.

#### Check 2: Duplicado

Search for similar notes using qmd BM25 search:

```bash
qmd search "<note title>" -c second-brain
```

**IMPORTANT:** Use `qmd search` (BM25 only), NOT `qmd query` (query crashes due to Metal reranker bug on macOS).

Parse the output for scores. qmd returns results in this format:
```
qmd://second-brain/path/to/note.md:line #hash
Title: note title
Score:  NN%
```

**Threshold:**
- Score >= 85% AND different note → FAIL (duplicate — propose merge)
- Score 70-84% AND different note → WARN (similar — suggest review)
- Score < 70% → PASS

#### Check 3: Fonte presente

Check that the note has at least one source reference:

```bash
# Check frontmatter for source: or sources: field
grep -c '^\(source\|sources\):' "<note-path>"

# Check body for wikilinks
grep -c '\[\[' "<note-path>"
```

**PASS if:** frontmatter contains `source:` or `sources:` with a non-empty value, OR the body contains at least one `[[wikilink]]`.

**If FAIL:** Suggest adding a `source:` frontmatter field or a `## Source` section with at least one `[[wikilink]]`.

#### Check 4: Tipo valido

```bash
grep '^type:' "<note-path>" | head -1 | sed 's/type:[[:space:]]*//'
```

**Valid types:** `claim`, `concept`, `person`, `project`, `event`, `decision`, `document`, `synthesis`

**If FAIL (missing):** Suggest `type: claim` as default.
**If FAIL (invalid value):** Show the invalid type and list the 8 valid options.

#### Check 5: Wikilinks outbound

Count outbound wikilinks in the note body (after frontmatter):

```bash
awk '/^---$/{n++; next} n>=2{print}' "<note-path>" | grep -o '\[\[' | wc -l
```

**Threshold:** Minimum 2 outbound wikilinks.

**If FAIL:** Suggest adding `[[MOC-<Domain>]]` and at least one `[[related-note]]`. Use `qmd search` to find candidates.

#### Check 6: Tamanho

```bash
wc -l < "<note-path>"
```

**Threshold:** Flag if > 200 lines. Not a hard failure — some synthesis notes may legitimately exceed this.

### Step 3: Present Results

```
## Verification Report

### <note-filename>

| # | Check | Result | Detail |
|---|-------|--------|--------|
| 1 | Titulo proposicional | PASS/FAIL | "<title>" — <reason if fail> |
| 2 | Duplicado | PASS/WARN/FAIL | <closest match NN%> or "no duplicates" |
| 3 | Fonte presente | PASS/FAIL | source: <value> or "no source found" |
| 4 | Tipo valido | PASS/FAIL | type: <value> or "missing/invalid" |
| 5 | Wikilinks outbound | PASS/FAIL | N wikilinks (min 2) |
| 6 | Tamanho | PASS/WARN | N lines (max 200) |

**Score:** N/6 checks passed

### Suggested Actions
1. [action for each failed check]
```

### Step 4: Propose Fixes

For each failed check, propose a specific fix and ask the user:

```
Fix N of M: [check name]

Problem: [what failed]
Proposed fix: [specific change]

Apply? (yes / skip / edit)
```

Apply fixes the user approves. Skip fixes the user declines.

### Step 5: Post-Verify

1. **Update queue.yaml** — set `stats.last_verify` timestamp:

```bash
sed -i '' "s/last_verify:.*/last_verify: $(date -u +%Y-%m-%dT%H:%M)/" ~/second-brain/A.DIVA/ops/queue.yaml
```

2. **Append to log.md:**

```
- HH:MM VERIFY N notas | passed: N | failed: N | fixed: N
```

3. **Git commit** (if any fixes applied):

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/vault-commit.sh
```

4. **Re-index qmd** (if note content changed):

```bash
qmd update --collection second-brain
```

---

## Workflow — Batch Mode (`/verify --all`)

### Step 1: Collect All Wiki Notes

```bash
find ~/second-brain/A.DIVA/wiki/ -name '*.md' -not -path '*/MOCs/*' -not -name '_log.md' | sort
```

### Step 2: Run All 6 Checks on Every Note

For each note, run a combined check. Process in groups of 10 to stay within tool-call limits:

```bash
filepath="<note-path>"

# Check 1: Proposition (exit code)
prop_result=$(bash ${CLAUDE_PLUGIN_ROOT}/scripts/validate-proposition.sh "$filepath" 2>&1; echo "EXIT:$?")

# Check 3: Source
has_source=$(grep -c '^\(source\|sources\):' "$filepath" 2>/dev/null || echo 0)
has_wikilinks_total=$(grep -o '\[\[' "$filepath" 2>/dev/null | wc -l | tr -d ' ')

# Check 4: Type
note_type=$(grep '^type:' "$filepath" 2>/dev/null | head -1 | sed 's/type:[[:space:]]*//' | tr -d ' ')

# Check 5: Outbound wikilinks (body only)
body_wikilinks=$(awk '/^---$/{n++; next} n>=2{print}' "$filepath" | grep -o '\[\[' | wc -l | tr -d ' ')

# Check 6: Line count
line_count=$(wc -l < "$filepath" | tr -d ' ')

echo "FILE:$(basename "$filepath")"
echo "PROP:$prop_result"
echo "SOURCE:$has_source"
echo "WIKILINKS_TOTAL:$has_wikilinks_total"
echo "TYPE:$note_type"
echo "BODY_WIKILINKS:$body_wikilinks"
echo "LINES:$line_count"
```

For Check 2 (duplicate detection), run qmd search per note title in batches of 10:

```bash
title=$(basename "<note-path>" .md)
qmd search "$title" -c second-brain 2>/dev/null | head -12
```

### Step 3: Generate verify-report.json

Write the JSON report to `~/second-brain/A.DIVA/ops/verify-report.json`:

```json
{
  "generated": "2026-04-10T12:00:00Z",
  "generator": "knowledge-verify v1.0.0",
  "model": "<model-id>",
  "total_notes": 119,
  "summary": {
    "all_passed": 95,
    "with_issues": 24,
    "by_check": {
      "titulo_proposicional": { "pass": 110, "fail": 9 },
      "duplicado": { "pass": 117, "fail": 2 },
      "fonte_presente": { "pass": 115, "fail": 4 },
      "tipo_valido": { "pass": 119, "fail": 0 },
      "wikilinks_outbound": { "pass": 112, "fail": 7 },
      "tamanho": { "pass": 118, "warn": 1 }
    }
  },
  "issues": [
    {
      "file": "note-filename.md",
      "path": "~/second-brain/A.DIVA/wiki/note-filename.md",
      "checks": {
        "titulo_proposicional": { "status": "fail", "detail": "Too short (2 words)" },
        "duplicado": { "status": "pass", "closest_match": "other-note.md", "score": 45 },
        "fonte_presente": { "status": "pass", "source": "[[source-doc]]" },
        "tipo_valido": { "status": "pass", "type": "claim" },
        "wikilinks_outbound": { "status": "fail", "count": 1, "min": 2 },
        "tamanho": { "status": "pass", "lines": 28 }
      },
      "suggested_actions": [
        "Rewrite title as proposition: 'X enables Y' instead of 'X Y'",
        "Add at least one more [[wikilink]] to body"
      ]
    }
  ]
}
```

### Step 4: Post-Batch

1. Report summary to user.
2. Update `queue.yaml` — set `stats.last_verify`.
3. Git commit: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/vault-commit.sh`

---

## Scope Boundary: /verify vs /lint

| Concern | /verify | /lint |
|---------|---------|-------|
| Propositional titles | Check 1 | No |
| Duplicate detection | Check 2 | No |
| Source presence | Check 3 | No |
| Type validation | Check 4 | No |
| Wikilink minimum | Check 5 | No |
| Note length | Check 6 | No |
| Broken wikilinks | No | Yes |
| Orphan notes | No | Yes |
| Stale claims (>18mo) | No | Yes |
| RAG sync | No | Yes |
| Divergence/counterpoints | No | Yes |

`/verify` = note quality (is this note well-formed?).
`/lint` = vault health (is the vault consistent?).

---

## Rules

1. **Never modify a note without user approval** — report and propose, never auto-fix
2. **Use `qmd search`, never `qmd query`** — `query` has a known Metal reranker bug on macOS
3. **Reuse `validate-proposition.sh`** — call at `${CLAUDE_PLUGIN_ROOT}/scripts/validate-proposition.sh`, do not duplicate
4. **85% is the duplicate threshold** — 70-84% = warning, not failure
5. **Minimum 2 outbound wikilinks** — per SCHEMA.md conventions
6. **200 lines maximum** — flag but do not block
7. **8 canonical types only** — claim, concept, person, project, event, decision, document, synthesis
8. **Bilingual** — match the note's language (PT or EN) in suggestions
9. **Batch mode: groups of 10** — for qmd searches to stay within tool-call limits

---

## Error Handling

- **`validate-proposition.sh` not found:** Skip Check 1, warn user
- **`qmd` not found or crashes:** Skip Check 2, log "qmd unavailable, duplicate check skipped"
- **`queue.yaml` missing:** Fall back to `find -mtime -1` for recent notes
- **Note has no frontmatter:** Fail checks 3 and 4, report "no frontmatter block found"
- **Batch > 500 notes:** Process in batches of 50, write incremental results
