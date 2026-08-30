# Audit Resume

Use `scripts/review_ledger.py` with the routing `context.json` and canonical
registry. JSONL records are append-only and resume terminal reviews when source
and compilation digests match. A changed registry reuses only checks whose body
hash still matches; changed source or build/dependency fingerprint invalidates
the checkpoint.
