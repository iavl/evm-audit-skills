---
name: evm-audit-oracles
description: Security review for price feeds, TWAPs, VRF, and external data inputs. Consume routed selected-check bodies at runtime.
---
# Oracle and Pricing Security

## Runtime Modes

Resolve `<suite-root>` as the parent directory containing this Skill, `data/`, and `scripts/`.

### Standalone

When invoked directly, create `audits/<repo>-<UTC timestamp>/` with `recon/`, `routing/`, `runtime/`, and `reviews/`, then run the shared pipeline for `evm-audit-oracles` once:

1. `python3 <suite-root>/scripts/recon.py <target> --audit-root <target-root> --output <run-dir>/recon/feature-map.json`
2. `python3 <suite-root>/scripts/select_checks.py --feature-map <run-dir>/recon/feature-map.json --target-root <target-root> --domain evm-audit-oracles --profile compact --manifest-out <run-dir>/routing/manifest.json --checks-out <run-dir>/runtime/selected-evm-audit-oracles.md --context-out <run-dir>/context.json`
3. Read `<suite-root>/evm-audit-master/references/check-review-contract.runtime.md`, review only the selected checks, and write `<run-dir>/reviews/review-evm-audit-oracles.md`.

### Orchestrated

When Master supplies `context.json`, the Feature Map v3, routing manifest, and `selected-evm-audit-oracles.md`, consume those artifacts directly. Never rerun Recon or Selector in orchestrated mode.

## Required Context

- feed contracts, decimals, heartbeat, bounds, and fallback behavior

## Domain Review Requirements

- verify freshness, scaling, sequencer, and manipulation resistance

Do not load `<suite-root>/data/canonical-checks.json` or the full generated checklist into model context. Apply the tri-state predicate router before deep review. Pattern matches are candidates, not findings. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and runnable PoC or deterministic invariant evidence.

Related domains (advisory only; never auto-expand direct scope): `evm-audit-chain-specific`, `evm-audit-precision-math`.

## Maintenance View
- `references/checklist.md` is generated for maintenance and compatibility.
