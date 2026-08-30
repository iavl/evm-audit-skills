---
name: evm-audit-erc4626
description: ERC4626 vault standard vulnerabilities including inflation attacks, rounding direction, share price manipulation, first depositor attacks, compliance checks, and cross-chain vault issues. Load when auditing any ERC4626 vault or vault-like protocol.
---
# EVM Audit — ERC4626 Vault Vulnerabilities
Load when auditing any ERC4626 vault implementation or protocol that integrates with ERC4626 vaults.
## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use canonical IDs embedded in the routed selected-check output.
2. Do not load `../data/canonical-checks.json` into model context; it is a machine-only source. Pattern matches are candidates, not findings; apply the tri-state predicate router before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- `references/checklist.md` — Generated maintenance/compatibility view; review selected check bodies emitted by the router instead of loading it wholesale.
