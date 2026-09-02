# Runtime Profiles

The `screen` profile powers Initial Review and carries ID, title, and a compact
`screen_gate` (falling back to the trigger). It may classify a check only as
`NOT_APPLICABLE_CONFIRMED` or `CANDIDATE`; it may not filter uncertainty.
The `deep` profile powers Deep Audit and adds risk, specific FP/proof,
verification, official provenance, related knowledge, and applicability.
The `proof` profile powers Vulnerability Validation and contains only current
`SUSPICIOUS` IDs, their latest review evidence, and targeted proof guidance.

Unknown Domain surfaces create a Deferred Domain screening card and a separate
`domain-resolution.json`. Resolve every Deferred Domain before calling an audit
clean. `LIKELY_SAFE` is intentionally absent.
