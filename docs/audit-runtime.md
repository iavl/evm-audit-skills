# Audit Runtime

The runtime flow is:

```text
source → Recon/Feature Map v4 → Environment Gate → Domain Gate → Check Gate
       → Deferred Domain Resolution → Required Domain Context → Screen
       → review snapshot → candidate-only Deep → proof → review-state digest
       → independently derived state → confirmed-only synthesis
       → severity → runnable PoC gate for High/Critical → final report
```

Standalone runs create `audits/<repo>-<UTC timestamp>/` and run Recon/Selector
once. Orchestrated Domain agents consume the shared context, immutable manifest,
Screen results, and rendered runtime file without rerunning routing.

The low-level CLIs below are runtime interfaces. The short user-facing entry
point is `scripts/audit_run.py`; its `next` command returns the next required
stage and its `report` command always re-derives the current state.

### Progress observability

The controller keeps terminal-oriented progress on `stderr` and returns
machine-readable `progress` metadata for executor/UI use on `stdout`. The
Master Skill renders a compact chat banner from that metadata after a
user-relevant stage transition; it does not parse or depend on `stderr`.

`init` additionally returns an additive `progress_history` array. It contains
the completed `RECON` and `ROUTING` entries followed by the current `next`
stage. Each entry has `stage`, display-only `state` (`COMPLETED` or `CURRENT`),
`progress`, and `recommended_execution`. `next`, `status`, and `report` keep
their existing single-stage response shape; the history is not persisted in
audit artifacts.

## Runtime profiles and artifacts

### Artifact authority

| Artifact | Authoritative? | Integrity binding | Failure behavior |
|---|---:|---|---|
| Feature Map | yes for Recon snapshot | source/compilation lineage | fail closed |
| Routing manifest | yes | `routing_snapshot_id` | invalid snapshot |
| Domain resolution/context | yes | routing/review snapshot | block downstream |
| Screen results | yes | review inputs | block downstream |
| Review JSONL | yes | checkpoint + review snapshot/state digest | block completion |
| runtime Markdown | no, generated view | sidecar identity + body SHA-256 | regenerate |
| code-index | no, navigation hint | Recon `navigation_artifacts.code_index.sha256` plus current target snapshot | disable navigation |
| severity/finding details | reporting input | review-state digest | report admission error |
| `poc-evidence` | reporting input for High/Critical only | severity-decision bytes, review/source/build lineage, source hashes, path safety | `INCOMPLETE_POC` |
| final report + issue candidates | derived outputs | immutable report generation, `report-current.json` v2, report-bundle v3 marker, body hashes, and finding-input hashes | stale/incomplete |

The machine-readable JSON/JSONL artifacts are authoritative. Runtime Markdown
is paired with a schema-validated `.meta.json` sidecar containing
`runtime_sha256`; cache reuse hashes the exact Markdown bytes and rejects any
body, sidecar, or identity mismatch. The non-authoritative code index is still
integrity-bound: Recon records its exact serialized body hash, and a changed or
unbound index is reported as unavailable without changing authoritative audit
state. Bound code-index queries validate the routing manifest, target snapshot,
Recon binding, exact body hash, schema version, and index lineage before lookup;
an unbound `--index` query requires explicit development opt-in. `report-bundle.json`
is written inside an immutable
`report-generations/generation-<bundle-sha256>/` directory. The small
`report-current.json` pointer is the publication commit boundary; a failed
generation leaves the previous pointer and generation untouched. Stable
top-level report files and `report-inputs/` files are convenience copies only,
and their synchronization status is returned explicitly. The current bundle is
accepted only when its identity, body hashes, exact generation snapshots, and
deterministic synthesis match the current state. Report publication is
serialized per run, and the pointer is committed only after a final state
identity check. A validated `poc-evidence.json` snapshot is included only when
the confirmed findings contain `High` or `Critical` severity.

`non-authoritative != integrity-unchecked`.

### Codex model policy

The Codex-only execution policy is stored separately from audit artifacts at
`<run-dir>/config/codex-model-profile.json`. Confirm it once in the Master Skill,
then persist either the canonical profile or a validated custom profile. New
runs use the user-level default at `~/.codex/evm-audit-model-profile.json` when
it exists:

```bash
python3 scripts/audit_run.py models --init-global
python3 scripts/audit_run.py init <target> --run-dir <run-dir> \
  --domain <domain> --accept-default-models
python3 scripts/audit_run.py init <target> --run-dir <run-dir> \
  --domain <domain> --model-profile <profile.json>
python3 scripts/audit_run.py models --run-dir <run-dir>
python3 scripts/audit_run.py models --run-dir <run-dir> --reset-defaults
```

`next` and `status` expose `recommended_execution` for the next stage, and
stderr gives the same compact model handoff. The controller does not switch the
active Codex conversation model. An absent profile on an older run resolves to
the canonical default in memory and does not change audit state. The global
file is read only during `init`; the run-scoped copy wins afterward.

Recon, routing, validation, hashing, and report admission remain deterministic
controller logic; the recommendation applies only to Codex model judgment.

