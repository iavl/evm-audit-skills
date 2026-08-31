---
name: evm-audit-precision-math
description: Precision, rounding, fixed-point math, conversion, and arithmetic security review for EVM contracts. Consume routed selected-check bodies at runtime.
---
# Precision and Math Security

## Review Focus

Precision, rounding, fixed-point math, conversion, and arithmetic security review for EVM contracts.

## Required Context

- `units`: units and dimensional meaning of values
- `decimals`: decimal scales and normalization
- `rounding_directions`: rounding direction at each user/protocol boundary
- `numeric_bounds`: numeric ranges, casts, and overflow assumptions

## Review Requirements

- prove conversion and accounting invariants at boundary values

## Runtime Modes

Standalone: `python3 <suite-root>/scripts/audit_run.py init <target> --run-dir <run-dir> --domain evm-audit-precision-math`. Run `next` until the next template or runtime view is ready, resolve only the generated evidence-bound templates, then use `status` and `report`.

Orchestrated: consume the Master-provided immutable routing artifacts and Screen/Deep views. Never rerun Recon or Selector in orchestrated mode.

The tri-state predicate router is conservative: `UNKNOWN` stays selected/deferred, and trusted absence is the only filter. Pattern matches are candidates, not findings. `NOT_APPLICABLE` requires complete scope and exclusion evidence; a finding requires a reachable path, exploitable preconditions, concrete impact, and runnable PoC or deterministic invariant evidence.

Apply `<suite-root>/skills/evm-audit-master/references/check-review-contract.runtime.md` to every Deep review record. Do not load `<suite-root>/data/canonical-checks.json` or the full generated checklist into model context.

Related Domains (advisory only; never auto-expand direct scope): `evm-audit-general`.

## Maintenance View
- `references/checklist.md` is a generated human-readable reference view.
