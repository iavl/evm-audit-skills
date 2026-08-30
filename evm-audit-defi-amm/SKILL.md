---
name: evm-audit-defi-amm
description: Security review for AMMs, DEXs, swap routers, liquidity pools, and hooks. Consume routed selected-check bodies at runtime.
---
# AMM and DEX Security

## Runtime Modes

Resolve `<suite-root>` as the parent directory containing this Skill, `data/`, and `scripts/`.

### Standalone

When invoked directly, create `audits/<repo>-<UTC timestamp>/` with `recon/`, `routing/`, `runtime/`, and `reviews/`, then run the shared pipeline for `evm-audit-defi-amm` once:

1. `python3 <suite-root>/scripts/recon.py <target> --audit-root <target-root> --output <run-dir>/recon/feature-map.json`
2. `python3 <suite-root>/scripts/select_checks.py --feature-map <run-dir>/recon/feature-map.json --target-root <target-root> --domain evm-audit-defi-amm --profile screen --manifest-out <run-dir>/routing/manifest.json --checks-out <run-dir>/runtime/screen-evm-audit-defi-amm.md --context-out <run-dir>/context.json`
3. Classify screen cards as `NOT_APPLICABLE`, `LIKELY_SAFE`, or `CANDIDATE`. Uncertain cards are `CANDIDATE`; Screen never filters.
4. Load only candidates with `--profile deep --candidate-ids <ids>` and apply `<suite-root>/evm-audit-master/references/check-review-contract.runtime.md`.

### Orchestrated

When Master supplies `context.json`, the Feature Map v3, routing manifest, and `selected-evm-audit-defi-amm.md`, consume those artifacts directly. Never rerun Recon or Selector in orchestrated mode.

## Required Context

- `pool_model_fee_tier_liquidity_hooks_and_price_source`: pool model, fee tier, liquidity, hooks, and price source

## Domain Review Requirements

- model price impact, slippage, callback, and accounting invariants

Do not load `<suite-root>/data/canonical-checks.json` or the full generated checklist into model context. Apply the tri-state predicate router before deep review. Pattern matches are candidates, not findings. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and runnable PoC or deterministic invariant evidence.

Related domains (advisory only; never auto-expand direct scope): `evm-audit-precision-math`, `evm-audit-erc20`, `evm-audit-oracles`.

## Maintenance View
- `references/checklist.md` is generated for maintenance and compatibility.
