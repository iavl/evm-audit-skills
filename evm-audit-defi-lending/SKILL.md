---
name: evm-audit-defi-lending
description: Security review for lending, borrowing, collateral, liquidation, and CDP protocols. Consume routed selected-check bodies at runtime.
---
# Lending and Liquidation Security

## Audit Contract
When invoked directly, run the shared pipeline for `evm-audit-defi-lending` only:

Resolve `<suite-root>` as the parent directory containing this Skill, `data/`, and `scripts/`.

1. Run `python3 <suite-root>/scripts/recon.py <target> --output recon-features.json`.
2. Run `python3 <suite-root>/scripts/select_checks.py --feature-map recon-features.json --domain evm-audit-defi-lending --format json > routing-manifest.json`.
3. Run `python3 <suite-root>/scripts/select_checks.py --feature-map recon-features.json --domain evm-audit-defi-lending --emit-checks --profile compact --format markdown > selected-checks.runtime.md`.
4. Read `<suite-root>/evm-audit-master/references/check-review-contract.md`, review only the routed checks, and write `review-evm-audit-defi-lending.md`.

Do not load `<suite-root>/data/canonical-checks.json` or the full generated checklist into model context. Apply the tri-state predicate router before deep review. Pattern matches are candidates, not findings. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and runnable PoC or deterministic invariant evidence.

Related domains (advisory only; never auto-expand direct scope): `evm-audit-precision-math`, `evm-audit-erc20`, `evm-audit-oracles`.

## Maintenance View
- `references/checklist.md` is generated for maintenance and compatibility.
