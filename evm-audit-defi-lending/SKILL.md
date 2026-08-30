---
name: evm-audit-defi-lending
description: CDP, lending market, liquidation, and borrowing vulnerabilities. Covers collateral handling, health factors, auction liquidations, bad debt, interest accrual, and lending protocol integration (AAVE, Compound). Load when auditing any lending/borrowing protocol.
---
# EVM Audit — Lending & Liquidation Vulnerabilities
Load when auditing CDPs, lending markets, liquidation mechanisms, or AAVE/Compound forks.

For every oracle-backed collateral or debt valuation, do not stop at verifying that the feed call, decimals, and staleness checks are correct. Build the economic bound in `references/checklist.md`: `C_manipulation > V_extractable_borrow`, using liquidity depth, TWAP window, deviation threshold, borrow/supply caps, available liquidity, LTV, and liquidation threshold. Load `evm-audit-oracles` for feed behavior and `evm-audit-defi-amm` when the price source depends on AMM liquidity.

## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use canonical IDs embedded in the routed selected-check output.
2. Do not load `../data/canonical-checks.json` into model context; it is a machine-only source. Pattern matches are candidates, not findings; apply the tri-state predicate router before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- `references/checklist.md` — Generated maintenance/compatibility view; review selected check bodies emitted by the router instead of loading it wholesale.
