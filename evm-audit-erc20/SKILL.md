---
name: evm-audit-erc20
description: Weird ERC20 token edge cases that break protocols. Covers fee-on-transfer, rebasing, missing return values, blocklists, multiple addresses, flash minting, ERC777 hooks, approval race conditions, and more. Load when the contract interacts with ANY ERC20 tokens.
---

# EVM Audit — Weird ERC20 Edge Cases

Load when the contract interacts with **any** ERC20 tokens via transfers, approvals, or balances.

## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use the canonical IDs from `../data/canonical-checks.json`.
2. Pattern matches are candidates, not findings; apply the feature filter before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- `references/checklist.md` — Full dense checklist of every weird ERC20 behavior
