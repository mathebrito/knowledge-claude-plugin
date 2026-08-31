"""End-to-end contract test for the local BioRedox MCP stdio process."""

from __future__ import annotations

import base64
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from nostr_sdk import Event


PLUGIN_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PLUGIN_ROOT))


class SignedApiHandler(BaseHTTPRequestHandler):
    calls: list[dict] = []
    expected_pubkey: str = ""
    base_url: str = ""

    def log_message(self, format, *args):  # noqa: A003 - stdlib API name
        pass

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0"))
        return self.rfile.read(length) if length else b""

    def _authenticate(self, body: bytes) -> None:
        scheme, token = self.headers["Authorization"].split(" ", 1)
        assert scheme == "Nostr"
        event = Event.from_json(base64.b64decode(token).decode())
        assert event.verify()
        assert event.kind().as_u16() == 27235
        assert event.author().to_hex() == self.expected_pubkey
        data = json.loads(event.as_json())
        tags = {tag[0]: tag[1] for tag in data["tags"]}
        assert tags["u"] == f"{self.base_url}{self.path}"
        assert tags["method"] == self.command
        if body:
            assert tags["payload"] == hashlib.sha256(body).hexdigest()

    def _respond(self, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802 - stdlib API name
        body = self._read_body()
        self._authenticate(body)
        self.calls.append({"method": "GET", "path": self.path, "body": body})
        if self.path.startswith("/v1/documents/doc-1"):
            self._respond(
                {
                    "id": "doc-1",
                    "title": "Source",
                    "collection": "nanolime",
                    "language": "en",
                    "summary": "Summary",
                    "key_findings": ["Finding"],
                }
            )
        elif self.path.startswith("/v1/documents"):
            assert "collection=" not in self.path
            self._respond(
                {
                    "documents": [
                        {
                            "id": "doc-1",
                            "title": "Source",
                            "collection": "nanolime",
                            "status": "completed",
                        }
                    ],
                    "total": 1,
                }
            )
        elif self.path == "/v1/health":
            self._respond(
                {
                    "status": "degraded",
                    "qdrant": False,
                    "models_loaded": True,
                    "models_lazy": True,
                }
            )
        else:
            self.send_error(404)

    def do_POST(self):  # noqa: N802 - stdlib API name
        body = self._read_body()
        self._authenticate(body)
        self.calls.append(
            {
                "method": "POST",
                "path": self.path,
                "body": body,
                "filename": self.headers.get("X-Filename"),
            }
        )
        if self.path == "/v1/search":
            request = json.loads(body)
            assert "collections" not in request
            self._respond(
                {
                    "query": request["query"],
                    "results": [],
                    "collections_searched": ["nanolime"],
                }
            )
        elif self.path == "/v1/upload":
            assert body == b"venture source"
            assert self.headers["X-Filename"] == "source.txt"
            self._respond(
                {
                    "document_id": "doc-1",
                    "status": "completed",
                    "message": "Ingested source.txt",
                    "collection": "nanolime",
                    "chunks_stored": 1,
                }
            )
        else:
            self.send_error(404)


@pytest.fixture
def signed_api():
    SignedApiHandler.calls = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), SignedApiHandler)
    SignedApiHandler.base_url = f"http://127.0.0.1:{server.server_port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _rpc(process: subprocess.Popen, message: dict) -> dict:
    assert process.stdin is not None
    assert process.stdout is not None
    process.stdin.write(json.dumps(message) + "\n")
    process.stdin.flush()
    response = process.stdout.readline()
    assert response, "MCP process closed before replying"
    return json.loads(response)


