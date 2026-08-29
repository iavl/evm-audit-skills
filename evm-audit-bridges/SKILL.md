---
name: evm-audit-bridges
description: Cross-chain bridge vulnerabilities for LayerZero V2, Chainlink CCIP, Wormhole, Across, and general bridge security. Covers message ordering, fee handling, relayer trust, dust/normalization, and configuration pitfalls. Load when auditing any cross-chain protocol.
---
# EVM Audit — Bridge & Cross-Chain Vulnerabilities
Load when auditing cross-chain bridges, messaging protocols, or any LayerZero/CCIP/Wormhole/Across integration.
## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use the canonical IDs from `../data/canonical-checks.json`.
2. Pattern matches are candidates, not findings; apply the feature filter before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- `references/checklist.md` — Full bridge/cross-chain checklist
