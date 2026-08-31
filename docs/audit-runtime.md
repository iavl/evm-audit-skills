# Audit Runtime

The runtime flow is:

```text
source → Recon/Feature Map v4 → Environment Gate → Domain Gate → Check Gate
       → Deferred Domain Resolution → Required Domain Context → Screen
       → candidate-only Deep → proof → independently derived state → confirmed-only synthesis
```

Standalone runs create `audits/<repo>-<UTC timestamp>/` and run Recon/Selector
once. Orchestrated Domain agents consume the shared context, immutable manifest,
Screen results, and rendered runtime file without rerunning routing.

The low-level CLIs below are runtime interfaces. The short user-facing entry
point is `scripts/audit_run.py`; its `next` command returns the next required
stage and its `report` command always re-derives the current state.

## Runtime profiles and artifacts

Build and route one immutable snapshot:

```bash
python3 scripts/recon.py <target> --audit-root <target-root> \
  --output recon/feature-map.json
python3 scripts/select_checks.py --feature-map recon/feature-map.json \
  --target-root <target-root> --manifest-out routing/manifest.json \
  --context-out context.json
```

Render the runtime views from the immutable manifest:

```bash
python3 scripts/render_runtime.py --manifest routing/manifest.json --profile screen \
  --output runtime/screen.md \
  --domain-resolution-out reviews/domain-resolution.json
python3 scripts/render_runtime.py --manifest routing/manifest.json --profile screen \
  --domain-resolution reviews/domain-resolution.json \
  --domain-context-out reviews/domain-context.json --output runtime/screen.md
python3 scripts/render_runtime.py --manifest routing/manifest.json --profile screen \
  --domain-resolution reviews/domain-resolution.json \
  --domain-context reviews/domain-context.json \
  --screen-results-out reviews/screen-results.json --output runtime/screen.md
python3 scripts/render_runtime.py --manifest routing/manifest.json --profile deep \
  --domain-resolution reviews/domain-resolution.json \
  --domain-context reviews/domain-context.json \
  --screen-results reviews/screen-results.json --output runtime/deep.md
```

`screen` carries only ID, title, trigger, and detection. It may classify a
check only as `NOT_APPLICABLE_CONFIRMED` or `CANDIDATE`; only `CANDIDATE` cards
reach `deep`. Resolve every Deferred Domain, then resolve the required
snapshot-bound Domain Context and rerun Screen with both artifacts.
`NOT_APPLICABLE_CONFIRMED` requires `scope_complete: true`, scope evidence, and
evidence for the relevant exclusion dimension; uncertainty remains `CANDIDATE`.
`LIKELY_SAFE` is not a valid state.

Each candidate canonical ID receives one owner-Domain JSONL event stream.
Events include snapshot/hash identity, a contiguous revision, applicability,
code path, preconditions, exploitability, impact, PoC/invariant evidence, and
one of `NOT_APPLICABLE`, `REVIEWED_SAFE`, `SUSPICIOUS`, or `CONFIRMED`.
`SUSPICIOUS` may be resolved only by a later `PROOF` event; the latest valid
event is the derived state and earlier events remain visible in the Markdown
view.

`--append-record` accepts a current review payload with `record_type: "review"`
and `schema_version: 5`; the append command assigns the next revision when it
is omitted. `CONFIRMED` requires `PROOF` and strong proof evidence. Missing,
stale, or older record shapes are rejected.

Append and render a ledger view with:

```bash
python3 scripts/review_ledger.py --manifest routing/manifest.json \
  --screen-results reviews/screen-results.json \
  --ledger reviews/review-<owner-domain>.jsonl --append-record review.json
python3 scripts/review_ledger.py --manifest routing/manifest.json \
  --screen-results reviews/screen-results.json \
  --ledger reviews/review-<owner-domain>.jsonl --render-markdown reviews/review.md
```

Runtime Markdown is a generated view with snapshot, registry, source,
compilation-input, profile, and candidate-set hashes; the renderer validates
those identities before reading check bodies. Filtered IDs remain in the
manifest and do not generate per-check Markdown records. Completion comes from
`validate_audit_run.py` rather than an upstream completion flag.

The controller equivalent is:

```bash
python3 scripts/audit_run.py init <target> --run-dir <run-dir> --domain <domain>
python3 scripts/audit_run.py next --run-dir <run-dir>
python3 scripts/audit_run.py status --run-dir <run-dir>
python3 scripts/audit_run.py report --run-dir <run-dir> \
  --severity-decisions <run-dir>/reviews/severity-decisions.json \
  --finding-details <run-dir>/reviews/finding-details.json
```

`next` returns `DEEP_REVIEW` for missing candidate records and `PROOF` for
latest `SUSPICIOUS` records. `report` always runs `status_run()` first. It
rewrites an explicitly incomplete report when current artifacts are incomplete
and exits non-zero; it never trusts a previous `audit-state.json`.

Derive completion independently from the manifest, Screen results, Domain
resolution, and owner-Domain ledgers:

```bash
python3 scripts/validate_audit_run.py --manifest routing/manifest.json \
  --context context.json \
  --screen-results reviews/screen-results.json \
  --domain-resolution reviews/domain-resolution.json \
  --domain-context reviews/domain-context.json \
  --ledger reviews/review-<owner-domain>.jsonl \
  --output audit-state.json
```

Only `CONFIRMED` records may become findings. `NOT_APPLICABLE`, `REVIEWED_SAFE`,
and `SUSPICIOUS` records never appear as findings in `AUDIT-REPORT.md`. The
machine state is `COMPLETE_CLEAN`, `COMPLETE_WITH_FINDINGS`, or an explicit
`INCOMPLETE_*` state; incomplete artifacts cannot claim a clean audit. Synthesis
also requires current ledger IDs to equal `coverage.deep_reviewed`, and a
complete state requires every Deep candidate to have a current ledger record.

## Confirmed finding format

Confirmed findings use this format:

```md
## [X-N] Title
**Status**: CONFIRMED
**Checklist reference**: `<canonical-id>`
**Provenance references**: `<source IDs from canonical registry>`
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

For a complete finding report, provide two snapshot-bound artifacts. Severity
decisions have `schema_version: 1`, the four artifact identity fields, and a
`decisions` object keyed by canonical ID. Each decision requires `severity`,
`rationale`, and `dimensions` with `impact`, `exploitability`, `privileges`,
`capital_required`, `repeatability`, `user_interaction`, `loss_bound`,
`protocol_exposure`, and `recoverability`. Valid severities are exactly
`Info`, `Low`, `Medium`, `High`, and `Critical`; the old flat map and
`Informational` are invalid.

`finding-details.json` has the same four identity fields and a `findings` array.
Each confirmed ID must occur exactly once with non-empty `location`,
`description`, and `recommendation`. Category is derived from `owner_domain`.
Missing severity or details is a report admission error (`INCOMPLETE_SEVERITY`
or `INCOMPLETE_REPORTING`), not a new audit-state status.

Severity is assigned only after confirmation using the dimensions and mapping
in [`severity-scoring.md`](../skills/evm-audit-master/references/severity-scoring.md).
Checklist type and confidence never determine severity. The full review
contract is in [`check-review-contract.md`](../skills/evm-audit-master/references/check-review-contract.md);
the compact runtime contract is in
[`check-review-contract.runtime.md`](../skills/evm-audit-master/references/check-review-contract.runtime.md).
