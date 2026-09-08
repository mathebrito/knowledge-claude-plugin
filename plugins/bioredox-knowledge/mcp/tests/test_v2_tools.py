"""Fixture-driven tests for the Knowledge v2 tools. No live calls."""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
import sys

import httpx
import pytest
from nostr_sdk import Keys


PLUGIN_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PLUGIN_ROOT))

from mcp import contract, nip98, server  # noqa: E402

LOAD_LOCAL_KEYS = nip98._load_local_keys


V2_FIXTURES = contract.V2 / "fixtures"
# The sealed v2 release declares no error-response schema. v2.1 proposes one and freezes
# the sanitized bodies below; they are the reference shapes here, not a sealed contract.
NEGATIVE_FIXTURES = contract.V2.with_name("v2.1") / "fixtures" / "negative"

V1_TOOL_NAMES = (
    "knowledge_search",
    "knowledge_ingest",
    "knowledge_documents",
    "knowledge_summary",
    "knowledge_health",
)
V1_SNAPSHOT = Path(__file__).with_name("v1-tools.frozen.json")


def load(path: Path) -> dict:
    return json.loads(path.read_text())


@pytest.fixture(autouse=True)
def local_signing_key(monkeypatch):
    keys = Keys.generate()
    monkeypatch.setattr(nip98, "_load_local_keys", lambda: keys)
    server._JOBS_BY_RECEIPT.clear()
    yield keys
    server._JOBS_BY_RECEIPT.clear()


def transport(handler):
    """An httpx client whose every request is answered in-process."""
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def responder(body: dict, status_code: int = 200):
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(status_code, json=body)

    return handle, calls


def run(coroutine):
    return asyncio.run(coroutine)


async def call(tool, handler, args: dict) -> str:
    async with transport(handler) as client:
        return await tool(client, args)


# --- G1: the sealed contract copy and the v1 surface are both frozen ------------------


def test_the_sealed_contract_copy_matches_the_sealed_manifest():
    assert contract.manifest_drift() == []


def test_the_declared_v1_tools_are_byte_identical_to_the_frozen_snapshot():
    declared = [tool for tool in server.TOOLS if tool["name"] in V1_TOOL_NAMES]
    assert len(declared) == len(V1_TOOL_NAMES)
    # The ingest description embeds the machine's upload root, which is not part of the
    # contract; everything else must match the snapshot byte for byte.
    frozen = json.dumps(declared, indent=2, sort_keys=True).replace(
        str(server.UPLOAD_ROOT), "{UPLOAD_ROOT}"
    )
    assert frozen == V1_SNAPSHOT.read_text()


# --- happy path from the sealed fixtures ----------------------------------------------


def test_ingest_async_sends_the_sealed_request_shape_and_reads_the_sealed_response(
    local_signing_key,
):
    sealed_request = load(V2_FIXTURES / "ingest-async-request.json")
    sealed_response = load(V2_FIXTURES / "ingest-async-response.json")
    receipt = load(V2_FIXTURES / "source-receipt.json")
    handler, calls = responder(sealed_response)

    text = run(
        call(
            server.tool_ingest_async,
            handler,
            {
                "source_receipt_id": receipt["receipt_id"],
                "source_sha256": receipt["file_sha256"],
                "upload_id": sealed_request["upload_id"],
            },
        )
    )

    assert sealed_response["job_id"] in text
    assert sealed_response["status_url"] in text

    (request,) = calls
    assert request.url.path == "/v2/knowledge_ingest_async"
    assert request.headers["Authorization"].startswith("Nostr ")
    sent = json.loads(request.content)

    # Everything outside `auth` is the sealed request fixture.
    payload = {key: value for key, value in sent.items() if key != "auth"}
    assert payload == {
        key: value for key, value in sealed_request.items() if key != "auth"
    }

    # The auth block is the local signing key's, not the fixture's placeholder principal.
    auth = sent["auth"]
    assert auth["principal_id"] == local_signing_key.public_key().to_hex()
    assert auth["principal_id"] != sealed_request["auth"]["principal_id"]
    assert auth["payload_sha256"] == hashlib.sha256(
        nip98.canonical_payload(payload)
    ).hexdigest()
    assert auth["expires_at"] - auth["created_at"] == nip98.V2_VALIDITY_SECONDS
    for field in ("method", "url", "payload_canonicalization", "collection"):
        assert auth[field] == sealed_request["auth"][field]


def test_canonical_payload_uses_rfc8785_number_and_unicode_rules():
    assert nip98.canonical_payload({"top_k": 1.0, "zero": -0.0, "text": "é"}) == (
        b'{"text":"\xc3\xa9","top_k":1,"zero":0}'
    )


