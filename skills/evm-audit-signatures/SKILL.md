---
name: evm-audit-signatures
description: Security review for signatures, permits, EIP-712, and meta-transactions. Consume routed selected-check bodies at runtime.
---
# Signature Security

## Review Focus

Security review for signatures, permits, EIP-712, and meta-transactions.

## Required Context

- `signed_payload`: signed fields and canonical encoding
- `domain_separator`: EIP-712 domain and version binding
- `nonce`: nonce, replay, and invalidation model
- `signer`: signer recovery and authorization mapping
- `chain_binding`: chain, contract, and fork binding

## Review Requirements

- test replay, malleability, expiry, and signer ambiguity

## Runtime Modes

Standalone: `python3 <suite-root>/scripts/audit_run.py init <target> --run-dir <run-dir> --domain evm-audit-signatures`. Run `next` until the next template or runtime view is ready, resolve only the generated evidence-bound templates, then use `status` and `report`.

Orchestrated: consume the Master-provided immutable routing artifacts and Screen/Deep views. Never rerun Recon or Selector in orchestrated mode.

The tri-state predicate router is conservative: `UNKNOWN` stays selected/deferred, and trusted absence is the only filter. Pattern matches are candidates, not findings. `NOT_APPLICABLE` requires complete scope and exclusion evidence; a finding requires a reachable path, exploitable preconditions, concrete impact, and runnable PoC or deterministic invariant evidence.

Apply `<suite-root>/skills/evm-audit-master/references/check-review-contract.runtime.md` to every Deep review record. Do not load `<suite-root>/data/canonical-checks.json` or the full generated checklist into model context.

Related Domains (advisory only; never auto-expand direct scope): `evm-audit-access-control`, `evm-audit-chain-specific`.

## Maintenance View
- `references/checklist.md` is a generated human-readable reference view.
