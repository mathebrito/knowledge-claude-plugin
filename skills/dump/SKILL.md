---
name: dump
description: >
  Classify and route a brain dump to the correct vault zone
  (inbox, daily, brain, CRM, projects).
version: 1.0.0
author: knowledge-engine
---

# Brain Dump — Classify and Route

Freeform brain dump. User says anything, Claude classifies and routes it
to the correct location in the vault.

## Triggers

- `/dump <content>` — classify and route the content

## Workflow

### Step 1: Read the User's Brain Dump

Accept any freeform text from the user.

### Step 2: Classify with Script

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/classify-message.py "<content>"
```

The script uses keyword matching (English + Portuguese) and returns a routing hint:
- `DECISION`
- `WIN`
- `PERSON_CONTEXT`
- `PROJECT_UPDATE`
- `IDEA`
- `KNOWLEDGE_CLAIM`
- `QUESTION` (no vault routing)
- `TASK` (no vault routing)

### Step 3: Apply LLM Judgment

The script is keyword-based — Claude refines the classification for edge cases.
Consider the full context: tone, intent, and whether the content fits better
in a different category than the script suggested.

### Step 4: Route to Correct Zone

| Classification | Destination | Action |
|---|---|---|
| DECISION | `~/second-brain/A.DIVA/brain/Key Decisions.md` | Append new entry at top, below frontmatter |
| WIN | `~/second-brain/D.DAILY/YYYY-MM-DD.md` under `## Wins` | Append to today's daily note |
| PERSON_CONTEXT | `~/second-brain/C.CRM/<Name>.md` | Create if new, append interaction if existing |
| PROJECT_UPDATE | `~/second-brain/01-projects/<project>.md` | Append update with date |
| IDEA / RESEARCH | `~/second-brain/00-inbox/YYYY-MM-DD-<slug>.md` | Create new inbox file |
| KNOWLEDGE_CLAIM | — | Trigger `/reduce` workflow |

### Step 5: Ensure Frontmatter

Every written or updated note must have:
- YAML frontmatter with `tags`, `date`, and `description`
- At least one `[[wikilink]]` to connect it to the knowledge graph

### Step 6: Commit

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/vault-commit.sh
```

## Output

Confirm to the user what was filed and where (path + brief summary).

**Pipeline integration:** When content is routed to `00-inbox/`, mention:
```
Filed to 00-inbox/<slug>.md
Tip: run /reduce to extract claims and add to the knowledge graph.
```

## Example

```
/dump decided to use PostgreSQL instead of SQLite for the analytics service
→ Appended to A.DIVA/brain/Key Decisions.md
  "2026-04-11 — Use PostgreSQL over SQLite for analytics service"
  Tagged: #decision #analytics
  Linked: [[Analytics Service]]
```

## Zone Rules

- `0-4` (PARA) — append only, never overwrite existing content
- `A.DIVA/` — write freely
- `C.CRM/` — coauthorship: `[DIVA]` sections auto-enriched, `[MATHEUS]` sections sacred
- `D.DAILY/` — coauthorship by design
