---
name: evm-audit-master
description: Master entry point for EVM smart-contract audits. Route once, enforce evidence-bound review, and synthesize only confirmed findings.
---
# EVM Smart Contract Security Audit — Master

Load this Skill first. Resolve `<suite-root>` as the nearest ancestor containing
`data/`, `domains/`, and `scripts/`; the Skill itself is under
`<suite-root>/skills/`.

## Invariants

- `<suite-root>/data/canonical-checks.json` is the only checklist knowledge source. Generated Markdown is a view; do not load the full registry into model context.
- Run Recon and immutable routing once. Preserve `routing_snapshot_id`, `registry_sha256`, `source_digest`, and `compilation_input_digest` across every artifact.
- `UNKNOWN` is never absence. Only trusted absence or confirmed environment mismatch may filter; Screen may emit only `NOT_APPLICABLE_CONFIRMED` or `CANDIDATE`.
- Deep reviews consume only Screen candidates. Every candidate needs one owner-Domain append-only JSONL event stream with valid revisions, typed evidence, and a terminal status.
- `SUSPICIOUS` has no severity and must go through a later `PROOF` event. Only `CONFIRMED` records enter the final report.

## Controller

```bash
python3 <suite-root>/scripts/audit_run.py init <target> --run-dir <run-dir> --domain <domain>
python3 <suite-root>/scripts/audit_run.py next --run-dir <run-dir>
python3 <suite-root>/scripts/audit_run.py status --run-dir <run-dir>
python3 <suite-root>/scripts/audit_run.py report --run-dir <run-dir> \
  --severity-decisions <run-dir>/reviews/severity-decisions.json \
  --finding-details <run-dir>/reviews/finding-details.json
```

Repeat `next` until it returns a template or `REPORT`. Resolve only generated
evidence-bound templates. `DEEP_REVIEW` means candidate records are missing;
`PROOF` means the latest record is `SUSPICIOUS`. `report` re-derives state from
current artifacts and refuses stale, incomplete, or under-specified reporting
inputs.

## Model decisions

The model may choose the audit scope, provide evidence-backed environment and
Domain resolutions, complete required context, classify Screen cards, write
Deep/Proof records, and assign structured severity plus reporting details after
confirmation. It may parallelize independent Domain work only when the active
runtime supports it; otherwise use sequential execution.

The model must not treat pattern matches as findings, turn `UNKNOWN` into
absence, rerun routing in a Domain Skill, assign severity to `SUSPICIOUS`, or
emit a final report from missing/malformed coverage. Filing GitHub issues is
separate and requires explicit scope; only confirmed Medium+ findings qualify.

Apply the compact review contract at
`<suite-root>/skills/evm-audit-master/references/check-review-contract.runtime.md`.
Use [`docs/audit-runtime.md`](../../docs/audit-runtime.md) for low-level CLI,
artifact schema, and report-format details.
