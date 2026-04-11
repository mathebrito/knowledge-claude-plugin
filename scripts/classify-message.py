#!/usr/bin/env python3
"""
classify-message.py — Fast keyword-based message classifier for vault routing.

Usage: python3 classify-message.py "user message text here"

Classifies messages into: DECISION, WIN, PERSON_CONTEXT, PROJECT_UPDATE, IDEA,
                          QUESTION, TASK, KNOWLEDGE_CLAIM, RESEARCH, NOTE
Prints classification and a vault routing hint.

No LLM calls — pure keyword matching for speed.
Supports English and Portuguese keywords.
"""

import sys
import re


def classify(message: str) -> tuple[str, str]:
    """Classify a message and return (category, vault_route)."""
    lower = message.lower()

    # DECISION keywords (EN + PT)
    decision_kw = [
        "decided", "decision", "decidimos", "optamos", "decidi",
        "we'll go with", "going with", "chose", "escolhemos",
        "vamos com", "opted for", "optei",
    ]
    for kw in decision_kw:
        if kw in lower:
            return "DECISION", "A.DIVA/brain/Key Decisions.md"

    # WIN keywords (EN + PT)
    win_kw = [
        "won", "shipped", "lancei", "consegui", "delivered",
        "launched", "completed", "finished", "conquered",
        "conquistei", "fechei", "achievement", "brag",
        "proud", "orgulho", "milestone reached",
    ]
    for kw in win_kw:
        if kw in lower:
            return "WIN", "D.DAILY/"

    # PERSON_CONTEXT — look for capitalized names after relational keywords
    person_patterns = [
        r"(?:com|with|met|meeting|conheci|falei com|talked to|spoke with)\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*)",
    ]
    for pattern in person_patterns:
        match = re.search(pattern, message)
        if match:
            name = match.group(1).strip()
            slug = name.replace(" ", "-")
            return "PERSON_CONTEXT", f"C.CRM/{slug}.md"

    # QUESTION keywords (EN + PT)
    question_kw = [
        "how", "why", "what", "como", "porque", "qual", "quando",
    ]
    if message.strip().endswith("?"):
        return "QUESTION", ""
    for kw in question_kw:
        if re.search(r'\b' + re.escape(kw) + r'\b', lower):
            return "QUESTION", ""

    # TASK keywords (EN + PT)
    task_kw = [
        "todo", "tarefa", "task", "fix", "implement",
        "need to", "preciso", "fazer",
    ]
    for kw in task_kw:
        if kw in lower:
            return "TASK", "A.DIVA/ops/backlog.md"

    # PROJECT_UPDATE keywords (EN + PT)
    project_kw = [
        "project", "projeto", "sprint", "milestone",
        "deploy", "release", "pr ", "pull request",
        "branch", "epic", "backlog", "kanban",
    ]
    for kw in project_kw:
        if kw in lower:
            return "PROJECT_UPDATE", "01-projects/"

    # KNOWLEDGE_CLAIM keywords (EN + PT) — triggers arscontexta pipeline
    knowledge_kw = [
        "/reduce", "/reflect", "/reweave", "/verify", "/rethink",
        "/learn", "extract insights", "extrair claims", "knowledge graph",
        "grafo de conhecimento", "pipeline", "claim", "proposição",
    ]
    for kw in knowledge_kw:
        if kw in lower:
            return "KNOWLEDGE_CLAIM", "A.DIVA/wiki/"

    # RESEARCH keywords (EN + PT) — send to inbox for later /reduce
    research_kw = [
        "research", "pesquisar", "pesquisa", "investigate",
        "investigar", "deep dive", "aprofundar", "study",
        "estudar", "learn about", "aprender sobre",
    ]
    for kw in research_kw:
        if kw in lower:
            return "RESEARCH", "00-inbox/"

    # IDEA keywords (EN + PT)
    idea_kw = [
        "idea", "ideia", "what if", "e se",
        "maybe we could", "brainstorm", "hypothesis",
        "hipótese", "could we", "imagine", "imagina",
        "thinking about", "pensando em",
    ]
    for kw in idea_kw:
        if kw in lower:
            return "IDEA", "00-inbox/"

    # Default — generic note
    return "NOTE", "00-inbox/"


def main():
    if len(sys.argv) < 2:
        print("Usage: classify-message.py <message>", file=sys.stderr)
        sys.exit(1)

    message = sys.argv[1]
    category, route = classify(message)

    print(f"{category}")
    print(f"[vault-route: {route}]")


if __name__ == "__main__":
    main()
