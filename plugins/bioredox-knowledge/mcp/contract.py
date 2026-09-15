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
CONTRACT_V22_VERSION = "2.2.0"
COLLECTION = "nanolime"

V2 = Path(__file__).with_name("contracts") / "v2"
SCHEMAS = V2 / "schemas"
V22 = V2.with_name("v2.2")
V22_SCHEMAS = V22 / "schemas"
SOURCE_ADMISSION_V22 = V2.with_name("source-admission-v2.2")
SOURCE_ADMISSION_V22_SCHEMAS = SOURCE_ADMISSION_V22 / "schemas"

# The sealed manifest seals every other artifact. Pinning the manifest itself closes
# the last gap: an upstream re-seal changes this digest even when nothing else moves.
SEALED_MANIFEST_SHA256 = "0e4f24f0428381f82967e3f5a3894e894c7a111a70ccb79b2c2b4bfe70e337ba"
V22_MANIFEST_SHA256 = "19628c9ac5518e28c06b62facb6f022deac0032aa0144f5bd88dfdbe997008bf"
SOURCE_ADMISSION_V22_MANIFEST_SHA256 = (
    "7847d86a1d79d75f3da0f8a3e1556d21eb493d9f45f0f43c77f22261a75fbe83"
)

INGEST_ASYNC_REQUEST = "knowledge-ingest-async-request.schema.json"
INGEST_ASYNC_RESPONSE = "knowledge-ingest-async-response.schema.json"
INGEST_STATUS_REQUEST = "knowledge-ingest-status-request.schema.json"
INGEST_STATUS_RESPONSE = "knowledge-ingest-status-response.schema.json"
SEARCH_V2_REQUEST = "knowledge-search-v2-request.schema.json"
SEARCH_V2_RESPONSE = "knowledge-search-v2-response.schema.json"
SOURCE_ADMISSION_REQUEST = "source-admission-request.schema.json"
SOURCE_ADMISSION_RESPONSE = "source-admission-response.schema.json"


class ContractViolation(RuntimeError):
    """A request or a response did not satisfy the sealed Knowledge v2 contract."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=None)
def _registry(schema_root: str = str(SCHEMAS)) -> Registry:
    """Resolve the schemas' relative `$ref`s from the local sealed copy, never the network."""
    return Registry().with_resources(
        (contents["$id"], Resource.from_contents(contents))
        for contents in (
            json.loads(path.read_text())
            for path in sorted(Path(schema_root).glob("*.schema.json"))
        )
    )


@lru_cache(maxsize=None)
def _validator(
    schema_name: str, schema_root: str = str(SCHEMAS)
) -> Draft202012Validator:
    root = Path(schema_root)
    return Draft202012Validator(
        json.loads((root / schema_name).read_text()), registry=_registry(schema_root)
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


def validate_v22(schema_name: str, instance: object, subject: str) -> None:
    _validate_at(V22_SCHEMAS, schema_name, instance, subject)


def validate_source_admission_v22(
    schema_name: str, instance: object, subject: str
) -> None:
    _validate_at(SOURCE_ADMISSION_V22_SCHEMAS, schema_name, instance, subject)


def _validate_at(
    root: Path, schema_name: str, instance: object, subject: str
) -> None:
    errors = sorted(
        _validator(schema_name, str(root)).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )
    if not errors:
        return
    faults = ", ".join(_fault(error) for error in errors[:5])
    raise ContractViolation(
        f"{subject} violates the Knowledge v2.2 contract ({schema_name}): {faults}"
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


def candidate_manifest_drift() -> list[str]:
    """Drift in either versioned v2.2 candidate consumed by this client."""
    drift = []
    for label, root, expected in (
        ("v2.2", V22, V22_MANIFEST_SHA256),
        (
            "source-admission-v2.2",
            SOURCE_ADMISSION_V22,
            SOURCE_ADMISSION_V22_MANIFEST_SHA256,
        ),
    ):
        manifest_path = root / "contract-manifest.json"
        if _sha256(manifest_path) != expected:
            drift.append(f"{label}/contract-manifest.json")
            continue
        artifacts = json.loads(manifest_path.read_text())["artifacts"]
        drift.extend(
            f"{label}/{name}"
            for name, digest in artifacts.items()
            if not (root / name).is_file() or _sha256(root / name) != digest
        )
    return sorted(drift)
