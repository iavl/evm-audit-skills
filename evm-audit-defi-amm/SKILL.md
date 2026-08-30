---
name: evm-audit-defi-amm
description: AMM-specific vulnerabilities including Uniswap V3/V4 hooks, concentrated liquidity, swap routing, TWAMM, slippage, and DEX integration pitfalls. Load when auditing any AMM, DEX, swap router, or Uniswap V4 hook.
---
# EVM Audit — AMM & DEX Vulnerabilities
Load when auditing AMMs, DEXes, swap routers, Uniswap V4 hooks, or concentrated liquidity managers.
## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use canonical IDs embedded in the routed selected-check output.
2. Do not load `../data/canonical-checks.json` into model context; it is a machine-only source. Pattern matches are candidates, not findings; apply the tri-state predicate router before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- `references/checklist.md` — Generated maintenance/compatibility view; review selected check bodies emitted by the router instead of loading it wholesale.
