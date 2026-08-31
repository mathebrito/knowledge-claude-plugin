#!/usr/bin/env python3
"""
Knowledge Engine MCP Server — 5 tools for remote Knowledge API access.

Runs as a stdio subprocess spawned by Claude Code. Wraps the Knowledge API
at the Mac Mini (Tailscale) with tools for search, ingest, documents, summary,
and health check. File ingestion uses rsync over SSH to transfer files from
MacBook to Mac Mini before triggering the API.

Based on: tejo-infra/knowledge/mcp_claude_desktop.py
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import httpx

API_URL = os.getenv("KNOWLEDGE_API_URL", "http://100.97.71.49:6380")
TIMEOUT = 120.0
VAULT_ROOT = Path(os.getenv("VAULT_ROOT", Path.home() / "second-brain"))

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("knowledge-engine.mcp")

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

VALID_COLLECTIONS = ["matheus", "milena", "arthur", "shared"]

TOOLS = [
    {
        "name": "knowledge_search",
        "description": (
            "Search the RAG knowledge base (Qdrant vector store) for relevant passages. "
            "IMPORTANT: Before calling this tool, always search the vault FIRST using "
            "qmd search on the second-brain collection. Only use this tool when the vault "
            "qmd score is < 72% or when vault results are insufficient. This tool searches "
            "raw ingested documents (PDFs, articles), not the compiled wiki."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (Portuguese or English)"},
                "top_k": {"type": "integer", "description": "Max results (1-20)", "default": 5},
                "collections": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": f"Filter by collections: {', '.join(VALID_COLLECTIONS)}. Omit to search all.",
                },
                "document_id": {"type": "string", "description": "Scope to one document"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"},
                "language": {"type": "string", "description": "Filter by language code (pt, en, es, fr)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "knowledge_ingest",
        "description": (
            "Ingest one or more local files into the knowledge base. Files are uploaded "
            "directly to the Knowledge API via multipart HTTP, then ingested into Qdrant + MongoDB. "
            "Use this when the user uploads documents (PDF, markdown, text, etc.) and wants "
            "them added to their knowledge base."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of absolute local file paths to ingest.",
                },
                "collection": {
                    "type": "string",
                    "description": (
                        f"Target collection. Options: {', '.join(VALID_COLLECTIONS)}. "
                        "Default: 'matheus'."
                    ),
                },
            },
            "required": ["file_paths"],
        },
    },
    {
        "name": "knowledge_documents",
        "description": "List documents in the knowledge base with metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "collection": {"type": "string", "description": f"Filter: {', '.join(VALID_COLLECTIONS)}"},
                "status": {"type": "string", "description": "Filter: processing, completed, failed"},
                "language": {"type": "string", "description": "ISO 639-1 language code"},
                "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
            },
        },
    },
    {
        "name": "knowledge_summary",
        "description": "Get the AI-generated summary, key findings, and PARA classification for a specific document.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "Document ID from knowledge_documents"},
            },
            "required": ["document_id"],
        },
    },
    {
        "name": "knowledge_health",
        "description": "Check Knowledge API and Qdrant status. Use to verify Tailscale connectivity.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def tool_search(client: httpx.AsyncClient, args: dict) -> str:
    """Semantic search across RAG collections."""
    collections = args.get("collections")
    if isinstance(collections, str):
        try:
            collections = json.loads(collections)
        except json.JSONDecodeError:
            collections = [collections]

    payload = {"query": args["query"], "top_k": args.get("top_k", 5)}
    for key in ("document_id", "tags", "language"):
        if args.get(key):
            payload[key] = args[key]
    if collections:
        payload["collections"] = collections

    resp = await client.post(f"{API_URL}/search", json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", [])

    if not results:
        return f'No results found for "{args["query"]}".'

    lines = [f'Found {len(results)} results for "{args["query"]}":\n']
    for i, r in enumerate(results, 1):
        score_pct = int(r["score"] * 100)
        lines.append(
            f'{i}. [Score: {score_pct}%] {r["source_file"]} '
            f'(chunk {r["chunk_index"]}, {r.get("collection", "")})'
        )
        text_preview = r.get("content", r.get("text", ""))[:300]
        lines.append(f"   {text_preview}...")
        lines.append("")
    return "\n".join(lines)


async def _ingest_one(client: httpx.AsyncClient, local_path: str, collection: str) -> dict:
    """Upload a local file to the Knowledge API via multipart/form-data.

    Uses the POST /api/v1/upload endpoint added in the rag_pipeline_gridfs_removal
    release (2026-04-11). No rsync or SSH needed — direct HTTP upload over Tailscale.
    """
    if not os.path.isfile(local_path):
        return {"file": local_path, "status": "error", "error": f"Local file not found: {local_path}"}

    filename = os.path.basename(local_path)

    try:
        with open(local_path, "rb") as f:
            resp = await client.post(
                f"{API_URL}/api/v1/upload",
                files={"file": (filename, f)},
                data={"collection": collection},
                timeout=300,  # OCR + embedding can take minutes
            )
        resp.raise_for_status()
        data = resp.json()
        return {
            "file": local_path,
            "status": "ok",
            "document_id": data.get("document_id"),
            "collection": data.get("collection", collection),
            "chunks": data.get("chunks_stored", 0),
        }
    except httpx.HTTPStatusError as e:
        detail = ""
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = e.response.text[:200]
        return {"file": local_path, "status": "error", "error": detail}


def _sync_vault() -> str | None:
    """Pull latest vault changes from remote (ficha generated on Mac Mini).

    Returns a status message, or None if vault is not a git repo.
    """
    if not (VAULT_ROOT / ".git").is_dir():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(VAULT_ROOT), "pull", "--rebase", "--autostash"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            # Check if anything was pulled (vs "Already up to date.")
            if "Already up to date" not in result.stdout:
                logger.info("Vault synced: %s", result.stdout.strip())
                return "vault synced"
            return None
        logger.warning("Vault pull failed: %s", result.stderr.strip())
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


async def tool_ingest(client: httpx.AsyncClient, args: dict) -> str:
    """Ingest files via Knowledge API and sync vault."""
    file_paths = args.get("file_paths", [])
    collection = args.get("collection") or "matheus"

    # Handle LLM serialization quirks
    if isinstance(file_paths, str):
        file_paths = file_paths.strip()
        if file_paths.startswith("["):
            try:
                file_paths = json.loads(file_paths.replace("'", '"'))
            except json.JSONDecodeError:
                file_paths = [file_paths.strip("[]'\"")]
        else:
            file_paths = [file_paths]

    if not file_paths:
        return "ERROR: No file paths provided."
    if collection not in VALID_COLLECTIONS:
        return f"ERROR: Invalid collection '{collection}'. Valid: {', '.join(VALID_COLLECTIONS)}"

    logger.info("Ingesting %d file(s) into '%s'", len(file_paths), collection)

    # Ingest files concurrently (max 4)
    sem = asyncio.Semaphore(4)

    async def bounded_ingest(path):
        async with sem:
            return await _ingest_one(client, path, collection)

    results = await asyncio.gather(*(bounded_ingest(p) for p in file_paths))

    # Format response
    ok = [r for r in results if r["status"] == "ok"]
    errors = [r for r in results if r["status"] == "error"]

    lines = []
    if ok:
        lines.append(f"Ingested {len(ok)} file(s) into '{collection}':")
        for r in ok:
            fname = os.path.basename(r["file"])
            doc_id = f" [ID: {r['document_id']}]" if r.get("document_id") else ""
            lines.append(f"  OK  {fname} ({r['chunks']} chunks){doc_id}")

        # Post-ingest: sync vault to pull Layer 1 fichas generated on Mac Mini.
        # The API writes fichas to the vault on the Mac Mini, commits via
        # vault-commit.sh (launchd, every 10min), and pushes to GitHub.
        # We trigger an immediate pull so the ficha is available locally.
        sync_status = await asyncio.get_running_loop().run_in_executor(None, _sync_vault)
        if sync_status:
            lines.append(f"\n  Vault: {sync_status} (Layer 1 fichas pulled)")

    if errors:
        lines.append(f"\nFailed {len(errors)} file(s):")
        for r in errors:
            fname = os.path.basename(r["file"])
            lines.append(f"  ERR {fname}: {r['error']}")
    return "\n".join(lines)


async def tool_documents(client: httpx.AsyncClient, args: dict) -> str:
    """List documents with optional filters."""
    params = {k: v for k, v in args.items() if v is not None}
    resp = await client.get(f"{API_URL}/api/v1/documents", params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    docs = data.get("documents", [])

    if not docs:
        return "No documents found."

    lines = [f"{len(docs)} documents found:\n"]
    for i, d in enumerate(docs, 1):
        lang = d.get("language") or "?"
        pages = d.get("page_count") or "?"
        chunks = d.get("chunk_count", 0)
        status = d.get("status", "?")
        coll = d.get("collection", "?")
        lines.append(
            f'{i}. {d["title"]} ({lang}) -- {pages} pages, '
            f"{chunks} chunks -- {status} [{coll}]"
        )
        lines.append(f'   ID: {d["id"]}')
        lines.append("")
    return "\n".join(lines)


async def tool_summary(client: httpx.AsyncClient, args: dict) -> str:
    """Get AI-generated summary for a document."""
    doc_id = args["document_id"]
    resp = await client.get(f"{API_URL}/api/v1/documents/{doc_id}", timeout=TIMEOUT)
    resp.raise_for_status()
    d = resp.json()

    lang_map = {"pt": "Portugues", "en": "English", "es": "Espanol", "fr": "Francais"}
    lang_display = lang_map.get(d.get("language", ""), d.get("language", "?"))

    lines = [
        f'# {d["title"]}',
        f"Language: {lang_display} | Pages: {d.get('page_count', '?')} | "
        f"Chunks: {d.get('chunk_count', 0)}",
        "",
    ]

    if d.get("summary"):
        lines.extend(["## Summary", d["summary"], ""])
    else:
        lines.extend(["## Summary", "(No summary available)", ""])

    if d.get("key_findings"):
        lines.append("## Key Findings")
        for finding in d["key_findings"]:
            lines.append(f"- {finding}")
        lines.append("")

    if d.get("suggested_para"):
        lines.extend([
            "## PARA Classification",
            f'Suggested: {d["suggested_para"]}',
            f'Reason: {d.get("suggested_para_reason", "")}',
        ])

    return "\n".join(lines)


async def tool_health(client: httpx.AsyncClient, args: dict) -> str:
    """Check Knowledge API and Qdrant status."""
    lines = []

    # Health check
    try:
        resp = await client.get(f"{API_URL}/health", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        lines.append(f"Knowledge API: {data.get('status', 'unknown')}")
        lines.append(
            f"Qdrant: {'connected' if data.get('qdrant') else 'disconnected'}"
        )
        lines.append(
            f"Models loaded: {'yes' if data.get('models_loaded') else 'no'}"
        )
    except httpx.ConnectError:
        return (
            f"Knowledge API not reachable at {API_URL}.\n"
            "Check: (1) Tailscale is connected (`tailscale status`), "
            "(2) Knowledge API is running on Mac Mini."
        )
    except httpx.TimeoutException:
        return f"Knowledge API timed out at {API_URL}. API may be starting up."

    # Stats
    try:
        resp = await client.get(f"{API_URL}/stats", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        colls = data.get("collections", {})
        if colls:
            lines.append("\nCollections:")
            for name, stats in colls.items():
                lines.append(
                    f"  {name}: {stats.get('points_count', 0)} vectors "
                    f"({stats.get('status', '?')})"
                )
    except Exception:
        pass  # Stats are optional

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------

TOOL_MAP = {
    "knowledge_search": tool_search,
    "knowledge_ingest": tool_ingest,
    "knowledge_documents": tool_documents,
    "knowledge_summary": tool_summary,
    "knowledge_health": tool_health,
}


# ---------------------------------------------------------------------------
# MCP Protocol (JSON-RPC over stdio)
# ---------------------------------------------------------------------------

def read_message():
    line = sys.stdin.readline()
    if not line:
        return None
    return json.loads(line)


def write_message(msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def respond(msg_id, result):
    write_message({"jsonrpc": "2.0", "id": msg_id, "result": result})


def respond_error(msg_id, code, message):
    write_message(
        {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}
    )


async def main():
    logger.info("Knowledge Engine MCP server starting (API: %s)", API_URL)

    async with httpx.AsyncClient() as client:
        while True:
            msg = await asyncio.to_thread(read_message)
            if msg is None:
                break

            method = msg.get("method")
            msg_id = msg.get("id")
            params = msg.get("params", {})

            if method == "initialize":
                respond(msg_id, {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "knowledge-engine", "version": "1.0.0"},
                })
            elif method == "notifications/initialized":
                pass
            elif method == "tools/list":
                respond(msg_id, {"tools": TOOLS})
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                handler = TOOL_MAP.get(tool_name)

                if not handler:
                    respond(msg_id, {
                        "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                        "isError": True,
                    })
                    continue

                try:
                    result_text = await handler(client, tool_args)
                    respond(msg_id, {
                        "content": [{"type": "text", "text": result_text}],
                    })
                except httpx.ConnectError:
                    respond(msg_id, {
                        "content": [{"type": "text", "text": (
                            f"Knowledge API not reachable at {API_URL}.\n"
                            "Check: (1) Tailscale is connected (`tailscale status`), "
                            "(2) Knowledge API is running on Mac Mini "
                            "(`ssh tejo 'curl -s localhost:6380/health'`)"
                        )}],
                        "isError": True,
                    })
                except httpx.HTTPStatusError as e:
                    detail = e.response.text[:200]
                    respond(msg_id, {
                        "content": [{"type": "text", "text": f"API error ({e.response.status_code}): {detail}"}],
                        "isError": True,
                    })
                except httpx.TimeoutException:
                    respond(msg_id, {
                        "content": [{"type": "text", "text": "Request timed out. The pipeline may still be processing."}],
                        "isError": True,
                    })
            elif method == "ping":
                respond(msg_id, {})


if __name__ == "__main__":
    asyncio.run(main())
