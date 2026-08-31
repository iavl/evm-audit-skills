---
name: evm-audit-dos
description: Security review for denial-of-service, gas griefing, unbounded work, and revert propagation. Consume routed selected-check bodies at runtime.
---
# Denial-of-Service and Griefing Security

## Review Focus

Security review for denial-of-service, gas griefing, unbounded work, and revert propagation.

## Required Context

- `collection_bounds`: collection, loop, queue, and batch bounds
- `external_call_surface`: external calls and failure propagation
- `callback_surface`: callbacks, hooks, and reentrant control flow
- `returndata_handling`: returndata size, decoding, and bubbling behavior

## Review Requirements

- establish attacker-controlled work and recovery paths

## Runtime Modes

Standalone: `python3 <suite-root>/scripts/audit_run.py init <target> --run-dir <run-dir> --domain evm-audit-dos`. Run `next` until the next template or runtime view is ready, resolve only the generated evidence-bound templates, then use `status` and `report`.

Orchestrated: consume the Master-provided immutable routing artifacts and Screen/Deep views. Never rerun Recon or Selector in orchestrated mode.

The tri-state predicate router is conservative: `UNKNOWN` stays selected/deferred, and trusted absence is the only filter. Pattern matches are candidates, not findings. `NOT_APPLICABLE` requires complete scope and exclusion evidence; a finding requires a reachable path, exploitable preconditions, concrete impact, and runnable PoC or deterministic invariant evidence.

Apply `<suite-root>/skills/evm-audit-master/references/check-review-contract.runtime.md` to every Deep review record. Do not load `<suite-root>/data/canonical-checks.json` or the full generated checklist into model context.

Related Domains (advisory only; never auto-expand direct scope): `evm-audit-general`.

## Maintenance View
- `references/checklist.md` is a generated human-readable reference view.
