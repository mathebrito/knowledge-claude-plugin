# BioRedox Knowledge v2 — Slice 0 contract

This directory freezes the implementation contract for Knowledge v2. It adds no tool registration, runtime route, service configuration, collection, worker, network rule, credential, or source bytes. Knowledge v1 schemas and behavior remain untouched.

`2.0.0` is the first contract-only version. Consumers must validate the request and response schema for each public tool before accepting a v2 integration:

- `knowledge_ingest_async`: asynchronous ingestion after an authenticated upload and immutable source-receipt lookup.
- `knowledge_ingest_status`: principal-bound, sanitized progress for one opaque job ID.
- `knowledge_search_v2`: principal-bound search of one logical document’s active version.

The public schemas never accept a collection selector, a local path, a GridFS key, a direct asset reference, or an instruction embedded in source content. The fixed collection is `nanolime`. Every public request schema references `schemas/nip98-auth-contract.schema.json`. That versioned contract binds the NIP-98 event to the request method, URL, timestamp window, canonical payload hash, server allowlists, and retained event ID before quota or work.

`contract-manifest.json` seals this release’s declared artifacts by SHA-256. Any substantive change requires a new version directory, an updated contract version, new fixtures, re-validation, and human contract approval; do not alter a sealed `v2` artifact in place.

The examples are synthetic. In particular, the BGR fixture freezes only the reviewed PDF’s identity and hash, never its bytes or extracted content. A first logical document ID is cryptographically random. It has no deterministic source-derived formula.
