# BioRedox Knowledge MCP

This plugin provides five tools for the isolated BioRedox knowledge collection:

- `knowledge_search`
- `knowledge_documents`
- `knowledge_summary`
- `knowledge_health`
- `knowledge_ingest`

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
It writes only the public endpoint and the local Keychain account to `mcp/local-config.json`.
The configuration file stays untracked.
The wizard also registers the same local MCP with Codex when the `codex` command is available.
