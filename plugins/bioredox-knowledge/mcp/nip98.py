"""Local Nostr identity retrieval and NIP-98 HTTP transport."""

from __future__ import annotations

import base64
import getpass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

import httpx
from nostr_sdk import EventBuilder, Keys, Kind, Tag, Timestamp
import rfc8785


CONFIG_PATH = Path(__file__).with_name("local-config.json")


def _local_config() -> dict[str, str]:
    try:
        data = json.loads(CONFIG_PATH.read_text())
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


LOCAL_CONFIG = _local_config()
API_URL = os.getenv(
    "KNOWLEDGE_API_URL",
    LOCAL_CONFIG.get("api_url", "https://knowledge.bioredox.bio:8444"),
).rstrip("/")


V2_VALIDITY_SECONDS = 60
V2_COLLECTION = "nanolime"


class LocalIdentityError(RuntimeError):
    """The local signer could not obtain a valid Nostr private key."""


def _load_local_keys() -> Keys:
    """Read the nsec only from the local macOS Keychain."""
    account = (
        os.getenv("KNOWLEDGE_NSEC_KEYCHAIN_ACCOUNT", "").strip()
        or LOCAL_CONFIG.get("keychain_account", "").strip()
        or getpass.getuser()
    )
    service = os.getenv(
        "KNOWLEDGE_NSEC_KEYCHAIN_SERVICE", "bio.bioredox.buzz.nsec"
    )
    argv = [
        "/usr/bin/security",
        "find-generic-password",
        "-s",
        service,
        "-a",
        account,
        "-w",
    ]

    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LocalIdentityError("The local Nostr secret provider failed") from exc

    if result.returncode != 0:
        raise LocalIdentityError("The local Nostr secret provider failed")
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise LocalIdentityError("The local Nostr secret provider returned invalid data")
    try:
        return Keys.parse(lines[0])
    except Exception as exc:
        raise LocalIdentityError("The local Nostr secret provider returned an invalid key") from exc


def _token(event) -> str:
    return f"Nostr {base64.b64encode(event.as_json().encode()).decode()}"


def _authorization(method: str, url: str, body: bytes) -> str:
    tags = [Tag.parse(["u", url]), Tag.parse(["method", method.upper()])]
    if body:
        tags.append(Tag.parse(["payload", hashlib.sha256(body).hexdigest()]))
    event = (
        EventBuilder(Kind(27235), "")
        .tags(tags)
        .custom_created_at(Timestamp.from_secs(int(time.time())))
        .sign_with_keys(_load_local_keys())
    )
    return _token(event)


def canonical_payload(payload: dict) -> bytes:
    """Canonical JSON for one v2 request body with its `auth` block excluded."""
    return rfc8785.dumps(payload)


def sign_v2_payload(url_path: str, payload: dict) -> tuple[dict, str]:
    """Sign a v2 payload; return its contract `auth` block and matching Authorization header.

    The contract binds the NIP-98 event to the canonical payload excluding `auth`, so one
    event covers both the header and the mirrored `auth` block. The principal is always the
    local signing key: no caller ever supplies it.
    """
    keys = _load_local_keys()
    payload_sha256 = hashlib.sha256(canonical_payload(payload)).hexdigest()
    created_at = int(time.time())
    event = (
        EventBuilder(Kind(27235), "")
        .tags(
            [
                Tag.parse(["u", f"{API_URL}{url_path}"]),
                Tag.parse(["method", "POST"]),
                Tag.parse(["payload", payload_sha256]),
            ]
        )
        .custom_created_at(Timestamp.from_secs(created_at))
        .sign_with_keys(keys)
    )
    auth = {
        "event_id": event.id().to_hex(),
        "principal_id": keys.public_key().to_hex(),
        "method": "POST",
        "url": url_path,
        "created_at": created_at,
        "expires_at": created_at + V2_VALIDITY_SECONDS,
        "payload_canonicalization": "rfc8785-json-excluding-auth",
        "payload_sha256": payload_sha256,
        "collection": V2_COLLECTION,
    }
    return auth, _token(event)


async def signed_request(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json_body: dict | None = None,
    content: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 120.0,
    authorization: str | None = None,
) -> httpx.Response:
    request = client.build_request(
        method,
        f"{API_URL}{path}",
        params=params,
        json=json_body,
        content=content,
        headers=headers,
        timeout=timeout,
    )
    request.headers["Authorization"] = authorization or _authorization(
        method, str(request.url), request.content
    )
    return await client.send(request)