def test_managed_service_identity_uses_one_private_mode_0600_file(tmp_path: Path):
    expected = Keys.generate()
    identity = tmp_path / "acervo.env"
    identity.write_text(
        "# existing managed service identity\n"
        f"export BUZZ_PRIVATE_KEY={expected.secret_key().to_bech32()}\n"
    )
    identity.chmod(0o600)

    loaded = nip98._load_managed_identity(str(identity))

    assert loaded.public_key().to_hex() == expected.public_key().to_hex()
    identity.chmod(0o640)
    with pytest.raises(nip98.LocalIdentityError, match="unavailable"):
        nip98._load_managed_identity(str(identity))


def test_explicit_managed_identity_bypasses_keychain(
    tmp_path: Path, monkeypatch
):
    expected = Keys.generate()
    identity = tmp_path / "acervo.env"
    identity.write_text(f"BUZZ_PRIVATE_KEY={expected.secret_key().to_bech32()}\n")
    identity.chmod(0o600)
    monkeypatch.setenv("KNOWLEDGE_NIP98_IDENTITY_FILE", str(identity))
    monkeypatch.setattr(
        nip98.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("keychain must not be read"),
    )

    assert LOAD_LOCAL_KEYS().public_key().to_hex() == expected.public_key().to_hex()


def test_default_identity_provider_remains_the_macos_keychain(monkeypatch):
    monkeypatch.delenv("KNOWLEDGE_NIP98_IDENTITY_FILE", raising=False)
    observed = {}

    def fake_run(argv, **kwargs):
        observed["argv"] = argv
        return __import__("subprocess").CompletedProcess(
            argv, 1, stdout="", stderr="missing"
        )

    monkeypatch.setattr(nip98.subprocess, "run", fake_run)
    with pytest.raises(nip98.LocalIdentityError):
        nip98._load_keychain_identity()
    assert observed["argv"][0] == "/usr/bin/security"


def test_ingest_status_reads_the_sealed_status_response():
    sealed_request = load(V2_FIXTURES / "ingest-status-request.json")
    sealed_response = load(V2_FIXTURES / "ingest-status-response.json")
    handler, calls = responder(sealed_response)

    text = run(call(server.tool_ingest_status, handler, {"job_id": sealed_request["job_id"]}))

    assert f'State: {sealed_response["job_state"]}' in text
    assert sealed_response["document_version"] in text
    assert "Timings (ms): PARSING=9, RECONCILING=2, VALIDATING=3" in text

    (request,) = calls
    assert request.url.path == "/v2/knowledge_ingest_status"
    sent = json.loads(request.content)
    assert {key: value for key, value in sent.items() if key != "auth"} == {
        key: value for key, value in sealed_request.items() if key != "auth"
    }


def test_a_replacement_carries_the_prior_document_id():
    sealed_request = load(V2_FIXTURES / "ingest-async-request.json")
    receipt = load(V2_FIXTURES / "source-receipt.json")
    prior = load(V2_FIXTURES / "ingest-async-response.json")["document_id"]
    handler, calls = responder(load(V2_FIXTURES / "ingest-async-response.json"))

    run(
        call(
            server.tool_ingest_async,
            handler,
            {
                "source_receipt_id": receipt["receipt_id"],
                "source_sha256": receipt["file_sha256"],
                "upload_id": sealed_request["upload_id"],
                "replace_document_id": prior,
            },
        )
    )

    assert json.loads(calls[0].content)["replace_document_id"] == prior


# --- idempotent submission -------------------------------------------------------------


def test_a_repeated_receipt_is_an_in_process_no_op():
    sealed_request = load(V2_FIXTURES / "ingest-async-request.json")
    sealed_response = load(V2_FIXTURES / "ingest-async-response.json")
    receipt = load(V2_FIXTURES / "source-receipt.json")
    handler, calls = responder(sealed_response)
    args = {
        "source_receipt_id": receipt["receipt_id"],
        "source_sha256": receipt["file_sha256"],
        "upload_id": sealed_request["upload_id"],
    }

    first = run(call(server.tool_ingest_async, handler, args))
    second = run(call(server.tool_ingest_async, handler, args))

    assert len(calls) == 1, "the repeat submission must not reach the gateway"
    assert sealed_response["job_id"] in first
    assert sealed_response["job_id"] in second
    assert "Already queued in this session" in second


# --- sealed negative shapes surfaced unchanged -----------------------------------------


