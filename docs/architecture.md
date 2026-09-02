# Architecture

The suite has four planes:

```text
 KNOWLEDGE  canonical-checks.json + domains/*.json + feature-detectors.json
     ↓
ROUTING    Recon/Feature Map v4 → environment → Domain → check gates → immutable manifest v7
     ↓
RUNTIME    manifest → Domain Resolution → Domain Context → Screen results → candidate-only Deep JSONL → proof
     ↓
REPORTING  confirmed-only synthesis → severity → conditional PoC gate → report generation → report-current.json
```

The authority boundary is explicit: the target/build tree is immutable audit
input, an external sibling `<run-dir>` is mutable authoring state, and
`report-generations/` contains immutable derived outputs. High/Critical PoC
sources are copied into the generation; recorded commands execute only through
the explicit `verify-poc` command.

User-facing Skill packages live under `skills/`; runtime assets remain in
`data/`, `domains/`, `scripts/`, and the small pure-decision package
`evm_audit_runtime/`. Benchmark fixtures live under
`development/` and are not part of a normal audit run.

The registry is the only checklist knowledge source. The generator renders
human-readable reference Markdown; Skills execute the selected runtime artifacts.

Safety invariants: UNKNOWN, Screen uncertainty, and DECLARED environment facts
never filter; only trusted absence or CONFIRMED environment mismatch filters;
all filtered/Deferred items stay manifest-visible; Deferred Domains must resolve
before clean completion; required Domain Context is a separate snapshot-bound
artifact; only CONFIRMED records reach reporting and SUSPICIOUS records never
receive severity. `validate_audit_run.py` derives completion from the artifacts
instead of trusting an upstream completion flag. Strong proof establishes
`CONFIRMED`; a runnable PoC is separate reporting evidence required only for
confirmed `High` and `Critical` findings. The PoC artifact is lineage-bound to
severity-decision bytes and source hashes, and is snapshotted in report-bundle
v3 without changing the review lifecycle. A separate v1 `poc-verification`
receipt is optional and non-gating.
