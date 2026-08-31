# Runtime Profiles

`screen` carries ID, title, trigger, and detection. It may classify a check only
as `NOT_APPLICABLE_CONFIRMED` or `CANDIDATE`; it may not filter uncertainty.
`deep` adds risk, specific FP/proof,
verification, official provenance, related knowledge, and applicability.

Unknown Domain surfaces create a Deferred Domain screening card and a separate
`domain-resolution.json`. Resolve every Deferred Domain before calling an audit
clean. `LIKELY_SAFE` is intentionally absent.
