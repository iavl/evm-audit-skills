---
name: evm-audit-access-control
description: EVM smart contract audit checklist for non-obvious access control issues. Covers centralization risks, privilege escalation, two-step ownership, role management, and admin rug vectors. Use when auditing protocols with privileged roles, admin functions, or governance. Load references/checklist.md for the full checklist.
---

# Access Control Audit Skill

## Overview
Non-obvious access control vulnerabilities beyond basic missing `onlyOwner` checks. Focuses on centralization risks, privilege escalation, and admin attack vectors.

## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use the canonical IDs from `../data/canonical-checks.json`.
2. Pattern matches are candidates, not findings; apply the feature filter before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- **references/checklist.md** — Full audit checklist, load this when auditing access control
