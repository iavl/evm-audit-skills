---
name: evm-audit-general
description: General Solidity and EVM security review for every smart contract. Consume routed selected-check bodies at runtime.
---
# General Solidity/EVM Security

## Review Focus

General Solidity and EVM security review for every smart contract.

## Required Context

- `scope_inventory`: complete source, dependency, and deployment scope inventory
- `entry_points`: state-changing entry points and call paths
- `trust_boundaries`: privilege, user, oracle, and external trust boundaries
- `external_dependencies`: external contracts, libraries, and integration assumptions

## Review Requirements

- trace reachable state changes and cross-domain interactions

## Runtime Modes

Standalone: `python3 <suite-root>/scripts/audit_run.py init <target> --run-dir <run-dir> --domain evm-audit-general`. Run `next` until the next template or runtime view is ready, resolve only the generated evidence-bound templates, then use `status` and `report`.

Orchestrated: consume the Master-provided immutable routing artifacts and Screen/Deep views. Never rerun Recon or Selector in orchestrated mode.

The tri-state predicate router is conservative: `UNKNOWN` stays selected/deferred, and trusted absence is the only filter. Pattern matches are candidates, not findings. `NOT_APPLICABLE` requires complete scope and exclusion evidence; a finding requires a reachable path, exploitable preconditions, concrete impact, and runnable PoC or deterministic invariant evidence.

Apply `<suite-root>/skills/evm-audit-master/references/check-review-contract.runtime.md` to every Deep review record. Do not load `<suite-root>/data/canonical-checks.json` or the full generated checklist into model context.

Related Domains (advisory only; never auto-expand direct scope): `evm-audit-precision-math`.

## Maintenance View
- `references/checklist.md` is a generated human-readable reference view.
