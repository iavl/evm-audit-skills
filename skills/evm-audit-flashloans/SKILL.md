---
name: evm-audit-flashloans
description: Security review for flash loans, flash minting, and atomic economic attacks. Consume routed selected-check bodies at runtime.
---
# Flash-Loan Security

## Review Focus

Security review for flash loans, flash minting, and atomic economic attacks.

## Required Context

- `flash_liquidity_sources`: flash-loan and flash-mint liquidity sources
- `same_transaction_state_dependencies`: same-transaction state, pricing, and callback dependencies

## Review Requirements

- test atomic manipulation of governance, prices, shares, and accounting

## Runtime Modes

Standalone: `python3 <suite-root>/scripts/audit_run.py init <target> --run-dir <run-dir> --domain evm-audit-flashloans`. Run `next` until the next template or runtime view is ready, resolve only the generated evidence-bound templates, then use `status` and `report`.

Orchestrated: consume the Master-provided immutable routing artifacts and Screen/Deep views. Never rerun Recon or Selector in orchestrated mode.

The tri-state predicate router is conservative: `UNKNOWN` stays selected/deferred, and trusted absence is the only filter. Pattern matches are candidates, not findings. `NOT_APPLICABLE` requires complete scope and exclusion evidence; a finding requires a reachable path, exploitable preconditions, concrete impact, and runnable PoC or deterministic invariant evidence.

Apply `<suite-root>/skills/evm-audit-master/references/check-review-contract.runtime.md` to every Deep review record. Do not load `<suite-root>/data/canonical-checks.json` or the full generated checklist into model context.

Related Domains (advisory only; never auto-expand direct scope): `evm-audit-governance`, `evm-audit-oracles`, `evm-audit-defi-amm`.

## Maintenance View
- `references/checklist.md` is a generated human-readable reference view.
