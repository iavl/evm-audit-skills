---
name: evm-audit-general
description: General Solidity/EVM security checklist — non-obvious footguns that apply to every smart contract. Covers external calls, force-feeding, pause mechanisms, read-only reentrancy, merkle trees, code asymmetry, multicall hazards, and general EVM quirks. Load this for EVERY audit.
---

# EVM Audit — General Solidity/EVM Footguns

Load this for **every** EVM smart contract audit. These items are non-obvious issues that apply universally.

## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use canonical IDs embedded in the routed selected-check output.
2. Do not load `../data/canonical-checks.json` into model context; it is a machine-only source. Pattern matches are candidates, not findings; apply the tri-state predicate router before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- `references/checklist.md` — Generated maintenance/compatibility view; review selected check bodies emitted by the router instead of loading it wholesale.
