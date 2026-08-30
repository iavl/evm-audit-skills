---
name: evm-audit-erc20
description: Weird ERC20 token edge cases that break protocols. Covers fee-on-transfer, rebasing, missing return values, blocklists, multiple addresses, flash minting, ERC777 hooks, approval race conditions, and more. Load when the contract interacts with ANY ERC20 tokens.
---

# EVM Audit — Weird ERC20 Edge Cases

Load when the contract interacts with **any** ERC20 tokens via transfers, approvals, or balances.

## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use canonical IDs embedded in the routed selected-check output.
2. Do not load `../data/canonical-checks.json` into model context; it is a machine-only source. Pattern matches are candidates, not findings; apply the tri-state predicate router before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- `references/checklist.md` — Generated maintenance/compatibility view; review selected check bodies emitted by the router instead of loading it wholesale.
