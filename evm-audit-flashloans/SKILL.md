---
name: evm-audit-flashloans
description: Security review for flash loans, flash minting, and atomic economic attacks. Consume routed selected-check bodies at runtime.
---
# Flash-Loan Security

## Audit Contract
When invoked directly, run the shared pipeline for `evm-audit-flashloans` only:

Resolve `<suite-root>` as the parent directory containing this Skill, `data/`, and `scripts/`.

1. Run `python3 <suite-root>/scripts/recon.py <target> --output recon-features.json`.
2. Run `python3 <suite-root>/scripts/select_checks.py --feature-map recon-features.json --domain evm-audit-flashloans --format json > routing-manifest.json`.
3. Run `python3 <suite-root>/scripts/select_checks.py --feature-map recon-features.json --domain evm-audit-flashloans --emit-checks --profile compact --format markdown > selected-checks.runtime.md`.
4. Read `<suite-root>/evm-audit-master/references/check-review-contract.md`, review only the routed checks, and write `review-evm-audit-flashloans.md`.

Do not load `<suite-root>/data/canonical-checks.json` or the full generated checklist into model context. Apply the tri-state predicate router before deep review. Pattern matches are candidates, not findings. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and runnable PoC or deterministic invariant evidence.

Related domains (advisory only; never auto-expand direct scope): `evm-audit-governance`, `evm-audit-oracles`, `evm-audit-defi-amm`.

## Maintenance View
- `references/checklist.md` is generated for maintenance and compatibility.
