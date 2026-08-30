---
name: evm-audit-flashloans
description: EVM smart contract audit checklist for flash loan attack patterns. Covers flash loan governance attacks, oracle manipulation via flash loans, flash deposit-withdraw attacks, and flash mint inflation. Use when auditing DeFi protocols vulnerable to single-transaction economic attacks; consume routed selected-check bodies at runtime.
---

# Flash Loan Attack Patterns Audit Skill

## Overview
Flash loan attack vectors for DeFi protocols. Focuses on how single-transaction unlimited capital changes the threat model.

## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use canonical IDs embedded in the routed selected-check output.
2. Do not load `../data/canonical-checks.json` into model context; it is a machine-only source. Pattern matches are candidates, not findings; apply the tri-state predicate router before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- **references/checklist.md** — Generated maintenance/compatibility view; review selected check bodies emitted by the router instead of loading it wholesale.
