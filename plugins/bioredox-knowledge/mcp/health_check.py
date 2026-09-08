#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27", "nostr-sdk==0.44.2", "rfc8785==0.1.4"]
# ///
"""Run one signed BioRedox Knowledge health check."""

from __future__ import annotations

import asyncio

import httpx

try:
    from .nip98 import API_URL, signed_request
except ImportError:
    from nip98 import API_URL, signed_request


async def main() -> int:
    async with httpx.AsyncClient() as client:
        response = await signed_request(client, "GET", "/v1/health", timeout=10)
    response.raise_for_status()
    data = response.json()
    qdrant_ready = data.get("qdrant") is True
    print(f"Knowledge API: {data.get('status', 'unknown')}")
    print(f"Qdrant: {'connected' if qdrant_ready else 'disconnected'}")
    return 0 if qdrant_ready else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
