#!/usr/bin/env python3
"""Lint the vault for structural issues.

Checks:
1. Broken wikilinks
2. Orphan notes (no inbound links)
3. Stale claims (>18 months without update)
4. Fichas without RAG correspondence

Usage: python3 lint-vault.py [vault_path] [--json]
"""

import sys
import os
import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

VAULT_ROOT = Path(
    sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--")
    else os.environ.get("VAULT_ROOT", os.path.expanduser("~/second-brain"))
)

KNOWLEDGE_API_URL = os.environ.get("KNOWLEDGE_API_URL", "http://100.97.71.49:6380")


def find_all_notes(wiki_dir: Path) -> dict[str, Path]:
    """Map note names to file paths."""
    notes = {}
    for f in wiki_dir.rglob("*.md"):
        if f.name.startswith("_") or f.name.startswith("."):
            continue
        notes[f.stem] = f
    return notes


def extract_wikilinks(filepath: Path) -> list[str]:
    """Extract all [[wikilink]] targets from a file."""
    content = filepath.read_text(encoding="utf-8")
    return re.findall(r'\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]', content)


def parse_frontmatter_simple(filepath: Path) -> dict:
    """Extract YAML frontmatter (simple parser)."""
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
            fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm


def check_broken_wikilinks(wiki_dir: Path, all_notes: dict) -> list[dict]:
    """Find wikilinks pointing to non-existent notes."""
    issues = []
    for name, filepath in all_notes.items():
        links = extract_wikilinks(filepath)
        for link in links:
            target = link.split("#")[0].strip()
            if target and target not in all_notes:
                issues.append({
                    "check": "broken_wikilink",
                    "file": str(filepath.relative_to(VAULT_ROOT)),
                    "target": target,
                })
    return issues


def check_orphan_notes(wiki_dir: Path, all_notes: dict) -> list[dict]:
    """Find notes with no inbound wikilinks."""
    inbound = defaultdict(int)
    for name, filepath in all_notes.items():
        links = extract_wikilinks(filepath)
        for link in links:
            target = link.split("#")[0].strip()
            if target in all_notes:
                inbound[target] += 1

    issues = []
    for name in all_notes:
        if name not in inbound and not name.startswith("MOC-") and name != "hub":
            issues.append({
                "check": "orphan_note",
                "file": str(all_notes[name].relative_to(VAULT_ROOT)),
                "inbound_links": 0,
            })
    return issues


def check_stale_claims(wiki_dir: Path, all_notes: dict) -> list[dict]:
    """Find notes older than 18 months without update."""
    issues = []
    cutoff = datetime.now() - timedelta(days=540)
    for name, filepath in all_notes.items():
        fm = parse_frontmatter_simple(filepath)
        date_str = fm.get("date", "")
        if date_str:
            try:
                note_date = datetime.strptime(date_str, "%Y-%m-%d")
                if note_date < cutoff:
                    issues.append({
                        "check": "stale_claim",
                        "file": str(filepath.relative_to(VAULT_ROOT)),
                        "date": date_str,
                        "age_days": (datetime.now() - note_date).days,
                    })
            except ValueError:
                pass
    return issues


def check_ficha_rag_sync(wiki_dir: Path, all_notes: dict) -> list[dict]:
    """Find fichas whose RAG collection may be deleted."""
    import urllib.request
    issues = []
    fichas = {n: p for n, p in all_notes.items()
              if parse_frontmatter_simple(p).get("type") == "ficha"}
    if not fichas:
        return issues

    try:
        req = urllib.request.Request(f"{KNOWLEDGE_API_URL}/health", method="GET")
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        return [{"check": "ficha_rag_sync", "error": "Knowledge API unavailable"}]

    try:
        req = urllib.request.Request(f"{KNOWLEDGE_API_URL}/stats", method="GET")
        resp = urllib.request.urlopen(req, timeout=10)
        stats = json.loads(resp.read())
        available_collections = set(stats.get("collections", {}).keys())
    except Exception:
        return []

    for name, filepath in fichas.items():
        fm = parse_frontmatter_simple(filepath)
        collection = fm.get("source_collection", "")
        if collection and collection not in available_collections:
            issues.append({
                "check": "ficha_rag_desync",
                "file": str(filepath.relative_to(VAULT_ROOT)),
                "collection": collection,
            })
    return issues


def run_lint(output_json: bool = False) -> dict:
    """Run all lint checks and return report."""
    wiki_dir = VAULT_ROOT / "A.DIVA" / "wiki"
    all_notes = find_all_notes(wiki_dir)

    report = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "vault": str(VAULT_ROOT),
        "total_notes": len(all_notes),
        "checks": {},
    }

    broken = check_broken_wikilinks(wiki_dir, all_notes)
    report["checks"]["broken_wikilinks"] = {"count": len(broken), "issues": broken}

    orphans = check_orphan_notes(wiki_dir, all_notes)
    report["checks"]["orphan_notes"] = {"count": len(orphans), "issues": orphans}

    stale = check_stale_claims(wiki_dir, all_notes)
    report["checks"]["stale_claims"] = {"count": len(stale), "issues": stale}

    rag_sync = check_ficha_rag_sync(wiki_dir, all_notes)
    report["checks"]["ficha_rag_sync"] = {"count": len(rag_sync), "issues": rag_sync}

    if output_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Lint Report — {report['date']}")
        print(f"Notes scanned: {report['total_notes']}")
        for check_name, data in report["checks"].items():
            print(f"  {check_name}: {data['count']} issues")
            for issue in data["issues"][:5]:
                print(f"    - {issue}")

    return report


if __name__ == "__main__":
    use_json = "--json" in sys.argv
    run_lint(use_json)
