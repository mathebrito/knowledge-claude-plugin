# 8 Canonical Note Types

## 1. claim

An atomic knowledge claim — a single argument or insight.

**Title rule:** Must be a proposition. "This note argues that [title]" reads as a complete sentence.

```yaml
type: claim
tags: [claim, <domain>]
source: "[[source-note]]"
```

Categories: `claim`, `core-claim`, `pattern`, `tension`, `anti-pattern`, `implementation`, `validation`

## 2. concept

A definition or explanation of a concept, mechanism, or framework.

```yaml
type: concept
tags: [concept, <domain>]
```

Sections: Definition, Mechanisms, Applications, Related Concepts

## 3. person

A profile of a person — role, interactions, context.

```yaml
type: person
tags: [person, <context>]
```

Sections: Context, Interactions (chronological), Notes

## 4. project

A project record with timeline, status, and linked tasks.

```yaml
type: project
tags: [project, <domain>]
```

Sections: Overview, Timeline, Status, Tasks, Links

## 5. event

An event with dates, participants, outcomes.

```yaml
type: event
tags: [event, <domain>]
```

Sections: Context, Participants, Outcomes, Follow-ups

## 6. decision

A decision record with rationale and trade-offs.

```yaml
type: decision
tags: [decision, <domain>]
```

Sections: Context, Alternatives Considered, Decision, Consequences

## 7. document

A summary of an external document (paper, article, report).

```yaml
type: document
tags: [document, <domain>]
source: "[[ficha-slug]]"
```

Sections: Summary, Key Findings, Relevance, Source

## 8. synthesis

A cross-ficha insight combining multiple sources.

```yaml
type: synthesis
origin: file|reduce
sources: ["[[nota-1]]", "[[nota-2]]"]
confidence: high|medium|low
```

Sections: Sintese, Claims derivados, Fontes, Contrapontos potenciais, Historico de revisoes

## Tag Taxonomy

### Category tags
claim, core-claim, pattern, tension, anti-pattern, implementation, validation, concept, person, project, event, decision, document, synthesis

### Domain tags
tech, climate, business, people, methodology

### Pipeline tags
reduce (from /reduce), file (from /file-note), lint (from /lint)
