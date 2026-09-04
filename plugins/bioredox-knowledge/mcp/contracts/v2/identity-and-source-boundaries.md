# Identity, source, and replay boundaries

The first accepted ingest creates a random logical document ID within its verified principal and `nanolime` scope. A replacement must name `replace_document_id`; the gateway verifies principal ownership before accepting the source bytes. Version, item, and point identities are defined exactly in `version-manifest.schema.json`; job IDs are random 128-bit opaque values and never derive from a document ID.

The BioRedox import workflow is the sole source-record issuer. It stores immutable receipts privately. A v2 gateway verifies receipt immutable status, file hash, principal, and collection before a job exists, and stores only the receipt reference in the immutable version manifest. No receipt body belongs in Qdrant chunks.

Every v2 request receives the established NIP-98 authentication checks and event-ID replay protection. Unknown, cross-principal, and cross-collection jobs and logical document IDs all return the same sanitized not-found response. Technical promotion into the isolated collection is not canonical venture evidence: an Acervo order or canonical register still requires the reviewed ficha or evidence record linking the source and ingestion receipts.
