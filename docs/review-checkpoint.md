# Review Checkpoint

Use `scripts/review_ledger.py` with the immutable manifest, `screen-results.json`,
and canonical registry. JSONL records are append-only. An interrupted audit
continues by loading the existing ledger, validating its checkpoint against the
same manifest, and appending the next validated revision.

| Change | Continue the same ledger? |
|---|---:|
| No identity change | Yes |
| Routing snapshot changed | No |
| Registry changed | No |
| Source changed | No |
| Build/dependency input changed | No |
| Domain resolution, Domain Context, or Screen result changed | No |
| Review schema changed | No |

The ledger belongs to exactly one routing snapshot and one post-routing review
snapshot. Any identity change starts a new audit epoch; old history remains
authoritative but is rejected for current completion and must not be rewritten.
