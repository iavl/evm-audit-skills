---
name: evm-audit-erc4337
description: Security review for ERC4337 wallets, paymasters, bundlers, and account-abstraction infrastructure. Consume routed selected-check bodies at runtime.
---
# ERC4337 Account Abstraction Security

## Audit Contract
When invoked directly, run the shared pipeline for `evm-audit-erc4337` only:

Resolve `<suite-root>` as the parent directory containing this Skill, `data/`, and `scripts/`.

1. Run `python3 <suite-root>/scripts/recon.py <target> --output recon-features.json`.
2. Run `python3 <suite-root>/scripts/select_checks.py --feature-map recon-features.json --domain evm-audit-erc4337 --format json > routing-manifest.json`.
3. Run `python3 <suite-root>/scripts/select_checks.py --feature-map recon-features.json --domain evm-audit-erc4337 --emit-checks --profile compact --format markdown > selected-checks.runtime.md`.
4. Read `<suite-root>/evm-audit-master/references/check-review-contract.md`, review only the routed checks, and write `review-evm-audit-erc4337.md`.

Do not load `<suite-root>/data/canonical-checks.json` or the full generated checklist into model context. Apply the tri-state predicate router before deep review. Pattern matches are candidates, not findings. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and runnable PoC or deterministic invariant evidence.

Related domains (advisory only; never auto-expand direct scope): `evm-audit-signatures`, `evm-audit-access-control`.

## Maintenance View
- `references/checklist.md` is generated for maintenance and compatibility.