The profile is execution metadata only. It is excluded from routing, review,
source, compilation, registry, and report identity digests; changing it cannot
stale valid security evidence.

Build and route one immutable snapshot:

```bash
python3 scripts/recon.py <target> --audit-root <target-root> --build-root <project-root> \
  --output recon/feature-map.json --code-index-out recon/code-index.json
python3 scripts/select_checks.py --feature-map recon/feature-map.json \
  --target-root <target-root> --manifest-out routing/manifest.json \
  --context-out context.json
```

Query the optional navigation hint only after binding it to the run:

```bash
python3 scripts/code_context.py --run-dir <run-dir> --function <function-id> \
  --include-callers --include-callees --depth 2 --max-nodes 25 --max-edges 200
```

`MISSING`, `TAMPERED`, and `UNAVAILABLE` disable navigation; they do not
invalidate authoritative audit state. `edge_count` and `unique_edge_count` are
the deterministic number of unique available graph edges before the cap;
`returned_edge_count` counts unique edges admitted by the cap and
`serialized_edge_count` is the same hard-bounded entry count. Query v5 returns
one `selected_edges` array plus `expansion.callers`/`expansion.callees`, so a
selected edge is not copied into separate caller and callee arrays.
`edges_truncated` exposes omitted unique edges. Capped edges are returned in
deterministic priority order: unresolved, selected, then boundary edges.

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

`screen` carries only ID, title, and a compact screen gate (or trigger fallback). It may classify a
check only as `NOT_APPLICABLE_CONFIRMED` or `CANDIDATE`; only `CANDIDATE` cards
reach `deep`. Resolve every Deferred Domain, then resolve the required
snapshot-bound Domain Context and rerun Screen with both artifacts.
`NOT_APPLICABLE_CONFIRMED` requires `scope_complete: true`, scope evidence, and
evidence for the relevant exclusion dimension; uncertainty remains `CANDIDATE`.
`LIKELY_SAFE` is not a valid state.

For required Domain Context, `NOT_APPLICABLE` is also trusted absence: it needs
`scope_complete: true` and evidence allowed by the owning Domain's
`trusted_absence_policy`. A manual explanation alone is never enough; use
`UNKNOWN` until non-applicability is proven.

Each candidate canonical ID receives one owner-Domain JSONL event stream. Its
checkpoint and every event bind the deterministic `review_snapshot_id`, derived
from the routing snapshot plus current Domain resolution, Domain Context, and
Screen results. Changing any of those artifacts makes prior events stale; start
a new review epoch instead of rewriting history.
Events include snapshot/hash identity, a contiguous revision, typed evidence,
and one of `NOT_APPLICABLE`, `REVIEWED_SAFE`, `SUSPICIOUS`, or `CONFIRMED`.
Payload fields are status-specific: safe/non-applicable records stay compact,
while `CONFIRMED` retains applicability, path, preconditions, exploitability,
impact, and proof.
`SUSPICIOUS` may be resolved only by a later `PROOF` event; the latest valid
event is the derived state and earlier events remain visible in the Markdown
view.

`proof` runtime views contain only current `SUSPICIOUS` IDs and are written as
`runtime/proof-<owner-domain>.md`; full machine identity is kept in the adjacent
`.meta.json` sidecar.

`scripts/benchmark_routing.py` reports UTF-8 byte sizes for Screen, Deep, Proof,
and representative safe/confirmed records; it uses no external tokenizer.

`--append-record` accepts a current review payload with `record_type: "review"`
and the version required by `schemas/review-record.schema.json`; the append command assigns the next revision and the
current `review_snapshot_id` when it
is omitted. `CONFIRMED` requires `PROOF` and strong proof evidence. Missing,
stale, or older record shapes are rejected.

Append and render a ledger view with:

```bash
python3 scripts/review_ledger.py --manifest routing/manifest.json \
  --screen-results reviews/screen-results.json \
  --domain-context reviews/domain-context.json \
  --ledger reviews/review-<owner-domain>.jsonl --append-record review.json
python3 scripts/review_ledger.py --manifest routing/manifest.json \
  --screen-results reviews/screen-results.json \
  --domain-context reviews/domain-context.json \
  --ledger reviews/review-<owner-domain>.jsonl --render-markdown reviews/review.md
```

Runtime Markdown is a generated model-facing view with only compact stage and
candidate metadata. Full routing/source/compilation/candidate-set identity is
kept in the adjacent `.meta.json` sidecar together with a SHA-256 hash of the
exact UTF-8 body; the controller verifies both the identity and body before
reusing a cached view. Filtered IDs remain in the
manifest and do not generate per-check Markdown records. Completion comes from
`validate_audit_run.py` rather than an upstream completion flag.

The controller equivalent is:

```bash
python3 scripts/audit_run.py init <target> --run-dir <run-dir> --domain <domain>
python3 scripts/audit_run.py next --run-dir <run-dir>
python3 scripts/audit_run.py status --run-dir <run-dir>
python3 scripts/audit_run.py report --run-dir <run-dir> \
  --severity-decisions <run-dir>/reviews/severity-decisions.json \
  --finding-details <run-dir>/reviews/finding-details.json \
  --poc-evidence <run-dir>/reviews/poc-evidence.json
```

