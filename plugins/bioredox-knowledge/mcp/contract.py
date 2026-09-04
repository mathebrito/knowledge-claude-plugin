"""Sealed BioRedox Knowledge v2 contract: schema loading, validation, drift detection.

`contracts/v2` is a verbatim copy of the sealed contract directory in tejo-infra.
`contracts/v2/contract-manifest.json` is the sealed contract's own SHA-256 manifest,
so any edit to a copied artifact is detectable, and the manifest's own digest is
pinned below so a re-sealed upstream contract is detectable too.
"""

from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


CONTRACT_VERSION = "2.0.0"
COLLECTION = "nanolime"

V2 = Path(__file__).with_name("contracts") / "v2"
SCHEMAS = V2 / "schemas"

# The sealed manifest seals every other artifact. Pinning the manifest itself closes
# the last gap: an upstream re-seal changes this digest even when nothing else moves.
SEALED_MANIFEST_SHA256 = "0e4f24f0428381f82967e3f5a3894e894c7a111a70ccb79b2c2b4bfe70e337ba"

INGEST_ASYNC_REQUEST = "knowledge-ingest-async-request.schema.json"
INGEST_ASYNC_RESPONSE = "knowledge-ingest-async-response.schema.json"
INGEST_STATUS_REQUEST = "knowledge-ingest-status-request.schema.json"
INGEST_STATUS_RESPONSE = "knowledge-ingest-status-response.schema.json"
SEARCH_V2_REQUEST = "knowledge-search-v2-request.schema.json"
SEARCH_V2_RESPONSE = "knowledge-search-v2-response.schema.json"


class ContractViolation(RuntimeError):
    """A request or a response did not satisfy the sealed Knowledge v2 contract."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=None)
def _registry() -> Registry:
    """Resolve the schemas' relative `$ref`s from the local sealed copy, never the network."""
    return Registry().with_resources(
        (contents["$id"], Resource.from_contents(contents))
        for contents in (
            json.loads(path.read_text()) for path in sorted(SCHEMAS.glob("*.schema.json"))
        )
    )


@lru_cache(maxsize=None)
def _validator(schema_name: str) -> Draft202012Validator:
    return Draft202012Validator(
        json.loads((SCHEMAS / schema_name).read_text()), registry=_registry()
    )


def _fault(error) -> str:
    """Describe one failure by location and keyword, never by echoing the value."""
    if error.validator == "required":
        return f"{error.json_path}: {error.message}"
    return f"{error.json_path} fails {error.validator}"


def validate(schema_name: str, instance: object, subject: str) -> None:
    """Raise ContractViolation when the instance does not satisfy the sealed schema.

    The message names failing locations and keywords only. Instance values are never
    repeated, so a sanitized server response stays sanitized in the tool output.
    """
    errors = sorted(
        _validator(schema_name).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )
    if not errors:
        return
    faults = ", ".join(_fault(error) for error in errors[:5])
    raise ContractViolation(
        f"{subject} violates the sealed Knowledge v2 contract ({schema_name}): {faults}"
    )


def manifest_drift() -> list[str]:
    """Sealed v2 artifacts whose local copy no longer matches the sealed manifest."""
    manifest_path = V2 / "contract-manifest.json"
    if _sha256(manifest_path) != SEALED_MANIFEST_SHA256:
        return ["contract-manifest.json"]
    artifacts = json.loads(manifest_path.read_text())["artifacts"]
    return sorted(
        name
        for name, digest in artifacts.items()
        if not (V2 / name).is_file() or _sha256(V2 / name) != digest
    )
