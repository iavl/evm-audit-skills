# Architecture

The suite has four planes:

```text
KNOWLEDGE  canonical-checks.json + domains/*.json
     ↓
ROUTING    Recon/Feature Map v3 → environment → Domain → check gates
     ↓
RUNTIME    selected Domain check bodies → review ledgers → proof
     ↓
REPORTING  confirmed-only synthesis → AUDIT-REPORT.md
```

The registry is the only checklist knowledge source. The generator renders
compatibility Markdown; Skills execute the selected runtime artifacts.

Safety invariants: UNKNOWN never filters; only trusted absence or confirmed
environment mismatch filters; all filtered/Deferred items stay manifest-visible;
Deferred Domains must resolve before clean completion; only CONFIRMED records
reach reporting and SUSPICIOUS records never receive severity.
