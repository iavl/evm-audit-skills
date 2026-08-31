---
name: evm-audit-erc721
description: Security review for ERC721, ERC1155, NFT implementations, and NFT integrations. Consume routed selected-check bodies at runtime.
---
# ERC721 and ERC1155 Security

## Review Focus

Security review for ERC721, ERC1155, NFT implementations, and NFT integrations.

## Required Context

- `accepted_nft_standards`: accepted ERC721/ERC1155 standards and token assumptions
- `receiver_hooks`: receiver callbacks and hook behavior
- `approval_model`: approval, operator, and transfer authorization model
- `custody_model`: custody, ownership, and escrow model

## Review Requirements

- trace ownership, callback, and transfer compatibility

## Runtime Modes

Standalone: `python3 <suite-root>/scripts/audit_run.py init <target> --run-dir <run-dir> --domain evm-audit-erc721`. Run `next` until the next template or runtime view is ready, resolve only the generated evidence-bound templates, then use `status` and `report`.

Orchestrated: consume the Master-provided immutable routing artifacts and Screen/Deep views. Never rerun Recon or Selector in orchestrated mode.

The tri-state predicate router is conservative: `UNKNOWN` stays selected/deferred, and trusted absence is the only filter. Pattern matches are candidates, not findings. `NOT_APPLICABLE` requires complete scope and exclusion evidence; a finding requires a reachable path, exploitable preconditions, concrete impact, and runnable PoC or deterministic invariant evidence.

Apply `<suite-root>/skills/evm-audit-master/references/check-review-contract.runtime.md` to every Deep review record. Do not load `<suite-root>/data/canonical-checks.json` or the full generated checklist into model context.

Related Domains (advisory only; never auto-expand direct scope): `evm-audit-general`, `evm-audit-access-control`.

## Maintenance View
- `references/checklist.md` is a generated human-readable reference view.
