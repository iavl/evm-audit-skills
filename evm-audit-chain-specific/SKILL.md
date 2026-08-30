---
name: evm-audit-chain-specific
description: Chain-specific EVM quirks for Arbitrum, Optimism, Base, zkSync, Blast, BNB, Berachain and other L2s. Covers block.number behavior, sequencer downtime, address aliasing, retryable tickets, opcode differences, gas fee variations, and PUSH0 support. Load when deploying to any non-mainnet EVM chain.
---
# EVM Audit — Chain-Specific Vulnerabilities
Load when auditing contracts deploying to Arbitrum, Optimism, Base, zkSync, Blast, BNB, or any L2.
## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use canonical IDs embedded in the routed selected-check output.
2. Do not load `../data/canonical-checks.json` into model context; it is a machine-only source. Pattern matches are candidates, not findings; apply the tri-state predicate router before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- `references/checklist.md` — Generated maintenance/compatibility view; review selected check bodies emitted by the router instead of loading it wholesale.
