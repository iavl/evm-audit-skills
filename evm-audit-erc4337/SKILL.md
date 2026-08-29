---
name: evm-audit-erc4337
description: Account abstraction (ERC-4337) vulnerabilities including wallet factories, paymaster replay, session keys, EntryPoint bugs, ERC-1271 cross-account replay, and module security. Load when auditing smart wallets, paymasters, or AA infrastructure.
---
# EVM Audit — ERC4337 Account Abstraction Vulnerabilities
Load when auditing smart wallets, paymasters, bundlers, or account abstraction infrastructure.
## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use the canonical IDs from `../data/canonical-checks.json`.
2. Pattern matches are candidates, not findings; apply the feature filter before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- `references/checklist.md` — Full ERC4337 checklist
