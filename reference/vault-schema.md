# Vault Schema — PARA + ABCD

## Structure

```
~/second-brain/
├── 00-inbox/           # Unprocessed captures, ideas
├── 01-projects/        # Active, deadline-driven projects
├── 02-areas/           # Ongoing responsibilities
├── 03-resources/       # Reference material (tech/, specs/, notas/)
├── 04-archive/         # Completed/inactive
├── A.DIVA/             # Agent persistent knowledge
│   ├── brain/          # North Star, Key Decisions, Patterns, Gotchas
│   ├── context/        # active-focus.md, travel.md, current-location.md
│   ├── ops/            # queue.yaml, log.md, backlog.md
│   ├── wiki/           # Living wiki — atomic claim notes
│   │   └── MOCs/       # Maps of Content (hub.md is index)
│   └── templates/      # wiki-concept.md, wiki-person.md, etc.
├── B.TEJO/             # RAG handoff zone (immutable)
│   ├── devops/         # SDLC docs: [SPEC], [PLAN], [RELEASE], [DECISION], [GUIDE]
│   ├── knowledge/      # External source fichas (Layer 1 — RAG pipeline output)
│   ├── meetings/       # Meeting transcripts + fichas
│   └── reports/        # Lint reports, audits
├── C.CRM/              # People profiles
└── D.DAILY/            # Daily journal (YYYY-MM-DD.md, flat)
```

## File Naming Conventions

| Location | Pattern | Example |
|----------|---------|---------|
| Wiki notes | `lowercase-slug.md` | `carbon-markets-need-transparent-verification.md` |
| Daily notes | `YYYY-MM-DD.md` | `2026-04-11.md` |
| B.TEJO/devops | `YYYYMMDD[TYPE]feature_name.md` | `20260411[SPEC]knowledge_engine_plugin.md` |
| Fichas | `ficha-<slug>.md` | `ficha-carbon-credit-methodology.md` |
| CRM | `First-Last.md` | `John-Smith.md` |

## Frontmatter Spec

### Minimum (all files)
```yaml
---
tags: [category, domain]
date: YYYY-MM-DD
---
```

### Wiki notes (A.DIVA/wiki/)
```yaml
---
tags: [claim, tech]
date: 2026-04-11
description: "One-line summary"
type: claim
source: "[[source-note]]"
domain: tech
moc: "[[MOC-Tech]]"
agent: DIVA
model: claude-opus-4-6
provider: anthropic
---
```

### Synthesis notes
```yaml
---
tags: [synthesis, domain]
date: 2026-04-11
type: synthesis
origin: file
sources: ["[[nota-1]]", "[[nota-2]]"]
query_origin: "original user query"
confidence: high|medium|low
moc: "[[MOC-Domain]]"
---
```

## Domain → MOC Mapping

| Domain | MOC |
|--------|-----|
| Tech, infra, software, AI | MOC-Tech |
| Climate, carbon, sustainability | MOC-Climate |
| Business, strategy, fundraising | MOC-Business |
| People, networking, relationships | MOC-People |
| Methodology, process, frameworks | MOC-Methodology |

## Wikilink Rules

- Minimum 2 outbound `[[wikilinks]]` per wiki note (MOC + related)
- Bidirectional: if A links to B, B must link back to A
- Inline over appendix: weave links into prose where reader benefits
- Files > 300 chars must have at least one `[[wikilink]]`
