<!-- GENERATED FILE: source is ../../data/canonical-checks.json; do not edit by hand. -->
# Precision & Math Security Checklist

Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.

## Division Before Multiplication

- [ ] **[EVM-MATH-001] Division-before-multiplication may cause precision loss** _(semantic; high)_: Division before multiplication can lose economically meaningful precision, but multiplying first is safe only when the product cannot overflow or a full-precision mulDiv is used.
  - **Trigger:** A division result is later multiplied and the operands are attacker-controlled or economically material.
  - **Risk:** Premature truncation can change accounting or economic outcomes; an overflow-aware rewrite is required.
  - **Detection:** Inspect expression trees and helper calls for division-before-multiplication ordering. If rewriting as (a * c) / b, prove a*c cannot overflow or use full-precision mulDiv(a, c, b).
  - **FP:** The truncation is proven bounded and economically harmless. The product is proven in range or a full-precision mulDiv implementation is used.
  - **Proof:** Construct a boundary input where the intended exact result differs from the implementation and quantify the value delta; separately check the multiplication range.
  - **Provenance:** Dacian, ERC4626 primer pattern #35; [Solidity Language Reference](https://docs.soliditylang.org/en/latest/types.html#integers)

- [ ] **[EVM-MATH-002] Hidden division-before-multiplication in library calls** _(exploit-pattern; medium)_: Expand function calls to reveal hidden ordering. Example: `utilRate.wmul(slope1).wdiv(optimalUsageRate)` expands to `utilRate * (slope1 / 1e18) * (1e18 / optimalUsageRate)` — division before multiplication. Fix: `utilRate * slope1 / optimalUsageRate`. Look for: chained `mulDiv`, `wmul`, or `wdiv` calls where division happens before a later multiplication. [Dacian, ERC4626 primer, Yield VR Audit]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Dacian, ERC4626 primer, Yield VR Audit

- [ ] **[EVM-MATH-003] Extra divisions by scaling factor** _(exploit-pattern; medium)_: A common copy-paste bug is dividing by 1e18 twice instead of once. Example: `(amountToBuyLeftUSD * 1e18 / collateralval) / 1e18) / 1e18` — the last `/1e18` destroys 18 digits of precision. Look for: sequential divisions by the same constant. [ERC4626 primer USSD example]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 primer USSD example

- [ ] **[EVM-MATH-004] Division resulting in zero for small values** _(semantic; high)_: When `amount < divisor`, Solidity integer division returns 0. Example: `(amount * rewardRate) / totalSupply` returns 0 when `amount * rewardRate < totalSupply`. Look for: intermediate values that could be < the denominator. [Dacian]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Dacian

## Rounding Direction

- [ ] **[EVM-MATH-005] Protocol-favoring rounding rule** _(exploit-pattern; medium)_: Deposits/mints should round DOWN (give fewer shares), withdrawals/redeems should round DOWN in assets or UP in shares, and protocol fees should not round in the user's favor. Any deviation lets users extract rounding dust or leaks value on repeated trades. Look for: `mulDiv` or division calls without an explicit rounding direction in vault, fee, or AMM math. [ERC4626 checklist, beirao M-06, Dacian — Precision Loss Errors, Cyfrin SudoSwap Audit]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist, beirao M-06, Dacian — Precision Loss Errors, Cyfrin SudoSwap Audit

- [ ] **[EVM-MATH-006] Inconsistent rounding across functions** _(exploit-pattern; medium)_: If `deposit()` rounds one way and `withdraw()` rounds the same way, an attacker can loop deposits/withdrawals to extract dust each cycle. Look for: both deposit and withdraw using `Math.mulDiv` with the same rounding mode. [ERC4626 checklist M1]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist M1

