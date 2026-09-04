# BioRedox Knowledge MCP

This plugin provides five v1 tools for the isolated BioRedox knowledge collection:

- `knowledge_search`
- `knowledge_documents`
- `knowledge_summary`
- `knowledge_health`
- `knowledge_ingest`

It also provides two asynchronous Knowledge v2 tools, which the gateway does not yet
serve:

- `knowledge_ingest_async` — queue one approved source and return its job ID
- `knowledge_ingest_status` — read sanitized progress for one job ID

Both validate their request against the sealed v2 contract before sending and their
response against it after receiving; a response that fails its schema is reported as a
contract violation rather than passed through. Neither accepts a principal, a collection,
or an auth block from the caller: the local signing key is the only identity. Repeating a
submission for a source receipt already queued in the same MCP process is a no-op, and
that memory does not survive a restart.

The sealed contract copy and its drift check live in `mcp/contracts/`.

The MCP process runs on the user's computer.
It reads the owner's Buzz `nsec` from the local macOS Keychain and signs each request with NIP-98.
It never sends the private key to the Knowledge API.

Install `uv` first.
Claude starts the local MCP with `uv run`, so no persistent virtual environment is necessary.

From a local repository checkout, install the Claude plugin:

```bash
claude plugin marketplace add .
claude plugin install bioredox-knowledge@mathebrito-knowledge
```

Then run `./plugins/bioredox-knowledge/setup.sh` from the repository root.
The local setup wizard verifies the existing Buzz identity and stores its key under the `bio.bioredox.buzz.nsec` Keychain service.
It writes only the public endpoint, the local Keychain account, and the upload folder to `mcp/local-config.json`.
The configuration file stays untracked.
The wizard also registers the same local MCP with Codex when the `codex` command is available.

Copy each approved source into `~/BioRedox Knowledge Uploads` before ingestion.
The MCP rejects paths outside that folder, symlink escapes, and files larger than 50 MiB.
