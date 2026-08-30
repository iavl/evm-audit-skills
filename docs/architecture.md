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
