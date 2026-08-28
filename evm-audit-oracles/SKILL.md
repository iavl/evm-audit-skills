---
name: evm-audit-oracles
description: Oracle vulnerabilities including Chainlink staleness, minAnswer/maxAnswer circuit breakers, L2 sequencer uptime, TWAP manipulation, VRF front-running, spot price attacks, peg assumptions, and oracle decimal mismatches. Load when the contract uses any price oracle or external data feed.
---
# EVM Audit — Oracle & Pricing Vulnerabilities
Load when auditing contracts that use Chainlink, TWAP, VRF, Pyth, or any external price/data oracle.

When an oracle prices lending collateral or debt, pair feed-integrity checks with the Lending economic bound: `C_manipulation > V_extractable_borrow`. Pass effective liquidity depth, TWAP window, deviation threshold, caps, available liquidity, LTV, and liquidation threshold into that model. If the feed is AMM-backed, also load `evm-audit-defi-amm` to assess executable depth and price impact.

## Reference Files
- `references/checklist.md` — Full oracle checklist