def test_stdio_process_lists_and_executes_five_signed_tools(
    tmp_path: Path, signed_api
):
    from nostr_sdk import Keys

    keys = Keys.generate()
    SignedApiHandler.expected_pubkey = keys.public_key().to_hex()
    source = tmp_path / "source.txt"
    source.write_bytes(b"venture source")

    key_read_fd, key_write_fd = os.pipe()
    os.write(key_write_fd, keys.secret_key().to_bech32().encode())
    os.close(key_write_fd)

    environment = os.environ.copy()
    environment.update(
        {
            "KNOWLEDGE_API_URL": SignedApiHandler.base_url,
            "KNOWLEDGE_UPLOAD_ROOT": str(tmp_path),
            "BIOREDOX_TEST_NSEC_FD": str(key_read_fd),
        }
    )
    process = subprocess.Popen(
        [sys.executable, "mcp/tests/stdio_test_runner.py"],
        cwd=PLUGIN_ROOT,
        env=environment,
        pass_fds=(key_read_fd,),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    os.close(key_read_fd)
    try:
        initialized = _rpc(
            process,
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert initialized["result"]["serverInfo"]["name"] == "bioredox-knowledge"

        listed = _rpc(
            process,
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        tools = listed["result"]["tools"]
        assert {tool["name"] for tool in tools} == {
            "knowledge_search",
            "knowledge_ingest",
            "knowledge_documents",
            "knowledge_summary",
            "knowledge_health",
        }
        assert all("collection" not in tool["inputSchema"]["properties"] for tool in tools)
        assert all("collections" not in tool["inputSchema"]["properties"] for tool in tools)

        calls = [
            ("knowledge_search", {"query": "jarosite"}),
            ("knowledge_documents", {"collection": "matheus"}),
            ("knowledge_summary", {"document_id": "doc-1"}),
            ("knowledge_health", {}),
            ("knowledge_ingest", {"file_paths": [str(source)]}),
        ]
        for request_id, (name, arguments) in enumerate(calls, start=3):
            response = _rpc(
                process,
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments},
                },
            )
            assert response["result"].get("isError") is not True, response

        assert len(SignedApiHandler.calls) == 5
        assert {call["path"].split("?", 1)[0] for call in SignedApiHandler.calls} == {
            "/v1/search",
            "/v1/documents",
            "/v1/documents/doc-1",
            "/v1/health",
            "/v1/upload",
        }
    finally:
        if process.stdin:
            process.stdin.close()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=3)

    assert process.stderr is not None
    stderr = process.stderr.read()
    assert keys.secret_key().to_bech32() not in stderr


def test_incomplete_ingestion_becomes_an_mcp_error(tmp_path: Path, monkeypatch):
    from mcp import server

    source = tmp_path / "source.txt"
    source.write_bytes(b"venture source")

    async def incomplete_request(*args, **kwargs):
        return httpx.Response(
            200,
            json={
                "document_id": "doc-1",
                "status": "processing",
                "collection": "nanolime",
                "chunks_stored": 0,
            },
            request=httpx.Request("POST", "http://knowledge.test/v1/upload"),
        )

    import httpx

    monkeypatch.setattr(server, "_signed_request", incomplete_request)
    monkeypatch.setattr(server, "UPLOAD_ROOT", tmp_path)
    with pytest.raises(server.ToolExecutionError, match="did not complete"):
        asyncio.run(server.tool_ingest(object(), {"file_paths": [str(source)]}))


def test_ingestion_rejects_a_path_outside_the_upload_root(tmp_path: Path, monkeypatch):
    from mcp import server

    upload_root = tmp_path / "allowed"
    upload_root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"private material")
    monkeypatch.setattr(server, "UPLOAD_ROOT", upload_root)

    result = asyncio.run(server._ingest_one(object(), str(outside)))

    assert result["status"] == "error"
    assert "inside" in result["error"]


def test_ingestion_rejects_an_oversize_file_before_reading(tmp_path: Path, monkeypatch):
    from mcp import server

    source = tmp_path / "source.txt"
    source.write_bytes(b"too large")
    monkeypatch.setattr(server, "UPLOAD_ROOT", tmp_path)
    monkeypatch.setattr(server, "MAX_UPLOAD_BYTES", 1)

    result = asyncio.run(server._ingest_one(object(), str(source)))

    assert result["status"] == "error"
    assert "50 MiB" in result["error"]
