---
name: evm-audit-signatures
description: Signature vulnerabilities including cross-chain replay, ecrecover pitfalls, EIP-712 domain separator issues, permit edge cases, malleability, and meta-transaction security. Load when the contract uses any off-chain signatures.
---
# EVM Audit — Signature Vulnerabilities
Load when auditing contracts that use ecrecover, EIP-712, permit, or any off-chain signature verification.
## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use canonical IDs embedded in the routed selected-check output.
2. Do not load `../data/canonical-checks.json` into model context; it is a machine-only source. Pattern matches are candidates, not findings; apply the tri-state predicate router before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- `references/checklist.md` — Generated maintenance/compatibility view; review selected check bodies emitted by the router instead of loading it wholesale.
