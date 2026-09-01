# Runtime Profiles

`screen` carries ID, title, and a compact `screen_gate` (falling back to the
trigger). It may classify a check only as `NOT_APPLICABLE_CONFIRMED` or
`CANDIDATE`; it may not filter uncertainty.
`deep` adds risk, specific FP/proof,
verification, official provenance, related knowledge, and applicability.
`proof` contains only current `SUSPICIOUS` IDs, their latest review evidence,
and the targeted proof guidance.

Unknown Domain surfaces create a Deferred Domain screening card and a separate
`domain-resolution.json`. Resolve every Deferred Domain before calling an audit
clean. `LIKELY_SAFE` is intentionally absent.
