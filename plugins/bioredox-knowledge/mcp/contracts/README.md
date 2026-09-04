# Sealed Knowledge contract copies

`v2/` is a verbatim copy of the sealed `knowledge/contracts/v2` directory in tejo-infra
at contract version `2.0.0`. Do not edit anything under it. A change upstream arrives as
a new version directory, never as an edit in place.

Drift is detectable in both directions:

- `v2/contract-manifest.json` is the sealed contract's own SHA-256 manifest and covers
  every artifact in `v2/`.
- `contract.SEALED_MANIFEST_SHA256` pins the manifest itself, so an upstream re-seal is
  visible even when every artifact it lists still matches.

`contract.manifest_drift()` returns the artifacts that no longer match, and
`test_the_sealed_contract_copy_matches_the_sealed_manifest` asserts it is empty.

`v2.1/` holds only the proposed negative fixtures and their case index. Contract version
2.1 is **not sealed**. The client uses these as the reference shape and wording for
sanitized refusals because sealed v2 declares no error-response schema. Re-check them
when v2.1 seals.
