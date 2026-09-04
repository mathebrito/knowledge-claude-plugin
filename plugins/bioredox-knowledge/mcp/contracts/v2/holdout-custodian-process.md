# Lawful unseen visual-PDF holdout — custodian process

This process deliberately contains neither a holdout filename, SHA-256 value, source location, document bytes, questions, nor answer key.

1. Matheus appoints a custodian with lawful access to one visual-PDF holdout that implementers cannot access.
2. Before implementation, the custodian records the holdout’s SHA-256, lawful-use decision, fixture class, 24-question answer key, and citation expectations in a private record outside this repository and outside implementer-accessible storage.
3. The custodian independently verifies the seal and records the date and candidate-release condition. Do not store the holdout bytes or answer key in this repository, test fixtures, logs, issue tracker, or implementation workspace.
4. Implementers may receive only this process and the public evaluation thresholds. They must not receive the holdout identity, bytes, answers, or a derivative that permits reconstruction.
5. After the candidate commit is frozen for Slice 6 evaluation, the custodian releases the holdout and answer key only to the approved blinded adjudication route. The adjudicator remains blind to configuration labels.
6. The custodian records release provenance and final disposal or retention handling under the lawful-use decision. A mismatch, premature disclosure, or unverified seal invalidates the holdout evaluation and requires a newly sealed holdout.
