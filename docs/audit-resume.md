# Audit Resume

Use `scripts/review_ledger.py` with the immutable manifest, `screen-results.json`,
and canonical registry. JSONL records are append-only and resume terminal
reviews only when source and compilation-input digests match and the check body
hash is unchanged. Resume writes a new ledger with source snapshot provenance;
it never appends to the old ledger. A changed source or build/dependency
fingerprint invalidates the checkpoint.

| Change | Reuse | Reason |
|---|---|---|
| Same source/input digests and same check body hash | yes | record remains reachable in the new route |
| Registry changed, body hash unchanged | explicit `--resume-from` only | new checkpoint records the new registry/snapshot |
| Check body changed | no | the review hypothesis changed |
| Source, dependency, or build-config digest changed | no | the reviewed program inputs changed |
| Old checkpoint/record schema without explicit rollover | no | old run artifacts are rejected by default |
