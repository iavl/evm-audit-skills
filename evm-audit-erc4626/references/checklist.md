# ERC4626 Vault Security Checklist

## First Depositor / Inflation Attack

- [ ] **Classic inflation attack**: Attacker deposits 1 wei → gets 1 share → donates large amount directly to vault → subsequent depositors get 0 shares due to rounding. Mitigate: virtual shares/assets (OpenZeppelin), minimum deposit, initial protocol deposit, dead shares (Uniswap V2 style). Look for: empty vaults where first deposit can be 1 wei. [ERC4626 checklist SP4, ERC4626 primer #3]

- [ ] **Inconsistent deposit/mint on first deposit**: Some vaults use different formulas for `previewDeposit` vs `previewMint` when supply=0. Astaria's ERC4626Cloned used `assets` for deposit but `10e18` for mint. Look for: different code paths in deposit vs mint when `totalSupply == 0`. [ERC4626 primer #3]

- [ ] **Virtual shares must equal virtual assets**: If virtual shares ≠ virtual assets, market rounding exploitation causes share deflation. Look for: ERC4626 implementations with asymmetric virtual offset values. [ERC4626 primer #5]

## Rounding Direction (EIP-4626 Compliance)

- [ ] **`convertToAssets` & `convertToShares` must round DOWN**: These are informational — always favor the vault. [ERC4626 checklist SC12]
- [ ] **`previewDeposit` must round DOWN** (give fewer shares): [ERC4626 checklist SC26]
- [ ] **`previewMint` must round UP** (require more assets): [ERC4626 checklist SC27]
- [ ] **`previewWithdraw` must round UP** (burn more shares): [ERC4626 checklist SC40]
- [ ] **`previewRedeem` must round DOWN** (give fewer assets): [ERC4626 checklist SC41]
- [ ] **All rounding must favor the vault**: If any preview function rounds in the user's favor, dust extraction via deposit/withdraw cycling is possible. Look for: `Math.mulDiv` calls with wrong rounding mode. [ERC4626 checklist M1]

## Compliance Requirements

- [ ] **`totalAssets` must include compounding yield AND external fees**: Not just deposited amount. [ERC4626 checklist SC5, SC6]
- [ ] **`totalAssets` must never revert**: [ERC4626 checklist SC7]
- [ ] **`convertToAssets`/`convertToShares` must never vary by caller**: These are global, not per-user. [ERC4626 checklist SC9]
- [ ] **`convertToAssets`/`convertToShares` must NOT include slippage or vault fees**: These are idealized math. [ERC4626 checklist SC10]
- [ ] **`maxDeposit`/`maxMint` must NOT rely on `balanceOf(asset)`**: Per spec, these represent protocol capacity, not token balance. [ERC4626 checklist SC17]
- [ ] **`maxDeposit`/`maxMint` return 0 when deposits disabled, `type(uint256).max` when no limit**: [ERC4626 checklist SC15, SC16]
- [ ] **`maxDeposit`/`maxMint`/`maxWithdraw`/`maxRedeem` must NEVER revert**: Return 0 instead. [ERC4626 checklist SC18, SC39]
- [ ] **`preview*` functions must include vault fees AND slippage/chain conditions**: Unlike `convertTo*`. [ERC4626 checklist SC23, SC25, SC47, SC48]
- [ ] **`preview*` functions must NEVER revert**: Except for integer overflow. [ERC4626 checklist SC24, SC49]
- [ ] **`deposit` must revert if exceeds `maxDeposit`**: [ERC4626 checklist SC32]
- [ ] **`deposit` must pull EXACTLY `assets` tokens**: [ERC4626 checklist SC28]
- [ ] **`mint` must mint EXACTLY `shares` shares**: [ERC4626 checklist SC29]
- [ ] **`withdraw`/`redeem` must support third-party operation with approval**: [ERC4626 checklist SC56]
- [ ] **Events: `Deposit` and `Withdraw` must always be emitted**: [ERC4626 checklist SC35, SC57]

## Share Price Manipulation

- [ ] **Direct token transfer inflates share price**: If vault uses `balanceOf(address(this))` for `totalAssets`, direct transfers manipulate conversion rate. Must track assets internally with deposit/withdraw accounting. Look for: `totalAssets()` implementations using raw `balanceOf`. [ERC4626 checklist SP3, beirao V-02]

- [ ] **Pessimistic `totalAssets` accounting**: `totalAssets` should be pessimistically calculated — don't count unrealized gains or pending yields until they're confirmed. [ERC4626 checklist SP1]

- [ ] **Share price depends too much on external protocols**: If `totalAssets` calls external contracts (oracles, strategies), those can be manipulated or fail. Look for: external calls in `totalAssets()`. [ERC4626 checklist SP2]

- [ ] **Exchange rate capped by flawed logic**: If the exchange rate can only increase (but the underlying logic is flawed), the rate gets stuck below fair value. Look for: rate increase mechanisms that can fail silently. [ERC4626 primer #4]

- [ ] **Profit lock mechanism not reflected in share price**: If there's a profit lock/drip mechanism, the share price must reflect the locked amount, not the full amount. [ERC4626 checklist SP5]

## Cross-Chain Vault Issues

- [ ] **Burn/mint cross-chain approach distorts share value**: If cross-chain transfers burn shares on source and mint on destination (via LayerZero), burning reduces totalSupply on the source chain, inflating share price for remaining holders. Others can withdraw at inflated price during transit. Fix: use lock/unlock approach. Look for: ERC4626 vaults with `_burn` in cross-chain send logic. [ERC4626 primer pattern #74]

## Vault Math Edge Cases

- [ ] **Zero shares or assets**: Can the vault handle `totalSupply == 0` and `totalAssets == 0` without division by zero? What about `totalAssets == 0` but `totalSupply > 0` (bad debt)? [ERC4626 checklist M7]

- [ ] **1 wei remaining in pool**: After withdrawals, if only 1 wei remains, does the math break? Can an attacker leave 1 wei to manipulate the next cycle? [beirao V-06]

- [ ] **Only 1 share minted from a large deposit**: Due to rounding, a deposit of 10,000 USDC might only yield 1 share if the exchange rate is very high. That 1 share can then be redeemed for a slightly different amount, creating extraction. [ERC4626 primer #5]

## Vault Token Interactions

- [ ] **Fee-on-transfer tokens**: If the underlying asset charges a transfer fee, `deposit(assets)` pulls `assets` but the vault receives `assets - fee`. Internal accounting is inflated. Look for: deposit functions that don't measure actual received amount. [ERC4626 checklist T1]

- [ ] **Rebase tokens as underlying**: Vault accounting drifts if the underlying is a rebasing token and the vault doesn't track rebases. [ERC4626 checklist T1]

- [ ] **Malicious token reentrancy**: If the underlying token has transfer hooks (ERC777), the vault is vulnerable to reentrancy during deposits/withdrawals. [ERC4626 checklist T2]

- [ ] **Approval race condition DoS**: If the underlying requires approve-to-zero (USDT), and the vault uses standard approve, transactions may revert. [ERC4626 checklist T2]

## Inheritance Issues

- [ ] **Override all needed functions**: If inheriting from `ERC4626.sol` and modifying logic, you must override ALL related functions. E.g., modifying deposit logic without overriding `previewDeposit` creates inconsistency. [ERC4626 checklist IC1]

- [ ] **Storage collision from inheritance**: Inherited contracts may have storage that collides with the vault's storage. [ERC4626 checklist IC2]

## Permissions

- [ ] **Fee bounds**: Are there maximum bounds on fees settable by admin? An admin setting 100% fees drains the vault. [ERC4626 checklist P1]
- [ ] **Trusted role can steal funds**: Can an admin withdraw vault funds directly? [ERC4626 checklist P2]
- [ ] **Funds locked on pause/shutdown**: If the vault is paused, can users still withdraw? [ERC4626 checklist P3]
- [ ] **Emergency liquidation**: Can the vault emergency-exit all strategy positions if needed? [ERC4626 checklist P6]

## ERC4626 Standard Compliance (Expanded from Solthodox Checklist)

- [ ] **`convertToAssets`/`convertToShares` must NOT vary by caller**: These are informational functions that MUST return the same value regardless of who calls them. If they include caller-specific fees or balances, they violate the spec and break composability. Look for: `msg.sender` references inside `convertToAssets`/`convertToShares`. [ERC4626 Checklist SC9]

- [ ] **`convertToAssets`/`convertToShares` must NOT include slippage**: These functions should return the ideal/theoretical conversion, not the practical amount after slippage. Slippage is only included in `previewDeposit`/`previewWithdraw`. Look for: slippage calculations in `convertTo*` functions. [ERC4626 Checklist SC10]

- [ ] **`previewDeposit` must round DOWN, `previewMint` must round UP**: `previewDeposit` returns fewer-or-equal shares than actual deposit mints. `previewMint` returns more-or-equal assets than actual mint costs. Wrong rounding direction allows extracting value. Look for: inconsistent rounding in preview functions. [ERC4626 Checklist SC26, SC27]

- [ ] **`previewWithdraw` must round UP, `previewRedeem` must round DOWN**: `previewWithdraw` shows more-or-equal shares burned than actual. `previewRedeem` shows fewer-or-equal assets received than actual. Look for: rounding direction that favors the user over the protocol. [ERC4626 Checklist SC40, SC41]

- [ ] **`maxDeposit`/`maxMint` must return 0 when deposits disabled, never revert**: These functions must never revert and must return 0 when deposits are paused/disabled. Look for: `maxDeposit` that reverts or returns non-zero when deposits are disabled. [ERC4626 Checklist SC15, SC18]

- [ ] **`totalAssets` must include yield AND external fees**: The `totalAssets()` function must account for all assets managed by the vault including accrued yield and externally charged fees. Failing to include these causes share price to be stale. Look for: `totalAssets()` that only returns deposited principal without accrued yield. [ERC4626 Checklist SC5, SC6]

## ERC4626 Math & Token Edge Cases (Expanded)

- [ ] **Inverse fee calculation when converting assets↔shares**: If the vault charges a deposit fee, converting from assets→shares and shares→assets requires using the inverse of the fee. `shares = assets * (1 - fee) / pricePerShare` but `assets = shares * pricePerShare / (1 - fee)`. Getting the inverse wrong means deposit/withdraw don't round-trip correctly. Look for: fee logic that doesn't properly invert between deposit and withdraw paths. [ERC4626 Checklist M5]

- [ ] **Direct token transfer can inflate share price**: Sending tokens directly to the vault (not through deposit) increases `totalAssets` without minting shares, inflating the share price. This can be weaponized for first-depositor attacks or to manipulate vault-based pricing. Look for: vaults using `balanceOf(address(this))` in `totalAssets()` without tracking deposits. [ERC4626 Checklist M4, beirao V-01, V-02]

- [ ] **Vault with 1 wei remaining**: If almost all assets are withdrawn leaving 1 wei, the share price may become extremely low or extremely high depending on implementation. This can cause precision issues for new depositors. Look for: edge case testing with near-zero vault balances. [beirao V-06]

- [ ] **Vault with zero shares but non-zero assets (or vice versa)**: If all shares are burned but some assets remain (or vice versa), the vault enters an inconsistent state. Look for: edge cases where `totalSupply == 0` but `totalAssets > 0`. [ERC4626 Checklist M7]

- [ ] **ERC4626 external swap slippage in withdrawals**: If vault strategies require swaps to liquidate positions for withdrawals, high slippage means users get fewer assets than expected. Vaults should have TVL limits so liquidation slippage stays manageable. Look for: vaults with illiquid strategies that don't cap deposits based on liquidation capacity. [ERC4626 Checklist E5, E6]

- [ ] **Inherited ERC4626 with overridden functions must override ALL dependent functions**: If you inherit from OZ's ERC4626 and modify deposit logic, you may also need to override `previewDeposit`, `maxDeposit`, `convertToShares`, etc. Missing overrides causes inconsistency. Look for: ERC4626 subclasses that override some but not all related functions. [ERC4626 Checklist IC1]

## Supplemental Attack Vectors (SAS-AV)

These vectors are merged from sanbir/solidity-auditor-skills; each item retains a detection condition (D), false-positive gate (FP), and source provenance.

- [ ] **[SAS-AV-103] ERC4626 convertToAssets Used Instead of previewWithdraw**
  - **D:** Integration calls `convertToAssets(shares)` to estimate withdrawal proceeds — excludes fees/slippage per spec. Downstream logic (health checks, rebalancing) operates on inflated values.
  - **FP:** `previewWithdraw()`/`previewRedeem()` used for estimates. No withdrawal fees. Fee delta accounted separately.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-240

- [ ] **[SAS-AV-104] Vault Insolvency via Accumulated Rounding Dust**
  - **D:** Vault tracks `totalAssets` as a storage variable separate from `token.balanceOf(vault)`. Solidity's floor rounding on each deposit/withdrawal creates tiny overages — user receives 1 wei more than burned shares represent. Over many operations `totalAssets` exceeds actual balance, causing last withdrawers to revert.
  - **FP:** Rounding consistently favors the vault (round shares up on deposit, round assets down on withdrawal). OZ Math with `Rounding.Ceil`/`Rounding.Floor` applied correctly.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-264

- [ ] **[SAS-AV-105] Idle Asset Dilution from Sub-Vault Deposit Caps**
  - **D:** Aggregator vault accepts deposits without checking sub-vault capacity. Excess assets sit idle earning zero yield but dilute share price for all depositors.
  - **FP:** `maxDeposit()` reflects combined sub-vault remaining capacity. Deposits revert when no capacity remains. Idle assets auto-routed to fallback yield.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-271

- [ ] **[SAS-AV-106] Partial Redemption Fails to Reduce Tracked Total**
  - **D:** Partial redemption fill doesn't reduce `totalQueuedShares`/`totalPendingAssets` proportionally. Inflated total skews share price.
  - **FP:** Partial fill reduces tracked totals proportionally. Per-request tracking. Atomic full-or-nothing redemptions.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-279

- [ ] **[SAS-AV-107] Share Redemption at Optimistic Rate**
  - **D:** Shares redeemed at projected end-of-term rate rather than current realized rate. Early redeemers take more than proportional share — late redeemers find vault depleted.
  - **FP:** Redemption uses current realized rate (`totalAssets() / totalSupply()`). Withdrawal queue enforces proportional access. Early redemption penalty applied.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-281

- [ ] **[SAS-AV-108] Withdrawal Rate Limit Bypassed via Share Transfer**
  - **D:** Per-address withdrawal limit bypassed by transferring shares to fresh addresses — each gets a fresh limit.
  - **FP:** Limit tracks underlying position, not address. Shares non-transferable or transfer resets allowance.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-283

- [ ] **[SAS-AV-109] Missing Slippage Protection on Vault Withdraw/Redeem**
  - **D:** ERC4626 `withdraw`/`redeem` accept no slippage parameter. Exchange rate changes between submission and execution (yield, donations, losses). Users receive fewer assets or burn more shares than expected.
  - **FP:** Fixed 1:1 exchange rate. Custom `withdrawWithSlippage` wrapper. Frontend simulation with revert. Loss-proof yield source.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-285

- [ ] **[SAS-AV-110] ERC4626 maxDeposit vs Actual Deposit Method Mismatch**
  - **D:** Vault queries `maxDeposit()` but deposits via `mint()` (or vice versa). Per ERC4626, `maxDeposit` governs `deposit()` and `maxMint` governs `mint()` — limits may differ. Same for withdrawal: `convertToAssets(maxRedeem(...))` instead of `maxWithdraw(...)` overstates amount (excludes fees/slippage).
  - **FP:** Method-matched queries (`maxMint` for `mint`, `maxDeposit` for `deposit`). `previewWithdraw`/`previewRedeem` for estimates. Underlying `max*` verified consistent.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-308

## drozer-lite Additions

The checks below are the canonical runtime additions from the EVM-relevant drozer-lite profiles. Each item retains the source profile and pinned commit.

- [ ] **[DROZER-UNI-89] Skip/Disable Flag Consistency**
  - **D:** A `skipForWithdrawal` flag is applied inconsistently across functions (correct for withdraw, wrong for deposit).
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** Build a function × flag × checked? table.
  - **Look for:** No source-specific red flags listed; trace the invariant and caller-controlled inputs described above.
  - **Origin:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-UNI-93] Emergency Function Input Validation**
  - **D:** `emergencyWithdrawFromYieldSources(address[])` accepts arbitrary addresses; accounting can be corrupted by a rogue address.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** Verify input validation against registered sources.
  - **Look for:** No source-specific red flags listed; trace the invariant and caller-controlled inputs described above.
  - **Origin:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-UNI-95] Irreversible Yield-Source Configuration**
  - **D:** `underlyingToVToken[token]` is set once with no unset; a wrong or deprecated mapping is permanent.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** Verify every configuration mapping has both set and unset admin paths.
  - **Look for:** No source-specific red flags listed; trace the invariant and caller-controlled inputs described above.
  - **Origin:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-VAULT-4] Return-Value Semantics on Deploy/Undeploy**
  - **D:** `deploy()` / `undeploy()` returns the ACTUAL amount (post-slippage, post-fees), but callers use the REQUESTED amount for downstream accounting.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** For each deploy/undeploy call, check whether the return value or the input parameter is used for `_deployedAmount` bookkeeping, for pro-rata allocation, and for return-to-user amounts. Verify `_deployedAmount` is decremented on undeploy.
  - **Look for:** `strategy.undeploy(amountRequested); _deployedAmount -= amountRequested;` instead of using the return value Multi-strategy withdrawal using requested-amount math Leverage undeploy returning 90% with 10% silently lost
  - **Origin:** [gdroz3r/drozer-lite — checklists/vault.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/vault.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-VAULT-5] Strategy Migration & Constructor Validation**
  - **D:** Strategies are added without validating the underlying protocol's expected asset, and migration does not fully unwind the old strategy before activating the new one.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** For each strategy constructor, verify it checks that the configured asset matches the underlying protocol's expected token. Verify `addStrategy` rejects duplicates and grants the token approval. Verify `removeStrategy` revokes the approval. Verify `migrateStrategy` fully unwinds before activating the replacement and has a timelock / user exit window.
  - **Look for:** No `require(market.loanToken() == asset)` in constructor Migration path that leaves old strategy still approved Removed strategy retains unlimited allowance
  - **Origin:** [gdroz3r/drozer-lite — checklists/vault.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/vault.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-VAULT-6] Access Control Principal (Receiver vs Caller)**
  - **D:** `deposit(assets, receiver)` checks `msg.sender` against a whitelist instead of checking `receiver`, allowing a whitelisted user to deposit on behalf of any non-whitelisted address.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** For every function accepting `receiver`/`owner`/`beneficiary`, check which principal is validated against whitelists/limits. `maxDeposit(address)` must accept `receiver` as the limit target.
  - **Look for:** `require(isWhitelisted[msg.sender])` on a function that credits shares to `receiver` `maxDeposit` read against `msg.sender` when `deposit` credits to `receiver`
  - **Origin:** [gdroz3r/drozer-lite — checklists/vault.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/vault.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