- [ ] **[EVM-MATH-007] Forward/inverse fee transformation must solve the requested variable** _(semantic; high)_: Fee transformations must distinguish gross assets paid, net assets received, and requested shares. For a fee rate f, netAssets = grossAssets * (1 - f); solving for grossAssets requires division by (1 - f). With pricePerShare p, shares = grossAssets * (1 - f) / p, while grossAssets = shares * p / (1 - f).
  - **Trigger:** A fee-adjusted conversion accepts gross assets, net assets, or requested shares and applies a rate before or after the share-price conversion.
  - **Risk:** Using the inverse for the wrong input variable can overcharge, undercharge, or break deposit/withdraw accounting and round-trip invariants.
  - **Detection:** Name the variable represented by every input and output, derive the forward and inverse equations, and compare both paths under the implementation's rounding policy.
  - **FP:** The implementation documents whether the fee is assessed on gross or net assets, and its direction-specific rounding is consistent with the solved variable.
  - **Proof:** Use exact rational arithmetic plus boundary integer cases to show that forward then inverse conversion differs only by the documented rounding bound.
  - **Provenance:** ERC4626 checklist M5; [EIP-4626 Tokenized Vaults](https://eips.ethereum.org/EIPS/eip-4626); [OpenZeppelin ERC4626 implementation guide](https://docs.openzeppelin.com/contracts/5.x/erc4626)
  - **Related:** EVM-ERC4626-043

## Integer Overflow/Underflow (Even with Solidity ≥0.8)

- [ ] **[EVM-MATH-008] Overflow in `unchecked` blocks** _(exploit-pattern; medium)_: Code in `unchecked { }` has no overflow protection. A value wrapping from `type(uint256).max` to 0 or vice versa in unchecked code is a critical bug. Look for: every `unchecked` block, especially those with user-influenced values, without a proof that the range is safe. [beirao M-10, Tamjid C44]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao M-10, Tamjid C44

- [ ] **[EVM-MATH-009] Downcast overflow** _(exploit-pattern; medium)_: Casting `uint256` to `uint128`, `uint64`, `uint32`, etc. silently truncates and can invalidate an invariant checked before the cast. Look for: any explicit or implicit downcast, especially `uint32`, `uint64`, or `uint128`; use `SafeCast`. [ERC4626 primer pattern #20, Dacian — Precision Loss Errors, Balancer Bug Bounty]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 primer pattern #20, Dacian — Precision Loss Errors, Balancer Bug Bounty

- [ ] **[EVM-TYPE-001] Signed-to-unsigned explicit conversion preserves the bit pattern** _(semantic; high)_: For same-width integer conversions, uint(signedValue) preserves the two's-complement bit pattern and can turn a negative value into a very large unsigned integer. Checked arithmetic does not make the explicit conversion itself revert.
  - **Trigger:** A signed value reaches an explicit unsigned conversion, especially after oracle, PnL, or accounting calculations.
  - **Risk:** A negative oracle delta, PnL, or accounting value can become a huge unsigned amount when converted without a non-negative guard.
  - **Detection:** Find uint256(signedValue), uint128(signedValue), and equivalent explicit conversions. Trace signed values derived from oracle deltas, PnL, or accounting and check signedValue >= 0 before conversion.
  - **FP:** The signed value is proven non-negative on every reachable path before conversion. An explicit range check or SafeCast-style helper rejects out-of-range values.
  - **Proof:** Exercise a reachable negative input such as int256(-3) and show the converted value or the invariant that prevents it.
  - **Provenance:** ERC4626 primer pattern #66, beirao M-09; beirao M-09; [Solidity Language Reference](https://docs.soliditylang.org/en/latest/types.html#explicit-conversions)

- [ ] **[EVM-MATH-011] Signed-unsigned addition/subtraction overflow** _(exploit-pattern; medium)_: `int256 x + uint256 y` — if `y > type(int256).max`, this overflows. Look for: mixed signed/unsigned arithmetic. [ERC4626 primer pattern #55]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 primer pattern #55

- [ ] **[EVM-MATH-012] Overflow in time-based calculations** _(exploit-pattern; medium)_: `block.timestamp * rate` or `(endTime - startTime) * emissionRate` can overflow for large time differences or rates, especially with `int40`/`int64` types. Look for: time arithmetic with narrow types. [ERC4626 primer pattern #72]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 primer pattern #72

## Decimal Handling

- [ ] **[EVM-MATH-013] Oracle decimal mismatch** _(exploit-pattern; medium)_: Code assuming 8-decimal Chainlink feeds breaks with 6-decimal or 18-decimal feeds. Example: `price * 10**(18 - feed.decimals())` — correct for 8 decimals, wrong for 6 or 18. Look for: hardcoded decimal adjustments without querying `decimals()`. [ERC4626 primer pattern #26]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 primer pattern #26

- [ ] **[EVM-MATH-014] Token decimal mismatch in price calculations** _(exploit-pattern; medium)_: When computing value of `tokenA` in terms of `tokenB`, both token decimals AND oracle decimals must be normalized. A 6-decimal token priced by an 8-decimal oracle requires different scaling than an 18-decimal token. Look for: price calculations that don't normalize for both token and oracle decimals. [beirao V-04, Decurity CDP]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao V-04, Decurity CDP

- [ ] **[EVM-MATH-015] Decimal scaling for vault with non-18 decimal assets** _(exploit-pattern; medium)_: ERC4626 vaults with 6-decimal underlying tokens (USDC) need careful decimal scaling between shares (usually 18) and assets (6). Look for: hardcoded `1e18` in vault math when the underlying isn't 18 decimals. [ERC4626 checklist M6]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist M6

- [ ] **[EVM-MATH-016] Zero/one remaining after division** _(exploit-pattern; medium)_: After fee deduction or precision scaling, a value of 1 wei may remain in the system. Over many operations, these round-to-1 remainders accumulate. Look for: fee calculations where `amount * fee / FEE_DENOMINATOR` always leaves ≥1 wei. [beirao V-06]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao V-06

## Accumulator & Interest Math

- [ ] **[EVM-MATH-017] Compounding when claiming simple interest** _(exploit-pattern; medium)_: If the interest accrual formula assumes simple interest but rewards/interest is claimed and re-deposited by users, the effective rate is higher than intended. Look for: interest rate formulas that don't account for compounding frequency. [ERC4626 primer]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 primer

- [ ] **[EVM-MATH-018] Reward per token precision loss** _(exploit-pattern; medium)_: In staking reward contracts, `rewardPerToken = rewardRate * duration / totalStaked`. If `totalStaked` is very large relative to `rewardRate * duration`, this rounds to 0 and rewards are permanently lost. Look for: reward distribution math where the numerator can be smaller than the denominator. [Dacian]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Dacian

- [ ] **[EVM-MATH-019] Missing state update before reward claim** _(exploit-pattern; medium)_: If `_updateIntegrals()` isn't called before `_fetchRewards()`, all rewards accrued since the last update are lost. The fetch updates `lastUpdate` without capturing pending rewards. Look for: reward claim functions that don't update global state first. [ERC4626 primer pattern #17]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 primer pattern #17

- [ ] **[EVM-MATH-020] Fee shares minted after reward distribution** _(exploit-pattern; medium)_: If fee shares are minted AFTER rewards are distributed, the fee captures a portion of the rewards meant for existing holders. Must mint fee shares BEFORE distributing rewards. Look for: ordering of fee minting vs reward distribution. [ERC4626 primer pattern #9]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 primer pattern #9

## Special Values

- [ ] **[EVM-MATH-021] Division by zero returns 0 in assembly** _(semantic; high)_: In Yul/inline assembly, `div(x, 0)` returns 0 instead of reverting. Look for: assembly division without prior zero-check on denominator. [beirao M-12]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao M-12

- [ ] **[EVM-MATH-022] `type(uint256).max` as sentinel value** _(exploit-pattern; medium)_: Using max-uint as "no limit" can cause overflow when added to anything. Look for: `type(uint256).max` used in calculations (not just comparisons). [weird-erc20]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** weird-erc20

- [ ] **[EVM-MATH-023] Extreme weight ratios cause overflow** _(exploit-pattern; medium)_: In weighted pool math, `balance * (ratio ^ (1/weight))` overflows when weight is very small (e.g., 1.166%). Example: `7500e21 * (3.0 ^ 85.76) = OVERFLOW`. Look for: exponential calculations where the exponent can be very large. [ERC4626 primer pattern #73]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 primer pattern #73

## Precision Loss Patterns (Expanded from Beirao/Tamjid)

- [ ] **[EVM-TIME-001] Time-unit arithmetic inherits operand and destination type** _(semantic; high)_: Solidity time-unit suffixes such as days, hours, and minutes produce number literal expressions. Their eventual type and range come from the non-literal operand or destination, so the risk is in narrowing, explicit casts, storage packing, or the target type of the result.
  - **Trigger:** Time-unit arithmetic is assigned to or explicitly converted to a narrow integer type.
  - **Risk:** A narrow destination or explicit conversion can truncate a time calculation; the literal itself is not a uint24 value.
  - **Detection:** Trace non-literal operands and the destination type of expressions using days, hours, or minutes. Inspect explicit casts, packed storage, and products such as uint32(365 days * years).
  - **FP:** The destination range is proven sufficient and no narrowing conversion or packed-storage truncation occurs.
  - **Proof:** Use a boundary duration that exceeds the destination range and demonstrate the resulting truncation or revert on the reachable path.
  - **Provenance:** beirao M-04; [Solidity Language Reference](https://docs.soliditylang.org/en/latest/units-and-global-variables.html#time-units)

- [ ] **[EVM-MATH-025] Off-by-one in comparison operators** _(exploit-pattern; medium)_: `>` vs `>=`, `<` vs `<=` can mean the difference between allowing/blocking an action at the exact boundary. In liquidation: `healthFactor < 1.0` vs `healthFactor <= 1.0` determines if exactly-at-threshold positions are liquidatable. Look for: boundary conditions in health checks, auction timing, and threshold comparisons. [beirao M-11, Tamjid C22, C23]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao M-11, Tamjid C22, C23

- [ ] **[EVM-MATH-026] Precision loss compounds across multiple operations** _(exploit-pattern; medium)_: A single division losing 1 wei is negligible. But if that result feeds into another division, and another, precision loss compounds exponentially. Look for: chains of divisions in multi-step calculations (e.g., reward distribution formulas with multiple intermediary divisions). [Tamjid C47]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Tamjid C47
  - **Notes:** ---

## Dacian — Precision Loss Errors (Phase 3)

- [ ] **[EVM-MATH-027] Rounding down to zero allows state changes without proper accounting** _(exploit-pattern; medium)_: If `decollateralized = loanCollateral * repaid / loanAmount` rounds to 0 for small repayments, the loan amount decreases but collateral stays unchanged. Repeated small repayments drain the loan while keeping all collateral. Fix: revert if decollateralized == 0. [Source: Dacian — Precision Loss Errors, Sherlock Cooler]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — Precision Loss Errors, Sherlock Cooler

- [ ] **[EVM-MATH-028] ~50% value understatement from mixing precisions without scaling** _(exploit-pattern; medium)_: Adding `primaryBalance` (18 decimals) + `secondaryAmountInPrimary` (6 decimals) without first scaling the secondary token to primary precision causes a ~50% undervaluation of LP positions. [Source: Dacian — Precision Loss Errors, Sherlock Notional]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — Precision Loss Errors, Sherlock Notional

- [ ] **[EVM-MATH-029] Excessive precision scaling — double-scaling already-scaled values** _(exploit-pattern; medium)_: When module A scales a token amount to 18 decimals, then passes it to module B which scales it again, the result is inflated by the scaling factor. Trace token amounts through the entire call path to verify they aren't re-scaled. [Source: Dacian — Precision Loss Errors, Sherlock Notional]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — Precision Loss Errors, Sherlock Notional

- [ ] **[EVM-MATH-030] Mismatched precision scaling — decimals vs hardcoded 1e18** _(exploit-pattern; medium)_: If module A uses `token.decimals()` for precision and module B hardcodes `1e18`, tokens with non-18 decimals will have incorrect valuations when flowing between modules. [Source: Dacian — Precision Loss Errors, Code4rena Sublime/Yearn]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Source: Dacian — Precision Loss Errors, Code4rena Sublime/Yearn

## Supplemental Attack Vectors (SAS-AV)

- [ ] **[EVM-MATH-031] Batch Distribution Dust Residual** _(exploit-pattern; medium)_: Loop distributes funds proportionally: `share = total * weight[i] / totalWeight`. Cumulative rounding causes `sum(shares) < total`, leaving dust locked in contract. Pattern: N recipients each computed independently without remainder handling.
  - **FP:** Last recipient gets `total - sumOfPrevious`. Dust swept to treasury. `mulDiv` with accumulator tracking. Protocol accepts bounded dust loss by design.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-004](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-35

- [ ] **[EVM-MATH-032] Time Unit Confusion in Interest Calculations** _(exploit-pattern; medium)_: Interest accrual logic confuses time units — using `block.timestamp` (seconds) in a formula expecting days or blocks, or vice versa. Results in interest rates off by orders of magnitude (e.g., 365x too high or 86400x too low).
  - **FP:** Documented time unit constants (`SECONDS_PER_YEAR = 365.25 days`). Unit tests with known interest calculations. Consistent use of `block.timestamp` (seconds) throughout.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-019](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-188

- [ ] **[EVM-MATH-033] Capacity Competition Between Accounting Variables** _(exploit-pattern; medium)_: Multiple accounting variables (user shares, fee shares, rewards) share a common cap. One can fill the cap, making another permanently unfulfillable. Pattern: `maxDeposit = supplyCap - totalSupply` ignores pending fee shares — deposits fill cap, fees can never mint.
  - **FP:** `maxDeposit` accounts for all future obligations. Fee shares minted eagerly. Separate caps for user/protocol shares.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-027](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-304

## drozer-lite Additions

- [ ] **[EVM-MATH-034] Multi-Step Normalization Ordering** _(exploit-pattern; medium)_: Non-commutative adjustments (normalize, halve, round, scale) are applied in different orders across branches of the same function.
  - **Trigger:** Non-commutative adjustments (normalize, halve, round, scale) are applied in different orders across branches of the same function. Large-value branch: halve-then-adjust; small-value branch: adjust-then-halve Pre-halving modification that should have been post-halving
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Proof:** For each multi-step adjustment sequence, list the steps in order for every branch. For each adjacent pair (A, B), ask whether swapping changes the result. If yes, verify the order is consistent across all branches.
  - **Provenance:** [DROZER-MATH-3](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/math.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/math.md); gdroz3r/drozer-lite — checklists/math.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/math.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/math.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-MATH-035] Format / Precision Selection Consistency** _(exploit-pattern; medium)_: A library supports multiple formats (small/large, compressed/full) but the format selector differs across paths — encoding uses more criteria than arithmetic output, for example, so values that qualify for the large format via encoding are downcast by arithmetic.
  - **Trigger:** A library supports multiple formats (small/large, compressed/full) but the format selector differs across paths — encoding uses more criteria than arithmetic output, for example, so values that qualify for the large format via encoding are downcast by arithmetic. Encoding uses [digit count, exponent]; arithmetic output uses [exponent] only Boundary values where decode loses information
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Proof:** Build a FORMAT SELECTION RULE TABLE per path. Verify all rows are identical. Construct boundary values that expose the asymmetry and trace them through each path. Verify `encode(decode(encode(x))) == encode(x)`.
  - **Provenance:** [DROZER-MATH-4](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/math.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/math.md); digit count, exponent; gdroz3r/drozer-lite — checklists/math.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/math.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/math.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-MATH-036] Representation Gap Integrity** _(exploit-pattern; medium)_: Values "in the gap" between small and large representations are silently truncated beyond stated tolerance; the loss compounds when two gap values are multiplied.
  - **Trigger:** Values "in the gap" between small and large representations are silently truncated beyond stated tolerance; the loss compounds when two gap values are multiplied. Selector checks exponent only, precision depends on digit count No explicit tolerance specification in code or spec Gap-value multiplication in a hot path
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Proof:** Identify the gap range from the format selector's criteria. Measure precision loss for values in the gap. Verify it stays within any stated tolerance (e.g., "1 ULP accuracy"). Test that `gap_value * gap_value` does not exceed acceptable error.
  - **Provenance:** [DROZER-MATH-5](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/math.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/math.md); gdroz3r/drozer-lite — checklists/math.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/math.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/math.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
