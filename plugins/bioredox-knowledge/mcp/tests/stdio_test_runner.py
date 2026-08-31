"""Start the MCP with a test key passed through an inherited file descriptor."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys

from nostr_sdk import Keys

sys.path.insert(0, str(Path(__file__).parents[2]))

from mcp import nip98, server


key_fd = int(os.environ.pop("BIOREDOX_TEST_NSEC_FD"))
with os.fdopen(key_fd) as key_stream:
    test_keys = Keys.parse(key_stream.read())

nip98._load_local_keys = lambda: test_keys

asyncio.run(server.main())
