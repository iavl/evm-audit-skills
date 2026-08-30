<!-- GENERATED FILE: source is ../../data/canonical-checks.json; do not edit by hand. -->
# AMM & DEX Security Checklist

Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.
Global FP/proof obligations live in the Review Contract; only check-specific gates and proofs are repeated below.

## General AMM

- [ ] **[EVM-AMM-001] Cross-contract view reentrancy on reserve updates** _(exploit-pattern; medium)_: Even with `nonReentrant`, if `reserves[]` is updated AFTER an external call (e.g., ERC777 token transfer), another contract can read stale reserves via a view function during the callback. Must follow CEI pattern when updating reserves. Look for: reserve state updates after `transfer()`/`transferFrom()` calls. [Decurity AMM]
  - **Provenance:** Decurity AMM

- [ ] **[EVM-AMM-002] Flash loan callback ordering** _(exploit-pattern; medium)_: AMM flash loan (FlashSwap in Uniswap) callback must be invoked AFTER the token transfer, not before. If called before, the borrower receives nothing but the callback has already executed. Look for: flash loan implementations where callback precedes token movement. [Decurity AMM]
  - **Provenance:** Decurity AMM

- [ ] **[EVM-AMM-003] Fee-on-transfer token handling** _(exploit-pattern; medium)_: AMM must either explicitly support FOT tokens (measure balance diff) or explicitly reject them. Neither = accounting mismatch. Balancer lost funds from a deflationary token that reduced reserves without AMM knowledge. Look for: AMMs that accept arbitrary tokens without FOT handling. [Decurity AMM, beirao AMM-03]
  - **Provenance:** Decurity AMM, beirao AMM-03

- [ ] **[EVM-AMM-004] Rebasing tokens break AMM accounting** _(exploit-pattern; medium)_: Rebasing tokens change balance without transfers, but AMMs track reserves internally. The AMM's reserves diverge from actual balances, creating extractable arbitrage. Look for: AMMs holding rebasing tokens without rebase tracking or explicit blocklist. [beirao AMM-04]
  - **Provenance:** beirao AMM-04

- [ ] **[EVM-AMM-005] Arbitrary call from user input** _(exploit-pattern; medium)_: If the AMM has a function accepting arbitrary calldata (e.g., for callbacks), an attacker can craft calls to drain approvals. Look for: `address.call(userProvidedData)` patterns. [Decurity AMM]
  - **Provenance:** Decurity AMM

- [ ] **[EVM-AMM-006] Signed integer balance updates** _(exploit-pattern; medium)_: If the AMM tracks balances with signed integers, `-int(amount)` can overflow for edge-case amounts such as `type(uint256).max`. Inline assembly and unchecked casts do not add overflow protection. Look for: `int256` or signed casts used for balance deltas without explicit bounds checking. [Decurity AMM]
  - **Provenance:** Decurity AMM

## Slippage Protection

- [ ] **[EVM-AMM-007] Hardcoded slippage (especially `minAmountOut = 0`)** _(exploit-pattern; medium)_: Hardcoded zero or fixed slippage enables a sandwich attack, while an excessively tight fixed value can freeze withdrawals during volatility. Every swap must have a user-controlled or safely bounded minimum output. Look for: `amountOutMinimum: 0`, `sqrtPriceLimitX96: 0`, or hardcoded slippage parameters. [beirao U-01, U-02, Dacian — DeFi Slippage Attacks]
  - **Provenance:** beirao U-01, U-02, Dacian — DeFi Slippage Attacks

- [ ] **[EVM-AMM-008] On-chain slippage calculation or quoting is manipulable** _(exploit-pattern; medium)_: If `minAmountOut` is calculated from on-chain data such as `getAmountsOut()`, pool reserves, or a Quoter, an attacker can manipulate the pool or quote before the check and make the bound accept adverse execution. Calculate user slippage off-chain or use a manipulation-resistant source. Look for: `minAmountOut` derived from `pool.getReserves()`, `router.getAmountsOut()`, or `Quoter.quoteExactInput()`. [beirao U-02, Dacian — DeFi Slippage Attacks, Sherlock Derby]
  - **Provenance:** beirao U-02, Dacian — DeFi Slippage Attacks, Sherlock Derby