@pytest.mark.parametrize(
    ("case", "tool", "fixture_name", "status_code"),
    [
        ("unknown job", "status", "not-found-unknown-document.json", 404),
        ("cross-principal job", "status", "not-found-foreign-document.json", 404),
        ("unauthorized receipt", "async", "not-found-foreign-document.json", 404),
        ("replayed event", "async", "replayed-event.json", 409),
        ("disallowed principal", "async", "disallowed-principal.json", 403),
        ("quota refused before action", "async", "quota-refused-before-action.json", 429),
        ("unknown document", "search", "not-found-unknown-document.json", 404),
        ("foreign document", "search", "not-found-foreign-document.json", 404),
    ],
)
def test_a_sanitized_refusal_reaches_the_caller_unchanged(
    case, tool, fixture_name, status_code
):
    sealed_request = load(V2_FIXTURES / "ingest-async-request.json")
    receipt = load(V2_FIXTURES / "source-receipt.json")
    refusal = load(NEGATIVE_FIXTURES / fixture_name)
    handler, calls = responder(refusal, status_code)

    if tool == "status":
        job_id = load(V2_FIXTURES / "ingest-status-request.json")["job_id"]
        coroutine = call(server.tool_ingest_status, handler, {"job_id": job_id})
    elif tool == "search":
        search_request = load(V2_FIXTURES / "search-v2-request.json")
        coroutine = call(
            server.tool_search_v2,
            handler,
            {
                "document_id": search_request["document_id"],
                "query": search_request["query"],
            },
        )
    else:
        coroutine = call(
            server.tool_ingest_async,
            handler,
            {
                "source_receipt_id": receipt["receipt_id"],
                "source_sha256": receipt["file_sha256"],
                "upload_id": sealed_request["upload_id"],
            },
        )

    with pytest.raises(server.ToolExecutionError) as failure:
        run(coroutine)

    assert str(failure.value) == refusal["message"], case
    assert server._JOBS_BY_RECEIPT == {}, "a refused submission must hold no job"


def test_the_two_sanitized_not_found_refusals_stay_indistinguishable():
    unknown = load(NEGATIVE_FIXTURES / "not-found-unknown-document.json")
    foreign = load(NEGATIVE_FIXTURES / "not-found-foreign-document.json")
    assert unknown == foreign


# --- contract violations ---------------------------------------------------------------


def test_a_response_missing_a_required_field_is_a_client_side_contract_violation():
    sealed_request = load(V2_FIXTURES / "ingest-async-request.json")
    receipt = load(V2_FIXTURES / "source-receipt.json")
    truncated = load(V2_FIXTURES / "ingest-async-response.json")
    del truncated["status_url"]
    handler, _ = responder(truncated)

    with pytest.raises(contract.ContractViolation) as failure:
        run(
            call(
                server.tool_ingest_async,
                handler,
                {
                    "source_receipt_id": receipt["receipt_id"],
                    "source_sha256": receipt["file_sha256"],
                    "upload_id": sealed_request["upload_id"],
                },
            )
        )

    assert "The Knowledge API response violates" in str(failure.value)
    assert "status_url" in str(failure.value)
    assert server._JOBS_BY_RECEIPT == {}, "a violating response must hold no job"


def test_a_status_response_with_an_unknown_job_state_is_a_contract_violation():
    invalid = load(V2_FIXTURES / "ingest-status-response.json")
    invalid["job_state"] = "IMPROVISED"
    handler, _ = responder(invalid)

    with pytest.raises(contract.ContractViolation, match="job_state fails enum"):
        run(call(server.tool_ingest_status, handler, {"job_id": "job_5gks1hqrrz4a8vkk0001"}))


def test_a_malformed_receipt_id_never_reaches_the_gateway():
    handler, calls = responder(load(V2_FIXTURES / "ingest-async-response.json"))

    with pytest.raises(contract.ContractViolation, match="The request violates"):
        run(
            call(
                server.tool_ingest_async,
                handler,
                {
                    "source_receipt_id": "not-a-receipt",
                    "source_sha256": "0" * 64,
                    "upload_id": "upl_bgrreviewedupload0001",
                },
            )
        )

    assert calls == []


def test_a_missing_required_argument_is_a_contract_violation_not_a_crash():
    handler, calls = responder(load(V2_FIXTURES / "ingest-status-response.json"))

    with pytest.raises(contract.ContractViolation, match="The request violates"):
        run(call(server.tool_ingest_status, handler, {}))

    assert calls == []


# --- principal safety -------------------------------------------------------------------


