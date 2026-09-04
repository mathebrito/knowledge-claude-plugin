# v2 recovery contract

This is a contract for later implementation and operation; Slice 0 runs none of these procedures.

1. A worker claims a job with a lease, heartbeat, and monotonic fencing token. On lease expiry, the recovery worker inspects persisted stage evidence before it retries or fails the job.
2. Promotion writes a complete `VALIDATED` manifest, then uses compare-and-swap to set `candidate_version`. Search continues to resolve `active_version`.
3. Reconciliation verifies manifest counts and integrity digests across vectors, assets, and projections. Only then may compare-and-swap promote candidate to active.
4. If candidate or post-activation reconciliation fails, mark its manifest `QUARANTINED`. Restore the prior pointer only if the pointer still names that candidate; if no prior version exists, clear active and candidate through the same compare-and-swap. The first logical document ID is random. It is not derived from source identity.
5. A post-activation rollback is audited and operator-only. It may select only a complete retained manifest and must use pointer compare-and-swap.
6. Never delete failed assets inline. Tombstone after reconciliation, retain required complete versions, wait for the retention window, perform an integrity scan, then use delayed cleanup with an audit-log record.

Every recovery path returns sanitized external errors: no source content, credentials, stack trace, local path, GridFS key, or direct asset reference.
