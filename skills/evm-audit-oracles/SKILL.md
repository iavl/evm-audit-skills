---
name: evm-audit-oracles
description: Security review for price feeds, TWAPs, VRF, and external data inputs. Consume routed selected-check bodies at runtime.
---
# Oracle and Pricing Security

## Review Focus

Security review for price feeds, TWAPs, VRF, and external data inputs.

## Required Context

- `feed_contracts`: feed contracts and data sources
- `feed_decimals`: feed and protocol decimal scaling
- `heartbeat`: heartbeat and staleness handling
- `bounds`: answer bounds, deviation, and circuit breakers
- `fallback_behavior`: fallback, sequencer, and failure behavior

## Review Requirements

- verify freshness, scaling, sequencer, and manipulation resistance

## Runtime Modes

Standalone: `python3 <suite-root>/scripts/audit_run.py init <target> --run-dir <run-dir> --domain evm-audit-oracles`. Run `next` until the next template or runtime view is ready, resolve only the generated evidence-bound templates, then use `status` and `report`.

Orchestrated: consume the Master-provided immutable routing artifacts and Screen/Deep views. Never rerun Recon or Selector in orchestrated mode.

The tri-state predicate router is conservative: `UNKNOWN` stays selected/deferred, and trusted absence is the only filter. Pattern matches are candidates, not findings. `NOT_APPLICABLE` requires complete scope and exclusion evidence; a finding requires a reachable path, exploitable preconditions, concrete impact, and runnable PoC or deterministic invariant evidence.

Apply `<suite-root>/skills/evm-audit-master/references/check-review-contract.runtime.md` to every Deep review record. Do not load `<suite-root>/data/canonical-checks.json` or the full generated checklist into model context.

Related Domains (advisory only; never auto-expand direct scope): `evm-audit-chain-specific`, `evm-audit-precision-math`.

## Maintenance View
- `references/checklist.md` is a generated human-readable reference view.
