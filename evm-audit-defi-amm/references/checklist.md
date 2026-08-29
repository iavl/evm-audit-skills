# AMM & DEX Security Checklist

## General AMM

- [ ] **Cross-contract view reentrancy on reserve updates**: Even with `nonReentrant`, if `reserves[]` is updated AFTER an external call (e.g., ERC777 token transfer), another contract can read stale reserves via a view function during the callback. Must follow CEI pattern when updating reserves. Look for: reserve state updates after `transfer()`/`transferFrom()` calls. [Decurity AMM]

- [ ] **Flash loan callback ordering**: AMM flash loan (FlashSwap in Uniswap) callback must be invoked AFTER the token transfer, not before. If called before, the borrower receives nothing but the callback has already executed. Look for: flash loan implementations where callback precedes token movement. [Decurity AMM]

- [ ] **Fee-on-transfer token handling**: AMM must either explicitly support FOT tokens (measure balance diff) or explicitly reject them. Neither = accounting mismatch. Balancer lost funds from a deflationary token that reduced reserves without AMM knowledge. Look for: AMMs that accept arbitrary tokens without FOT handling. [Decurity AMM, beirao AMM-03]

- [ ] **Rebasing tokens break AMM accounting**: Rebasing tokens change balance without transfers, but AMMs track reserves internally. The AMM's reserves diverge from actual balances, creating extractable arbitrage. Look for: AMMs holding rebasing tokens without rebase tracking or explicit blocklist. [beirao AMM-04]

- [ ] **Arbitrary call from user input**: If the AMM has a function accepting arbitrary calldata (e.g., for callbacks), an attacker can craft calls to drain approvals. Look for: `address.call(userProvidedData)` patterns. [Decurity AMM]

- [ ] **Signed integer balance updates**: If the AMM tracks balances with signed integers, `-int(amount)` can overflow for edge-case amounts like `type(uint256).max`. Look for: `int256` used for balance deltas without bounds checking. [Decurity AMM]

## Slippage Protection

- [ ] **Hardcoded slippage (especially `minAmountOut = 0`)**: Hardcoded zero slippage = sandwich attack for free. Every swap must have a user-specified or properly-calculated minimum output. Look for: `amountOutMinimum: 0`, `sqrtPriceLimitX96: 0`, or any hardcoded slippage parameter. [beirao U-01, U-02]

- [ ] **On-chain slippage calculation is manipulable**: If `minAmountOut` is calculated from on-chain data (e.g., `getAmountsOut()`, pool reserves), the attacker manipulates the pool first, then the slippage check passes the manipulated value. Must calculate slippage off-chain or use TWAPs. Look for: `minAmountOut` derived from pool.getReserves() or router.getAmountsOut(). [beirao U-02, Dacian]

