<!-- GENERATED FILE: source is ../../data/canonical-checks.json; do not edit by hand. -->
# Flash Loan Security Checklist

Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.

## Governance Attacks

- [ ] **[EVM-FLASH-001] Flash-loan voting** _(exploit-pattern; medium)_: Attacker flash-borrows governance tokens, votes or creates a proposal, returns tokens. Beanstalk lost $182M to this. Mitigation: snapshot-based voting at a past block. Look for: governance using current-block balanceOf or getVotes. [beirao GOV, Dacian governance]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao GOV, Dacian governance

- [ ] **[EVM-FLASH-002] Flash-loan quorum manipulation** _(exploit-pattern; medium)_: Even if voting uses snapshots, an attacker can accumulate tokens before the snapshot block, then dump after. If proposal creation doesn't require a minimum holding period, this is viable. Look for: proposal creation without minimum token holding duration. [Dacian governance]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Dacian governance

## Oracle Manipulation

- [ ] **[EVM-FLASH-003] Flash loan + AMM spot price manipulation** _(exploit-pattern; medium)_: Attacker flash-borrows to massively skew AMM reserves, then uses the manipulated spot price in a protocol (lending, options). This works because AMM spot price = f(reserves), and reserves are manipulable. Look for: any price derivation from `getReserves()` or `slot0.sqrtPriceX96`. [beirao G-05, Tamjid D3]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao G-05, Tamjid D3

- [ ] **[EVM-FLASH-004] Flash loan + TWAP manipulation** _(exploit-pattern; medium)_: TWAPs are resistant to single-block manipulation but vulnerable to multi-block attacks. On L2s with cheap gas, an attacker can manipulate the price at block boundaries across multiple blocks. Look for: short TWAP windows (<30 minutes) on L2s. [Decurity AMM]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Decurity AMM

## Vault / Yield Attacks

- [ ] **[EVM-FLASH-005] Flash deposit-harvest-withdraw in yield vaults** _(exploit-pattern; medium)_: Attacker flash-deposits into a vault, triggers reward harvest (claiming accumulated yield), then withdraws — capturing yield earned by long-term depositors. Look for: vaults where depositing + harvesting + withdrawing can happen in the same transaction without penalty. [beirao V-07]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao V-07

- [ ] **[EVM-FLASH-006] Share price manipulation via flash loan** _(exploit-pattern; medium)_: Flash-borrow to inflate vault deposits, skewing the share-to-asset ratio. In the same tx, withdraw more assets than deposited. Look for: vaults where share price depends on balance ratios that can be manipulated intra-tx. [beirao V-08]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao V-08

- [ ] **[EVM-FLASH-007] Flash mint inflating totalSupply** _(exploit-pattern; medium)_: DAI and other flash-mintable tokens can temporarily have totalSupply = type(uint256).max during a flash mint. Any formula using `totalSupply()` is manipulable. Look for: pricing or share calculations referencing `totalSupply()` of flash-mintable tokens. [weird-erc20]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** weird-erc20

## Auction Attacks

- [ ] **[EVM-FLASH-008] Flash loan to win auctions** _(exploit-pattern; medium)_: An attacker flash-borrows to outbid legitimate participants in auction liquidations. After winning and receiving discounted collateral, they repay the flash loan at profit. Look for: auction mechanisms where the full bid amount is only needed temporarily. [Decurity CDP]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Decurity CDP

- [ ] **[EVM-FLASH-009] Flash loan to prematurely close auctions** _(exploit-pattern; medium)_: If a borrower can repay their debt to prematurely end a liquidation auction, they can flash-borrow to repay, close the auction, and then take a new undercollateralized position. Look for: auction systems where the debtor can terminate the auction by proving solvency. [Decurity CDP]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Decurity CDP

## DeFi Protocol Attacks

- [ ] **[EVM-FLASH-010] Flash loan + self-liquidation** _(exploit-pattern; medium)_: Attacker borrows via flash loan, uses those tokens to open a position, lets it become instantly underwater (by manipulating the oracle in the same tx), then liquidates their own position to collect the liquidation bonus. Look for: protocols where position creation + liquidation can happen in the same block. [beirao LEN-02]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao LEN-02

- [ ] **[EVM-FLASH-011] AAVE flash loans inflate pool index** _(exploit-pattern; medium)_: On AAVE, each flash loan inflates the pool interest rate index. A maximum of ~180 flash loans per block can compound this effect. Look for: protocols built on AAVE that assume stable index growth. [beirao AC-05]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao AC-05

## Cross-Protocol Flash Loans

- [ ] **[EVM-FLASH-012] Cross-protocol reentrancy via flash loan callbacks** _(exploit-pattern; medium)_: Flash loan callbacks execute arbitrary code. An attacker can use the callback to interact with other protocols that reference the flash-loaned asset's balance. Look for: protocols that use `balanceOf` for accounting where the token supports flash loans. [Tamjid D10]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Tamjid D10

- [ ] **[EVM-FLASH-013] Flash loan to bypass rate limits** _(exploit-pattern; medium)_: Some protocols have per-transaction or per-block limits on actions. Flash loans can bypass these by executing all actions atomically. Look for: rate-limiting mechanisms that check per-tx rather than cumulative. [general]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** legacy-checklist

## Supplemental Attack Vectors (SAS-AV)

- [ ] **[EVM-FLASH-014] Circular Flash Loan Amplification Across Protocols** _(exploit-pattern; medium)_: Attacker uses flash-loaned assets to deposit in Protocol A, borrows from A, deposits borrowed assets in Protocol B, borrows from B, and repeats. Creates leveraged positions across multiple protocols in a single transaction with zero initial capital, amplifying any exploit (oracle manipulation, governance attack) by orders of magnitude.
  - **FP:** Flash loan detection via `require(block.number > depositBlock)` or same-block withdrawal restriction. Cross-protocol exposure limits. Deposit cooldown periods. Conservative LTV ratios that make circular amplification unprofitable after fees.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-113](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-219
