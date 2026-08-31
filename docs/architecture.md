# Architecture

The suite has four planes:

```text
KNOWLEDGE  canonical-checks.json + domains/*.json
     ↓
ROUTING    Recon/Feature Map v4 → environment → Domain → check gates → immutable manifest v6
     ↓
RUNTIME    manifest → Screen results → candidate-only Deep JSONL → proof
     ↓
REPORTING  confirmed-only synthesis → AUDIT-REPORT.md
```

User-facing Skill packages live under `skills/`; runtime assets remain in
`data/`, `domains/`, and `scripts/`. Benchmark fixtures live under
`development/` and are not part of a normal audit run.

The registry is the only checklist knowledge source. The generator renders
human-readable reference Markdown; Skills execute the selected runtime artifacts.

Safety invariants: UNKNOWN, Screen uncertainty, and DECLARED environment facts
never filter; only trusted absence or CONFIRMED environment mismatch filters;
all filtered/Deferred items stay manifest-visible; Deferred Domains must resolve
before clean completion; only CONFIRMED records reach reporting and SUSPICIOUS
records never receive severity. `validate_audit_run.py` derives completion from
the artifacts instead of trusting an upstream completion flag.
