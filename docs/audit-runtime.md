# Audit Runtime

The runtime flow is:

```text
source → Recon/Feature Map v4 → Environment Gate → Domain Gate → Check Gate
       → Screen → candidate-only Deep → proof → independently derived state → confirmed-only synthesis
```

Standalone runs create `audits/<repo>-<UTC timestamp>/` and run Recon/Selector
once. Orchestrated Domain agents consume the shared context, immutable manifest,
Screen results, and rendered runtime file without rerunning routing.

## Runtime profiles and artifacts

Render the runtime views from the immutable manifest:

```bash
python3 scripts/render_runtime.py --manifest routing/manifest.json --profile screen \
  --output runtime/screen.md --screen-results-out reviews/screen-results.json \
  --domain-resolution-out reviews/domain-resolution.json
python3 scripts/render_runtime.py --manifest routing/manifest.json --profile deep \
  --screen-results reviews/screen-results.json --output runtime/deep.md
```

`screen` carries only ID, title, trigger, and detection. It may classify a
check only as `NOT_APPLICABLE_CONFIRMED` or `CANDIDATE`; only `CANDIDATE` cards
reach `deep`. Resolve every Deferred Domain and rerun Screen with
`--domain-resolution` before Deep when a Deferred Domain is `PRESENT`.
`LIKELY_SAFE` is not a valid state.

Each candidate canonical ID receives exactly one owner-Domain JSONL review
record. Deep/proof records include snapshot/hash identity, applicability, code
path, preconditions, exploitability, impact, PoC/invariant evidence, and one
of `NOT_APPLICABLE`, `REVIEWED_SAFE`, `SUSPICIOUS`, or `CONFIRMED`.

`--append-record` accepts a current review payload with `record_type: "review"`
and `schema_version: 3`; the ledger binds its identity fields to the manifest.
Missing, stale, or older record shapes are rejected.

Runtime Markdown is a generated view with snapshot, registry, source,
compilation-input, profile, and candidate-set hashes; the renderer validates
those identities before reading check bodies. Filtered IDs remain in the
manifest and do not generate per-check Markdown records. Completion comes from
`validate_audit_run.py` rather than an upstream completion flag.

Derive completion independently from the manifest, Screen results, Domain
resolution, and owner-Domain ledgers:

```bash
python3 scripts/validate_audit_run.py --manifest routing/manifest.json \
  --screen-results reviews/screen-results.json \
  --domain-resolution reviews/domain-resolution.json \
  --ledger reviews/review-<owner-domain>.jsonl \
  --output audit-state.json
```

Only `CONFIRMED` records may become findings. `NOT_APPLICABLE`, `REVIEWED_SAFE`,
and `SUSPICIOUS` records never appear as findings in `AUDIT-REPORT.md`. If
suspicious items remain, the report must disclose unresolved review status and
must not claim the audit is clean.

## Confirmed finding format

Confirmed findings use this format:

```md
## [X-N] Title
**Status**: CONFIRMED
**Checklist reference**: `<canonical-id>`
**Provenance references**: `<source IDs or aliases from canonical registry>`
**Severity**: Critical / High / Medium / Low / Info
**Category**: [skill name]
**Location**: `functionName()` or file:line
**Applicability**: APPLICABLE — why the checklist item applies
**Code path**: Exact reachable path
**Preconditions**: Concrete conditions
**Exploitability**: How the conditions are satisfied
**Impact**: Concrete consequence
**Proof of Concept / Invariant Violation**: Runnable proof or deterministic invariant violation
**Description**: What the issue is and why it matters.
**Recommendation**: Concrete fix with code snippet.
```

Severity is assigned only after confirmation using the dimensions and mapping
in [`severity-scoring.md`](../skills/evm-audit-master/references/severity-scoring.md).
Checklist type and confidence never determine severity. The full review
contract is in [`check-review-contract.md`](../skills/evm-audit-master/references/check-review-contract.md);
the compact runtime contract is in
[`check-review-contract.runtime.md`](../skills/evm-audit-master/references/check-review-contract.runtime.md).
