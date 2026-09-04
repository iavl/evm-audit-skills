# Review Checkpoint

Use `scripts/review_ledger.py` with the immutable manifest, Initial Review
(`screen-results.json`), and canonical registry. JSONL records are append-only.
The adjacent `<ledger>.commit.json` records the committed byte prefix and its
hash. An interrupted audit continues by loading only that prefix, validating
its checkpoint against the same manifest, and appending the next validated
revision. Extra tail bytes are reported as recovery diagnostics and remain
non-authoritative; a truncated or mismatched committed prefix fails closed.

| Change | Continue the same ledger? |
|---|---:|
| No identity change | Yes |
| Project Analysis routing snapshot changed | No |
| Registry changed | No |
| Source changed | No |
| Build/dependency input changed | No |
| Context Analysis or Initial Review result changed | No |
| Review schema changed | No |

The ledger belongs to exactly one Project Analysis routing snapshot and one
post-routing review
snapshot. Any identity change starts a new audit epoch; old history remains
authoritative but is rejected for current completion and must not be rewritten.
