---
name: evm-audit-erc4626
description: ERC4626 vault standard vulnerabilities including inflation attacks, rounding direction, share price manipulation, first depositor attacks, compliance checks, and cross-chain vault issues. Load when auditing any ERC4626 vault or vault-like protocol.
---
# EVM Audit — ERC4626 Vault Vulnerabilities
Load when auditing any ERC4626 vault implementation or protocol that integrates with ERC4626 vaults.
## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use the canonical IDs from `../data/canonical-checks.json`.
2. Pattern matches are candidates, not findings; apply the feature filter before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- `references/checklist.md` — Full ERC4626 checklist
