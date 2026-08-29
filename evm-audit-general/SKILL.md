---
name: evm-audit-general
description: General Solidity/EVM security checklist — non-obvious footguns that apply to every smart contract. Covers external calls, force-feeding, pause mechanisms, read-only reentrancy, merkle trees, code asymmetry, multicall hazards, and general EVM quirks. Load this for EVERY audit.
---

# EVM Audit — General Solidity/EVM Footguns

Load this for **every** EVM smart contract audit. These items are non-obvious issues that apply universally.

## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use the canonical IDs from `../data/canonical-checks.json`.
2. Pattern matches are candidates, not findings; apply the feature filter before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- `references/checklist.md` — Full dense checklist
