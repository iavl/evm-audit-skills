---
name: evm-audit-access-control
description: EVM smart contract audit checklist for non-obvious access control issues. Covers centralization risks, privilege escalation, two-step ownership, role management, and admin rug vectors. Use when auditing protocols with privileged roles, admin functions, or governance; consume routed selected-check bodies at runtime.
---

# Access Control Audit Skill

## Overview
Non-obvious access control vulnerabilities beyond basic missing `onlyOwner` checks. Focuses on centralization risks, privilege escalation, and admin attack vectors.

## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use canonical IDs embedded in the routed selected-check output.
2. Do not load `../data/canonical-checks.json` into model context; it is a machine-only source. Pattern matches are candidates, not findings; apply the tri-state predicate router before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- **references/checklist.md** — Generated maintenance/compatibility view; review selected check bodies emitted by the router instead of loading it wholesale.
