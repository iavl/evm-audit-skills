---
name: evm-audit-erc4626
description: Security review for ERC4626 vaults and vault integrations. Consume routed selected-check bodies at runtime.
---
# ERC4626 Vault Security

## Runtime Modes

Resolve `<suite-root>` as the parent directory containing this Skill, `data/`, and `scripts/`.

### Standalone

When invoked directly, create `audits/<repo>-<UTC timestamp>/` with `recon/`, `routing/`, `runtime/`, and `reviews/`, then run the shared pipeline for `evm-audit-erc4626` once:

1. `python3 <suite-root>/scripts/recon.py <target> --audit-root <target-root> --output <run-dir>/recon/feature-map.json`
2. `python3 <suite-root>/scripts/select_checks.py --feature-map <run-dir>/recon/feature-map.json --target-root <target-root> --domain evm-audit-erc4626 --profile compact --manifest-out <run-dir>/routing/manifest.json --checks-out <run-dir>/runtime/selected-evm-audit-erc4626.md --context-out <run-dir>/context.json`
3. Read `<suite-root>/evm-audit-master/references/check-review-contract.runtime.md`, review only the selected checks, and write `<run-dir>/reviews/review-evm-audit-erc4626.md`.

### Orchestrated

When Master supplies `context.json`, the Feature Map v3, routing manifest, and `selected-evm-audit-erc4626.md`, consume those artifacts directly. Never rerun Recon or Selector in orchestrated mode.

## Required Context

- asset/share decimals, conversion formulas, fees, and initial state

## Domain Review Requirements

- verify preview parity, rounding, donation, and inflation resistance

Do not load `<suite-root>/data/canonical-checks.json` or the full generated checklist into model context. Apply the tri-state predicate router before deep review. Pattern matches are candidates, not findings. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and runnable PoC or deterministic invariant evidence.

Related domains (advisory only; never auto-expand direct scope): `evm-audit-precision-math`, `evm-audit-erc20`.

## Maintenance View
- `references/checklist.md` is generated for maintenance and compatibility.
