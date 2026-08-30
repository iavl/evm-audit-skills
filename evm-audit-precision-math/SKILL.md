---
name: evm-audit-precision-math
description: Precision loss, rounding errors, division ordering, fixed-point math, and mathematical edge cases in Solidity. Load this for EVERY audit — math bugs are the #1 source of DeFi exploits.
---
# EVM Audit — Precision & Math Vulnerabilities
Load for **every** audit. Math issues are the most common source of critical DeFi bugs.
## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use canonical IDs embedded in the routed selected-check output.
2. Do not load `../data/canonical-checks.json` into model context; it is a machine-only source. Pattern matches are candidates, not findings; apply the tri-state predicate router before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- `references/checklist.md` — Generated maintenance/compatibility view; review selected check bodies emitted by the router instead of loading it wholesale.