`next` returns `DEEP_REVIEW` for missing candidate records and `PROOF` for
latest `SUSPICIOUS` records. `report` always runs `status_run()` first,
validates and synthesizes in memory, then commits a complete immutable
generation through `report-current.json`. A failed report leaves the previous
current generation untouched and exits non-zero if current reporting is
incomplete. It never trusts a previous `audit-state.json`.

`Proof != PoC`. Proof establishes that a finding is real and may be a trace,
invariant violation, calculation, or test. A runnable PoC is a reporting gate
after severity is assigned: `Info`, `Low`, and `Medium` findings report without
one; `High` and `Critical` findings require a completed, lineage-bound
`poc-evidence` artifact. The controller records the reproduction command but
does not execute arbitrary commands during `status` or ordinary reporting.

When severity is current, controller output exposes the policy projection:

```json
{
  "poc_policy": {
    "minimum_severity": "High",
    "required_count": 1,
    "skipped_below_high_count": 2,
    "required_ids": ["EVM-..."]
  }
}
```

The returned `report` and `issue_candidates` paths point into the committed
generation. Use `report_generation.report`, `.issue_candidates`, `.bundle`, and
`.current_pointer` from controller output/status as authoritative paths; stable
top-level files are convenience copies. Older runs with top-level outputs but no
pointer are uncommitted. Rerun the explicit `report` command to rederive state
and republish them; old bodies are never migrated blindly.

Inspect or recover report history with:

```bash
python3 scripts/audit_run.py reports --run-dir <run-dir> --list
python3 scripts/audit_run.py reports --run-dir <run-dir> --gc --dry-run
python3 scripts/audit_run.py reports --run-dir <run-dir> --gc --apply
```

Cleanup protects the current generation, ignores unknown directories, and only
removes stale staging directories or verified orphan generations. A generation
does not yet contain a hashed `audit-state.json` snapshot; its historical state
is reconstructed from the immutable run inputs and ledger.

The low-level `synthesize_report.py --audit-state` argument is an optional
derived cache for compatibility; synthesis re-derives the current state from
the authoritative inputs and uses that same state for any report bundle.

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
**Strong proof evidence**: Trace, calculation, test, or deterministic invariant violation
**Description**: What the issue is and why it matters.
**Recommendation**: Concrete fix with code snippet.
```

For a complete finding report, provide two snapshot-bound artifacts. Severity
decisions have `schema_version: 2`, the four artifact identity fields, a current
`review_state_digest`, and a
`decisions` object keyed by canonical ID. Each decision requires `severity`,
`rationale`, and `dimensions` with `impact`, `exploitability`, `privileges`,
`capital_required`, `repeatability`, `user_interaction`, `loss_bound`,
`protocol_exposure`, and `recoverability`. Valid severities are exactly
`Info`, `Low`, `Medium`, `High`, and `Critical`; the old flat map and
`Informational` are invalid.

`finding-details.json` has the same identity fields and `review_state_digest`,
plus a `findings` array. `audit-state.json`, `issue-candidates.json`, and final
report metadata also carry the current review snapshot/state identity.
Each confirmed ID must occur exactly once with non-empty `location`,
`description`, and `recommendation`. Category is derived from `owner_domain`.
Missing severity or details is a report admission error (`INCOMPLETE_SEVERITY`
or `INCOMPLETE_REPORTING`), not a new audit-state status.

The controller stores the exact validated UTF-8 reporting inputs in the
committed generation as `severity-decisions.json` and `finding-details.json`.
The report-bundle v3 marker hashes those snapshots and adds
`poc_evidence_sha256`. Clean reports set all three reporting-input hashes to
`null`. A report with only sub-High findings hashes severity and finding details
but leaves `poc_evidence_sha256` as `null`. A High/Critical report stores the
exact validated PoC bytes in the immutable generation. Previous generations
remain available for reproducibility; operators may remove unreferenced
generations only under an explicit retention policy after preserving any
required audit evidence.

For a completed PoC, `poc-evidence.json` contains only the exact current
High/Critical projection. Each entry records its runner, non-empty reproduction
command, entrypoint, expected result, result summary, durable source path, and
SHA-256. Sources must resolve inside the audited target/build tree or
`<run-dir>/poc/`; symlink escapes, missing files, changed bytes, stale severity
bytes, and `TEMPLATE` artifacts are rejected.

Severity is assigned only after confirmation using the dimensions and mapping
in [`severity-scoring.md`](../skills/evm-audit-master/references/severity-scoring.md).
Checklist type and confidence never determine severity. The full review
contract is in [`check-review-contract.md`](../skills/evm-audit-master/references/check-review-contract.md);
the compact runtime contract is in
[`check-review-contract.runtime.md`](../skills/evm-audit-master/references/check-review-contract.runtime.md).
