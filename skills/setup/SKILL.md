---
name: setup
description: >
  Bootstrap the knowledge-engine plugin — install qmd, create collection,
  embed vectors, create MCP venv, verify connectivity.
version: 1.0.0
author: knowledge-engine
---

# Setup — Bootstrap Knowledge Engine

One-time setup to get the knowledge-engine plugin fully operational.
Installs dependencies, creates the search index, generates embeddings,
and verifies all connectivity.

## Triggers

- `/setup` — run the full bootstrap

## Workflow

### Step 1: Check Prerequisites

```bash
node --version        # Requires Node.js (for qmd)
python3 --version     # Requires Python 3.11+
```

Verify the vault exists and is a git repo:

```bash
test -d ~/second-brain/.git && echo "OK: vault is a git repo" || echo "FAIL: ~/second-brain/ is not a git repo"
```

Report any missing prerequisites and stop if critical ones are absent.

### Step 2: Install qmd

```bash
npm install -g @tobilu/qmd@2.1.0
```

Verify installation:

```bash
qmd --version
```

**Note:** qmd is the local search engine for the vault. It provides BM25
keyword search and vector search with Metal GPU acceleration.

### Step 3: Create qmd Collection

```bash
qmd collection add ~/second-brain --name second-brain
```

This registers the vault directory as a searchable collection.

### Step 4: Generate Embeddings

```bash
qmd embed --collection second-brain
```

**Note:** This downloads ~1-2GB of embedding models on first run and uses
Metal GPU for acceleration. Expect 5-15 minutes depending on vault size.

### Step 5: Create MCP Server Venv

If the MCP server virtual environment does not exist:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/mcp/setup.sh
```

This creates a Python venv with the Knowledge MCP server dependencies.

### Step 6: Verify Tailscale Connectivity

Test connectivity to the RAG backend:

```bash
ping -c1 100.97.71.49
```

```bash
curl -s http://100.97.71.49:6380/health
```

If connectivity fails, the plugin still works for local-only search
(qmd). RAG enrichment via `mcp__knowledge__knowledge_search` will be
unavailable until Tailscale is connected.

### Step 7: Report Status

Present a status summary:

```
SETUP COMPLETE

Prerequisites:
  Node.js:    vX.Y.Z  OK
  Python:     3.11.X   OK
  Vault:      ~/second-brain/ (git repo)  OK

Components:
  qmd:        2.1.0 installed  OK
  Collection: second-brain created  OK
  Embeddings: N files embedded  OK
  MCP venv:   created  OK

Connectivity:
  Tailscale:  100.97.71.49 reachable  OK
  RAG health: http://100.97.71.49:6380/health  OK

Ready to use. Try /knowledge-search or /standup.
```
