<!-- GENERATED FILE: source is ../../data/canonical-checks.json; do not edit by hand. -->
# ERC4626 Vault Security Checklist

Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.

## First Depositor / Inflation Attack

- [ ] **[EVM-ERC4626-001] Classic inflation attack** _(exploit-pattern; medium)_: Attacker deposits 1 wei → gets 1 share → donates large amount directly to vault → subsequent depositors get 0 shares due to rounding. Mitigate: virtual shares/assets (OpenZeppelin), minimum deposit, initial protocol deposit, dead shares (Uniswap V2 style). Look for: empty vaults where first deposit can be 1 wei. [ERC4626 checklist SP4, ERC4626 primer #3]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist SP4, ERC4626 primer #3

- [ ] **[EVM-ERC4626-002] Inconsistent deposit/mint on first deposit** _(exploit-pattern; medium)_: Some vaults use different formulas for `previewDeposit` vs `previewMint` when supply=0. Astaria's ERC4626Cloned used `assets` for deposit but `10e18` for mint. Look for: different code paths in deposit vs mint when `totalSupply == 0`. [ERC4626 primer #3]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 primer #3

- [ ] **[EVM-ERC4626-003] Asymmetric virtual shares/assets require invariant analysis** _(exploit-pattern; medium)_: Virtual shares and virtual assets do not universally have to be equal. An offset may be chosen to address decimals, inflation resistance, or another accounting design; assess the resulting conversion, rounding, and donation invariants instead of treating asymmetry as an automatic vulnerability.
  - **Trigger:** An ERC4626 implementation uses virtual assets, virtual shares, or a decimals offset.
  - **Risk:** An unjustified offset can distort share value or leave an inflation path, but the defect is the violated invariant rather than inequality alone.
  - **Detection:** Derive the exact conversion formulas at empty and non-empty states and test donation, deposit, mint, withdraw, and redeem boundaries.
  - **FP:** The offset is documented and the resulting conversions preserve ERC4626-ROUND-001 and the vault's solvency invariant.
  - **Proof:** Construct boundary deposits and donations and quantify any share-price or solvency deviation caused by the selected offsets.
  - **Provenance:** ERC4626 primer #5

## Rounding Direction (EIP-4626 Compliance)

- [ ] **[ERC4626-ROUND-001] Canonical ERC-4626 rounding directions** _(normative; high)_: Apply the EIP-4626 vault-favoring directions consistently: assets supplied to shares received DOWN; shares requested to assets supplied UP; assets requested to shares burned UP; shares burned to assets received DOWN; convertToShares DOWN; convertToAssets DOWN.
  - **Trigger:** A vault converts between assets and shares or implements previewDeposit, previewMint, previewWithdraw, or previewRedeem.
  - **Risk:** Inconsistent rounding can transfer dust through repeated operations or make the vault insolvent.
  - **Detection:** Compare every mutable and preview conversion with the canonical table: deposit DOWN, mint UP, withdraw UP, redeem DOWN, convertToShares DOWN, convertToAssets DOWN. Check every override and helper path for the same direction and fee treatment.
  - **FP:** The implementation follows the canonical table and any fee/slippage difference is explicitly accounted for in the corresponding preview function.
  - **Proof:** Construct boundary values around one wei and demonstrate that each operation favors the vault according to the canonical direction without violating solvency.
  - **Provenance:** ERC4626 checklist SC12; [EIP-4626](https://eips.ethereum.org/EIPS/eip-4626); ERC4626 checklist SC26; ERC4626 checklist SC27; ERC4626 checklist SC40; ERC4626 checklist SC41; ERC4626 checklist M1

## Compliance Requirements

- [ ] **[EVM-ERC4626-010] `totalAssets` must include compounding yield AND external fees** _(exploit-pattern; medium)_: Not just deposited amount. [ERC4626 checklist SC5, SC6]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist SC5, SC6

- [ ] **[EVM-ERC4626-011] `totalAssets` must never revert** _(exploit-pattern; medium)_: [ERC4626 checklist SC7]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist SC7

- [ ] **[EVM-ERC4626-012] `convertToAssets`/`convertToShares` must never vary by caller** _(exploit-pattern; medium)_: These are global, not per-user. [ERC4626 checklist SC9]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist SC9

- [ ] **[EVM-ERC4626-013] `convertToAssets`/`convertToShares` must NOT include slippage or vault fees** _(exploit-pattern; medium)_: These are idealized math. [ERC4626 checklist SC10]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist SC10

- [ ] **[EVM-ERC4626-014] `maxDeposit`/`maxMint` must NOT rely on `balanceOf(asset)`** _(exploit-pattern; medium)_: Per spec, these represent protocol capacity, not token balance. [ERC4626 checklist SC17]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist SC17

- [ ] **[EVM-ERC4626-015] `maxDeposit`/`maxMint` return 0 when deposits disabled, `type(uint256).max` when no limit** _(exploit-pattern; medium)_: [ERC4626 checklist SC15, SC16]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist SC15, SC16

- [ ] **[EVM-ERC4626-016] `maxDeposit`/`maxMint`/`maxWithdraw`/`maxRedeem` must NEVER revert** _(exploit-pattern; medium)_: Return 0 instead. [ERC4626 checklist SC18, SC39]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist SC18, SC39

- [ ] **[EVM-ERC4626-017] `preview*` functions must include vault fees AND slippage/chain conditions** _(exploit-pattern; medium)_: Unlike `convertTo*`. [ERC4626 checklist SC23, SC25, SC47, SC48]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist SC23, SC25, SC47, SC48

- [ ] **[EVM-ERC4626-018] `preview*` functions may revert for operation-level conditions** _(normative; high)_: ERC-4626 preview functions should reflect the corresponding operation and may revert for conditions that would also make that operation revert, including unreasonably large inputs. They must not revert merely because a vault-specific limit such as maxDeposit or maxWithdraw is exceeded.
  - **Trigger:** An integration assumes every preview call always succeeds or uses a preview value without handling operation-level failures.
  - **Risk:** Treating preview calls as unconditionally non-reverting can hide a required error path or make an integration rely on a value that cannot be produced by the operation.
  - **Detection:** Compare each preview function with its corresponding mutable operation, vault-specific limits, fees, slippage conditions, and overflow behavior.
  - **FP:** The preview function does not fail solely on vault limits and the caller handles other failures that the operation can also produce.
  - **Proof:** Exercise the operation-level failure conditions and verify preview and mutable-call behavior match the declared EIP-4626 semantics.
  - **Provenance:** ERC4626 checklist SC24, SC49; [EIP-4626 Tokenized Vaults](https://eips.ethereum.org/EIPS/eip-4626)

- [ ] **[EVM-ERC4626-019] `deposit` must revert if exceeds `maxDeposit`** _(exploit-pattern; medium)_: [ERC4626 checklist SC32]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist SC32

- [ ] **[EVM-ERC4626-020] `deposit` must pull EXACTLY `assets` tokens** _(exploit-pattern; medium)_: [ERC4626 checklist SC28]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist SC28

- [ ] **[EVM-ERC4626-021] `mint` must mint EXACTLY `shares` shares** _(exploit-pattern; medium)_: [ERC4626 checklist SC29]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist SC29

- [ ] **[EVM-ERC4626-022] `withdraw`/`redeem` must support third-party operation with approval** _(exploit-pattern; medium)_: [ERC4626 checklist SC56]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist SC56

- [ ] **[EVM-ERC4626-023] Events: `Deposit` and `Withdraw` must always be emitted** _(exploit-pattern; medium)_: [ERC4626 checklist SC35, SC57]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist SC35, SC57

## Share Price Manipulation

- [ ] **[EVM-ERC4626-024] Direct token transfer inflates share price** _(exploit-pattern; medium)_: If a vault uses `balanceOf(address(this))` for `totalAssets`, a direct transfer increases assets without minting shares and manipulates the conversion rate. Track assets through explicit accounting or otherwise neutralize unsolicited transfers. Look for: `totalAssets()` implementations using raw `balanceOf` without handling direct donations. [ERC4626 checklist SP3, M4, beirao V-01, V-02]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist SP3, M4, beirao V-01, V-02

- [ ] **[EVM-ERC4626-025] Pessimistic `totalAssets` accounting** _(exploit-pattern; medium)_: `totalAssets` should be pessimistically calculated — don't count unrealized gains or pending yields until they're confirmed. [ERC4626 checklist SP1]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist SP1

- [ ] **[EVM-ERC4626-026] Share price depends too much on external protocols** _(heuristic; contextual)_: If `totalAssets` calls external contracts (oracles, strategies), those can be manipulated or fail. Look for: external calls in `totalAssets()`. [ERC4626 checklist SP2]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist SP2

- [ ] **[EVM-ERC4626-027] Exchange rate capped by flawed logic** _(exploit-pattern; medium)_: If the exchange rate can only increase (but the underlying logic is flawed), the rate gets stuck below fair value. Look for: rate increase mechanisms that can fail silently. [ERC4626 primer #4]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 primer #4

- [ ] **[EVM-ERC4626-028] Profit lock mechanism not reflected in share price** _(exploit-pattern; medium)_: If there's a profit lock/drip mechanism, the share price must reflect the locked amount, not the full amount. [ERC4626 checklist SP5]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist SP5

## Cross-Chain Vault Issues

- [ ] **[EVM-ERC4626-029] Burn/mint cross-chain approach distorts share value** _(exploit-pattern; medium)_: If cross-chain transfers burn shares on source and mint on destination (via LayerZero), burning reduces totalSupply on the source chain, inflating share price for remaining holders. Others can withdraw at inflated price during transit. Fix: use lock/unlock approach. Look for: ERC4626 vaults with `_burn` in cross-chain send logic. [ERC4626 primer pattern #74]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 primer pattern #74

## Vault Math Edge Cases

- [ ] **[EVM-ERC4626-030] Zero shares or assets** _(exploit-pattern; medium)_: Can the vault handle `totalSupply == 0` and `totalAssets == 0` without division by zero? What about `totalAssets == 0` but `totalSupply > 0` (bad debt)? [ERC4626 checklist M7]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist M7

- [ ] **[EVM-ERC4626-031] 1 wei remaining in pool** _(exploit-pattern; medium)_: After withdrawals, if only 1 wei remains, does the math break? Can an attacker leave 1 wei to manipulate the next cycle? [beirao V-06]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao V-06

- [ ] **[EVM-ERC4626-032] Only 1 share minted from a large deposit** _(exploit-pattern; medium)_: Due to rounding, a deposit of 10,000 USDC might only yield 1 share if the exchange rate is very high. That 1 share can then be redeemed for a slightly different amount, creating extraction. [ERC4626 primer #5]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 primer #5

## Vault Token Interactions

- [ ] **[EVM-ERC4626-033] Fee-on-transfer tokens** _(exploit-pattern; medium)_: If the underlying asset charges a transfer fee, `deposit(assets)` pulls `assets` but the vault receives `assets - fee`. Internal accounting is inflated. Look for: deposit functions that don't measure actual received amount. [ERC4626 checklist T1]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist T1

- [ ] **[EVM-ERC4626-034] Rebase tokens as underlying** _(exploit-pattern; medium)_: Vault accounting drifts if the underlying is a rebasing token and the vault doesn't track rebases. [ERC4626 checklist T1]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist T1

- [ ] **[EVM-ERC4626-035] Malicious token reentrancy** _(exploit-pattern; medium)_: If the underlying token has transfer hooks (ERC777), the vault is vulnerable to reentrancy during deposits/withdrawals. [ERC4626 checklist T2]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist T2

- [ ] **[EVM-ERC4626-036] Approval race condition DoS** _(exploit-pattern; medium)_: If the underlying requires approve-to-zero (USDT), and the vault uses standard approve, transactions may revert. [ERC4626 checklist T2]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist T2

## Inheritance Issues

- [ ] **[EVM-ERC4626-037] Override all needed functions** _(exploit-pattern; medium)_: If inheriting from `ERC4626.sol` and modifying logic, you must override ALL related functions. E.g., modifying deposit logic without overriding `previewDeposit` creates inconsistency. [ERC4626 checklist IC1]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist IC1

- [ ] **[EVM-ERC4626-038] Storage collision from inheritance** _(exploit-pattern; medium)_: Inherited contracts may have storage that collides with the vault's storage. [ERC4626 checklist IC2]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist IC2

## Permissions

- [ ] **[EVM-ERC4626-039] Fee bounds** _(exploit-pattern; medium)_: Are there maximum bounds on fees settable by admin? An admin setting 100% fees drains the vault. [ERC4626 checklist P1]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist P1

- [ ] **[EVM-ERC4626-040] Trusted role can steal funds** _(exploit-pattern; medium)_: Can an admin withdraw vault funds directly? [ERC4626 checklist P2]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist P2

- [ ] **[EVM-ERC4626-041] Funds locked on pause/shutdown** _(exploit-pattern; medium)_: If the vault is paused, can users still withdraw? [ERC4626 checklist P3]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist P3

- [ ] **[EVM-ERC4626-042] Emergency liquidation** _(exploit-pattern; medium)_: Can the vault emergency-exit all strategy positions if needed? [ERC4626 checklist P6]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 checklist P6

## ERC4626 Math & Token Edge Cases (Expanded)

- [ ] **[EVM-ERC4626-043] Inverse fee calculation when converting assets↔shares** _(exploit-pattern; medium)_: For an ERC4626 fee on gross deposit assets, netAssets = assets * (1 - fee) and shares = netAssets / pricePerShare; when solving for gross assets for requested shares, assets = shares * pricePerShare / (1 - fee). Verify the fee basis and rounding on each operation.
  - **Trigger:** The vault charges a deposit or withdrawal fee while converting between gross assets, net assets, and shares.
  - **Risk:** If the vault charges a deposit fee, converting from assets→shares and shares→assets requires using the inverse of the fee. `shares = assets * (1 - fee) / pricePerShare` but `assets = shares * pricePerShare / (1 - fee)`. Getting the inverse wrong means deposit/withdraw don't round-trip correctly. Look for: fee logic that doesn't properly invert between deposit and withdraw paths. [ERC4626 Checklist M5]
  - **Detection:** Compare deposit/mint/withdraw/redeem and preview paths with the fee basis, price per share, and direction-specific rounding.
  - **FP:** The fee basis is explicit and the implementation follows the corresponding gross/net equation; a different fee convention is documented and tested.
  - **Proof:** Exercise forward and inverse ERC4626 conversions at zero, one-unit, and maximal fee/rounding boundaries and compare exact asset/share relations.
  - **Provenance:** ERC4626 Checklist M5; [OpenZeppelin ERC4626 implementation guide](https://docs.openzeppelin.com/contracts/5.x/erc4626)
  - **Related:** EVM-MATH-007

- [ ] **[EVM-ERC4626-044] ERC4626 external swap slippage in withdrawals** _(exploit-pattern; medium)_: If vault strategies require swaps to liquidate positions for withdrawals, high slippage means users get fewer assets than expected. Vaults should have TVL limits so liquidation slippage stays manageable. Look for: vaults with illiquid strategies that don't cap deposits based on liquidation capacity. [ERC4626 Checklist E5, E6]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** ERC4626 Checklist E5, E6

## Supplemental Attack Vectors (SAS-AV)

- [ ] **[EVM-ERC4626-045] ERC4626 convertToAssets Used Instead of previewWithdraw** _(exploit-pattern; medium)_: Integration calls `convertToAssets(shares)` to estimate withdrawal proceeds — excludes fees/slippage per spec. Downstream logic (health checks, rebalancing) operates on inflated values.
  - **FP:** `previewWithdraw()`/`previewRedeem()` used for estimates. No withdrawal fees. Fee delta accounted separately.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-103](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-240

- [ ] **[EVM-ERC4626-046] Vault Insolvency via Accumulated Rounding Dust** _(exploit-pattern; medium)_: Vault tracks `totalAssets` as a storage variable separate from `token.balanceOf(vault)`. Solidity's floor rounding on each deposit/withdrawal creates tiny overages — user receives 1 wei more than burned shares represent. Over many operations `totalAssets` exceeds actual balance, causing last withdrawers to revert.
  - **FP:** Rounding follows ERC4626-ROUND-001: assets-to-shares on deposit DOWN, shares-to-assets on redeem DOWN, shares required for withdrawal UP, and assets required for mint UP. Tracked totals, actual token balances, and partial-fill accounting remain solvent after repeated boundary operations.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-104](https://github.com/sanbir/solidity-auditor-skills)
  - **Related:** ERC4626-ROUND-001
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-264

- [ ] **[EVM-ERC4626-047] Idle Asset Dilution from Sub-Vault Deposit Caps** _(exploit-pattern; medium)_: Aggregator vault accepts deposits without checking sub-vault capacity. Excess assets sit idle earning zero yield but dilute share price for all depositors.
  - **FP:** `maxDeposit()` reflects combined sub-vault remaining capacity. Deposits revert when no capacity remains. Idle assets auto-routed to fallback yield.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-105](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-271

- [ ] **[EVM-ERC4626-048] Partial Redemption Fails to Reduce Tracked Total** _(exploit-pattern; medium)_: Partial redemption fill doesn't reduce `totalQueuedShares`/`totalPendingAssets` proportionally. Inflated total skews share price.
  - **FP:** Partial fill reduces tracked totals proportionally. Per-request tracking. Atomic full-or-nothing redemptions.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-106](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-279

- [ ] **[EVM-ERC4626-049] Share Redemption at Optimistic Rate** _(exploit-pattern; medium)_: Shares redeemed at projected end-of-term rate rather than current realized rate. Early redeemers take more than proportional share — late redeemers find vault depleted.
  - **FP:** Redemption uses current realized rate (`totalAssets() / totalSupply()`). Withdrawal queue enforces proportional access. Early redemption penalty applied.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-107](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-281

- [ ] **[EVM-ERC4626-050] Withdrawal Rate Limit Bypassed via Share Transfer** _(exploit-pattern; medium)_: Per-address withdrawal limit bypassed by transferring shares to fresh addresses — each gets a fresh limit.
  - **FP:** Limit tracks underlying position, not address. Shares non-transferable or transfer resets allowance.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-108](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-283

- [ ] **[EVM-ERC4626-051] Missing Slippage Protection on Vault Withdraw/Redeem** _(exploit-pattern; medium)_: ERC4626 `withdraw`/`redeem` accept no slippage parameter. Exchange rate changes between submission and execution (yield, donations, losses). Users receive fewer assets or burn more shares than expected.
  - **FP:** Fixed 1:1 exchange rate. Custom `withdrawWithSlippage` wrapper. Frontend simulation with revert. Loss-proof yield source.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-109](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-285

- [ ] **[EVM-ERC4626-052] ERC4626 maxDeposit vs Actual Deposit Method Mismatch** _(exploit-pattern; medium)_: Vault queries `maxDeposit()` but deposits via `mint()` (or vice versa). Per ERC4626, `maxDeposit` governs `deposit()` and `maxMint` governs `mint()` — limits may differ. Same for withdrawal: `convertToAssets(maxRedeem(...))` instead of `maxWithdraw(...)` overstates amount (excludes fees/slippage).
  - **FP:** Method-matched queries (`maxMint` for `mint`, `maxDeposit` for `deposit`). `previewWithdraw`/`previewRedeem` for estimates. Underlying `max*` verified consistent.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-110](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-308

## drozer-lite Additions

- [ ] **[EVM-ERC4626-053] Skip/Disable Flag Consistency** _(exploit-pattern; medium)_: A `skipForWithdrawal` flag is applied inconsistently across functions (correct for withdraw, wrong for deposit).
  - **Trigger:** A `skipForWithdrawal` flag is applied inconsistently across functions (correct for withdraw, wrong for deposit). No source-specific red flags listed; trace the invariant and caller-controlled inputs described above.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Proof:** Build a function × flag × checked? table.
  - **Provenance:** [DROZER-UNI-89](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md); gdroz3r/drozer-lite — checklists/universal.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-ERC4626-054] Emergency Function Input Validation** _(exploit-pattern; medium)_: `emergencyWithdrawFromYieldSources(address[])` accepts arbitrary addresses; accounting can be corrupted by a rogue address.
  - **Trigger:** `emergencyWithdrawFromYieldSources(address[])` accepts arbitrary addresses; accounting can be corrupted by a rogue address. No source-specific red flags listed; trace the invariant and caller-controlled inputs described above.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Proof:** Verify input validation against registered sources.
  - **Provenance:** [DROZER-UNI-93](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md); gdroz3r/drozer-lite — checklists/universal.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-ERC4626-055] Irreversible Yield-Source Configuration** _(exploit-pattern; medium)_: `underlyingToVToken[token]` is set once with no unset; a wrong or deprecated mapping is permanent.
  - **Trigger:** `underlyingToVToken[token]` is set once with no unset; a wrong or deprecated mapping is permanent. No source-specific red flags listed; trace the invariant and caller-controlled inputs described above.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Proof:** Verify every configuration mapping has both set and unset admin paths.
  - **Provenance:** [DROZER-UNI-95](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md); gdroz3r/drozer-lite — checklists/universal.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-ERC4626-056] Return-Value Semantics on Deploy/Undeploy** _(exploit-pattern; medium)_: `deploy()` / `undeploy()` returns the ACTUAL amount (post-slippage, post-fees), but callers use the REQUESTED amount for downstream accounting.
  - **Trigger:** `deploy()` / `undeploy()` returns the ACTUAL amount (post-slippage, post-fees), but callers use the REQUESTED amount for downstream accounting. `strategy.undeploy(amountRequested); _deployedAmount -= amountRequested;` instead of using the return value Multi-strategy withdrawal using requested-amount math Leverage undeploy returning 90% with 10% silently lost
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Proof:** For each deploy/undeploy call, check whether the return value or the input parameter is used for `_deployedAmount` bookkeeping, for pro-rata allocation, and for return-to-user amounts. Verify `_deployedAmount` is decremented on undeploy.
  - **Provenance:** [DROZER-VAULT-4](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/vault.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/vault.md); gdroz3r/drozer-lite — checklists/vault.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/vault.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/vault.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-ERC4626-057] Strategy Migration & Constructor Validation** _(exploit-pattern; medium)_: Strategies are added without validating the underlying protocol's expected asset, and migration does not fully unwind the old strategy before activating the new one.
  - **Trigger:** Strategies are added without validating the underlying protocol's expected asset, and migration does not fully unwind the old strategy before activating the new one. No `require(market.loanToken() == asset)` in constructor Migration path that leaves old strategy still approved Removed strategy retains unlimited allowance
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Proof:** For each strategy constructor, verify it checks that the configured asset matches the underlying protocol's expected token. Verify `addStrategy` rejects duplicates and grants the token approval. Verify `removeStrategy` revokes the approval. Verify `migrateStrategy` fully unwinds before activating the replacement and has a timelock / user exit window.
  - **Provenance:** [DROZER-VAULT-5](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/vault.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/vault.md); gdroz3r/drozer-lite — checklists/vault.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/vault.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/vault.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-ERC4626-058] Access Control Principal (Receiver vs Caller)** _(exploit-pattern; medium)_: `deposit(assets, receiver)` checks `msg.sender` against a whitelist instead of checking `receiver`, allowing a whitelisted user to deposit on behalf of any non-whitelisted address.
  - **Trigger:** `deposit(assets, receiver)` checks `msg.sender` against a whitelist instead of checking `receiver`, allowing a whitelisted user to deposit on behalf of any non-whitelisted address. `require(isWhitelisted[msg.sender])` on a function that credits shares to `receiver` `maxDeposit` read against `msg.sender` when `deposit` credits to `receiver`
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Proof:** For every function accepting `receiver`/`owner`/`beneficiary`, check which principal is validated against whitelists/limits. `maxDeposit(address)` must accept `receiver` as the limit target.
  - **Provenance:** [DROZER-VAULT-6](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/vault.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/vault.md); gdroz3r/drozer-lite — checklists/vault.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/vault.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/vault.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
