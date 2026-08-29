---
name: evm-audit-dos
description: EVM smart contract audit checklist for denial-of-service and griefing attacks. Covers gas griefing, unbounded loops, returndata bombing, block stuffing, and DoS via revert. Use when auditing protocols with loops, external calls, or time-sensitive operations. Load references/checklist.md for the full checklist.
---

# DoS & Griefing Audit Skill

## Overview
Denial-of-service and griefing attack patterns in smart contracts. Focuses on gas exhaustion, revert-based DoS, and economic griefing.

## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use the canonical IDs from `../data/canonical-checks.json`.
2. Pattern matches are candidates, not findings; apply the feature filter before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- **references/checklist.md** — Full audit checklist, load this when auditing for DoS/griefing
