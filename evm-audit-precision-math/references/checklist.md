# Precision & Math Security Checklist

## Division Before Multiplication

- [ ] **Division-before-multiplication may cause precision loss**: `(a / b) * c` loses precision from the division. Must be `(a * c) / b`. This is the single most common precision bug in DeFi. Look for: any expression where a division appears to the left of a multiplication. [Dacian, ERC4626 primer pattern #35]

- [ ] **Hidden division-before-multiplication in library calls**: Expand function calls to reveal hidden ordering. Example: `utilRate.wmul(slope1).wdiv(optimalUsageRate)` expands to `utilRate * (slope1 / 1e18) * (1e18 / optimalUsageRate)` — division before multiplication. Fix: `utilRate * slope1 / optimalUsageRate`. Look for: chained `mulDiv`, `wmul`, or `wdiv` calls where division happens before a later multiplication. [Dacian, ERC4626 primer, Yield VR Audit]

- [ ] **Extra divisions by scaling factor**: A common copy-paste bug is dividing by 1e18 twice instead of once. Example: `(amountToBuyLeftUSD * 1e18 / collateralval) / 1e18) / 1e18` — the last `/1e18` destroys 18 digits of precision. Look for: sequential divisions by the same constant. [ERC4626 primer USSD example]

- [ ] **Division resulting in zero for small values**: When `amount < divisor`, Solidity integer division returns 0. Example: `(amount * rewardRate) / totalSupply` returns 0 when `amount * rewardRate < totalSupply`. Look for: intermediate values that could be < the denominator. [Dacian]

## Rounding Direction

- [ ] **Protocol-favoring rounding rule**: Deposits/mints should round DOWN (give fewer shares), withdrawals/redeems should round DOWN in assets or UP in shares, and protocol fees should not round in the user's favor. Any deviation lets users extract rounding dust or leaks value on repeated trades. Look for: `mulDiv` or division calls without an explicit rounding direction in vault, fee, or AMM math. [ERC4626 checklist, beirao M-06, Dacian — Precision Loss Errors, Cyfrin SudoSwap Audit]

- [ ] **Inconsistent rounding across functions**: If `deposit()` rounds one way and `withdraw()` rounds the same way, an attacker can loop deposits/withdrawals to extract dust each cycle. Look for: both deposit and withdraw using `Math.mulDiv` with the same rounding mode. [ERC4626 checklist M1]

- [ ] **Inverse fee calculation error**: When converting between assets and shares with fees: `shares = assets / (1 - fee)` NOT `shares = assets * (1 - fee)`. The latter under-charges. Look for: fee-adjusted conversion formulas. [ERC4626 checklist M5]

## Integer Overflow/Underflow (Even with Solidity ≥0.8)

- [ ] **Overflow in `unchecked` blocks**: Code in `unchecked { }` has no overflow protection. A value wrapping from `type(uint256).max` to 0 or vice versa in unchecked code is a critical bug. Look for: every `unchecked` block, especially those with user-influenced values, without a proof that the range is safe. [beirao M-10, Tamjid C44]

- [ ] **Downcast overflow**: Casting `uint256` to `uint128`, `uint64`, `uint32`, etc. silently truncates and can invalidate an invariant checked before the cast. Look for: any explicit or implicit downcast, especially `uint32`, `uint64`, or `uint128`; use `SafeCast`. [ERC4626 primer pattern #20, Dacian — Precision Loss Errors, Balancer Bug Bounty]

- [ ] **Negative-to-unsigned cast**: `uint256(negativeInt256)` creates a massive positive number in unchecked context or reverts in checked context. When taking an absolute value, use `uint256(-negativeValue)` with an appropriate minimum-value guard. Look for: `uint256(signedVariable)` or `uint128(signedVariable)`. [ERC4626 primer pattern #66, beirao M-09]

- [ ] **Signed-unsigned addition/subtraction overflow**: `int256 x + uint256 y` — if `y > type(int256).max`, this overflows. Look for: mixed signed/unsigned arithmetic. [ERC4626 primer pattern #55]

- [ ] **Overflow in time-based calculations**: `block.timestamp * rate` or `(endTime - startTime) * emissionRate` can overflow for large time differences or rates, especially with `int40`/`int64` types. Look for: time arithmetic with narrow types. [ERC4626 primer pattern #72]

## Decimal Handling

- [ ] **Oracle decimal mismatch**: Code assuming 8-decimal Chainlink feeds breaks with 6-decimal or 18-decimal feeds. Example: `price * 10**(18 - feed.decimals())` — correct for 8 decimals, wrong for 6 or 18. Look for: hardcoded decimal adjustments without querying `decimals()`. [ERC4626 primer pattern #26]

- [ ] **Token decimal mismatch in price calculations**: When computing value of `tokenA` in terms of `tokenB`, both token decimals AND oracle decimals must be normalized. A 6-decimal token priced by an 8-decimal oracle requires different scaling than an 18-decimal token. Look for: price calculations that don't normalize for both token and oracle decimals. [beirao V-04, Decurity CDP]

- [ ] **Decimal scaling for vault with non-18 decimal assets**: ERC4626 vaults with 6-decimal underlying tokens (USDC) need careful decimal scaling between shares (usually 18) and assets (6). Look for: hardcoded `1e18` in vault math when the underlying isn't 18 decimals. [ERC4626 checklist M6]

- [ ] **Zero/one remaining after division**: After fee deduction or precision scaling, a value of 1 wei may remain in the system. Over many operations, these round-to-1 remainders accumulate. Look for: fee calculations where `amount * fee / FEE_DENOMINATOR` always leaves ≥1 wei. [beirao V-06]

## Accumulator & Interest Math

- [ ] **Compounding when claiming simple interest**: If the interest accrual formula assumes simple interest but rewards/interest is claimed and re-deposited by users, the effective rate is higher than intended. Look for: interest rate formulas that don't account for compounding frequency. [ERC4626 primer]

- [ ] **Reward per token precision loss**: In staking reward contracts, `rewardPerToken = rewardRate * duration / totalStaked`. If `totalStaked` is very large relative to `rewardRate * duration`, this rounds to 0 and rewards are permanently lost. Look for: reward distribution math where the numerator can be smaller than the denominator. [Dacian]

- [ ] **Missing state update before reward claim**: If `_updateIntegrals()` isn't called before `_fetchRewards()`, all rewards accrued since the last update are lost. The fetch updates `lastUpdate` without capturing pending rewards. Look for: reward claim functions that don't update global state first. [ERC4626 primer pattern #17]

- [ ] **Fee shares minted after reward distribution**: If fee shares are minted AFTER rewards are distributed, the fee captures a portion of the rewards meant for existing holders. Must mint fee shares BEFORE distributing rewards. Look for: ordering of fee minting vs reward distribution. [ERC4626 primer pattern #9]

## Special Values

- [ ] **Division by zero returns 0 in assembly**: In Yul/inline assembly, `div(x, 0)` returns 0 instead of reverting. Look for: assembly division without prior zero-check on denominator. [beirao M-12]

- [ ] **`type(uint256).max` as sentinel value**: Using max-uint as "no limit" can cause overflow when added to anything. Look for: `type(uint256).max` used in calculations (not just comparisons). [weird-erc20]

- [ ] **Extreme weight ratios cause overflow**: In weighted pool math, `balance * (ratio ^ (1/weight))` overflows when weight is very small (e.g., 1.166%). Example: `7500e21 * (3.0 ^ 85.76) = OVERFLOW`. Look for: exponential calculations where the exponent can be very large. [ERC4626 primer pattern #73]

## Precision Loss Patterns (Expanded from Beirao/Tamjid)

- [ ] **Solidity time literals are uint24**: Expressions like `1 days`, `1 hours` are `uint24`. Operations involving these literals cast the result to `uint24`, which can overflow for large time calculations. `1 days * largeNumber` may silently truncate. Look for: arithmetic with Solidity time literals and large multipliers. [beirao M-04]

- [ ] **Off-by-one in comparison operators**: `>` vs `>=`, `<` vs `<=` can mean the difference between allowing/blocking an action at the exact boundary. In liquidation: `healthFactor < 1.0` vs `healthFactor <= 1.0` determines if exactly-at-threshold positions are liquidatable. Look for: boundary conditions in health checks, auction timing, and threshold comparisons. [beirao M-11, Tamjid C22, C23]

- [ ] **Precision loss compounds across multiple operations**: A single division losing 1 wei is negligible. But if that result feeds into another division, and another, precision loss compounds exponentially. Look for: chains of divisions in multi-step calculations (e.g., reward distribution formulas with multiple intermediary divisions). [Tamjid C47]

---

## Dacian — Precision Loss Errors (Phase 3)

- [ ] **Rounding down to zero allows state changes without proper accounting**: If `decollateralized = loanCollateral * repaid / loanAmount` rounds to 0 for small repayments, the loan amount decreases but collateral stays unchanged. Repeated small repayments drain the loan while keeping all collateral. Fix: revert if decollateralized == 0. [Source: Dacian — Precision Loss Errors, Sherlock Cooler]

- [ ] **~50% value understatement from mixing precisions without scaling**: Adding `primaryBalance` (18 decimals) + `secondaryAmountInPrimary` (6 decimals) without first scaling the secondary token to primary precision causes a ~50% undervaluation of LP positions. [Source: Dacian — Precision Loss Errors, Sherlock Notional]

- [ ] **Excessive precision scaling — double-scaling already-scaled values**: When module A scales a token amount to 18 decimals, then passes it to module B which scales it again, the result is inflated by the scaling factor. Trace token amounts through the entire call path to verify they aren't re-scaled. [Source: Dacian — Precision Loss Errors, Sherlock Notional]

- [ ] **Mismatched precision scaling — decimals vs hardcoded 1e18**: If module A uses `token.decimals()` for precision and module B hardcodes `1e18`, tokens with non-18 decimals will have incorrect valuations when flowing between modules. [Source: Dacian — Precision Loss Errors, Code4rena Sublime/Yearn]

## Supplemental Attack Vectors (SAS-AV)

These vectors are merged from sanbir/solidity-auditor-skills; each item retains a detection condition (D), false-positive gate (FP), and source provenance.

- [ ] **[SAS-AV-004] Batch Distribution Dust Residual**
  - **D:** Loop distributes funds proportionally: `share = total * weight[i] / totalWeight`. Cumulative rounding causes `sum(shares) < total`, leaving dust locked in contract. Pattern: N recipients each computed independently without remainder handling.
  - **FP:** Last recipient gets `total - sumOfPrevious`. Dust swept to treasury. `mulDiv` with accumulator tracking. Protocol accepts bounded dust loss by design.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-35

- [ ] **[SAS-AV-019] Time Unit Confusion in Interest Calculations**
  - **D:** Interest accrual logic confuses time units — using `block.timestamp` (seconds) in a formula expecting days or blocks, or vice versa. Results in interest rates off by orders of magnitude (e.g., 365x too high or 86400x too low).
  - **FP:** Documented time unit constants (`SECONDS_PER_YEAR = 365.25 days`). Unit tests with known interest calculations. Consistent use of `block.timestamp` (seconds) throughout.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-188

- [ ] **[SAS-AV-027] Capacity Competition Between Accounting Variables**
  - **D:** Multiple accounting variables (user shares, fee shares, rewards) share a common cap. One can fill the cap, making another permanently unfulfillable. Pattern: `maxDeposit = supplyCap - totalSupply` ignores pending fee shares — deposits fill cap, fees can never mint.
  - **FP:** `maxDeposit` accounts for all future obligations. Fee shares minted eagerly. Separate caps for user/protocol shares.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-304

## drozer-lite Additions

The checks below are the canonical runtime additions from the EVM-relevant drozer-lite profiles. Each item retains the source profile and pinned commit.

- [ ] **[DROZER-MATH-3] Multi-Step Normalization Ordering**
  - **D:** Non-commutative adjustments (normalize, halve, round, scale) are applied in different orders across branches of the same function.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** For each multi-step adjustment sequence, list the steps in order for every branch. For each adjacent pair (A, B), ask whether swapping changes the result. If yes, verify the order is consistent across all branches.
  - **Look for:** Large-value branch: halve-then-adjust; small-value branch: adjust-then-halve Pre-halving modification that should have been post-halving
  - **Origin:** [gdroz3r/drozer-lite — checklists/math.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/math.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-MATH-4] Format / Precision Selection Consistency**
  - **D:** A library supports multiple formats (small/large, compressed/full) but the format selector differs across paths — encoding uses more criteria than arithmetic output, for example, so values that qualify for the large format via encoding are downcast by arithmetic.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** Build a FORMAT SELECTION RULE TABLE per path. Verify all rows are identical. Construct boundary values that expose the asymmetry and trace them through each path. Verify `encode(decode(encode(x))) == encode(x)`.
  - **Look for:** Encoding uses [digit count, exponent]; arithmetic output uses [exponent] only Boundary values where decode loses information
  - **Origin:** [gdroz3r/drozer-lite — checklists/math.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/math.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-MATH-5] Representation Gap Integrity**
  - **D:** Values "in the gap" between small and large representations are silently truncated beyond stated tolerance; the loss compounds when two gap values are multiplied.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** Identify the gap range from the format selector's criteria. Measure precision loss for values in the gap. Verify it stays within any stated tolerance (e.g., "1 ULP accuracy"). Test that `gap_value * gap_value` does not exceed acceptable error.
  - **Look for:** Selector checks exponent only, precision depends on digit count No explicit tolerance specification in code or spec Gap-value multiplication in a hot path
  - **Origin:** [gdroz3r/drozer-lite — checklists/math.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/math.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