- [ ] **[AUDITMOS-SLIPPAGE-3] Slippage calculated from the wrong reference amount**: If `minAmountOut` is derived from the input amount or another denomination instead of the expected output for the actual route, the bound can be far too loose or too strict and fail to protect value. Look for: `minOut = amountIn * ...` in swaps between differently priced tokens, or slippage calculations that do not use the expected output amount. [Source: Auditmos `audit-slippage`, pattern #3](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010

- [ ] **No expiration deadline**: Swaps without a deadline parameter can be held by validators/MEV bots and executed later at a worse price. Look for: `deadline: type(uint256).max` or missing deadline parameter. [beirao U-02]

- [ ] **Missing refunds after swaps**: If a swap doesn't use all input tokens, the remainder should be refunded. Look for: swap functions that pull exact `amountIn` but may not use all of it. [beirao U-03]

## Uniswap V4 Hooks

- [ ] **Hook permissions derived from address bits, not contract code**: Uniswap V4 checks `uint160(address(hook)) & flag` to determine permissions. If the hook is deployed at an address that doesn't encode the right flag bits, the function is silently never called. Look for: hook deployment without proper address mining for permission flags. [Hacken UniV4]

- [ ] **Incorrect return type from hooks**: `beforeSwap` must return `(bytes4, BeforeSwapDelta, uint24)`. Returning wrong types causes overflow or reverts. Look for: hook functions with non-standard return types. [Hacken UniV4]

- [ ] **BeforeSwapDelta sign confusion**: BeforeSwapDelta is from the HOOK's perspective. Fees (hook takes tokens) must be NEGATIVE. Rebates (hook gives tokens) must be POSITIVE. Getting the sign wrong sends tokens the wrong way. Look for: positive deltas used as fees. [Hacken UniV4]

- [ ] **Delta ordering depends on `zeroForOne`**: The meaning of specified/unspecified in `BeforeSwapDelta` depends on `params.zeroForOne`. Using the wrong mapping causes tokens to flow in the wrong direction. Look for: `toBeforeSwapDelta()` calls that don't check swap direction. [Hacken UniV4]

- [ ] **Unsettled deltas revert `unlock()`**: ALL hook deltas must sum to zero via `settle()`/`take()` before transaction finalization. If any delta is non-zero, `NonzeroDeltaCount` check in `unlock()` reverts the entire transaction. Look for: hooks that modify deltas without corresponding settlement calls. [Hacken UniV4]

- [ ] **Async hooks steal custody**: Async hooks (where `specifiedTokenDelta = -params.amountSpecified`) completely replace Uniswap's swap logic and take full custody of the user's tokens. A malicious async hook can simply transfer tokens to the deployer. Look for: `beforeSwap` returning a specifiedTokenDelta equal to negative amountSpecified. [Hacken UniV4]

- [ ] **Hooks attached to multiple pools**: PoolManager doesn't enforce hook exclusivity. An attacker can create a pool with your hook attached and trigger it from their pool. Look for: hooks that don't validate the PoolKey against an expected pool. [Hacken UniV4]

- [ ] **Upgradeable hooks can't gain new permissions post-deploy**: Hook address encodes permission bits at deploy time. Upgrading the implementation to add `afterSwap()` won't work if the address bits don't include `AFTER_SWAP_FLAG`. Look for: UUPSUpgradeable hooks with planned future function additions. [Hacken UniV4]

- [ ] **Missing access control on hook functions**: If hooks don't check that `msg.sender == poolManager`, anyone can call them directly with arbitrary parameters. Look for: hook functions without `onlyPoolManager` or similar checks. [Hacken UniV4]

- [ ] **Dynamic fee manipulation via front-running**: Hooks that adjust swap fees based on oracle prices or market conditions can be front-run by MEV bots who trade before/after fee changes. Look for: fee logic that depends on manipulable on-chain state. [Hacken UniV4]

- [ ] **Unbounded loops in hooks cause DoS**: A hook with a growing array that's iterated on every swap will eventually hit gas limits, making the pool unusable. Look for: loops over dynamic arrays in hook functions. [Hacken UniV4]


## TWAMM (Time-Weighted AMM)

- [ ] **Rebasing token balance changes during long-term swaps**: If a TWAMM holds rebasing tokens, balance changes mid-swap corrupt the order execution math. Look for: TWAMM implementations that don't block rebasing tokens. [Decurity AMM]

- [ ] **Insufficient liquidity check before swap execution**: TWAMM must verify sufficient liquidity exists before executing long-term orders. Look for: missing liquidity validation in TWAMM execution logic. [Decurity AMM]

## AMM Integration (for protocols integrating AMMs)

- [ ] **Callback function must verify caller is the pool**: When implementing Uniswap-style callbacks (`uniswapV3SwapCallback`, etc.), the callback must verify `msg.sender` is the legitimate pool contract. Without this, anyone can call the callback to steal tokens. Look for: swap callbacks without pool address verification. [Decurity AMM]

- [ ] **Don't use `pool.swap()` directly**: Always use Router contracts which enforce safety checks (deadline, slippage). Direct pool calls skip all protections. Look for: direct `IUniswapV3Pool.swap()` calls instead of router. [beirao U-07]

- [ ] **Pool reserves are manipulable**: Never use `pool.getReserves()` as a price oracle. Flash loans can manipulate reserves within a single transaction. Look for: `getReserves()` used in price calculations or access control. [beirao U-06]

- [ ] **AMM pool token0/token1 order differs by chain**: On Arbitrum, a pair may be WETH/USDC (WETH=token0), while on Polygon it's USDC/WETH (USDC=token0). Hardcoding the order breaks cross-chain. Look for: hardcoded assumptions about which token is token0 or token1. [multichain-auditor, beirao U-04]

- [ ] **Verify pool factory address**: If pools aren't from a whitelisted factory, they could be fakes. Verify `pool.factory() == expectedFactory`. Look for: pool addresses from user input without factory verification. [beirao U-05]

- [ ] **Hardcoded DEX pool fees prevent optimal routing**: Using a fixed fee tier (e.g., always 0.3%) may route through a suboptimal pool when a better fee tier exists. Look for: hardcoded fee parameters in swap paths. [ERC4626 primer pattern #46]

## Uniswap V4 Hooks Security (Expanded)

- [ ] **Hook address encodes permissions via low bits**: V4 derives hook permissions from the hook contract's address using bitwise operations, NOT from the contract itself. If a hook is deployed at an address missing the required flag bits, PoolManager will never call it. Conversely, extra bits cause calls to non-existent functions → revert → DoS. Look for: hooks deployed without address mining that matches intended permission flags. [Hacken UniV4, OpenZeppelin UniV4]

- [ ] **Hooks on multiple pools without pool isolation**: Any hook can be attached to multiple pools by default (no exclusivity enforcement in PoolManager). If hook state is shared across pools, one pool's operations corrupt another's state. Look for: hooks without per-PoolKey storage mapping or `beforeInitialize` that restricts to one pool. [Hacken UniV4, OpenZeppelin UniV4]

- [ ] **Async hooks take full custody of swap amounts**: Async hooks can set `specifiedTokenDelta = -params.amountSpecified`, completely bypassing Uniswap's swap logic. A malicious async hook can steal all swapped tokens by transferring them to an attacker address. Look for: hooks that return non-zero BeforeSwapDelta that reverses the swap amount. [Hacken UniV4]

- [ ] **Missing `onlyPoolManager` on hook functions**: Hook callback functions (beforeSwap, afterSwap, etc.) should only be callable by PoolManager. Without this check, anyone can call the hook directly and manipulate state or drain funds (see Cork Protocol $11M hack). Look for: hook functions without `msg.sender == address(poolManager)` check. [Hacken UniV4, OpenZeppelin UniV4]

- [ ] **Hook BeforeSwapDelta sign convention**: BeforeSwapDelta is from the hook's perspective: negative = hook takes tokens, positive = hook gives tokens. Wrong sign means the hook pays users instead of charging fees, or vice versa. Look for: positive deltas where fees should be negative. [Hacken UniV4]

- [ ] **Unsettled hook deltas cause revert in `unlock()`**: PoolManager checks `NonzeroDeltaCount` at end of `unlock()`. If a hook modifies deltas but doesn't settle them (via `settle()`/`take()`), the entire transaction reverts. Look for: hooks that return non-zero deltas without corresponding settlement logic. [Hacken UniV4]

- [ ] **Upgradeable hooks break address-encoded permissions**: If a hook is upgradeable (UUPS/Transparent proxy), the deployed address permissions are fixed at deployment. Adding new callback functions in an upgrade won't work because the address bits don't encode the new permissions. Look for: upgradeable hook contracts that plan to add callbacks post-deployment. [Hacken UniV4, OpenZeppelin UniV4]

- [ ] **lpFeeOverride can DoS swaps**: If a hook returns an invalid or excessive lpFeeOverride value, swaps on that pool fail. A centralized hook owner can set fees to 100%, effectively locking pool funds. Look for: hooks with admin-controlled fee parameters without bounds. [Hacken UniV4]

- [ ] **Hook `unlockCallback` data can call arbitrary functions**: The data passed to `unlockCallback` can be crafted to call any function on the hook. If the callback data formation isn't restricted, it acts as an unprotected entry point. Look for: hooks where users can influence unlockCallback calldata. [OpenZeppelin UniV4]

- [ ] **JIT liquidity attacks on hook-managed positions**: If a hook manages liquidity positions, anyone can trigger fee accrual on those positions at any time. Just-in-time liquidity modifications can conflict with the hook's fee accounting. Look for: hooks that accrue fees on positions without protecting against JIT manipulation. [OpenZeppelin UniV4]

- [ ] **Swap direction symmetry in hooks**: A swap can be zeroForOne or oneForZero, exactInput or exactOutput. Hook deltas must correctly handle all 4 combinations. Missing symmetry means hooks work for some swap types but break for others. Look for: hook logic that only handles `params.zeroForOne == true` or `params.amountSpecified < 0`. [OpenZeppelin UniV4, Hacken UniV4]

## AMM General (Expanded from Decurity/Beirao)

- [ ] **TWAMM rebasing token interaction**: If a TWAMM (Time-Weighted AMM) holds a rebasing token during a long-term swap, the balance changes from rebasing create an undercollateralized or overcollateralized position. Look for: TWAMM implementations that don't track rebasing token balance changes. [Decurity AMM]

- [ ] **Signed integer overflow in pool balance updates**: If an AMM uses signed integers for balance deltas, `-int(amount)` can overflow when `amount = type(uint256).max`. Look for: signed casts of user-supplied amounts in pool accounting. [Decurity AMM]

- [ ] **AMM callback address validation**: Callback functions (flash swap callbacks, swap callbacks) must validate that the caller is the expected AMM pool. Without this check, an attacker deploys a fake pool and calls the callback to steal tokens. Look for: callback functions that don't verify `msg.sender` against a known factory/pool address. [Decurity AMM]

- [ ] **AMM `token0`/`token1` order differs across chains**: In Uniswap-style AMMs, `token0 < token1` by address sort. The same token pair has different ordering on different chains because contract addresses differ. Price calculations that assume a fixed order will invert on some chains. Look for: hardcoded assumptions about which token is token0 vs token1. [multichain-auditor, beirao U-04]

- [ ] **Hardcoded slippage is forbidden**: Setting `amountOutMin = 0` or a hardcoded value allows sandwich attacks. Slippage must be calculated off-chain or via oracle and passed as parameter. Look for: `swapExactTokensForTokens(..., 0, ...)` or similar with zero/hardcoded minOut. [beirao U-01, U-02]

- [ ] **On-chain slippage calculation can be manipulated**: If slippage bounds are calculated on-chain from the current pool state, an attacker manipulates the pool state first, then the slippage calculation reflects the manipulated state. Look for: `minAmountOut = pool.getAmountOut(amount) * 99 / 100` patterns. [beirao U-02]

- [ ] **Don't rely on `pool.swap()` directly — use Router**: Direct pool interaction skips safety checks (deadline, slippage, path validation) that the router provides. Look for: direct calls to `IUniswapV3Pool.swap()` instead of going through `SwapRouter`. [beirao U-06, U-07]

- [ ] **Missing swap refund handling**: If a swap function receives more input tokens than needed (exact output swaps), the excess must be refunded. Look for: swap wrappers that don't return unused input tokens to the caller. [beirao U-03]

---

## Dacian — Concentrated Liquidity Manager Vulnerabilities (Phase 3)

- [ ] **Drain protocol via sandwich attack on owner functions missing TWAP check**: If `setPositionWidth()` or `unpause()` calls `_setTicks()` + `_addLiquidity()` without `onlyCalmPeriods` TWAP check, an attacker can sandwich the owner's tx to force liquidity deployment at manipulated prices, draining all protocol tokens. Beefy Finance lost ~$1.2M in this pattern. [Source: Dacian — CLM Vulnerabilities, Cyfrin Beefy Audit]

- [ ] **Owner rug-pull via ineffective TWAP parameters**: If `maxDeviation` and `twapInterval` can be set to arbitrary values by owner (e.g., maxDeviation=100%, twapInterval=1), the TWAP manipulation check becomes ineffective. Gamma Strategies was exploited this way. Fix: enforce min/max bounds on TWAP parameters. [Source: Dacian — CLM Vulnerabilities, Cyfrin Beefy Audit]

- [ ] **Tokens permanently stuck due to fee distribution rounding**: When distributing fees via `nativeEarned * fees.call / DIVISOR` etc., rounding remainders accumulate permanently in the contract. Fix: compute last recipient's share as `total - sum(others)`. [Source: Dacian — CLM Vulnerabilities, Cyfrin Beefy Audit]

- [ ] **Stale token approvals after router address update**: If `setUnirouter()` updates the router address without revoking unlimited `forceApprove` from the old router, the old router can still spend all protocol tokens. [Source: Dacian — CLM Vulnerabilities, Cyfrin Beefy Audit]

- [ ] **Updated management fees retrospectively applied to pending LP rewards**: If owner changes fee % and LP rewards are only collected at next `harvest()`, new higher fees apply retroactively to rewards earned under the previous lower fee. Fix: collect pending rewards before updating fees. [Source: Dacian — CLM Vulnerabilities, Cyfrin Beefy/Arrakis]

- [ ] **CLM overflow for large but valid sqrtPriceX96**: Protocol should not revert due to overflow for valid range of `sqrtPriceX96` values from the Uniswap pool. [Source: Dacian — CLM Vulnerabilities, Cyfrin Beefy Audit]

- [ ] **Withdraw returns 0 tokens while burning positive shares**: Edge case where `withdraw()` returns zero tokens but burns user's shares, effectively stealing from the user. [Source: Dacian — CLM Vulnerabilities, Cyfrin Beefy Audit]

## Dacian — DeFi Slippage Attacks (Phase 3)

- [ ] **No expiration deadline — block.timestamp provides no protection**: Setting deadline to `block.timestamp` offers zero protection because validators can hold the tx and `block.timestamp` will always equal the block it's included in. Deadline must be user-specified future timestamp. [Source: Dacian — DeFi Slippage Attacks]

- [ ] **Slippage enforced on intermediate operation, not final amount**: If `minTokensOut` is checked during `_exitBalancerPool()` but a subsequent treasury skim further reduces the user's output, the user receives less than their specified minimum. Slippage must be enforced on the final step. [Source: Dacian — DeFi Slippage Attacks, Sherlock Olympus Update]

- [ ] **On-chain slippage calculation via Quoter is manipulable**: `Quoter.quoteExactInput()` itself performs a swap and is subject to sandwich manipulation. Slippage parameters must be calculated off-chain by the user. [Source: Dacian — DeFi Slippage Attacks, Sherlock Derby]

- [ ] **Hard-coded slippage freezes user funds during volatility**: Fixed low slippage (e.g., 1%) protects in normal conditions but causes all withdrawals to revert during high volatility, freezing user funds. Users must be able to override default slippage. [Source: Dacian — DeFi Slippage Attacks, Code4rena Sturdy]

- [ ] **Hard-coded UniswapV3 fee tier**: If the swap function hard-codes fee tier (e.g., 3000), it will fail for token pairs where that tier doesn't exist, or provide inferior liquidity vs another tier. Allow users to pass fee tier. [Source: Dacian — DeFi Slippage Attacks]

- [ ] **Minting functions are swaps without slippage**: When protocol mints native tokens based on pool reserves (effectively a swap), users must be able to specify slippage. Without it, the mint is sandwichable. [Source: Dacian — DeFi Slippage Attacks, Code4rena Vader]

- [ ] **Mismatched slippage precision across token decimals**: If `minTokenOut` is calculated in 6 decimals but the output token has 18 decimals, the slippage check is ineffective (off by 12 orders of magnitude). Must scale slippage to output token's precision. [Source: Dacian — DeFi Slippage Attacks, Sherlock RageTrade]

- [ ] **[AUDITMOS-SLIPPAGE-10] Token-unit slippage can hide economic loss**: A minimum amount expressed only in token units may still accept a large loss in USD value when the token price moves sharply or the operation changes asset composition. Look for: slippage checks that compare raw token quantity while the protected value is economically denominated in another asset, with no price/risk bound or explicit design rationale. [Source: Auditmos `audit-slippage`, pattern #10](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/SKILL.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010

- [ ] **[AUDITMOS-SLIPPAGE-12] Flash-swap repayment lacks slippage/amount bounds**: If a flash-swap callback obtains the repayment token through a swap without a caller-controlled minimum output or maximum input and a final repayment check, adverse execution can force overpayment. Look for: callback repayment swaps with `amountOutMinimum == 0`, an unbounded `amountInMaximum`, or repayment based on a manipulable quote. [Source: Auditmos `audit-slippage`, pattern #12](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/SKILL.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010

## Supplemental Attack Vectors (SAS-AV)

These vectors are merged from sanbir/solidity-auditor-skills; each item retains a detection condition (D), false-positive gate (FP), and source provenance.

- [ ] **[SAS-AV-111] Uniswap V4 Cached State Desynchronization**
  - **D:** Hook caches pool state (`sqrtPriceX96`, `liquidity`, `tick`) in `beforeSwap` but state changes during the swap. `afterSwap` reads stale cached values for fee calculations or rebalancing decisions.
  - **FP:** State re-read from pool in `afterSwap`. Cache explicitly invalidated between hooks. No cross-hook state dependency.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-197

- [ ] **[SAS-AV-112] Uniswap V4 Hook Data Manipulation**
  - **D:** Hook reads parameters from `hookData` bytes passed through the swap path. Attacker crafts `hookData` to manipulate hook behavior — bypassing fee calculations, altering routing decisions, or triggering unintended state changes in the hook contract.
  - **FP:** `hookData` validated against expected schema (length, types). Critical parameters derived from pool state, not `hookData`. Hook ignores or doesn't use `hookData`. Authenticated `hookData` (signed by trusted relayer).
  - **Origin:** `sanbir/solidity-auditor-skills` AV-214

- [ ] **[SAS-AV-116] Loss-Versus-Rebalancing (LVR) in Constant-Function AMMs**
  - **D:** AMM with constant-function pricing and static fees. Searchers continuously arbitrage stale pool price against external markets, extracting from LPs on every price movement. Concentrated liquidity amplifies extraction.
  - **FP:** Dynamic fee adjusting for volatility (Uniswap V4 hooks). MEV-aware design (batch auctions, CoW AMM). Fee tier covers expected LVR for pair volatility.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-249

- [ ] **[SAS-AV-117] TWAP Accumulator Not Updated During Sync or Skim**
  - **D:** `sync()`/`skim()` updates reserves but doesn't call `_update()` to advance TWAP accumulator. Stale TWAP enables manipulation via sync-then-trade.
  - **FP:** `sync()` calls `_update()` before overwriting reserves. TWAP from external oracle. Uniswap V3 `observe()` used.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-256

- [ ] **[SAS-AV-118] Adverse Selection — Passive LP Value Extraction via Selective JIT**
  - **D:** No time-weighting or lock on fee distribution. JIT providers enter only during high-fee moments and exit during adverse moves. Passive LPs bear 100% IL but share fees with JIT providers bearing zero IL.
  - **FP:** Fee share time-weighted by duration. Dynamic fee increases during volatility. Withdrawal cooldown makes selective entry costly.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-265

- [ ] **[SAS-AV-119] Tick Crossing Fee Accounting Manipulation via JIT**
  - **D:** On tick crossing, `feesPerLiquidityOutside` flips (`global - outside`). JIT provider adds at tick boundary after fees accumulate but before crossing — flip credits position with pre-existing fees it didn't earn.
  - **FP:** `feesPerLiquidityInsideLast` set at creation; crossing correctly partitions pre/post fees. Same-block creation and crossing yield zero claimable.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-266

- [ ] **[SAS-AV-120] Fee Accumulation Rounding Extraction via Large JIT Position**
  - **D:** `feesPerLiquidity += (feeAmount << 128) / totalLiquidity`. Large JIT position inflates `totalLiquidity` — per-unit increment rounds to zero for existing LPs while JIT provider captures truncated amount.
  - **FP:** Sufficient precision (Q128+) ensures rounding loss < 1 wei at realistic ratios. Protocol minimum fee increment.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-267

- [ ] **[SAS-AV-121] Atomic JIT Liquidity via Flash Accounting**
  - **D:** Flash accounting / lock-callback allows add-liquidity + swap + remove-liquidity atomically with zero capital. No minimum hold duration or fee decay. Attacker adds concentrated liquidity at current tick, swap executes through it, liquidity removed — all in one callback.
  - **FP:** Minimum hold duration enforced. Fee share weighted by time-in-pool. Withdrawal fee on short-lived positions. Flash callback restricted from `updatePosition`.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-268

- [ ] **[SAS-AV-122] First-Swap Extraction on Newly Created Pools**
  - **D:** New pool with minimal liquidity — first significant swap is extremely fee-rich. Attacker front-runs by adding concentrated liquidity, captures outsized fees, removes. Extreme: initializes at skewed price, profits from arb correction.
  - **FP:** Minimum locked seed liquidity (Uniswap V2 `MINIMUM_LIQUIDITY`). Fee ramp-up for new pools. Anti-sniping delay on creation.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-291

- [ ] **[SAS-AV-123] Empty Swap Path Bypasses Token Validation**
  - **D:** Empty swap data/zero-length path returns input amount without swapping — and without validating input == output token. Attacker skips swap, receives output token from contract's balance. Pattern: `if (swapData.length == 0) return amount;` without `require(fromToken == toToken)`.
  - **FP:** Empty path enforces `require(fromToken == toToken)`. Swap mandatory. Reverts on empty data. Post-swap balance delta check.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-294

## drozer-lite Additions

The checks below are the canonical runtime additions from the EVM-relevant drozer-lite profiles. Each item retains the source profile and pinned commit.

- [ ] **[DROZER-DEX-7] Pool Formula / Token-Count Mismatch**
  - **D:** A DEX supports multiple pool types (constant product, stable swap, weighted). Each pool type's swap formula is designed for a specific number of tokens. The pool creation function validates the token count against a global max (e.g., MAX_ASSETS = 4) but does NOT validate against the pool-type-specific maximum. A constant-product pool can be created with 3+ tokens even though the x*y=k formula only works for 2 tokens.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** 1. For each pool type, identify the mathematical formula used for swaps. 2. Determine how many tokens the formula supports: constant product (x*y=k) = 2; Balancer weighted = N; StableSwap = N. 3. Check whether pool creation enforces the pool-type-specific token limit. If a constant-product pool can be created with >2 tokens, flag as HIGH. 4. Check slippage tolerance assertions — if they hardcode `deposits.len() == 2` but the check is conditional (e.g., only runs when slippage_tolerance is Some), the guard can be bypassed.
  - **Look for:** `MAX_ASSETS_PER_POOL = 4` applied uniformly to both constant-product and stable-swap pools Constant-product swap formula uses only `offer_pool` and `ask_pool` (2 tokens) but pool has 3+ tokens Slippage check requires exactly 2 deposits but is inside `if let Some(slippage_tolerance)` — bypassed when None Liquidity addition works for N tokens but shares calculated via `sqrt(d0 * d1)` (2-token formula) Pool creation validates `len >= 2 && len <= MAX` but not `if ConstantProduct then len == 2`
  - **Origin:** [gdroz3r/drozer-lite — checklists/dex.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-DEX-8] Liquidity Operation Lacks Minimum-Output Protection**
  - **D:** An `add_liquidity` / `withdraw_liquidity` / `remove_liquidity` function computes asset amounts from the pool's current ratios but does not expose minimum-output or maximum-input bounds. A user can receive fewer assets, or donate excess assets, after pool state changes between submission and execution. Industry-standard routers provide `amountAMin`/`amountBMin` and deadline parameters.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** 1. For every liquidity add/remove path, check whether the user can specify minimum received amounts and maximum input amounts. 2. Verify the bounds are checked after the final pool operation, not only on an intermediate calculation. 3. If neither minimum-output nor equivalent slippage protection exists, flag. 4. For deposits, separately check whether imbalanced excess is refunded.
  - **Look for:** `withdraw_liquidity(pool_id)` with no `min_assets_out` parameter `addLiquidity()` with `amountAMin == 0` and `amountBMin == 0` Refund calculated from current ratios with no floor check No deadline or user-controlled tolerance on liquidity operations
  - **Origin:** [gdroz3r/drozer-lite — checklists/dex.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-DEX-10] Disproportionate Deposit Loss (Excess Not Refunded)**
  - **D:** A `provide_liquidity` function calculates per-asset share ratios (`deposit_amount * total_share / pool_amount`) and mints LP tokens based on `min(share_ratios)`. The excess tokens from the non-minimum asset are added to the pool but not reflected in the minted shares. These excess tokens are permanently donated to all existing LPs. The function does NOT refund the excess to the depositor.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** 1. For every liquidity provision function, check how shares are computed when deposit ratios don't match pool ratios. 2. If `min(share_ratios)` is used, calculate the implied excess for each asset. 3. Check whether the excess is: (a) refunded to the depositor, (b) used to compute additional shares, or (c) silently donated to the pool. 4. If (c), check whether slippage tolerance protects against this loss. Note: slippage tolerance checks LP tokens received, NOT whether excess tokens are returned.
  - **Look for:** `share = min(deposit_A * total_share / pool_A, deposit_B * total_share / pool_B)` with no refund of the difference User deposits 100A + 200B into a 1:1 pool; receives shares worth 100A + 100B; 100B is donated Slippage tolerance passes because LP tokens are within tolerance — but user lost 100B No industry-standard `_addLiquidity` that computes optimal amounts before the actual deposit (cf. Uniswap V2 Router) A front-runner changes the pool ratio between tx submission and execution, maximizing the user's excess donation
  - **Origin:** [gdroz3r/drozer-lite — checklists/dex.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-DEX-11] Spread / Slippage Computed Before Fee Deduction**
  - **D:** A swap function computes `return_amount` (before fees), then `spread_amount = expected_return - return_amount`. Fees are then deducted from `return_amount` to get `final_return`. The `spread_amount` is compared against `max_spread`. Because `spread_amount` is computed before fees, it INCLUDES the fee as part of the "spread." The actual price slippage (excluding fees) is smaller than the reported `spread_amount`, making the spread check pass when the real slippage exceeds the user's tolerance.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** 1. In the swap computation, identify where `spread_amount` is calculated relative to fee deduction. 2. If `spread_amount = expected - return_amount` and `return_amount` is PRE-fee, the spread includes fees. 3. Check whether the spread check (`assert_max_spread`) uses this inflated spread or the actual post-fee slippage. 4. The correct approach: compute spread AFTER fees, or compute spread as `expected_return - (return_amount - fees)`.
  - **Look for:** `spread_amount = offer_amount * exchange_rate - return_amount` where `return_amount` is before fees `assert_max_spread(spread_amount, return_amount + spread_amount)` — spread includes fees For StableSwap: `spread_amount = offer_amount - return_amount` (1:1 assumption) computed before fees Fees are 5-10% but spread check uses 1% tolerance — the fee inflates the spread past the tolerance, so the check effectively allows ~15% real slippage with a 1% setting
  - **Origin:** [gdroz3r/drozer-lite — checklists/dex.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-SS-1] Decimal Normalization Inconsistency Between Swap and LP Paths**
  - **D:** A StableSwap implementation has two code paths that compute the invariant D: one for swaps (which normalizes via `decimal_with_precision` or rate multipliers) and one for LP minting/withdrawal (which sums raw amounts). When tokens have different decimals (e.g., 6 vs 18), the LP path computes a D that is dominated by the higher-decimal token, granting disproportionate shares to depositors of that token.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** 1. Identify every call site that computes the StableSwap invariant D. 2. For each call site, check whether token amounts are normalized to a common decimal base BEFORE being passed to the D computation. 3. Compare the normalization logic between the swap path and the LP mint path. If they differ, flag. 4. Test with two tokens of different decimals (e.g., 6 and 18): deposit equal-value amounts via both paths and compare the D values.
  - **Look for:** Swap path: `offer_pool = Decimal256::decimal_with_precision(amount, precision)` — normalized LP path: `sum_x = deposits.iter().fold(zero, |acc, x| acc + x.amount)` — raw amounts, no normalization D computation for LP uses raw `Uint128` amounts while swap uses `Decimal256` with precision Two tokens with 6 and 18 decimals: depositing 1e6 USDC and 1e18 DAI produces wildly different D vs depositing 1e18 USDC and 1e6 DAI — but both should be equivalent in value
  - **Origin:** [gdroz3r/drozer-lite — checklists/stableswap.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/stableswap.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-SS-2] Multi-Token Invariant Uses Only Swap Pair (Disjoint Computation)**
  - **D:** The StableSwap invariant D is defined over ALL N tokens: `An∑(all xi) + D = ADⁿ + Dⁿ⁺¹/(nⁿ∏(all xi))`. When computing a swap between token A and token B in a 3-token pool, the implementation passes only `(offer_pool, ask_pool)` to the D/y computation, but uses `n_coins = 3`. This produces an incorrect D because the sum and product only include 2 of the 3 token balances, while the exponent uses N=3. Swaps between different pairs in the same pool preserve different (incorrect) invariants, creating arbitrage opportunities.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** 1. For every StableSwap swap computation, check how many token balances are passed to the D/y computation function. 2. If the function receives only the offer and ask balances (2 tokens) but `n_coins` reflects the actual pool size (3+), flag as HIGH. 3. Compare against Curve reference: the `get_y` function iterates over ALL pool balances except the target token. 4. Test: in a 3-token pool, check if A-B swaps produce different slippage than B-C swaps with identical pool composition — they should be equivalent in a correct implementation.
  - **Look for:** `compute_swap(n_coins=3, offer_pool, ask_pool, ...)` but D is computed from only `offer_pool + ask_pool` `calculate_stableswap_d(offer_pool, ask_pool)` — sum uses 2 values but `ann = amp * n_coins` uses 3 The `pool_sum` or `sum_pools` variable only includes 2 token balances D/y functions accept only 2 pool amounts as parameters despite being called for pools with 3+ tokens Different token-pair swaps in the same pool produce inconsistent pricing
  - **Origin:** [gdroz3r/drozer-lite — checklists/stableswap.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/stableswap.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-SS-3] Missing Imbalanced Deposit Fee**
  - **D:** The LP minting function computes shares as `total_supply * (D1 - D0) / D0` where D1 includes the new deposits and D0 is the pre-deposit invariant. Curve additionally computes per-token ideal balances (`ideal_balance = D1 * old_balance / D0`) and charges a fee on the `|ideal_balance - new_balance|` for each token. This fee is missing in the implementation — users can deposit one-sided or skewed liquidity without penalty.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** 1. In the LP minting function for StableSwap, check whether any fee is charged based on the imbalance of the deposit. 2. If the only calculation is `shares = total_supply * (D1 - D0) / D0` with no per-token fee computation, flag. 3. Test: deposit a large one-sided amount (e.g., 2x of token A, 0 of token B). Compare the cost (shares received / value deposited) against a balanced deposit. In a correct implementation, the one-sided deposit should receive fewer shares due to the imbalance fee.
  - **Look for:** `compute_lp_mint_amount = total_supply * (D1 - D0) / D0` — no per-token fee calculation No `ideal_balance`, `difference`, or `dynamic_fee` computation anywhere in the LP mint path One-sided deposit of 2x tokenA costs less than 0.5% in slippage — should cost at least the swap fee (e.g., 3-5%) on the skewed portion A user can skew the pool ratio dramatically with a deposit, then withdraw balanced, capturing value from other LPs
  - **Origin:** [gdroz3r/drozer-lite — checklists/stableswap.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/stableswap.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-SS-4] Newton-Raphson Non-Convergence Returns Result Instead of Error**
  - **D:** The D or y computation uses a loop with a fixed iteration cap (e.g., 32, 256, 1000). On each iteration, it checks if `|current - previous| <= 1`. If the loop completes without converging, the function returns the last value instead of an error. In a correct implementation (Curve reference), non-convergence raises an error and the swap/deposit fails — only withdrawals remain functional, protecting LPs.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** 1. For every Newton-Raphson loop, check what happens after the loop ends WITHOUT convergence (i.e., the break condition was never met). 2. If the function returns `Some(last_value)` or `Ok(last_value)` after the loop, flag. It should return `None`, `Err(ConvergeError)`, or equivalent. 3. Check whether there are two D computation functions with different iteration caps (e.g., 32 for swaps, 256 for LP) — inconsistency flag per MATH-4. 4. Test with extremely imbalanced pools where convergence is slow — the function will return a wrong value instead of failing.
  - **Look for:** Loop `for _ in 0..N { ... if converged { break; } }` followed by `Some(d)` outside the loop — always returns even if not converged No `return` or early exit on convergence — the `break` exits the loop and falls through to a successful return Correct pattern: convergence should `return Some(d)` inside the loop; after the loop, return `None` or `Err` Curve reference: `raise` after the loop (Python); the function never returns normally without convergence
  - **Origin:** [gdroz3r/drozer-lite — checklists/stableswap.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/stableswap.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-SS-5] Static Amplification Parameter (No Ramping Mechanism)**
  - **D:** The amplification parameter is stored as a static field in the pool configuration (e.g., `PoolType::StableSwap { amp: u64 }`). No `update_amp`, `ramp_A`, or similar function exists to modify it post-creation. During normal conditions, the pool works fine. During a depegging event (one stablecoin loses its peg), a high A value keeps the price artificially stable, allowing holders of the depegged asset to swap at near-1:1 rates and drain the pool of the healthy asset.domain=defi-amm EVM=21 new=9 provenance=12

  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** 1. Check whether the amplification parameter can be modified after pool creation. Search for `ramp`, `update_amp`, `set_amp`, `modify_amp` in the execute message enum and handler. 2. If no modification mechanism exists, flag as MEDIUM — the pool cannot adapt to market conditions. 3. Check whether pool parameters are generally immutable post-creation (intentional design) or whether other parameters can be updated. 4. Assess the severity: if the DEX is designed for stablecoin pairs only, this is higher severity (depegging is the primary risk). If it supports volatile pairs via StableSwap (unusual), severity is lower.
  - **Look for:** `PoolType::StableSwap { amp: u64 }` — static field, no update path No `ExecuteMsg::RampAmp` or `ExecuteMsg::UpdatePoolParams` in the message enum Pool fees can be set at creation but amp cannot be adjusted — asymmetric mutability Documentation mentions "stable assets" or "pegged assets" but no depeg protection mechanism Contrast with Curve: `ramp_A(future_A, future_time)` with `MIN_RAMP_TIME` safety constraint
  - **Origin:** [gdroz3r/drozer-lite — checklists/stableswap.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/stableswap.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

## drozer-lite Provenance (deduplicated)

The source checks below are already represented by canonical checks in this domain. These provenance records do not add checklist items.

- `DROZER-DEX-1` **Slippage & Deadline Enforcement** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-DEX-2` **Route Integrity & Intermediate Token Safety** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-DEX-3` **Constant-Product / StableSwap Invariant Preservation** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-DEX-4` **TWAP Oracle Integrity** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-DEX-5` **Flash Swap Repayment Enforcement** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-DEX-6` **Token Approval Safety & Weird Tokens** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-DEX-9` **Asset Ordering Inconsistency Between Input and Internal State** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/dex.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-76` **Router Permissionless Entry Points** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-77` **Approval Persistence on Router** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-78` **Permit Frontrunning on Router** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-79` **Router Identity Confusion** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-80` **Router Token Residual / Sweep** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

## Auditmos/skills Provenance (deduplicated)

The source patterns below are already represented by canonical checks in this suite. These provenance records retain Auditmos coverage without adding duplicate checklist items.

- `AUDITMOS-CLM-1` **Forced Unfavorable Liquidity Deployment** -> existing canonical coverage in evm-audit-defi-amm; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-clm/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-CLM-2` **Owner Rug-Pull via TWAP Parameters** -> existing canonical coverage in evm-audit-defi-amm; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-clm/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-CLM-3` **Tokens Permanently Stuck** -> existing canonical coverage in evm-audit-defi-amm; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-clm/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-CLM-4` **Stale Token Approvals** -> existing canonical coverage in evm-audit-defi-amm; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-clm/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-CLM-5` **Retrospective Fee Application** -> existing canonical coverage in evm-audit-defi-amm; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-clm/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-SLIPPAGE-1` **No Slippage Parameter** -> existing canonical coverage in evm-audit-defi-amm; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-SLIPPAGE-2` **No Expiration Deadline** -> existing canonical coverage in evm-audit-defi-amm; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-SLIPPAGE-4` **Mismatched Slippage Precision** -> existing canonical coverage in evm-audit-defi-amm; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-SLIPPAGE-5` **Hard-coded Slippage Freezes Funds** -> existing canonical coverage in evm-audit-defi-amm; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-SLIPPAGE-6` **MinTokensOut For Intermediate Amount** -> existing canonical coverage in evm-audit-defi-amm; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-SLIPPAGE-7` **On-Chain Slippage Calculation** -> existing canonical coverage in evm-audit-defi-amm; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-SLIPPAGE-8` **Fixed Fee Tier Assumption** -> existing canonical coverage in evm-audit-defi-amm; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-SLIPPAGE-9` **Block.timestamp Deadline** -> existing canonical coverage in evm-audit-defi-amm; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-SLIPPAGE-11` **No slippage on liquidity ops** -> updated canonical liquidity-operation minimum-output check; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/SKILL.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-SLIPPAGE-13` **Approval race on router upgrade** -> existing stale router approval check; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-slippage/SKILL.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
