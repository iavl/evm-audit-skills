<!-- GENERATED FILE: source is ../../data/canonical-checks.json; do not edit by hand. -->
# Lending & Liquidation Security Checklist

Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.

## Liquidation Mechanics

- [ ] **[EVM-LEND-001] Self-liquidation for profit** _(exploit-pattern; medium)_: If liquidation bonus exceeds gas + price impact, a user can borrow, let position go underwater, and liquidate themselves to net the bonus. Check if the liquidation incentive is small enough that self-liquidation is unprofitable, and whether a permissionless oracle update can be followed immediately by liquidation without a delay or cooldown. Look for: liquidation functions callable by the position owner or oracle-update paths whose price can be consumed in the same transaction/window. [beirao LEN-02, Decurity CDP]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao LEN-02, Decurity CDP

- [ ] **[EVM-LEND-002] No liquidation incentive** _(exploit-pattern; medium)_: Trustless liquidators need positive net compensation after gas, debt repayment, fees, and price impact. If liquidation provides no reward or the net reward can be zero for valid positions, underwater positions may remain unliquidated and bad debt accumulates. Look for: liquidation paths with no liquidator compensation or no profitability analysis across valid positions. [Source: Auditmos `audit-liquidation`, pattern #1](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-liquidation/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [AUDITMOS-LIQUIDATION-1](https://github.com/auditmos/skills); [https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-liquidation/reference.md](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-liquidation/reference.md); Source: Auditmos `audit-liquidation`, pattern #1

- [ ] **[EVM-LEND-003] Paused collateral token blocks defense** _(exploit-pattern; medium)_: If a collateral token is paused (USDC, USDT have pause), users can't add collateral or repay debt, but can still be liquidated. This creates unfair liquidation. Look for: collateral tokens with pause functionality and whether the protocol handles it. [beirao LEN-03, LEN-07]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao LEN-03, LEN-07

- [ ] **[EVM-LEND-004] Large price drops make liquidation unprofitable** _(exploit-pattern; medium)_: If oracle price drops 50%+ in one update (Maker Black Thursday scenario), the liquidation bonus may not cover the liquidator's cost. Liquidators won't participate, leaving bad debt. Look for: liquidation incentive size vs potential price drop scenarios. [beirao LEN-04, Sigmaprime oracles]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao LEN-04, Sigmaprime oracles

- [ ] **[EVM-LEND-005] Small positions unincentivized** _(exploit-pattern; medium)_: Gas costs for liquidating a $10 position may exceed the liquidation bonus. These tiny positions accumulate as bad debt. Look for: minimum position size enforcement or gas-subsidized liquidation. [beirao LEN-09]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao LEN-09

- [ ] **[EVM-LEND-006] No bad-debt recovery mechanism** _(exploit-pattern; medium)_: When debt exceeds collateral, liquidation needs an explicit insurance, reserve, socialization, or loss-accounting path. If the implementation assumes every position can repay in full, insolvent positions can revert or leave protocol accounting insolvent. Look for: liquidation code with no branch for debt greater than seized collateral and no documented loss coverage mechanism. [Source: Auditmos `audit-liquidation`, pattern #4](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-liquidation/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [AUDITMOS-LIQUIDATION-4](https://github.com/auditmos/skills); [https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-liquidation/reference.md](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-liquidation/reference.md); Source: Auditmos `audit-liquidation`, pattern #4

- [ ] **[EVM-LEND-007] Front-running liquidation with dust collateral** _(exploit-pattern; medium)_: An attacker watches the mempool, sees a liquidation transaction, and front-runs it by adding 1 wei of collateral — just enough to make the position healthy and revert the liquidation. Look for: liquidation functions that re-check health factor without minimum improvement threshold. [beirao LEN-08]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao LEN-08

- [ ] **[EVM-LEND-008] Liquidation pause + unpause = cascading crisis** _(exploit-pattern; medium)_: When liquidations are paused (oracle issues, upgrades) and then unpaused, all positions that became unhealthy during the pause are liquidatable simultaneously. Mass liquidations can cascade through shared collateral pools. Look for: time-based position accumulation during pause periods. [beirao LEN-06]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao LEN-06

- [ ] **[EVM-LEND-009] Liquidator receives less than expected** _(exploit-pattern; medium)_: If liquidation uses a swap to convert collateral, slippage during the swap may make the liquidation unprofitable. Look for: swap-based liquidation without slippage protection. [beirao LEN-05]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao LEN-05

- [ ] **[EVM-LEND-010] Cannot repay loan = permanent bad debt** _(exploit-pattern; medium)_: If `repay()` can enter a state where it always reverts — for example because a required token or dependency is paused, a repayment condition is impossible, interest overflows, or accounting contains a logic error — the borrower cannot close the loan and the lender may never be repaid. Look for: repay functions with external dependencies or state-dependent conditions that can permanently block repayment. [Decurity CDP, Dacian — Lending/Borrowing DeFi Attacks]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Decurity CDP, Dacian — Lending/Borrowing DeFi Attacks

- [ ] **[EVM-LEND-011] No partial liquidation for whale positions** _(exploit-pattern; medium)_: If positions can exceed one liquidator's capital or transaction capacity and only full closure is supported, large underwater positions may remain unliquidated and accumulate bad debt. Look for: full-close-only liquidation with no bounded partial amount, batching, or other path for large positions. [Source: Auditmos `audit-liquidation`, pattern #6](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-liquidation/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [AUDITMOS-LIQUIDATION-6](https://github.com/auditmos/skills); [https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-liquidation/reference.md](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-liquidation/reference.md); Source: Auditmos `audit-liquidation`, pattern #6

- [ ] **[EVM-LEND-012] Single borrower can't be liquidated** _(exploit-pattern; medium)_: Some implementations skip liquidation when `borrowerCount == 1`, leaving the last borrower immune during protocol sunsetting or single-position cleanup. Look for: liquidation loops and terminal-position branches with `count > 1` or equivalent conditions. [ERC4626 primer pattern #18, Dacian — DeFi Liquidation Vulnerabilities, Cyfrin Bima]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 primer pattern #18, Dacian — DeFi Liquidation Vulnerabilities, Cyfrin Bima

- [ ] **[EVM-LEND-013] Liquidation before grace period** _(exploit-pattern; medium)_: After repayments resume following a pause, borrowers need a grace period to repay; immediately liquidating positions that became unhealthy during the pause is unfair and MEV-sensitive. Look for: post-unpause liquidation without a pause-duration-based or otherwise enforced delay. [ERC4626 primer, Dacian — Lending/Borrowing DeFi Attacks]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 primer, Dacian — Lending/Borrowing DeFi Attacks

- [ ] **[EVM-LEND-014] Forced loan assignment without lender consent** _(exploit-pattern; medium)_: `buyLoan()` or equivalent transfer paths must not let an actor assign a loan to an unwilling lender. Look for: loan ownership transfers that omit lender consent, a lender whitelist, or an equivalent acceptance rule. [Source: Auditmos `audit-lending`, pattern #9](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-lending/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [AUDITMOS-LENDING-9](https://github.com/auditmos/skills); [https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-lending/reference.md](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-lending/reference.md); Source: Auditmos `audit-lending`, pattern #9

## Auction Liquidations

- [ ] **[EVM-LEND-015] Self-bidding can reset an auction indefinitely** _(exploit-pattern; medium)_: If a borrower can bid on their own auction and a winning bid resets the timer, they can repeatedly delay seizure while debt continues to accumulate. Look for: no bidder-versus-borrower/owner separation or unconditional timer resets on self-bids. [Source: Auditmos `audit-auction`, pattern #1](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-auction/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [AUDITMOS-AUCTION-1](https://github.com/auditmos/skills); [https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-auction/reference.md](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-auction/reference.md); Source: Auditmos `audit-auction`, pattern #1

- [ ] **[EVM-LEND-016] Flash loan to prove solvency during auction** _(exploit-pattern; medium)_: If a liquidated user can prove solvency to cancel an auction, they can flash-loan collateral, cancel, then return it. Look for: auction cancel functions that don't prevent flash loans. [Decurity CDP]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Decurity CDP

- [ ] **[EVM-LEND-017] Incomplete or too-short auction launch** _(exploit-pattern; medium)_: Missing input validation when starting an auction can create auctions in invalid states; accepting a near-zero duration can enable immediate seizure without competitive bidding. Look for: auction start functions without parameter bounds or an enforced minimum duration. [Decurity CDP]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Decurity CDP

- [ ] **[EVM-LEND-018] Partial collateral auction math** _(exploit-pattern; medium)_: When only a portion of collateral is auctioned, the split and the remaining collateral-to-debt ratio must be exact. Rounding errors can leave dust, overvalue the remainder, or under-collateralize the remaining position. Look for: partial liquidation and auction functions that do not recompute the remaining position's health. [Decurity CDP]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Decurity CDP

- [ ] **[EVM-LEND-019] Interrupted bid funds not returned** _(exploit-pattern; medium)_: If a bidder is outbid, a debtor repays, or an auction is cancelled/prematurely closed, every affected bidder's escrow must be returned exactly once. Look for: bid escrow that does not track and refund all higher-bid, repayment, cancellation, and interruption paths. [Decurity CDP]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Decurity CDP

## CDP-Specific

- [ ] **[EVM-LEND-020] Closed vault storage not cleaned** _(exploit-pattern; medium)_: When a CDP is closed after debt repayment, stale storage fields or nested mapping data can make later reads treat the vault as active or reuse old collateral/debt. Look for: close functions that do not clear the storage struct/mapping entry and subsequent paths that do not enforce an explicit existence flag. [Decurity CDP]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Decurity CDP

- [ ] **[EVM-LEND-021] Pool value calculation with fee split** _(exploit-pattern; medium)_: If borrower fees split between lender and pool, verify both calculations sum correctly and neither path rounds in the wrong direction. Look for: fee distribution math with multiple recipients. [Decurity CDP]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Decurity CDP

- [ ] **[EVM-LEND-022] Stablecoin collateral arbitrage across assets** _(exploit-pattern; medium)_: If a CDP treats multiple stablecoins as equivalent at 1:1, an attacker can deposit a depegged stablecoin, swap collateral types, or borrow against it at full value. Look for: stablecoin collateral and cross-asset withdrawals without independent prices or depeg checks. [Decurity CDP]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Decurity CDP

- [ ] **[EVM-LEND-023] Health ratio checked AFTER safeTransferFrom** _(exploit-pattern; medium)_: ERC721 `safeTransferFrom` calls `onERC721Received` callback before the health ratio check. An attacker can reenter during the callback when the health ratio is invalid. Look for: health factor checks after `safeTransferFrom` or `_safeMint`. [Decurity CDP]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Decurity CDP

- [ ] **[EVM-LEND-024] Interest accrual ordering around close and liquidation** _(heuristic; contextual)_: Interest must be accrued at the intended point before debt settlement, health checks, liquidation, or vault closure. Wrong ordering can use stale debt, charge too much or too little interest, or create a timing window between the check and execution. Look for: close/liquidation paths whose accrual timing differs from the protocol's stated accounting model. [Decurity CDP]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Decurity CDP

## AAVE/Compound Integration

- [ ] **[EVM-LEND-025] High utilization blocks withdrawal** _(exploit-pattern; medium)_: At 100% utilization rate, lenders can't withdraw their deposits. The protocol should handle this gracefully rather than reverting. Look for: integrations that assume utilization is below 100% or do not handle an external pool's unavailable liquidity. [beirao AC-01]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao AC-01

- [ ] **[EVM-LEND-026] AAVE siloed asset prohibition** _(exploit-pattern; medium)_: Borrowing a siloed asset on AAVE prohibits borrowing ANY other asset. If an integration auto-selects or fails to check `getSiloedBorrowing()`, subsequent borrow operations fail and can lock a position. Look for: AAVE borrow paths without siloed-asset checks. [beirao AC-08]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao AC-08

- [ ] **[EVM-LEND-027] AAVE flashloans inflate pool index** _(exploit-pattern; medium)_: Each AAVE flashloan slightly inflates the pool index. Max 180 flashloans per block. This can be used to manipulate lending rates. Look for: rate-sensitive logic that doesn't account for flashloan-induced index inflation. [beirao AC-05]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao AC-05

- [ ] **[EVM-LEND-028] AAVE isolated-asset debt cap can block borrowing** _(exploit-pattern; medium)_: On AAVE, when the debt ceiling for an isolated asset is reached, all new borrows revert. An attacker can fill the ceiling to DoS other users. Look for: borrow paths against AAVE isolated markets without checking remaining capacity. [beirao AC-09]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao AC-09

- [ ] **[EVM-LEND-029] Paused AAVE/Compound market blocks integration** _(exploit-pattern; medium)_: If the integrated market is paused, deposit, withdrawal, borrow, and repayment calls can all revert. The wrapper needs an explicit fallback or user-safe handling path. Look for: external lending calls without pause-aware behavior. [beirao AC-02]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao AC-02

- [ ] **[EVM-LEND-030] Deprecated AAVE/Compound pool can strand funds** _(exploit-pattern; medium)_: A deprecated pool may change behavior or stop supporting operations while positions remain. Look for: long-lived integrations that do not monitor pool status or provide migration and withdrawal handling. [beirao AC-03]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao AC-03

- [ ] **[EVM-LEND-031] eMode category interactions** _(exploit-pattern; medium)_: If the protocol's assets are in the same eMode category on AAVE, liquidation parameters are different. Look for: eMode-specific LTV/threshold values not accounted for. [beirao AC-04]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao AC-04

- [ ] **[EVM-LEND-032] AAVE/Compound reward claims** _(exploit-pattern; medium)_: If the protocol deposits user funds in AAVE/Compound, reward token claims (COMP, stkAAVE) must be properly distributed to users. Look for: missing reward claim functionality or rewards stuck in contract. [beirao AC-06]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao AC-06

## Oracle-to-Borrow Economic Safety

- [ ] **[EVM-LEND-033] Oracle manipulation cost must exceed maximum extractable borrow value** _(exploit-pattern; medium)_: An oracle-backed lending market can be profitable to attack even when the feed call, decimals, and staleness checks are correct. For a price move of `ΔP` held over horizon `H`, require `C_manipulation(ΔP, H) > V_extractable_borrow(ΔP)`. `C_manipulation` is the minimum cost to move and maintain the reported price, including effective liquidity depth, price impact, swap fees, flash-loan or funding fees, gas, MEV, and the cost of unwinding. `V_extractable_borrow` is the maximum net value that can be borrowed while the manipulated price is accepted.
  - **Trigger:** An oracle-backed lending market can be profitable to attack even when the feed call, decimals, and staleness checks are correct. For a price move of `ΔP` held over horizon `H`, require `C_manipulation(ΔP, H) > V_extractable_borrow(ΔP)`. `C_manipulation` is the minimum cost to move and maintain the reported price, including effective liquidity depth, price impact, swap fees, flash-loan or funding fees, gas, MEV, and the cost of unwinding. `V_extractable_borrow` is the maximum net value that can be borrowed while the manipulated price is accepted. Raw spot or shallow AMM liquidity used for collateral/debt pricing; a TWAP window shorter than the attacker's affordable holding horizon; a deviation threshold that only delays updates or is derived from the same manipulable source; borrow cap or supply cap checks performed for only one route or market; available borrow liquidity larger than the modeled cap; LTV set close to the liquidation threshold with no buffer for oracle latency and liquidation costs; or a model that uses a fixed TVL heuristic instead of executable depth and price impact.
  - **FP:** No finding when a conservative stress model covers both overvalued-collateral and undervalued-debt directions across every reachable market, and the inequality remains strict after fees, oracle latency, available liquidity, borrow cap, supply cap, LTV, liquidation threshold, and liquidation costs are applied. A circuit breaker that prevents borrowing or collateral changes at the affected price may also close the path.
  - **Proof:** Build one matrix per collateral/debt asset and market with: price source; effective liquidity depth (not aggregate TVL); target `ΔP`; TWAP window or feed heartbeat; deviation threshold; remaining borrow cap; remaining supply cap; available borrow liquidity; LTV; liquidation threshold; and the resulting manipulation cost and maximum extractable borrow value. Model a one-transaction spot attack and the capital/time required to hold a TWAP distortion for the full window. Test both increasing collateral value and decreasing debt value, then recurse through cross-market, isolated/eMode, and collateral-supply routes to find the maximum extraction. Record the safety margin rather than treating any single parameter as a proof of safety.
  - **Provenance:** legacy-checklist
  - **Source detail:** Cross-domain economic invariant synthesizing the existing Oracle, Lending, and liquidation checks.

## LP Token Collateral

- [ ] **[EVM-LEND-034] LP token valuation via `pool.getReserves()` is manipulable** _(exploit-pattern; medium)_: Flash loans can manipulate reserves to inflate LP token value, allowing over-borrowing. Must use fair pricing formulas (e.g., Alpha Homora's formula). Look for: LP token price calculations using raw reserve amounts. [Decurity CDP]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Decurity CDP

- [ ] **[EVM-LEND-035] Multiple pool types for same pair** _(exploit-pattern; medium)_: Uniswap has 0.01%, 0.05%, 0.3%, 1% fee tiers for the same token pair. Each has different LP token value. Look for: LP token handling that doesn't account for fee tier differences. [Decurity CDP]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Decurity CDP

## Earn/Yield-Bearing Collateral

- [ ] **[EVM-LEND-036] Pegged asset collateral depeg risk** _(exploit-pattern; medium)_: renBTC, WBTC, stETH as collateral — if they depeg, counting them 1:1 with the underlying asset creates bad debt instantly. Look for: pegged-asset collateral priced without its own oracle feed. [Decurity CDP]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Decurity CDP

- [ ] **[EVM-LEND-037] Staked collateral share manipulation** _(exploit-pattern; medium)_: If collateral is staked in an external protocol, the share calculation can be manipulated if it depends on instantaneous balance. Look for: share-based collateral valuation without TWAP or time-weighted averaging. [Decurity CDP]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Decurity CDP

## Lending Integration (AAVE/Compound - from Beirao)

- [ ] **[EVM-LEND-038] cETH has no `underlying()` function** _(exploit-pattern; medium)_: Compound's cETH token doesn't implement `underlying()` (since its underlying is native ETH). Code that calls `cToken.underlying()` generically will revert on cETH. Look for: generic Compound integrations that call `underlying()` on all cTokens. [beirao AC-07]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao AC-07
  - **Notes:** ---

## Dacian — Lending/Borrowing DeFi Attacks (Phase 3)

- [ ] **[EVM-LEND-039] Liquidation before default — paymentDefaultDuration < paymentCycleDuration** _(exploit-pattern; medium)_: If the liquidation threshold timer starts from `acceptedTimestamp` (loan acceptance) rather than the next payment due date, borrowers can be liquidated before their first repayment is even due when `paymentDefaultDuration` is small. Fix: calculate liquidation threshold as offset from when the next repayment is due. [Source: Dacian — Lending/Borrowing DeFi Attacks, Sherlock TellerV2]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — Lending/Borrowing DeFi Attacks, Sherlock TellerV2

- [ ] **[EVM-LEND-040] Liquidation via unchecked collateralToken parameter** _(exploit-pattern; medium)_: If `liquidate(collateralToken, position)` doesn't validate that `collateralToken` actually corresponds to the position's collateral, an attacker can pass address(0) or a different token to force the collateral valuation to 0, triggering liquidation of non-defaulting borrowers. [Source: Dacian — Lending/Borrowing DeFi Attacks, Hats Finance Tempus Raft]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — Lending/Borrowing DeFi Attacks, Hats Finance Tempus Raft

- [ ] **[EVM-LEND-041] Borrower overwrites collateral to zero via unchecked AddressSet.add()** _(exploit-pattern; medium)_: If `commitCollateral()` uses `EnumerableSetUpgradeable.AddressSet.add()` without checking its boolean return value, calling it again with the same token and 0 amount silently overwrites the collateral record. Borrowers can zero their collateral after loan validation. [Source: Dacian — Lending/Borrowing DeFi Attacks, Sherlock TellerV2]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — Lending/Borrowing DeFi Attacks, Sherlock TellerV2

- [ ] **[EVM-LEND-042] Debt closed without repayment via non-existent ID decrement** _(exploit-pattern; medium)_: If `close(id)` doesn't validate that `id` exists in the credits mapping, calling with non-existent IDs still decrements the loan `count` variable. Repeatedly calling with bogus IDs gets `count == 0`, marking the loan as fully repaid. [Source: Dacian — Lending/Borrowing DeFi Attacks, Code4rena DebtDAO]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — Lending/Borrowing DeFi Attacks, Code4rena DebtDAO

- [ ] **[EVM-LEND-043] Token disallow stops existing loan repayment but not liquidation** _(exploit-pattern; medium)_: If `repay()` has `onlyWhitelistedToken` modifier but `liquidate()` doesn't, disallowing a previously-allowed token creates an asymmetric state where borrowers can't repay but can be liquidated. Token disallow should only affect new loans. [Source: Dacian — Lending/Borrowing DeFi Attacks, Sherlock Blueberry Update 1]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — Lending/Borrowing DeFi Attacks, Sherlock Blueberry Update 1

- [ ] **[EVM-LEND-044] Liquidator takes all collateral by repaying smallest debt position** _(exploit-pattern; medium)_: If liquidation share calculation uses `share / oldShare` from a single position rather than total debt across all positions, a liquidator can drain all collateral by repaying only the smallest debt tranche. [Source: Dacian — Lending/Borrowing DeFi Attacks, Sherlock Blueberry]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — Lending/Borrowing DeFi Attacks, Sherlock Blueberry

- [ ] **[EVM-LEND-045] Infinite loan rollover** _(exploit-pattern; medium)_: If the borrower can rollover their loan without any limit on count, duration, or lender approval, the lender may never be repaid and never be able to liquidate. [Source: Dacian — Lending/Borrowing DeFi Attacks, Sherlock Cooler; ERC4626 primer]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — Lending/Borrowing DeFi Attacks, Sherlock Cooler; ERC4626 primer

- [ ] **[EVM-LEND-046] Repayment sent to zero address after storage deletion** _(exploit-pattern; medium)_: If `loans[loanID]` is deleted before `debt.transferFrom(msg.sender, loan.lender, repaid)`, `loan.lender` resolves to address(0). Many ERC20s will silently succeed, losing the repayment forever. [Source: Dacian — Lending/Borrowing DeFi Attacks, Sherlock Cooler]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** loanID; Source: Dacian — Lending/Borrowing DeFi Attacks, Sherlock Cooler

- [ ] **[EVM-LEND-047] Borrower permanently unable to repay — repay() always reverts** _(exploit-pattern; medium)_: If the system can enter a state where `repay()` always reverts (e.g., due to token accounting bugs, whitelist changes, or paused dependencies), both borrower and lender lose — borrower loses collateral to liquidation, lender never gets repaid. [Source: Dacian — Lending/Borrowing DeFi Attacks]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — Lending/Borrowing DeFi Attacks

- [ ] **[EVM-LEND-048] Bulk repayment overflow not credited to subsequent loans** _(exploit-pattern; medium)_: When a borrower's single repayment amount exceeds the first loan's remaining debt, the excess must roll over to pay subsequent loans. If it doesn't, the borrower's total repayment is only partially credited while lender receives full amount. [Source: Dacian — Lending/Borrowing DeFi Attacks, Sherlock Astaria]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — Lending/Borrowing DeFi Attacks, Sherlock Astaria

- [ ] **[EVM-LEND-049] Liquidation leaves traders with unhealthier collateral basket** _(exploit-pattern; medium)_: If multi-collateral liquidation uses the more stable collaterals first instead of the riskiest, post-liquidation positions have worse risk profiles. Liquidation should prioritize less stable, riskier collateral. [Source: Dacian — Lending/Borrowing DeFi Attacks, Cyfrin Zaros]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — Lending/Borrowing DeFi Attacks, Cyfrin Zaros

## Dacian — DeFi Liquidation Vulnerabilities (Phase 3)

- [ ] **[EVM-LEND-050] Liquidator reward paid after competing fees** _(exploit-pattern; medium)_: If protocol fees or penalties are deducted before the liquidator reward, a valid liquidation can leave zero or uneconomic compensation and reduce the supply of liquidators. Look for: fee distribution order where the liquidator is paid from the remainder after other deductions, without a positive-reward check. [Source: Auditmos `audit-liquidation-calculation`, pattern #2](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-liquidation-calculation/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [AUDITMOS-LIQUIDATION-CALCULATION-2](https://github.com/auditmos/skills); [https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-liquidation-calculation/reference.md](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-liquidation-calculation/reference.md); Source: Auditmos `audit-liquidation-calculation`, pattern #2

- [ ] **[EVM-LEND-051] Liquidation swap omits the protocol swap fee** _(exploit-pattern; medium)_: When liquidation swaps collateral into the debt token, bypassing the normal swap fee understates protocol revenue and can invalidate economic assumptions. This is an economic-loss check, not by itself a direct exploit. Look for: liquidation-only swap paths that do not apply the protocol's normal fee or route the fee to the treasury. [Source: Auditmos `audit-liquidation-calculation`, pattern #6](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-liquidation-calculation/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [AUDITMOS-LIQUIDATION-CALCULATION-6](https://github.com/auditmos/skills); [https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-liquidation-calculation/reference.md](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-liquidation-calculation/reference.md); Source: Auditmos `audit-liquidation-calculation`, pattern #6

- [ ] **[EVM-LEND-052] Profitable user withdraws all collateral, removing liquidation incentive** _(exploit-pattern; medium)_: In perpetuals, users with large positive PNL can withdraw all deposited collateral while remaining solvent. If PNL reverses, there's nothing to seize for liquidation reward. Fix: enforce minimum collateral deposit regardless of PNL. [Source: Dacian — DeFi Liquidation Vulnerabilities]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — DeFi Liquidation Vulnerabilities

- [ ] **[EVM-LEND-053] Partial liquidation bypasses bad debt accounting** _(exploit-pattern; medium)_: If bad debt coverage check only triggers on full position closure (`if (!hasPosition)`), a partial liquidator can strategically avoid closing the position entirely, bypassing the requirement to cover bad debt. [Source: Dacian — DeFi Liquidation Vulnerabilities, Code4rena Predy]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — DeFi Liquidation Vulnerabilities, Code4rena Predy

- [ ] **[EVM-LEND-054] EnumerableSet ordering corruption prevents multi-position liquidation** _(exploit-pattern; medium)_: When liquidating accounts with multiple active markets, iterating over `EnumerableSet` while removing elements causes swap-and-pop ordering corruption, resulting in `panic: array out-of-bounds`. Fix: iterate over `values()` memory copy. [Source: Dacian — DeFi Liquidation Vulnerabilities, Cyfrin Zaros]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — DeFi Liquidation Vulnerabilities, Cyfrin Zaros

- [ ] **[EVM-LEND-055] Front-running liquidation via nonce increment or micro self-liquidation** _(exploit-pattern; medium)_: If user-controlled variables (nonce, cooldown timer) are checked during liquidation, a liquidatable user can front-run the liquidation tx to change these variables, forcing the liquidation to revert. [Source: Dacian — DeFi Liquidation Vulnerabilities]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — DeFi Liquidation Vulnerabilities

- [ ] **[EVM-LEND-056] Pending withdrawal blocks liquidation** _(exploit-pattern; medium)_: If liquidation checks `require(balance - pendingWithdrawals > 0)`, a user can create a pending withdrawal equal to balance, making all subsequent liquidation attempts revert. [Source: Dacian — DeFi Liquidation Vulnerabilities, Dolomite]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — DeFi Liquidation Vulnerabilities, Dolomite

- [ ] **[EVM-LEND-057] ERC721 onReceived callback reverts liquidation** _(exploit-pattern; medium)_: If an NFT is "pushed" to a user-controlled address during liquidation, the attacker can revert in `onERC721Received`, making liquidation impossible. Same applies to ERC20 tokens with transfer hooks. Fix: use pull-based claims. [Source: Dacian — DeFi Liquidation Vulnerabilities, Code4rena Revert Lend]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — DeFi Liquidation Vulnerabilities, Code4rena Revert Lend

- [ ] **[EVM-LEND-058] Yield vault collateral not seized during liquidation** _(exploit-pattern; medium)_: If the protocol allows depositing collateral into external yield vaults but the liquidation code doesn't account for vault-deposited collateral, attackers can take loans, get liquidated, then withdraw collateral from the vault. [Source: Dacian — DeFi Liquidation Vulnerabilities, Cyfrin The Standard]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — DeFi Liquidation Vulnerabilities, Cyfrin The Standard

- [ ] **[EVM-LEND-059] Insurance fund exhaustion blocks liquidation permanently** _(exploit-pattern; medium)_: If `liquidation reverts when badDebt > insuranceFund`, the protocol enters a permanent state where large insolvent positions cannot be liquidated until the fund accrues enough fees. [Source: Dacian — DeFi Liquidation Vulnerabilities]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — DeFi Liquidation Vulnerabilities

- [ ] **[EVM-LEND-060] Fixed liquidation bonus causes revert below bonus threshold** _(exploit-pattern; medium)_: A fixed 10% bonus causes liquidation to revert when user has <110% collateral ratio, even though they're under-collateralized. Fix: cap bonus to maximum available amount. [Source: Dacian — DeFi Liquidation Vulnerabilities]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — DeFi Liquidation Vulnerabilities

- [ ] **[EVM-LEND-061] Liquidation fails for non-18 decimal collateral tokens** _(exploit-pattern; medium)_: Multi-collateral protocols using mixed 18-decimal internal math and native-decimal transfers can have inconsistencies slip in that cause liquidation to revert for non-standard decimal tokens. [Source: Dacian — DeFi Liquidation Vulnerabilities, Pashov GainsNetwork]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — DeFi Liquidation Vulnerabilities, Pashov GainsNetwork

- [ ] **[EVM-LEND-062] Two nonReentrant modifiers in liquidation path** _(exploit-pattern; medium)_: Complex liquidation code that optionally calls multiple contracts can hit two `nonReentrant` modifiers on the same contract, causing liquidation to revert. [Source: Dacian — DeFi Liquidation Vulnerabilities, SigmaPrime August]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — DeFi Liquidation Vulnerabilities, SigmaPrime August

- [ ] **[EVM-LEND-063] Zero-value transfer reverts block liquidation** _(exploit-pattern; medium)_: If liquidation code calculates small fee/reward amounts that round to zero, and the token reverts on zero-value transfers, liquidation is blocked. [Source: Dacian — DeFi Liquidation Vulnerabilities]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — DeFi Liquidation Vulnerabilities

- [ ] **[EVM-LEND-064] Token deny list (USDC blacklist) blocks liquidation via push mechanism** _(exploit-pattern; medium)_: If liquidation sends tokens to addresses on a deny list (e.g., USDC blacklist), the transfer reverts, making liquidation impossible. Fix: use pull-based claims. [Source: Dacian — DeFi Liquidation Vulnerabilities]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — DeFi Liquidation Vulnerabilities

- [ ] **[EVM-LEND-065] Liquidation reward calculated using wrong token decimals** _(exploit-pattern; medium)_: If reward is paid in 18-decimal collateral but calculated using 6-decimal debt position value, the reward shrinks by 12 orders of magnitude, removing all liquidation incentive. [Source: Dacian — DeFi Liquidation Vulnerabilities, Code4rena Size]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — DeFi Liquidation Vulnerabilities, Code4rena Size

- [ ] **[EVM-LEND-066] Liquidation fee as % of seized collateral makes liquidation unprofitable** _(exploit-pattern; medium)_: A 30% protocol fee on total seized collateral (rather than on liquidator profit) removes incentive to liquidate many positions. Fee should be % of profit, not raw collateral. [Source: Dacian — DeFi Liquidation Vulnerabilities, Sherlock Sentiment V2]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — DeFi Liquidation Vulnerabilities, Sherlock Sentiment V2

- [ ] **[EVM-LEND-067] Liquidation fees not included in minimum collateral requirement** _(exploit-pattern; medium)_: If min collateral to avoid liquidation doesn't account for liquidation fees, insufficient collateral exists at liquidation time, causing reverts or bad debt. [Source: Dacian — DeFi Liquidation Vulnerabilities, CodeHawks Zaros]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — DeFi Liquidation Vulnerabilities, CodeHawks Zaros

- [ ] **[EVM-LEND-068] Earned yield or positive PNL omitted from liquidation value/settlement — unfair liquidation** _(exploit-pattern; medium)_: If deposited collateral earns yield or a position has positive PNL but liquidation values only principal or fails to credit the gain before settlement, users can be liquidated or lose value despite sufficient economic collateral. [Source: Dacian — DeFi Liquidation Vulnerabilities]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — DeFi Liquidation Vulnerabilities

- [ ] **[EVM-LEND-069] Borrow interest accumulates while protocol is paused** _(exploit-pattern; medium)_: If users can't repay during pause but interest keeps accruing, they can be instantly liquidated when unpaused due to interest buildup. [Source: Dacian — DeFi Liquidation Vulnerabilities, Code4rena BendDAO]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — DeFi Liquidation Vulnerabilities, Code4rena BendDAO

- [ ] **[EVM-LEND-070] isLiquidatable doesn't refresh interest/funding fees before check** _(exploit-pattern; medium)_: View functions checking liquidation eligibility must first calculate latest accrued fees. Stale fee data means positions appear healthier than they are. [Source: Dacian — DeFi Liquidation Vulnerabilities]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — DeFi Liquidation Vulnerabilities

- [ ] **[EVM-LEND-071] Repayment misattributed after borrower replacement** _(exploit-pattern; medium)_: When a transferable position or loan changes owner, repayments must be credited to the current debt owner/lender and the correct accounting record. Look for: repayment recipients, debt keys, or borrower references that remain bound to the original owner after transfer. [Source: Auditmos `audit-unfair-liquidation`, pattern #8](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-unfair-liquidation/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [AUDITMOS-UNFAIR-LIQUIDATION-8](https://github.com/auditmos/skills); [https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-unfair-liquidation/reference.md](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-unfair-liquidation/reference.md); Source: Auditmos `audit-unfair-liquidation`, pattern #8

## Supplemental Attack Vectors (SAS-AV)

- [ ] **[EVM-LEND-072] Accrued Interest Omitted from Health Factor or LTV Calculation** _(exploit-pattern; medium)_: Health factor or LTV computed from principal debt without adding accrued interest. Understates actual debt, delays necessary liquidations.
  - **FP:** `getDebt()` includes accrued interest. Interest accrual function called before health check.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-125](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-146

- [ ] **[EVM-LEND-073] Unfair Liquidation via Cherry-Picked Collateral** _(exploit-pattern; medium)_: Liquidator selects which collateral asset to seize, choosing the most liquid/stable asset while leaving volatile collateral. Borrower's position becomes unhealthier post-liquidation despite liquidator profiting.
  - **FP:** Collateral seizure follows defined priority ordering. Liquidation enforces health improvement post-seizure (`healthFactorAfter > healthFactorBefore`). Single-collateral system.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-126](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-172

- [ ] **[EVM-LEND-074] No LTV Gap Between Borrow and Liquidation Threshold** _(exploit-pattern; medium)_: Liquidation threshold equals max borrow LTV. Positions become immediately liquidatable after borrowing with zero buffer for normal price volatility. Users have no margin to avoid liquidation.
  - **FP:** Explicit gap between max borrow LTV and liquidation threshold (e.g., borrow at 75%, liquidate at 80%). Documentation explains chosen parameters. Per-asset configurable thresholds.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-127](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-176

- [ ] **[EVM-LEND-075] Interest Accrual During Liquidation Auction** _(exploit-pattern; medium)_: While collateral is being auctioned (Dutch auction, English auction), borrower's debt continues accruing interest. Long auctions make the position progressively worse, potentially causing auction proceeds to be insufficient.
  - **FP:** Interest frozen at auction start timestamp. Auction duration bounded. Instant liquidation (no auction). Interest-inclusive reserve price.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-128](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-184

- [ ] **[EVM-LEND-076] No Liquidation Slippage Protection** _(exploit-pattern; medium)_: Liquidator calls `liquidate()` but received collateral amount has no minimum parameter. MEV bot sandwiches the liquidation tx, extracting value via collateral price manipulation.
  - **FP:** `minCollateralReceived` parameter in liquidation function. Private mempool for liquidation txs. Protocol-operated liquidation bot with MEV protection.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-129](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-185

- [ ] **[EVM-LEND-077] Permissionless accrueInterest Griefing** _(exploit-pattern; medium)_: Permissionless `accrueInterest()` called at short intervals — each computes zero interest (rounding) but advances timestamp, systematically suppressing accumulation.
  - **FP:** Minimum accrual interval enforced. Precision ensures per-block interest > 0. Access-restricted accrual.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-131](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-251

- [ ] **[EVM-LEND-078] Profit Tracking Underflow Blocks Withdrawals** _(exploit-pattern; medium)_: Vault tracks cumulative profit. Strategy loss exceeding recorded profit causes `totalProfit -= loss` to underflow (revert on 0.8+), bricking all withdrawals.
  - **FP:** Loss capped: `totalProfit -= min(loss, totalProfit)`. Signed integer for profit/loss. Per-strategy tracking.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-132](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-252

- [ ] **[EVM-LEND-079] Liquidated Position Continues Accruing Rewards** _(exploit-pattern; medium)_: Position liquidated (balance zeroed) but not removed from reward distribution. `rewardDebt` not reset — phantom rewards accrue or are locked permanently.
  - **FP:** Liquidation calls `_withdrawRewards()` before zeroing. Reward system checks `balance > 0` before accruing.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-133](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-273

- [ ] **[EVM-LEND-080] Liquidation Blocked by External Pool Illiquidity** _(exploit-pattern; medium)_: Liquidation swaps collateral for debt token via external DEX. Drained pool reverts swap, making liquidation impossible. Bad debt accumulates.
  - **FP:** Liquidation accepts collateral directly. Fallback path uses different DEX. Liquidator provides debt token.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-134](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-275

- [ ] **[EVM-LEND-081] Liquidation Discount Applied Inconsistently Across Code Paths** _(exploit-pattern; medium)_: One path calculates debt at face value, another applies discount. Mismatch causes underflow or leaves residual bad debt unaccounted.
  - **FP:** Discount applied consistently across all liquidation paths. Single source of truth for discounted value.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-135](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-276

- [ ] **[EVM-LEND-082] No-Bid Auction Fails to Clear State** _(exploit-pattern; medium)_: Auction expires with no bids but finalization doesn't clear lien/escrow data — collateral locked with no return path or re-auction mechanism.
  - **FP:** No-bid finalization returns collateral and clears state. Auto re-auction. Timeout-based release.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-136](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-278

- [ ] **[EVM-LEND-083] Repeated Liquidation of Same Position** _(exploit-pattern; medium)_: Liquidation doesn't flag position as processed. After partial liquidation, position still appears undercollateralized — second liquidator seizes collateral beyond intent.
  - **FP:** Position marked `liquidated` or deleted. `require(status != Liquidated)`. Post-liquidation health check.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-137](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-280

- [ ] **[EVM-LEND-084] MEV Withdrawal Before Bad Debt Socialization** _(exploit-pattern; medium)_: External event (liquidation, exploit, depeg) causes vault loss. MEV actor observes pending loss-causing tx in mempool and front-runs a withdrawal at pre-loss share price, leaving remaining depositors to absorb the full loss.
  - **FP:** Withdrawals require time-delayed request queue (epoch-based or cooldown). Loss realization and share price update are atomic. Private mempool used for liquidation txs.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-138](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-293

- [ ] **[EVM-LEND-085] Open Interest Tracked with Pre-Fee Position Size** _(exploit-pattern; medium)_: OI incremented by full position size before fee deduction. Actual exposure < recorded OI. Permanently inflated OI hits caps, blocking new positions.
  - **FP:** OI incremented by post-fee size. OI decremented on close by same amount used at open.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-139](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-297

- [ ] **[EVM-LEND-086] Interest Accrual Rounds to Zero but Timestamp Advances** _(exploit-pattern; medium)_: `interest = rate * timeDelta / SECONDS_PER_YEAR` rounds to zero for small `timeDelta`, but `lastAccrualTime` still advances — fractional interest permanently lost.
  - **FP:** Accumulator uses sufficient precision (RAY = 1e27). `lastAccrualTime` only advances when interest > 0.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-140](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-299

- [ ] **[EVM-LEND-087] Position Reduction Triggers Liquidation** _(exploit-pattern; medium)_: Partial repay/withdrawal creates intermediate state below liquidation threshold — bot liquidates before atomic completion. Health check applied to intermediate, not final state.
  - **FP:** Repay and collateral changes atomic. Health check on final state only. Grace period after modification.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-141](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-305

## drozer-lite Additions

- [ ] **[EVM-LEND-088] Compound Treasury Fee Activation Risk** _(exploit-pattern; medium)_: Governance of an external Compound fork enables a treasury fee; the integrating protocol reverts or silently loses amount.
  - **Trigger:** Governance of an external Compound fork enables a treasury fee; the integrating protocol reverts or silently loses amount. No source-specific red flags listed; trace the invariant and caller-controlled inputs described above.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Proof:** Check whether the adapter reads `treasuryPercent` and how it handles non-zero results.
  - **Provenance:** [DROZER-UNI-82](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md); gdroz3r/drozer-lite — checklists/universal.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
