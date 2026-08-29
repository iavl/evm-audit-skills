---
name: evm-audit-proxies
description: Proxy and upgrade vulnerabilities including UUPS, transparent proxy, beacon proxy, storage collisions, metamorphic contracts, initializer issues, and function selector clashing. Load when auditing any upgradeable contract.
---
# EVM Audit — Proxy & Upgrade Vulnerabilities
Load when auditing any upgradeable contract, proxy pattern, or diamond standard implementation.
## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use the canonical IDs from `../data/canonical-checks.json`.
2. Pattern matches are candidates, not findings; apply the feature filter before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- `references/checklist.md` — Full proxy/upgrade checklist
