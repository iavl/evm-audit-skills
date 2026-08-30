---
name: evm-audit-bridges
description: Cross-chain bridge vulnerabilities for LayerZero V2, Chainlink CCIP, Wormhole, Across, and general bridge security. Covers message ordering, fee handling, relayer trust, dust/normalization, and configuration pitfalls. Load when auditing any cross-chain protocol.
---
# EVM Audit — Bridge & Cross-Chain Vulnerabilities
Load when auditing cross-chain bridges, messaging protocols, or any LayerZero/CCIP/Wormhole/Across integration.
## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use canonical IDs embedded in the routed selected-check output.
2. Do not load `../data/canonical-checks.json` into model context; it is a machine-only source. Pattern matches are candidates, not findings; apply the tri-state predicate router before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- `references/checklist.md` — Generated maintenance/compatibility view; review selected check bodies emitted by the router instead of loading it wholesale.