@pytest.mark.parametrize(
    "identity", ["principal_id", "principal", "auth", "collection", "collections"]
)
def test_a_caller_supplied_principal_or_collection_is_refused_before_any_request(identity):
    sealed_request = load(V2_FIXTURES / "ingest-async-request.json")
    receipt = load(V2_FIXTURES / "source-receipt.json")
    handler, calls = responder(load(V2_FIXTURES / "ingest-async-response.json"))
    args = {
        "source_receipt_id": receipt["receipt_id"],
        "source_sha256": receipt["file_sha256"],
        "upload_id": sealed_request["upload_id"],
        identity: sealed_request["auth"]["principal_id"],
    }

    with pytest.raises(server.ToolExecutionError, match="only identity"):
        run(call(server.tool_ingest_async, handler, args))
    with pytest.raises(server.ToolExecutionError, match="only identity"):
        run(call(server.tool_ingest_status, handler, {"job_id": "job_x", identity: "x"}))
    with pytest.raises(server.ToolExecutionError, match="only identity"):
        run(
            call(
                server.tool_search_v2,
                handler,
                {"document_id": "doc_x", "query": "x", identity: "x"},
            )
        )

    assert calls == []


def test_no_v2_tool_declares_a_principal_or_collection_input():
    for name in ("knowledge_ingest_async", "knowledge_ingest_status", "knowledge_search_v2"):
        schema = next(tool for tool in server.TOOLS if tool["name"] == name)["inputSchema"]
        assert schema["additionalProperties"] is False
        assert server.CALLER_FORBIDDEN_KEYS.isdisjoint(schema["properties"])


# --- document-scoped search --------------------------------------------------------------


def test_search_v2_sends_the_sealed_request_shape_and_lists_the_sealed_evidence(
    local_signing_key,
):
    sealed_request = load(V2_FIXTURES / "search-v2-request.json")
    sealed_response = load(V2_FIXTURES / "search-v2-response.json")
    handler, calls = responder(sealed_response)

    text = run(
        call(
            server.tool_search_v2,
            handler,
            {
                "document_id": sealed_request["document_id"],
                "query": sealed_request["query"],
                "top_k": sealed_request["top_k"],
            },
        )
    )

    (unit,) = sealed_response["evidence_units"]
    assert sealed_response["document_version"] in text
    assert unit["content"] in text
    assert unit["source_caption"] in text
    assert " > ".join(unit["section_path"]) in text
    # The reader gets a 1-based page and the 0-based index it came from.
    assert f'{unit["item_type"]} -- page 1 (page_index 0)' in text
    assert "Box (points, top-left): 0,0 to 10,10 on 595x842" in text

    (request,) = calls
    assert request.url.path == "/v2/knowledge_search_v2"
    assert request.headers["Authorization"].startswith("Nostr ")
    sent = json.loads(request.content)

    payload = {key: value for key, value in sent.items() if key != "auth"}
    assert payload == {
        key: value for key, value in sealed_request.items() if key != "auth"
    }

    auth = sent["auth"]
    assert auth["principal_id"] == local_signing_key.public_key().to_hex()
    assert auth["url"] == sealed_request["auth"]["url"]
    # top_k is the first integer in a signed v2 payload; canonicalization must still bind.
    assert auth["payload_sha256"] == hashlib.sha256(
        nip98.canonical_payload(payload)
    ).hexdigest()


def test_search_v2_defaults_top_k_to_the_sealed_default():
    sealed_request = load(V2_FIXTURES / "search-v2-request.json")
    handler, calls = responder(load(V2_FIXTURES / "search-v2-response.json"))

    run(
        call(
            server.tool_search_v2,
            handler,
            {
                "document_id": sealed_request["document_id"],
                "query": sealed_request["query"],
            },
        )
    )

    assert json.loads(calls[0].content)["top_k"] == sealed_request["top_k"] == 5


def test_a_search_response_missing_a_required_field_is_a_client_side_contract_violation():
    sealed_request = load(V2_FIXTURES / "search-v2-request.json")
    truncated = load(V2_FIXTURES / "search-v2-response.json")
    del truncated["document_version"]
    handler, _ = responder(truncated)

    with pytest.raises(contract.ContractViolation) as failure:
        run(
            call(
                server.tool_search_v2,
                handler,
                {
                    "document_id": sealed_request["document_id"],
                    "query": sealed_request["query"],
                },
            )
        )

    assert "The Knowledge API response violates" in str(failure.value)
    assert "document_version" in str(failure.value)


def test_a_top_k_outside_the_sealed_bounds_never_reaches_the_gateway():
    sealed_request = load(V2_FIXTURES / "search-v2-request.json")
    handler, calls = responder(load(V2_FIXTURES / "search-v2-response.json"))

    with pytest.raises(contract.ContractViolation, match="The request violates"):
        run(
            call(
                server.tool_search_v2,
                handler,
                {
                    "document_id": sealed_request["document_id"],
                    "query": sealed_request["query"],
                    "top_k": 21,
                },
            )
        )

    assert calls == []
