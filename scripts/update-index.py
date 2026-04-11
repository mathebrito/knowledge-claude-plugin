#!/usr/bin/env python3
"""Generate index.md for a vault by scanning wiki notes.

Usage: python3 update-index.py [vault_path]
Default vault: $VAULT_ROOT or ~/second-brain
"""

import sys
import os
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

VAULT_ROOT = Path(
    sys.argv[1] if len(sys.argv) > 1
    else os.environ.get("VAULT_ROOT", os.path.expanduser("~/second-brain"))
)


def parse_frontmatter(filepath: Path) -> dict:
    """Extract YAML frontmatter from a markdown file."""
    content = filepath.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    fm_text = content[3:end].strip()
    fm = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if value.startswith("[") and value.endswith("]"):
                value = [v.strip().strip('"').strip("'") for v in value[1:-1].split(",")]
            fm[key] = value
    return fm


def count_wikilinks(filepath: Path) -> int:
    """Count outbound [[wikilinks]] in a file."""
    content = filepath.read_text(encoding="utf-8")
    return len(re.findall(r'\[\[([^\]]+)\]\]', content))


def generate_index() -> str:
    """Generate the full index.md content."""
    wiki_dir = VAULT_ROOT / "A.DIVA" / "wiki"
    if not wiki_dir.exists():
        return f"# Vault Index\n\nWiki directory not found: {wiki_dir}"

    notes = []
    for f in sorted(wiki_dir.glob("*.md")):
        if f.name.startswith("_"):
            continue
        fm = parse_frontmatter(f)
        notes.append({
            "file": f,
            "name": f.stem,
            "type": fm.get("type", "claim"),
            "date": fm.get("date", ""),
            "description": fm.get("description", ""),
            "tags": fm.get("tags", []),
            "wikilinks": count_wikilinks(f),
        })

    mocs_dir = wiki_dir / "MOCs"
    mocs = []
    if mocs_dir.exists():
        for f in sorted(mocs_dir.glob("MOC-*.md")):
            content = f.read_text(encoding="utf-8")
            note_count = content.count("[[")
            mocs.append({"name": f.stem, "count": note_count})

    by_type = defaultdict(list)
    for n in notes:
        by_type[n["type"]].append(n)

    syntheses = sorted(
        [n for n in notes if n["type"] == "synthesis"],
        key=lambda n: n["date"], reverse=True
    )[:10]

    lines = [
        "---",
        f'title: "Vault Index"',
        f'updated: {datetime.now().strftime("%Y-%m-%d")}',
        "---",
        "",
        "# Vault Index",
        "",
        "> Atualizado automaticamente. Nao editar manualmente.",
        f"> Total notes: {len(notes)} | Last updated: {datetime.now().strftime('%Y-%m-%d')}",
        "",
    ]

    for note_type in ["concept", "person", "project", "event", "decision", "document", "claim", "synthesis"]:
        type_notes = by_type.get(note_type, [])
        if type_notes:
            lines.append(f"## {note_type.title()} ({len(type_notes)})")
            lines.append("")
            lines.append("| Note | Description | Updated |")
            lines.append("|---|---|---|")
            for n in sorted(type_notes, key=lambda x: x["name"]):
                desc = n["description"][:80] if n["description"] else ""
                lines.append(f"| [[{n['name']}]] | {desc} | {n['date']} |")
            lines.append("")

    if mocs:
        lines.append("## MOCs disponveis")
        lines.append("")
        for m in mocs:
            lines.append(f"- [[{m['name']}]] -- {m['count']} notas")
        lines.append("")

    if syntheses:
        lines.append("## Sinteses recentes (ultimas 10)")
        lines.append("")
        for s in syntheses:
            lines.append(f"- {s['date']} [[{s['name']}]]")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    index_content = generate_index()
    index_path = VAULT_ROOT / "index.md"
    index_path.write_text(index_content, encoding="utf-8")
    print(f"Index updated: {index_path} ({index_content.count(chr(10))} lines)")
