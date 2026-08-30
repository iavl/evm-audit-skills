---
name: evm-audit-governance
description: DAO governance vulnerabilities including flash loan voting, proposal execution ordering, timelock bypass, fake proposals via CREATE2, quorum manipulation, Gnosis Safe module bypasses, and reward distribution attacks. Load when auditing any governance system.
---
# EVM Audit — Governance & DAO Vulnerabilities
Load when auditing DAO voting, timelocks, proposal execution, multi-sig governance, or reward distribution.
## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use canonical IDs embedded in the routed selected-check output.
2. Do not load `../data/canonical-checks.json` into model context; it is a machine-only source. Pattern matches are candidates, not findings; apply the tri-state predicate router before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- `references/checklist.md` — Generated maintenance/compatibility view; review selected check bodies emitted by the router instead of loading it wholesale.
