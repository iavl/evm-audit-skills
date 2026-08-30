---
name: evm-audit-dos
description: Security review for denial-of-service, gas griefing, unbounded work, and revert propagation. Consume routed selected-check bodies at runtime.
---
# Denial-of-Service and Griefing Security

## Audit Contract
When invoked directly, run the shared pipeline for `evm-audit-dos` only:

Resolve `<suite-root>` as the parent directory containing this Skill, `data/`, and `scripts/`.

1. Run `python3 <suite-root>/scripts/recon.py <target> --output recon-features.json`.
2. Run `python3 <suite-root>/scripts/select_checks.py --feature-map recon-features.json --domain evm-audit-dos --format json > routing-manifest.json`.
3. Run `python3 <suite-root>/scripts/select_checks.py --feature-map recon-features.json --domain evm-audit-dos --emit-checks --profile compact --format markdown > selected-checks.runtime.md`.
4. Read `<suite-root>/evm-audit-master/references/check-review-contract.md`, review only the routed checks, and write `review-evm-audit-dos.md`.

Do not load `<suite-root>/data/canonical-checks.json` or the full generated checklist into model context. Apply the tri-state predicate router before deep review. Pattern matches are candidates, not findings. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and runnable PoC or deterministic invariant evidence.

Related domains (advisory only; never auto-expand direct scope): `evm-audit-general`.

## Maintenance View
- `references/checklist.md` is generated for maintenance and compatibility.