- [ ] **[EVM-AMM-009] Slippage calculated from the wrong reference amount** _(exploit-pattern; medium)_: If `minAmountOut` is derived from the input amount or another denomination instead of the expected output for the actual route, the bound can be far too loose or too strict and fail to protect value. Look for: `minOut = amountIn * ...` in swaps between differently priced tokens, or slippage calculations that do not use the expected output amount. [Source: Auditmos `audit-slippage`, pattern #3](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
  - **Provenance:** [AUDITMOS-SLIPPAGE-3](https://github.com/auditmos/skills); [https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/reference.md](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/reference.md); Source: Auditmos `audit-slippage`, pattern #3

- [ ] **[EVM-AMM-010] No expiration deadline** _(exploit-pattern; medium)_: Swaps without a user-specified future deadline can be held by validators/MEV bots and executed later at a worse price; setting `deadline` to `block.timestamp` provides no protection. Look for: `deadline: type(uint256).max`, `deadline: block.timestamp`, or a missing deadline parameter. [beirao U-02, Dacian — DeFi Slippage Attacks]
  - **Provenance:** beirao U-02, Dacian — DeFi Slippage Attacks

- [ ] **[EVM-AMM-011] Missing refunds after swaps** _(exploit-pattern; medium)_: If a swap does not use all input tokens, the remainder must be returned exactly once. Look for: swap functions that pull an exact-output amount but do not refund unused input. [beirao U-03]
  - **Provenance:** beirao U-03

## Uniswap V4 Hooks

- [ ] **[EVM-AMM-012] Hook permissions derived from address bits, not contract code** _(exploit-pattern; medium)_: Uniswap V4 checks `uint160(address(hook)) & flag` to determine permissions. If the hook is deployed at an address missing required flag bits, PoolManager will never call the function; extra bits can route calls to non-existent functions and cause a DoS. Upgrades cannot add callback permissions because the deployed address bits do not change. Look for: hook deployment without address mining for permission flags or upgrade plans that add callbacks post-deployment. [Hacken UniV4, OpenZeppelin UniV4]
  - **Provenance:** Hacken UniV4, OpenZeppelin UniV4

- [ ] **[EVM-AMM-013] Incorrect return type from hooks** _(exploit-pattern; medium)_: `beforeSwap` must return `(bytes4, BeforeSwapDelta, uint24)`. Returning wrong types causes overflow or reverts. Look for: hook functions with non-standard return types. [Hacken UniV4]
  - **Provenance:** Hacken UniV4

- [ ] **[EVM-AMM-014] BeforeSwapDelta sign confusion** _(exploit-pattern; medium)_: `BeforeSwapDelta` is from the hook's perspective: negative means the hook takes tokens and positive means it gives tokens. A wrong sign can make the hook pay users instead of charging fees, or vice versa. Look for: positive deltas used as fees. [Hacken UniV4]
  - **Provenance:** Hacken UniV4

- [ ] **[EVM-AMM-015] Delta ordering depends on `zeroForOne`** _(exploit-pattern; medium)_: The meaning of specified/unspecified in `BeforeSwapDelta` depends on `params.zeroForOne`. Using the wrong mapping causes tokens to flow in the wrong direction. Look for: `toBeforeSwapDelta()` calls that don't check swap direction. [Hacken UniV4]
  - **Provenance:** Hacken UniV4

- [ ] **[EVM-AMM-016] Unsettled deltas revert `unlock()`** _(exploit-pattern; medium)_: All hook deltas must be settled through `settle()` or `take()` before transaction finalization. If any delta remains non-zero, PoolManager's `NonzeroDeltaCount` check in `unlock()` reverts the entire transaction. Look for: hooks that modify deltas without corresponding settlement calls. [Hacken UniV4]
  - **Provenance:** Hacken UniV4

- [ ] **[EVM-AMM-017] Async hooks steal custody** _(exploit-pattern; medium)_: Async hooks (where `specifiedTokenDelta = -params.amountSpecified`) can replace Uniswap's swap logic and take custody of the full swap amount. Look for: `beforeSwap` returning a specifiedTokenDelta equal to negative amountSpecified or transferring the resulting custody to an attacker-controlled address. [Hacken UniV4]
  - **Provenance:** Hacken UniV4

- [ ] **[EVM-AMM-018] Hooks attached to multiple pools** _(exploit-pattern; medium)_: PoolManager doesn't enforce hook exclusivity. An attacker can create a pool with your hook attached and trigger it from their pool. Look for: hooks that don't validate the PoolKey against an expected pool. [Hacken UniV4]
  - **Provenance:** Hacken UniV4

- [ ] **[EVM-AMM-019] Missing access control on hook functions** _(exploit-pattern; medium)_: Hook callbacks should only be callable by PoolManager. Without `msg.sender == poolManager` or an equivalent guard, anyone can call them directly with arbitrary parameters and manipulate state or drain funds. Look for: hook functions without `onlyPoolManager` or similar checks. [Hacken UniV4, OpenZeppelin UniV4]
  - **Provenance:** Hacken UniV4, OpenZeppelin UniV4

- [ ] **[EVM-AMM-020] Dynamic fee manipulation via front-running** _(exploit-pattern; medium)_: Hooks that adjust swap fees based on oracle prices or market conditions can be front-run by MEV bots who trade before/after fee changes. Look for: fee logic that depends on manipulable on-chain state. [Hacken UniV4]
  - **Provenance:** Hacken UniV4

- [ ] **[EVM-AMM-021] Unbounded loops in hooks cause DoS** _(exploit-pattern; medium)_: A hook with a growing array that's iterated on every swap will eventually hit gas limits, making the pool unusable. Look for: loops over dynamic arrays in hook functions. [Hacken UniV4]
  - **Provenance:** Hacken UniV4

## TWAMM (Time-Weighted AMM)

- [ ] **[EVM-AMM-022] Rebasing token balance changes during long-term swaps** _(exploit-pattern; medium)_: If a TWAMM holds rebasing tokens, balance changes mid-swap can corrupt order-execution math and create an under- or over-collateralized position. Look for: TWAMM implementations that don't block or track rebasing tokens. [Decurity AMM]
  - **Provenance:** Decurity AMM

- [ ] **[EVM-AMM-023] Insufficient liquidity check before swap execution** _(exploit-pattern; medium)_: TWAMM must verify sufficient liquidity exists before executing long-term orders. Look for: missing liquidity validation in TWAMM execution logic. [Decurity AMM]
  - **Provenance:** Decurity AMM

## AMM Integration (for protocols integrating AMMs)

- [ ] **[EVM-AMM-024] Callback function must verify caller is the pool** _(exploit-pattern; medium)_: Uniswap-style callbacks (`uniswapV3SwapCallback`, flash-swap callbacks, and similar) must verify that `msg.sender` is the legitimate pool or a factory-approved pool. Without this, anyone can call the callback to steal tokens. Look for: callbacks without pool/factory address validation. [Decurity AMM]
  - **Provenance:** Decurity AMM

- [ ] **[EVM-AMM-025] Don't use `pool.swap()` directly** _(exploit-pattern; medium)_: Direct pool interaction skips router protections such as deadline, slippage, and path validation. Use a router or reproduce every required guard. Look for: direct `IUniswapV3Pool.swap()` calls instead of a protected route. [beirao U-06, U-07]
  - **Provenance:** beirao U-06, U-07

- [ ] **[EVM-AMM-026] Pool reserves are manipulable** _(exploit-pattern; medium)_: Never use `pool.getReserves()` as a price oracle. Flash loans can manipulate reserves within a single transaction. Look for: `getReserves()` used in price calculations or access control. [beirao U-06]
  - **Provenance:** beirao U-06

- [ ] **[EVM-AMM-027] AMM pool token0/token1 order differs by chain** _(exploit-pattern; medium)_: `token0` and `token1` are address-sorted, so the same pair may have a different order across chains. Hardcoding the order in prices or swap logic can invert token flow. Look for: assumptions about which asset is token0 or token1. [multichain-auditor, beirao U-04]
  - **Provenance:** multichain-auditor, beirao U-04

- [ ] **[EVM-AMM-028] Verify pool factory address** _(heuristic; contextual)_: If pools aren't from a whitelisted factory, they could be fakes. Verify `pool.factory() == expectedFactory`. Look for: pool addresses from user input without factory verification. [beirao U-05]
  - **Provenance:** beirao U-05

- [ ] **[EVM-AMM-029] Hardcoded DEX pool fees prevent optimal routing** _(exploit-pattern; medium)_: Using a fixed fee tier (for example, always 0.3%) may fail when that tier does not exist or route through a suboptimal pool when another tier has better liquidity. Look for: hardcoded fee parameters in swap paths. [ERC4626 primer pattern #46, Dacian — DeFi Slippage Attacks]
  - **Provenance:** ERC4626 primer pattern #46, Dacian — DeFi Slippage Attacks

## Uniswap V4 Hooks Security (Expanded)

- [ ] **[EVM-AMM-030] Hooks on multiple pools without pool isolation** _(exploit-pattern; medium)_: Any hook can be attached to multiple pools by default. If hook state is shared across pools, one pool's operations corrupt another's state. Look for: hooks without per-PoolKey storage mapping or `beforeInitialize` restrictions. [Hacken UniV4, OpenZeppelin UniV4]
  - **Provenance:** Hacken UniV4, OpenZeppelin UniV4

- [ ] **[EVM-AMM-031] lpFeeOverride can DoS swaps** _(exploit-pattern; medium)_: If a hook returns an invalid or excessive lpFeeOverride value, swaps on that pool fail. A centralized hook owner can set fees to 100%, effectively locking pool funds. Look for: hooks with admin-controlled fee parameters without bounds. [Hacken UniV4]
  - **Provenance:** Hacken UniV4

- [ ] **[EVM-AMM-032] Hook `unlockCallback` data can call arbitrary functions** _(exploit-pattern; medium)_: The data passed to `unlockCallback` can be crafted to call any function on the hook. If the callback data formation isn't restricted, it acts as an unprotected entry point. Look for: hooks where users can influence unlockCallback calldata. [OpenZeppelin UniV4]
  - **Provenance:** OpenZeppelin UniV4

- [ ] **[EVM-AMM-033] JIT liquidity attacks on hook-managed positions** _(exploit-pattern; medium)_: If a hook manages liquidity positions, anyone can trigger fee accrual on those positions at any time. Just-in-time liquidity modifications can conflict with the hook's fee accounting. Look for: hooks that accrue fees on positions without protecting against JIT manipulation. [OpenZeppelin UniV4]
  - **Provenance:** OpenZeppelin UniV4

- [ ] **[EVM-AMM-034] Swap direction symmetry in hooks** _(exploit-pattern; medium)_: A swap can be zeroForOne or oneForZero, exactInput or exactOutput. Hook deltas must correctly handle all 4 combinations. Missing symmetry means hooks work for some swap types but break for others. Look for: hook logic that only handles `params.zeroForOne == true` or `params.amountSpecified < 0`. [OpenZeppelin UniV4, Hacken UniV4]
  - **Provenance:** OpenZeppelin UniV4, Hacken UniV4

## Dacian — Concentrated Liquidity Manager Vulnerabilities (Phase 3)

- [ ] **[EVM-AMM-035] Drain protocol via sandwich attack on owner functions missing TWAP check** _(exploit-pattern; medium)_: If `setPositionWidth()` or `unpause()` calls `_setTicks()` + `_addLiquidity()` without `onlyCalmPeriods` TWAP check, an attacker can sandwich the owner's tx to force liquidity deployment at manipulated prices, draining all protocol tokens. Beefy Finance lost ~$1.2M in this pattern. [Source: Dacian — CLM Vulnerabilities, Cyfrin Beefy Audit]
  - **Provenance:** Source: Dacian — CLM Vulnerabilities, Cyfrin Beefy Audit

- [ ] **[EVM-AMM-036] Owner rug-pull via ineffective TWAP parameters** _(exploit-pattern; medium)_: If `maxDeviation` and `twapInterval` can be set to arbitrary values by owner (e.g., maxDeviation=100%, twapInterval=1), the TWAP manipulation check becomes ineffective. Gamma Strategies was exploited this way. Fix: enforce min/max bounds on TWAP parameters. [Source: Dacian — CLM Vulnerabilities, Cyfrin Beefy Audit]
  - **Provenance:** Source: Dacian — CLM Vulnerabilities, Cyfrin Beefy Audit

- [ ] **[EVM-AMM-037] Tokens permanently stuck due to fee distribution rounding** _(exploit-pattern; medium)_: When distributing fees via `nativeEarned * fees.call / DIVISOR` etc., rounding remainders accumulate permanently in the contract. Fix: compute last recipient's share as `total - sum(others)`. [Source: Dacian — CLM Vulnerabilities, Cyfrin Beefy Audit]
  - **Provenance:** Source: Dacian — CLM Vulnerabilities, Cyfrin Beefy Audit

- [ ] **[EVM-AMM-038] Stale token approvals after router address update** _(exploit-pattern; medium)_: If `setUnirouter()` updates the router address without revoking unlimited `forceApprove` from the old router, the old router can still spend all protocol tokens. [Source: Dacian — CLM Vulnerabilities, Cyfrin Beefy Audit]
  - **Provenance:** Source: Dacian — CLM Vulnerabilities, Cyfrin Beefy Audit

- [ ] **[EVM-AMM-039] Updated management fees retrospectively applied to pending LP rewards** _(exploit-pattern; medium)_: If owner changes fee % and LP rewards are only collected at next `harvest()`, new higher fees apply retroactively to rewards earned under the previous lower fee. Fix: collect pending rewards before updating fees. [Source: Dacian — CLM Vulnerabilities, Cyfrin Beefy/Arrakis]
  - **Provenance:** Source: Dacian — CLM Vulnerabilities, Cyfrin Beefy/Arrakis

- [ ] **[EVM-AMM-040] CLM overflow for large but valid sqrtPriceX96** _(exploit-pattern; medium)_: Protocol should not revert due to overflow for valid range of `sqrtPriceX96` values from the Uniswap pool. [Source: Dacian — CLM Vulnerabilities, Cyfrin Beefy Audit]
  - **Provenance:** Source: Dacian — CLM Vulnerabilities, Cyfrin Beefy Audit

- [ ] **[EVM-AMM-041] Withdraw returns 0 tokens while burning positive shares** _(exploit-pattern; medium)_: Edge case where `withdraw()` returns zero tokens but burns user's shares, effectively stealing from the user. [Source: Dacian — CLM Vulnerabilities, Cyfrin Beefy Audit]
  - **Provenance:** Source: Dacian — CLM Vulnerabilities, Cyfrin Beefy Audit

## Dacian — DeFi Slippage Attacks (Phase 3)

- [ ] **[EVM-AMM-042] Slippage enforced on intermediate operation, not final amount** _(exploit-pattern; medium)_: If `minTokensOut` is checked during `_exitBalancerPool()` but a subsequent treasury skim further reduces the user's output, the user receives less than their specified minimum. Slippage must be enforced on the final step. [Source: Dacian — DeFi Slippage Attacks, Sherlock Olympus Update]
  - **Provenance:** Source: Dacian — DeFi Slippage Attacks, Sherlock Olympus Update

- [ ] **[EVM-AMM-043] Hard-coded slippage freezes user funds during volatility** _(exploit-pattern; medium)_: Fixed low slippage (e.g., 1%) protects in normal conditions but causes all withdrawals to revert during high volatility, freezing user funds. Users must be able to override default slippage. [Source: Dacian — DeFi Slippage Attacks, Code4rena Sturdy]
  - **Provenance:** Source: Dacian — DeFi Slippage Attacks, Code4rena Sturdy

- [ ] **[EVM-AMM-044] Minting functions are swaps without slippage** _(exploit-pattern; medium)_: When protocol mints native tokens based on pool reserves (effectively a swap), users must be able to specify slippage. Without it, the mint is sandwichable. [Source: Dacian — DeFi Slippage Attacks, Code4rena Vader]
  - **Provenance:** Source: Dacian — DeFi Slippage Attacks, Code4rena Vader

- [ ] **[EVM-AMM-045] Mismatched slippage precision across token decimals** _(exploit-pattern; medium)_: If `minTokenOut` is calculated in 6 decimals but the output token has 18 decimals, the slippage check is ineffective (off by 12 orders of magnitude). Must scale slippage to output token's precision. [Source: Dacian — DeFi Slippage Attacks, Sherlock RageTrade]
  - **Provenance:** Source: Dacian — DeFi Slippage Attacks, Sherlock RageTrade

- [ ] **[EVM-AMM-046] Token-unit slippage can hide economic loss** _(exploit-pattern; medium)_: A minimum amount expressed only in token units may still accept a large loss in USD value when the token price moves sharply or the operation changes asset composition. Look for: slippage checks that compare raw token quantity while the protected value is economically denominated in another asset, with no price/risk bound or explicit design rationale. [Source: Auditmos `audit-slippage`, pattern #10](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/SKILL.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
  - **Provenance:** [AUDITMOS-SLIPPAGE-10](https://github.com/auditmos/skills); [https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/SKILL.md](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/SKILL.md); Source: Auditmos `audit-slippage`, pattern #10

- [ ] **[EVM-AMM-047] Flash-swap repayment lacks slippage/amount bounds** _(exploit-pattern; medium)_: If a flash-swap callback obtains the repayment token through a swap without a caller-controlled minimum output or maximum input and a final repayment check, adverse execution can force overpayment. Look for: callback repayment swaps with `amountOutMinimum == 0`, an unbounded `amountInMaximum`, or repayment based on a manipulable quote. [Source: Auditmos `audit-slippage`, pattern #12](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/SKILL.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
  - **Provenance:** [AUDITMOS-SLIPPAGE-12](https://github.com/auditmos/skills); [https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/SKILL.md](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/SKILL.md); Source: Auditmos `audit-slippage`, pattern #12

## Supplemental Attack Vectors (SAS-AV)

- [ ] **[EVM-AMM-048] Uniswap V4 Cached State Desynchronization** _(exploit-pattern; medium)_: Hook caches pool state (`sqrtPriceX96`, `liquidity`, `tick`) in `beforeSwap` but state changes during the swap. `afterSwap` reads stale cached values for fee calculations or rebalancing decisions.
  - **Specific FP:** State re-read from pool in `afterSwap`. Cache explicitly invalidated between hooks. No cross-hook state dependency.
  - **Provenance:** [SAS-AV-111](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-197

- [ ] **[EVM-AMM-049] Uniswap V4 Hook Data Manipulation** _(exploit-pattern; medium)_: Hook reads parameters from `hookData` bytes passed through the swap path. Attacker crafts `hookData` to manipulate hook behavior — bypassing fee calculations, altering routing decisions, or triggering unintended state changes in the hook contract.
  - **Specific FP:** `hookData` validated against expected schema (length, types). Critical parameters derived from pool state, not `hookData`. Hook ignores or doesn't use `hookData`. Authenticated `hookData` (signed by trusted relayer).
  - **Provenance:** [SAS-AV-112](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-214

- [ ] **[EVM-AMM-050] Loss-Versus-Rebalancing (LVR) in Constant-Function AMMs** _(exploit-pattern; medium)_: AMM with constant-function pricing and static fees. Searchers continuously arbitrage stale pool price against external markets, extracting from LPs on every price movement. Concentrated liquidity amplifies extraction.
  - **Specific FP:** Dynamic fee adjusting for volatility (Uniswap V4 hooks). MEV-aware design (batch auctions, CoW AMM). Fee tier covers expected LVR for pair volatility.
  - **Provenance:** [SAS-AV-116](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-249

- [ ] **[EVM-AMM-051] TWAP Accumulator Not Updated During Sync or Skim** _(exploit-pattern; medium)_: `sync()`/`skim()` updates reserves but doesn't call `_update()` to advance TWAP accumulator. Stale TWAP enables manipulation via sync-then-trade.
  - **Specific FP:** `sync()` calls `_update()` before overwriting reserves. TWAP from external oracle. Uniswap V3 `observe()` used.
  - **Provenance:** [SAS-AV-117](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-256

- [ ] **[EVM-AMM-052] Adverse Selection — Passive LP Value Extraction via Selective JIT** _(exploit-pattern; medium)_: No time-weighting or lock on fee distribution. JIT providers enter only during high-fee moments and exit during adverse moves. Passive LPs bear 100% IL but share fees with JIT providers bearing zero IL.
  - **Specific FP:** Fee share time-weighted by duration. Dynamic fee increases during volatility. Withdrawal cooldown makes selective entry costly.
  - **Provenance:** [SAS-AV-118](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-265

- [ ] **[EVM-AMM-053] Tick Crossing Fee Accounting Manipulation via JIT** _(exploit-pattern; medium)_: On tick crossing, `feesPerLiquidityOutside` flips (`global - outside`). JIT provider adds at tick boundary after fees accumulate but before crossing — flip credits position with pre-existing fees it didn't earn.
  - **Specific FP:** `feesPerLiquidityInsideLast` set at creation; crossing correctly partitions pre/post fees. Same-block creation and crossing yield zero claimable.
  - **Provenance:** [SAS-AV-119](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-266

- [ ] **[EVM-AMM-054] Fee Accumulation Rounding Extraction via Large JIT Position** _(exploit-pattern; medium)_: `feesPerLiquidity += (feeAmount << 128) / totalLiquidity`. Large JIT position inflates `totalLiquidity` — per-unit increment rounds to zero for existing LPs while JIT provider captures truncated amount.
  - **Specific FP:** Sufficient precision (Q128+) ensures rounding loss < 1 wei at realistic ratios. Protocol minimum fee increment.
  - **Provenance:** [SAS-AV-120](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-267

- [ ] **[EVM-AMM-055] Atomic JIT Liquidity via Flash Accounting** _(exploit-pattern; medium)_: Flash accounting / lock-callback allows add-liquidity + swap + remove-liquidity atomically with zero capital. No minimum hold duration or fee decay. Attacker adds concentrated liquidity at current tick, swap executes through it, liquidity removed — all in one callback.
  - **Specific FP:** Minimum hold duration enforced. Fee share weighted by time-in-pool. Withdrawal fee on short-lived positions. Flash callback restricted from `updatePosition`.
  - **Provenance:** [SAS-AV-121](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-268

- [ ] **[EVM-AMM-056] First-Swap Extraction on Newly Created Pools** _(exploit-pattern; medium)_: New pool with minimal liquidity — first significant swap is extremely fee-rich. Attacker front-runs by adding concentrated liquidity, captures outsized fees, removes. Extreme: initializes at skewed price, profits from arb correction.
  - **Specific FP:** Minimum locked seed liquidity (Uniswap V2 `MINIMUM_LIQUIDITY`). Fee ramp-up for new pools. Anti-sniping delay on creation.
  - **Provenance:** [SAS-AV-122](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-291

- [ ] **[EVM-AMM-057] Empty Swap Path Bypasses Token Validation** _(exploit-pattern; medium)_: Empty swap data/zero-length path returns input amount without swapping — and without validating input == output token. Attacker skips swap, receives output token from contract's balance. Pattern: `if (swapData.length == 0) return amount;` without `require(fromToken == toToken)`.
  - **Specific FP:** Empty path enforces `require(fromToken == toToken)`. Swap mandatory. Reverts on empty data. Post-swap balance delta check.
  - **Provenance:** [SAS-AV-123](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-294

## drozer-lite Additions

- [ ] **[EVM-AMM-058] Pool Formula / Token-Count Mismatch** _(exploit-pattern; medium)_: A DEX supports multiple pool types (constant product, stable swap, weighted). Each pool type's swap formula is designed for a specific number of tokens. The pool creation function validates the token count against a global max (e.g., MAX_ASSETS = 4) but does NOT validate against the pool-type-specific maximum. A constant-product pool can be created with 3+ tokens even though the x*y=k formula only works for 2 tokens.
  - **Trigger:** A DEX supports multiple pool types (constant product, stable swap, weighted). Each pool type's swap formula is designed for a specific number of tokens. The pool creation function validates the token count against a global max (e.g., MAX_ASSETS = 4) but does NOT validate against the pool-type-specific maximum. A constant-product pool can be created with 3+ tokens even though the x*y=k formula only works for 2 tokens. `MAX_ASSETS_PER_POOL = 4` applied uniformly to both constant-product and stable-swap pools Constant-product swap formula uses only `offer_pool` and `ask_pool` (2 tokens) but pool has 3+ tokens Slippage check requires exactly 2 deposits but is inside `if let Some(slippage_tolerance)` — bypassed when None Liquidity addition works for N tokens but shares calculated via `sqrt(d0 * d1)` (2-token formula) Pool creation validates `len >= 2 && len <= MAX` but not `if ConstantProduct then len == 2`
  - **Specific proof:** 1. For each pool type, identify the mathematical formula used for swaps. 2. Determine how many tokens the formula supports: constant product (x*y=k) = 2; Balancer weighted = N; StableSwap = N. 3. Check whether pool creation enforces the pool-type-specific token limit. If a constant-product pool can be created with >2 tokens, flag as HIGH. 4. Check slippage tolerance assertions — if they hardcode `deposits.len() == 2` but the check is conditional (e.g., only runs when slippage_tolerance is Some), the guard can be bypassed.
  - **Provenance:** [DROZER-DEX-7](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md); gdroz3r/drozer-lite — checklists/dex.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/dex.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-AMM-059] Liquidity Operation Lacks Minimum-Output Protection** _(exploit-pattern; medium)_: An `add_liquidity` / `withdraw_liquidity` / `remove_liquidity` function computes asset amounts from the pool's current ratios but does not expose minimum-output or maximum-input bounds. A user can receive fewer assets, or donate excess assets, after pool state changes between submission and execution. Industry-standard routers provide `amountAMin`/`amountBMin` and deadline parameters.
  - **Trigger:** An `add_liquidity` / `withdraw_liquidity` / `remove_liquidity` function computes asset amounts from the pool's current ratios but does not expose minimum-output or maximum-input bounds. A user can receive fewer assets, or donate excess assets, after pool state changes between submission and execution. Industry-standard routers provide `amountAMin`/`amountBMin` and deadline parameters. `withdraw_liquidity(pool_id)` with no `min_assets_out` parameter `addLiquidity()` with `amountAMin == 0` and `amountBMin == 0` Refund calculated from current ratios with no floor check No deadline or user-controlled tolerance on liquidity operations
  - **Specific proof:** 1. For every liquidity add/remove path, check whether the user can specify minimum received amounts and maximum input amounts. 2. Verify the bounds are checked after the final pool operation, not only on an intermediate calculation. 3. If neither minimum-output nor equivalent slippage protection exists, flag. 4. For deposits, separately check whether imbalanced excess is refunded.
  - **Provenance:** [DROZER-DEX-8](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md); gdroz3r/drozer-lite — checklists/dex.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/dex.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-AMM-060] Disproportionate Deposit Loss (Excess Not Refunded)** _(exploit-pattern; medium)_: A `provide_liquidity` function calculates per-asset share ratios (`deposit_amount * total_share / pool_amount`) and mints LP tokens based on `min(share_ratios)`. The excess tokens from the non-minimum asset are added to the pool but not reflected in the minted shares. These excess tokens are permanently donated to all existing LPs. The function does NOT refund the excess to the depositor.
  - **Trigger:** A `provide_liquidity` function calculates per-asset share ratios (`deposit_amount * total_share / pool_amount`) and mints LP tokens based on `min(share_ratios)`. The excess tokens from the non-minimum asset are added to the pool but not reflected in the minted shares. These excess tokens are permanently donated to all existing LPs. The function does NOT refund the excess to the depositor. `share = min(deposit_A * total_share / pool_A, deposit_B * total_share / pool_B)` with no refund of the difference User deposits 100A + 200B into a 1:1 pool; receives shares worth 100A + 100B; 100B is donated Slippage tolerance passes because LP tokens are within tolerance — but user lost 100B No industry-standard `_addLiquidity` that computes optimal amounts before the actual deposit (cf. Uniswap V2 Router) A front-runner changes the pool ratio between tx submission and execution, maximizing the user's excess donation
  - **Specific proof:** 1. For every liquidity provision function, check how shares are computed when deposit ratios don't match pool ratios. 2. If `min(share_ratios)` is used, calculate the implied excess for each asset. 3. Check whether the excess is: (a) refunded to the depositor, (b) used to compute additional shares, or (c) silently donated to the pool. 4. If (c), check whether slippage tolerance protects against this loss. Note: slippage tolerance checks LP tokens received, NOT whether excess tokens are returned.
  - **Provenance:** [DROZER-DEX-10](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md); gdroz3r/drozer-lite — checklists/dex.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/dex.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-AMM-061] Spread / Slippage Computed Before Fee Deduction** _(exploit-pattern; medium)_: A swap function computes `return_amount` (before fees), then `spread_amount = expected_return - return_amount`. Fees are then deducted from `return_amount` to get `final_return`. The `spread_amount` is compared against `max_spread`. Because `spread_amount` is computed before fees, it INCLUDES the fee as part of the "spread." The actual price slippage (excluding fees) is smaller than the reported `spread_amount`, making the spread check pass when the real slippage exceeds the user's tolerance.
  - **Trigger:** A swap function computes `return_amount` (before fees), then `spread_amount = expected_return - return_amount`. Fees are then deducted from `return_amount` to get `final_return`. The `spread_amount` is compared against `max_spread`. Because `spread_amount` is computed before fees, it INCLUDES the fee as part of the "spread." The actual price slippage (excluding fees) is smaller than the reported `spread_amount`, making the spread check pass when the real slippage exceeds the user's tolerance. `spread_amount = offer_amount * exchange_rate - return_amount` where `return_amount` is before fees `assert_max_spread(spread_amount, return_amount + spread_amount)` — spread includes fees For StableSwap: `spread_amount = offer_amount - return_amount` (1:1 assumption) computed before fees Fees are 5-10% but spread check uses 1% tolerance — the fee inflates the spread past the tolerance, so the check effectively allows ~15% real slippage with a 1% setting
  - **Specific proof:** 1. In the swap computation, identify where `spread_amount` is calculated relative to fee deduction. 2. If `spread_amount = expected - return_amount` and `return_amount` is PRE-fee, the spread includes fees. 3. Check whether the spread check (`assert_max_spread`) uses this inflated spread or the actual post-fee slippage. 4. The correct approach: compute spread AFTER fees, or compute spread as `expected_return - (return_amount - fees)`.
  - **Provenance:** [DROZER-DEX-11](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md); gdroz3r/drozer-lite — checklists/dex.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/dex.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-AMM-062] Decimal Normalization Inconsistency Between Swap and LP Paths** _(exploit-pattern; medium)_: A StableSwap implementation has two code paths that compute the invariant D: one for swaps (which normalizes via `decimal_with_precision` or rate multipliers) and one for LP minting/withdrawal (which sums raw amounts). When tokens have different decimals (e.g., 6 vs 18), the LP path computes a D that is dominated by the higher-decimal token, granting disproportionate shares to depositors of that token.
  - **Trigger:** A StableSwap implementation has two code paths that compute the invariant D: one for swaps (which normalizes via `decimal_with_precision` or rate multipliers) and one for LP minting/withdrawal (which sums raw amounts). When tokens have different decimals (e.g., 6 vs 18), the LP path computes a D that is dominated by the higher-decimal token, granting disproportionate shares to depositors of that token. Swap path: `offer_pool = Decimal256::decimal_with_precision(amount, precision)` — normalized LP path: `sum_x = deposits.iter().fold(zero, |acc, x| acc + x.amount)` — raw amounts, no normalization D computation for LP uses raw `Uint128` amounts while swap uses `Decimal256` with precision Two tokens with 6 and 18 decimals: depositing 1e6 USDC and 1e18 DAI produces wildly different D vs depositing 1e18 USDC and 1e6 DAI — but both should be equivalent in value
  - **Specific proof:** 1. Identify every call site that computes the StableSwap invariant D. 2. For each call site, check whether token amounts are normalized to a common decimal base BEFORE being passed to the D computation. 3. Compare the normalization logic between the swap path and the LP mint path. If they differ, flag. 4. Test with two tokens of different decimals (e.g., 6 and 18): deposit equal-value amounts via both paths and compare the D values.
  - **Provenance:** [DROZER-SS-1](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/stableswap.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/stableswap.md); gdroz3r/drozer-lite — checklists/stableswap.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/stableswap.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/stableswap.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-AMM-063] Multi-Token Invariant Uses Only Swap Pair (Disjoint Computation)** _(exploit-pattern; medium)_: The StableSwap invariant D is defined over ALL N tokens: `An∑(all xi) + D = ADⁿ + Dⁿ⁺¹/(nⁿ∏(all xi))`. When computing a swap between token A and token B in a 3-token pool, the implementation passes only `(offer_pool, ask_pool)` to the D/y computation, but uses `n_coins = 3`. This produces an incorrect D because the sum and product only include 2 of the 3 token balances, while the exponent uses N=3. Swaps between different pairs in the same pool preserve different (incorrect) invariants, creating arbitrage opportunities.
  - **Trigger:** The StableSwap invariant D is defined over ALL N tokens: `An∑(all xi) + D = ADⁿ + Dⁿ⁺¹/(nⁿ∏(all xi))`. When computing a swap between token A and token B in a 3-token pool, the implementation passes only `(offer_pool, ask_pool)` to the D/y computation, but uses `n_coins = 3`. This produces an incorrect D because the sum and product only include 2 of the 3 token balances, while the exponent uses N=3. Swaps between different pairs in the same pool preserve different (incorrect) invariants, creating arbitrage opportunities. `compute_swap(n_coins=3, offer_pool, ask_pool, ...)` but D is computed from only `offer_pool + ask_pool` `calculate_stableswap_d(offer_pool, ask_pool)` — sum uses 2 values but `ann = amp * n_coins` uses 3 The `pool_sum` or `sum_pools` variable only includes 2 token balances D/y functions accept only 2 pool amounts as parameters despite being called for pools with 3+ tokens Different token-pair swaps in the same pool produce inconsistent pricing
  - **Specific proof:** 1. For every StableSwap swap computation, check how many token balances are passed to the D/y computation function. 2. If the function receives only the offer and ask balances (2 tokens) but `n_coins` reflects the actual pool size (3+), flag as HIGH. 3. Compare against Curve reference: the `get_y` function iterates over ALL pool balances except the target token. 4. Test: in a 3-token pool, check if A-B swaps produce different slippage than B-C swaps with identical pool composition — they should be equivalent in a correct implementation.
  - **Provenance:** [DROZER-SS-2](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/stableswap.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/stableswap.md); gdroz3r/drozer-lite — checklists/stableswap.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/stableswap.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/stableswap.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-AMM-064] Missing Imbalanced Deposit Fee** _(exploit-pattern; medium)_: The LP minting function computes shares as `total_supply * (D1 - D0) / D0` where D1 includes the new deposits and D0 is the pre-deposit invariant. Curve additionally computes per-token ideal balances (`ideal_balance = D1 * old_balance / D0`) and charges a fee on the `|ideal_balance - new_balance|` for each token. This fee is missing in the implementation — users can deposit one-sided or skewed liquidity without penalty.
  - **Trigger:** The LP minting function computes shares as `total_supply * (D1 - D0) / D0` where D1 includes the new deposits and D0 is the pre-deposit invariant. Curve additionally computes per-token ideal balances (`ideal_balance = D1 * old_balance / D0`) and charges a fee on the `|ideal_balance - new_balance|` for each token. This fee is missing in the implementation — users can deposit one-sided or skewed liquidity without penalty. `compute_lp_mint_amount = total_supply * (D1 - D0) / D0` — no per-token fee calculation No `ideal_balance`, `difference`, or `dynamic_fee` computation anywhere in the LP mint path One-sided deposit of 2x tokenA costs less than 0.5% in slippage — should cost at least the swap fee (e.g., 3-5%) on the skewed portion A user can skew the pool ratio dramatically with a deposit, then withdraw balanced, capturing value from other LPs
  - **Specific proof:** 1. In the LP minting function for StableSwap, check whether any fee is charged based on the imbalance of the deposit. 2. If the only calculation is `shares = total_supply * (D1 - D0) / D0` with no per-token fee computation, flag. 3. Test: deposit a large one-sided amount (e.g., 2x of token A, 0 of token B). Compare the cost (shares received / value deposited) against a balanced deposit. In a correct implementation, the one-sided deposit should receive fewer shares due to the imbalance fee.
  - **Provenance:** [DROZER-SS-3](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/stableswap.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/stableswap.md); gdroz3r/drozer-lite — checklists/stableswap.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/stableswap.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/stableswap.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-AMM-065] Newton-Raphson Non-Convergence Returns Result Instead of Error** _(exploit-pattern; medium)_: The D or y computation uses a loop with a fixed iteration cap (e.g., 32, 256, 1000). On each iteration, it checks if `|current - previous| <= 1`. If the loop completes without converging, the function returns the last value instead of an error. In a correct implementation (Curve reference), non-convergence raises an error and the swap/deposit fails — only withdrawals remain functional, protecting LPs.
  - **Trigger:** The D or y computation uses a loop with a fixed iteration cap (e.g., 32, 256, 1000). On each iteration, it checks if `|current - previous| <= 1`. If the loop completes without converging, the function returns the last value instead of an error. In a correct implementation (Curve reference), non-convergence raises an error and the swap/deposit fails — only withdrawals remain functional, protecting LPs. Loop `for _ in 0..N { ... if converged { break; } }` followed by `Some(d)` outside the loop — always returns even if not converged No `return` or early exit on convergence — the `break` exits the loop and falls through to a successful return Correct pattern: convergence should `return Some(d)` inside the loop; after the loop, return `None` or `Err` Curve reference: `raise` after the loop (Python); the function never returns normally without convergence
  - **Specific proof:** 1. For every Newton-Raphson loop, check what happens after the loop ends WITHOUT convergence (i.e., the break condition was never met). 2. If the function returns `Some(last_value)` or `Ok(last_value)` after the loop, flag. It should return `None`, `Err(ConvergeError)`, or equivalent. 3. Check whether there are two D computation functions with different iteration caps (e.g., 32 for swaps, 256 for LP) — inconsistency flag per MATH-4. 4. Test with extremely imbalanced pools where convergence is slow — the function will return a wrong value instead of failing.
  - **Provenance:** [DROZER-SS-4](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/stableswap.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/stableswap.md); gdroz3r/drozer-lite — checklists/stableswap.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/stableswap.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/stableswap.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-AMM-066] Static Amplification Parameter (No Ramping Mechanism)** _(exploit-pattern; medium)_: The amplification parameter is stored as a static field in the pool configuration (e.g., `PoolType::StableSwap { amp: u64 }`). No `update_amp`, `ramp_A`, or similar function exists to modify it post-creation. During normal conditions, the pool works fine. During a depegging event (one stablecoin loses its peg), a high A value keeps the price artificially stable, allowing holders of the depegged asset to swap at near-1:1 rates and drain the pool of the healthy asset.
  - **Trigger:** The amplification parameter is stored as a static field in the pool configuration (e.g., `PoolType::StableSwap { amp: u64 }`). No `update_amp`, `ramp_A`, or similar function exists to modify it post-creation. During normal conditions, the pool works fine. During a depegging event (one stablecoin loses its peg), a high A value keeps the price artificially stable, allowing holders of the depegged asset to swap at near-1:1 rates and drain the pool of the healthy asset. `PoolType::StableSwap { amp: u64 }` — static field, no update path No `ExecuteMsg::RampAmp` or `ExecuteMsg::UpdatePoolParams` in the message enum Pool fees can be set at creation but amp cannot be adjusted — asymmetric mutability Documentation mentions "stable assets" or "pegged assets" but no depeg protection mechanism Contrast with Curve: `ramp_A(future_A, future_time)` with `MIN_RAMP_TIME` safety constraint
  - **Specific proof:** 1. Check whether the amplification parameter can be modified after pool creation. Search for `ramp`, `update_amp`, `set_amp`, `modify_amp` in the execute message enum and handler. 2. If no modification mechanism exists, flag as MEDIUM — the pool cannot adapt to market conditions. 3. Check whether pool parameters are generally immutable post-creation (intentional design) or whether other parameters can be updated. 4. Assess the severity: if the DEX is designed for stablecoin pairs only, this is higher severity (depegging is the primary risk). If it supports volatile pairs via StableSwap (unusual), severity is lower.
  - **Provenance:** [DROZER-SS-5](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/stableswap.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/stableswap.md); gdroz3r/drozer-lite — checklists/stableswap.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/stableswap.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/stableswap.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
