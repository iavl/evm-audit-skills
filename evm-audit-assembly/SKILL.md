---
name: evm-audit-assembly
description: Inline assembly, CREATE/CREATE2, EXTCODESIZE, and low-level opcode vulnerabilities. Covers metamorphic contracts, constructor-time code absence, assembly math overflow, and div-by-zero returning 0. Load when the contract uses inline assembly or CREATE2.
---
# EVM Audit — Assembly & Opcode Vulnerabilities
Load when auditing contracts that use inline assembly, Yul, CREATE/CREATE2, or low-level EVM opcodes.
## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use canonical IDs embedded in the routed selected-check output.
2. Do not load `../data/canonical-checks.json` into model context; it is a machine-only source. Pattern matches are candidates, not findings; apply the tri-state predicate router before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- `references/checklist.md` — Generated maintenance/compatibility view; review selected check bodies emitted by the router instead of loading it wholesale.
