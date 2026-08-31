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

Run `./setup.sh` after installation.
The local setup wizard verifies the existing Buzz identity and stores its key under the `bio.bioredox.buzz.nsec` Keychain service.
It writes only the public endpoint and the local Keychain account to `mcp/local-config.json`.
The configuration file stays untracked.
