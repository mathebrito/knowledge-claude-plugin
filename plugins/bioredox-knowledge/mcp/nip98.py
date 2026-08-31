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
    token = base64.b64encode(event.as_json().encode()).decode()
    return f"Nostr {token}"


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
    request.headers["Authorization"] = _authorization(
        method, str(request.url), request.content
    )
    return await client.send(request)
