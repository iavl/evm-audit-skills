---
name: evm-audit-flashloans
description: EVM smart contract audit checklist for flash loan attack patterns. Covers flash loan governance attacks, oracle manipulation via flash loans, flash deposit-withdraw attacks, and flash mint inflation. Use when auditing DeFi protocols vulnerable to single-transaction economic attacks. Load references/checklist.md for the full checklist.
---

# Flash Loan Attack Patterns Audit Skill

## Overview
Flash loan attack vectors for DeFi protocols. Focuses on how single-transaction unlimited capital changes the threat model.

## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use the canonical IDs from `../data/canonical-checks.json`.
2. Pattern matches are candidates, not findings; apply the feature filter before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- **references/checklist.md** — Full audit checklist, load this when auditing for flash loan vulnerabilities
