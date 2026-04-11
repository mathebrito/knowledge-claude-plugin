---
name: reflect
description: >
  Find and articulate connections between notes in the knowledge graph.
  Uses dual discovery (MOC reading + qmd BM25 search), adds bidirectional
  wikilinks inline, and updates Maps of Content.
version: 1.0.0
author: knowledge-engine plugin (adapted from arscontexta)
---

# Knowledge Reflect — Find Connections in the Knowledge Graph

**Triggers:** `/reflect`, `/reflect [note-name]`, `find connections`

Finds meaningful connections between notes, articulates *why* they connect,
adds bidirectional wikilinks, and keeps MOCs up to date.

## Vault Layout

- **Vault root:** `~/second-brain/`
- **Notes:** `A.DIVA/wiki/`
- **MOCs:** `A.DIVA/wiki/MOCs/` (hub.md is the index)
- **Domain MOCs:** MOC-Tech, MOC-Climate, MOC-Business, MOC-People, MOC-Methodology
- **qmd binary:** `qmd` (assume in PATH after /setup)

## Workflow

### Step 1 — Identify Target Note(s)

If the user specifies a note:
```bash
# Find the note
find ~/second-brain/A.DIVA/wiki/ -name "*<note-name>*" -type f
```

If no note specified, find recently modified notes:
```bash
find ~/second-brain/A.DIVA/wiki/ -name '*.md' -not -path '*/MOCs/*' -mtime -3 | head -10
```

Read the target note fully:
```bash
read_file("~/second-brain/A.DIVA/wiki/<note>.md")
```

### Step 2 — Dual Discovery

**Path A: Read the relevant MOC**

Determine which domain MOC(s) the note belongs to based on its content/tags.
Read that MOC to see what other notes exist in the same domain:
```bash
read_file("~/second-brain/A.DIVA/wiki/MOCs/MOC-Tech.md")
```

Read any linked notes from the MOC that look potentially related (max 3-5).

**Path B: Search via qmd (BM25)**

Extract 2-3 key concepts from the target note and search:
```bash
# IMPORTANT: Use 'qmd search', NOT 'qmd query' (query crashes due to Metal reranker bug on macOS)
qmd search 'concept1 concept2' -c second-brain
```

Run 2-3 searches with different concept combinations for breadth.
Read the top candidates returned by qmd.

### Step 3 — The Articulation Test

For each candidate connection, you MUST articulate WHY the notes connect.
Use one of these connection types:

| Type | Meaning | Example |
|------|---------|---------|
| **extends** | Builds on, adds depth to | "Note A extends B because it takes B's framework and applies it to a new domain" |
| **contradicts** | Challenges, offers counter-evidence | "Note A contradicts B because it presents data showing the opposite trend" |
| **provides foundation for** | Is prerequisite knowledge | "Note A provides foundation for B because B's argument depends on A's definitions" |
| **is evidence for** | Supports empirically | "Note A is evidence for B because it documents a case where B's prediction held true" |
| **is an instance of** | Concrete example of an abstract claim | "Note A is an instance of B because it shows B's pattern playing out in practice" |

**The test:** If you cannot complete the sentence "A connects to B because ___",
the connection is not real. Do NOT add weak or vague links.

Format each connection as:
```
[[Note A]] <connection-type> [[Note B]] because <specific explanation>
```

### Step 4 — Add Wikilinks (Bidirectional)

For each validated connection, add wikilinks INLINE in both notes.
Place them where they're contextually relevant, not just dumped at the bottom.

**In the source note** — find the paragraph where the connection is most relevant:
```
patch(path="~/second-brain/A.DIVA/wiki/source-note.md",
  old_string="<relevant paragraph>",
  new_string="<paragraph with [[Target Note]] wikilink woven in naturally>")
```

**In the target note** — add a backlink in context:
```
patch(path="~/second-brain/A.DIVA/wiki/target-note.md",
  old_string="<relevant paragraph>",
  new_string="<paragraph with [[Source Note]] wikilink woven in naturally>")
```

Guidelines for inline links:
- Place the `[[wikilink]]` where the reader would benefit from jumping to the other note
- Don't add a "See also" dump — weave links into prose
- If no natural inline spot exists, add under a `## Conexoes` section at the end

### Step 5 — Update MOCs

For each note that isn't already listed in its domain MOC, add it.

**Find the right MOC:**
- Tech/infra/software/AI → MOC-Tech
- Climate/carbon/sustainability → MOC-Climate
- Business/strategy/fundraising → MOC-Business
- People/networking/relationships → MOC-People
- Methodology/process/frameworks → MOC-Methodology
- If unsure, check the note's tags and content

**Add the entry** under `## Notas` in the MOC:
```
patch(path="~/second-brain/A.DIVA/wiki/MOCs/MOC-<Domain>.md",
  old_string="## Notas\n",
  new_string="## Notas\n\n- [[Note Title]] — one-line description of the note's core claim\n")
```

If the note bridges two domains, add it to both MOCs.

Update hub.md note counts if you added new entries:
```
patch(path="~/second-brain/A.DIVA/wiki/MOCs/hub.md",
  old_string="| [[MOC-Tech]] | Tecnologia, infra, arquitetura de software | 0 |",
  new_string="| [[MOC-Tech]] | Tecnologia, infra, arquitetura de software | 1 |")
```

### Step 6 — Post-Reflect

1. **Git commit**:
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/scripts/vault-commit.sh
   ```

2. **Re-index qmd**:
   ```bash
   qmd update --collection second-brain
   ```

### Step 7 — Report

Present a summary of all connections made:

```
## Reflection Report

### Connections Made
1. [[Note A]] extends [[Note B]]
   Because: <explanation>

2. [[Note C]] is evidence for [[Note A]]
   Because: <explanation>

### MOC Updates
- Added [[Note A]] to MOC-Tech
- Added [[Note C]] to MOC-Climate, MOC-Tech (cross-domain)

### Notes Touched
- note-a.md — added 2 wikilinks
- note-b.md — added 1 backlink
- note-c.md — added 1 wikilink
- MOC-Tech.md — added 2 entries
- MOC-Climate.md — added 1 entry

### Orphan Notes (no connections found)
- (none, or list any notes that had no valid connections)
```

## Validation Script

Before reflecting on a note, optionally check if its title is a proper proposition:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/validate-proposition.sh '~/second-brain/A.DIVA/wiki/note-name.md'
```

A good title can be prefixed with "This note argues that..." and still read as a sentence.
Topic labels like "Carbon Markets" or "Docker Setup" are flags — the note may need
to be rewritten as a claim before it can be meaningfully connected.

## Rules

1. **Never add a link without a 'because'** — the articulation test is mandatory
2. **Bidirectional** — if A links to B, B must link back to A
3. **Inline over appendix** — prefer wikilinks woven into prose over "See also" lists
4. **Quality over quantity** — 3 well-articulated connections beat 10 vague ones
5. **Use qmd search, never qmd query** — query crashes due to Metal reranker bug on macOS
6. **Respect note sovereignty** — don't rewrite the note's argument, only add links
7. **Progressive discovery** — read hub → MOC → individual notes. Don't load everything.
8. **Bilingual** — notes may be in Portuguese or English. Match the note's language for any text you add.
