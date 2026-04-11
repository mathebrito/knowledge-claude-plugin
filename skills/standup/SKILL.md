---
name: standup
description: >
  Morning briefing — North Star, inbox items, active focus, recent daily
  notes, knowledge graph stats.
version: 1.0.0
author: knowledge-engine
---

# Standup — Morning Briefing

On-demand morning kickoff. Gives context on where things stand and
surfaces priorities, pending triage, and vault health.

## Triggers

- `/standup` — run the morning briefing

## Workflow

### Step 1: Read North Star

Read the first 30 lines of `~/second-brain/A.DIVA/brain/North Star.md`.
Extract top goals and current priorities.

### Step 2: List Inbox (Pending Triage)

```bash
ls ~/second-brain/00-inbox/
```

Show files awaiting triage, sorted by date.

### Step 3: Read Active Focus

Read `~/second-brain/A.DIVA/context/active-focus.md` (if it exists).
This contains the current focus area / deep-work topic.

### Step 4: Recent Daily Notes

Show the last 3 daily notes from `~/second-brain/D.DAILY/`:

```bash
ls -t ~/second-brain/D.DAILY/*.md | head -3
```

Read the first ~20 lines of each to extract key items.

### Step 5: Knowledge Graph Stats

Count wiki notes:

```bash
ls ~/second-brain/A.DIVA/wiki/*.md | wc -l
```

### Step 6: Knowledge API Health

Check the Knowledge MCP server:

```
mcp__knowledge__knowledge_health
```

Report connectivity status (OK / unreachable).

### Step 7: Present Briefing

Format output as a structured briefing:

```
Good morning! Here's your standup:

NORTH STAR: <top goals from North Star.md>

ACTIVE FOCUS: <current focus from active-focus.md>

INBOX (N items pending triage):
  - 2026-04-10-api-rate-limit-idea.md
  - 2026-04-09-book-recommendation.md

RECENT DAILY NOTES:
  - 2026-04-10.md — <key items>
  - 2026-04-09.md — <key items>
  - 2026-04-08.md — <key items>

KNOWLEDGE GRAPH: N wiki notes | API: OK

Here's where you left off: <contextual summary>
```
