#!/usr/bin/env python3
"""Local BioRedox Knowledge MCP client with NIP-98 request signing."""

from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
from pathlib import Path
import sys

import httpx

try:
    from .nip98 import API_URL, LocalIdentityError, signed_request as _signed_request
except ImportError:
    from nip98 import API_URL, LocalIdentityError, signed_request as _signed_request


TIMEOUT = 120.0

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("bioredox-knowledge.mcp")


TOOLS = [
    {
        "name": "knowledge_search",
        "description": "Search BioRedox source material in the isolated nanolime knowledge collection.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
                "document_id": {"type": "string", "description": "Scope to one document"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "language": {"type": "string", "description": "Language code such as pt or en"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "knowledge_ingest",
        "description": "Upload lawful, venture-relevant, sanitized local source files to BioRedox knowledge.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Absolute local file paths selected by the user",
                }
            },
            "required": ["file_paths"],
        },
    },
    {
        "name": "knowledge_documents",
        "description": "List documents in the isolated BioRedox knowledge collection.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "processing, completed, or failed"},
                "language": {"type": "string", "description": "Language code such as pt or en"},
                "tags": {"type": "string", "description": "Comma-separated tags"},
            },
        },
    },
    {
        "name": "knowledge_summary",
        "description": "Read the summary and findings for one BioRedox knowledge document.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "Document ID"},
            },
            "required": ["document_id"],
        },
    },
    {
        "name": "knowledge_health",
        "description": "Check the private BioRedox Knowledge API and Qdrant state.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


class ToolExecutionError(RuntimeError):
    """A tool finished without a completed Knowledge operation."""


async def tool_search(client: httpx.AsyncClient, args: dict) -> str:
    payload = {"query": args["query"], "top_k": args.get("top_k", 5)}
    for key in ("document_id", "tags", "language"):
        if args.get(key):
            payload[key] = args[key]
    response = await _signed_request(client, "POST", "/v1/search", json_body=payload)
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results:
        return f'No results found for "{args["query"]}".'

    lines = [f'Found {len(results)} results for "{args["query"]}":', ""]
    for index, result in enumerate(results, 1):
        score = int(result.get("score", 0) * 100)
        lines.append(f'{index}. [Score: {score}%] {result.get("source_file", "unknown")}')
        lines.append(f'   {result.get("content", result.get("text", ""))[:300]}')
    return "\n".join(lines)


async def _ingest_one(client: httpx.AsyncClient, local_path: str) -> dict:
    path = Path(local_path).expanduser()
    if not path.is_file():
        return {"file": local_path, "status": "error", "error": "Local file not found"}
    file_bytes = path.read_bytes()
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    try:
        response = await _signed_request(
            client,
            "POST",
            "/v1/upload",
            content=file_bytes,
            headers={"Content-Type": content_type, "X-Filename": path.name},
            timeout=300,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "completed" or data.get("collection") != "nanolime":
            return {
                "file": local_path,
                "status": "error",
                "error": "Knowledge ingestion did not complete",
            }
        return {
            "file": local_path,
            "status": "ok",
            "document_id": data.get("document_id"),
            "chunks": data.get("chunks_stored", 0),
        }
    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json().get("detail", "Upload failed")
        except Exception:
            detail = "Upload failed"
        return {"file": local_path, "status": "error", "error": detail}


async def tool_ingest(client: httpx.AsyncClient, args: dict) -> str:
    file_paths = args.get("file_paths", [])
    if isinstance(file_paths, str):
        file_paths = [file_paths]
    if not file_paths:
        raise ToolExecutionError("No file paths provided")

    semaphore = asyncio.Semaphore(4)

    async def bounded(path: str) -> dict:
        async with semaphore:
            return await _ingest_one(client, path)

    results = await asyncio.gather(*(bounded(path) for path in file_paths))
    lines = []
    for result in results:
        name = Path(result["file"]).name
        if result["status"] == "ok":
            document_id = f' [ID: {result["document_id"]}]' if result.get("document_id") else ""
            lines.append(f'OK {name} ({result["chunks"]} chunks){document_id}')
        else:
            lines.append(f'ERROR {name}: {result["error"]}')
    output = "\n".join(lines)
    if any(result["status"] == "error" for result in results):
        raise ToolExecutionError(output)
    return output


async def tool_documents(client: httpx.AsyncClient, args: dict) -> str:
    params = {
        key: args[key]
        for key in ("status", "language", "tags")
        if args.get(key) is not None
    }
    response = await _signed_request(client, "GET", "/v1/documents", params=params)
    response.raise_for_status()
    documents = response.json().get("documents", [])
    if not documents:
        return "No documents found."
    lines = [f"{len(documents)} documents found:", ""]
    for index, document in enumerate(documents, 1):
        lines.append(
            f'{index}. {document["title"]} -- {document.get("status", "?")} '
            f'[ID: {document["id"]}]'
        )
    return "\n".join(lines)


async def tool_summary(client: httpx.AsyncClient, args: dict) -> str:
    document_id = args["document_id"]
    response = await _signed_request(client, "GET", f"/v1/documents/{document_id}")
    response.raise_for_status()
    document = response.json()
    lines = [f'# {document["title"]}', ""]
    lines.extend(["## Summary", document.get("summary") or "(No summary available)", ""])
    findings = document.get("key_findings") or []
    if findings:
        lines.append("## Key Findings")
        lines.extend(f"- {finding}" for finding in findings)
    return "\n".join(lines)


async def tool_health(client: httpx.AsyncClient, args: dict) -> str:
    response = await _signed_request(client, "GET", "/v1/health", timeout=10)
    response.raise_for_status()
    data = response.json()
    return "\n".join(
        [
            f'Knowledge API: {data.get("status", "unknown")}',
            f'Qdrant: {"connected" if data.get("qdrant") else "disconnected"}',
            f'Models loaded: {"yes" if data.get("models_loaded") else "no"}',
        ]
    )


TOOL_MAP = {
    "knowledge_search": tool_search,
    "knowledge_ingest": tool_ingest,
    "knowledge_documents": tool_documents,
    "knowledge_summary": tool_summary,
    "knowledge_health": tool_health,
}


def read_message():
    line = sys.stdin.readline()
    return json.loads(line) if line else None


def write_message(message: dict) -> None:
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def respond(message_id, result: dict) -> None:
    write_message({"jsonrpc": "2.0", "id": message_id, "result": result})


async def main() -> None:
    logger.info("BioRedox Knowledge MCP starting (API: %s)", API_URL)
    async with httpx.AsyncClient() as client:
        while True:
            message = await asyncio.to_thread(read_message)
            if message is None:
                break
            method = message.get("method")
            message_id = message.get("id")
            params = message.get("params", {})

            if method == "initialize":
                respond(
                    message_id,
                    {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "bioredox-knowledge", "version": "1.0.0"},
                    },
                )
            elif method == "notifications/initialized":
                continue
            elif method == "tools/list":
                respond(message_id, {"tools": TOOLS})
            elif method == "ping":
                respond(message_id, {})
            elif method == "tools/call":
                name = params.get("name")
                handler = TOOL_MAP.get(name)
                if handler is None:
                    respond(
                        message_id,
                        {
                            "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
                            "isError": True,
                        },
                    )
                    continue
                try:
                    text = await handler(client, params.get("arguments", {}))
                    respond(message_id, {"content": [{"type": "text", "text": text}]})
                except LocalIdentityError as exc:
                    respond(
                        message_id,
                        {
                            "content": [{"type": "text", "text": str(exc)}],
                            "isError": True,
                        },
                    )
                except ToolExecutionError as exc:
                    respond(
                        message_id,
                        {
                            "content": [{"type": "text", "text": str(exc)}],
                            "isError": True,
                        },
                    )
                except httpx.HTTPStatusError as exc:
                    respond(
                        message_id,
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Knowledge API error ({exc.response.status_code})",
                                }
                            ],
                            "isError": True,
                        },
                    )
                except (httpx.ConnectError, httpx.TimeoutException):
                    respond(
                        message_id,
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Knowledge API is not reachable at {API_URL}",
                                }
                            ],
                            "isError": True,
                        },
                    )


if __name__ == "__main__":
    asyncio.run(main())
