# Audit Resume

Use `scripts/review_ledger.py` with the immutable manifest, `screen-results.json`,
and canonical registry. JSONL records are append-only. An interrupted audit
continues by loading the existing ledger, validating its checkpoint against the
current manifest, and appending only missing records.

| Change | Resume same ledger? |
|---|---:|
| No identity change | Yes |
| Routing snapshot changed | No |
| Registry changed | No |
| Source changed | No |
| Build/dependency input changed | No |
| Review schema changed | No |

The ledger belongs to exactly one routing snapshot. Any identity change starts
a new audit run; old artifacts are rejected and must be regenerated.
