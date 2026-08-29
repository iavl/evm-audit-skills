<!-- GENERATED FILE: source is ../../data/canonical-checks.json; do not edit by hand. -->
# Chain-Specific Security Checklist

Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.

## Compiler & EVM Version Quirks

- [ ] **[EVM-ASM-025] `PUSH0` availability depends on compiler target and chain fork**: Shared canonical check; apply the primary definition and evidence requirements for `evm-audit-assembly`.

## Arbitrum

- [ ] **[EVM-CHAIN-001] `block.number` returns L1 block number on Arbitrum** _(semantic; high)_: On Arbitrum, `block.number` returns the approximate L1 block number, not the L2 block number; it can update in jumps and has much lower short-term resolution than expected. Use the Arbitrum system contract for L2 block number when required. Look for: `block.number` used for timing, deadlines, uniqueness, or block-frequency calculations on Arbitrum. [multichain-auditor, beirao ARB-01, Arbitrum Checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor, beirao ARB-01, Arbitrum Checklist

- [ ] **[EVM-CHAIN-002] Multiple L2 transactions per L1 block** _(semantic; high)_: Unlike mainnet (1 tx can change `block.number`), many Arbitrum transactions share the same `block.number`. This breaks assumptions like "different block = different transaction". Look for: `require(block.number > lastBlock)` for uniqueness checks. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor

- [ ] **[EVM-CHAIN-003] `block.basefee` returns L1 basefee on Arbitrum** _(exploit-pattern; medium)_: Use `ArbGasInfo.getL1BaseFeeEstimate()` for L1 fees, and `ArbGasInfo` precompile methods for L2 gas prices. Look for: `block.basefee` used for gas calculations on Arbitrum. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor
  - **Notes:** ### Sequencer & Retryable Tickets

- [ ] **[EVM-CHAIN-004] Sequencer downtime = stale oracle prices + delayed liquidations/auctions** _(exploit-pattern; medium)_: When the sequencer is down, no new transactions execute. When it resumes, oracle prices are stale, positions may have gone deeply underwater, and auctions started immediately after restart can give the first bidder an unfair catch-up window. Check the Chainlink sequencer uptime feed and apply grace periods before liquidation or auction start. Look for: L2 liquidation or auction paths without sequencer uptime and restart-grace checks. [multichain-auditor, beirao ARB-02]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor, beirao ARB-02

- [ ] **[EVM-CHAIN-005] Retryable ticket auto-redeem failure** _(exploit-pattern; medium)_: If a retryable ticket's auto-redeem fails (insufficient gas), it must be manually redeemed within 7 days or funds are permanently lost. Look for: L1→L2 message passing that assumes auto-redemption always succeeds. [Arbitrum docs]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Arbitrum docs

- [ ] **[EVM-CHAIN-006] L2→L1 message delay is 7+ days** _(exploit-pattern; medium)_: Withdrawals and messages from Arbitrum to L1 are subject to the challenge period (~7 days). Protocols that need faster finality should use a bridge/liquidity network. Look for: UX flows that assume fast L2→L1 message delivery. [Arbitrum docs]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Arbitrum docs
  - **Notes:** ### Address Aliasing

- [ ] **[EVM-CHAIN-007] L1→L2 msg.sender is aliased** _(exploit-pattern; medium)_: When an L1 contract sends a message to L2, the `msg.sender` on L2 is `L1_address + 0x1111000000000000000000000000000000001111`. If access control on L2 checks the raw L1 address, it will ALWAYS fail. Must un-alias the sender. Look for: L1→L2 access control that compares `msg.sender` directly with an L1 contract address. [multichain-auditor, beirao ARB-03]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor, beirao ARB-03

## Optimism / Base / OP Stack

- [ ] **[EVM-CHAIN-008] `block.number` is L2 block number** _(semantic; high)_: Unlike Arbitrum, Optimism returns the L2 block number from `block.number`. But L2 blocks on OP stack are produced every 2 seconds, not 12. Code calibrated for mainnet block times will run 6x faster. Look for: block-number-based timing with mainnet assumptions on OP Stack chains. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor

- [ ] **[EVM-CHAIN-009] L1 data fees** _(exploit-pattern; medium)_: Transactions on OP Stack pay both L2 execution gas AND L1 data posting gas. The L1 portion can be 90%+ of total cost. Protocols must account for this in gas estimation. Look for: gas estimation using only `gasleft()` without L1 data fee component. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor

- [ ] **[EVM-CHAIN-010] No `prevrandao` / `difficulty`** _(exploit-pattern; medium)_: On OP Stack L2s, `block.prevrandao` (formerly `block.difficulty`) returns a fixed value. It's NOT random. Look for: `block.prevrandao` or `block.difficulty` used as randomness source. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor

## zkSync Era

- [ ] **[EVM-CHAIN-011] `msg.sender == tx.origin` is not an EOA proof on L2s** _(exploit-pattern; medium)_: zkSync Era has native account abstraction, and L2 message paths on other stacks can also make `tx.origin == msg.sender` appear true for a contract-originated action. This breaks EOA-only checks. Look for: `require(msg.sender == tx.origin)` as a contract-blocking mechanism on any supported L2. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor

- [ ] **[EVM-CHAIN-012] `EXTCODESIZE` returns 0 for non-EVM contracts** _(exploit-pattern; medium)_: zkSync has system contracts and native AA accounts that are contracts but return 0 for `extcodesize`. Look for: `extcodesize`-based contract detection. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor

- [ ] **[EVM-CHAIN-013] Different CREATE/CREATE2 address derivation** _(exploit-pattern; medium)_: zkSync uses a different formula for CREATE/CREATE2 addresses than EVM. Counterfactual addresses computed using the EVM formula will be wrong. Look for: off-chain address pre-computation using standard EVM CREATE2 formula. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor

- [ ] **[EVM-CHAIN-014] Opcode support and SELFDESTRUCT semantics are chain- and fork-specific** _(semantic; high)_: Do not assume that an opcode's availability or behavior is identical across EVM-compatible chains. In particular, SELFDESTRUCT behavior depends on the chain's adopted fork rules, while custom execution environments may differ in supported opcodes or precompiles.
  - **Trigger:** The contract uses an opcode whose support or semantics may differ on the declared target chain.
  - **Risk:** A deployment that relies on unsupported or differently specified opcode behavior can fail or violate a code/lifecycle invariant.
  - **Detection:** Compare the bytecode and opcode behavior with the target chain's documented fork and execution environment.
  - **FP:** The target chain explicitly supports the opcode and the implementation's assumptions match its documented semantics.
  - **Proof:** Execute the relevant opcode path against the target chain or a matching fork and record the observed result.
  - **Provenance:** multichain-auditor; [EIP-6780 SELFDESTRUCT](https://eips.ethereum.org/EIPS/eip-6780)

- [ ] **[EVM-CHAIN-015] No `receive()` / `fallback()` for ETH transfers** _(exploit-pattern; medium)_: On zkSync, receiving ETH may require explicit function handling. The default receive/fallback may not work as expected for system-level transfers. Look for: contracts expecting ETH via `receive()` on zkSync. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor

## Blast

- [ ] **[EVM-CHAIN-016] Native yield accrual on ETH balances** _(exploit-pattern; medium)_: On Blast, ETH held by contracts automatically earns yield. If a contract's logic depends on `address(this).balance` being stable, the balance will drift upward. Look for: precise balance checks like `require(address(this).balance == expectedAmount)`. [Blast docs]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Blast docs

- [ ] **[EVM-CHAIN-017] USDB/WETH rebasing** _(exploit-pattern; medium)_: Blast-native tokens (USDB, WETH) are rebasing by default. Protocols that assume stable balances will have accounting errors. Opt for non-rebasing mode via `IERC20Rebasing(token).configure(YieldMode.CLAIMABLE)` or `YieldMode.VOID`. Look for: Blast deployments using USDB/WETH without configuring yield mode. [Blast docs]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Blast docs

- [ ] **[EVM-CHAIN-018] Gas refund claim** _(exploit-pattern; medium)_: Blast refunds gas fees to contracts. If the contract doesn't implement yield/gas claiming, the refund is stuck. Look for: Blast contracts without `IBlast.claimAllGas()` functionality. [Blast docs]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Blast docs

## BNB Chain (BSC)

- [ ] **[EVM-CHAIN-019] BNB token quirks** _(exploit-pattern; medium)_: BNB reverts on `approve(addr, 0)` but requires approval reset for USDT pattern. There's no universal approve pattern that works for both BNB and USDT. Look for: generic approve-to-zero patterns on BSC. [weird-erc20]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** weird-erc20

- [ ] **[EVM-CHAIN-020] 3-second block times** _(exploit-pattern; medium)_: BSC produces blocks every 3 seconds. Block-number-based timing runs 4x faster than Ethereum mainnet. Look for: block-count timing calibrated for 12-second blocks. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor

- [ ] **[EVM-CHAIN-021] Precompile addresses differ across chains** _(exploit-pattern; medium)_: BSC and other chains may add or relocate precompiles, so a hardcoded address can call an empty account or different contract. Look for: precompile address assumptions in multi-chain deployments. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor

## Polygon

- [ ] **[EVM-CHAIN-022] MATIC → POL migration** _(exploit-pattern; medium)_: MATIC is being replaced by POL as the native gas token. Protocols hardcoding WMATIC addresses or assuming MATIC will need updates. Look for: hardcoded MATIC/WMATIC addresses. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor

- [ ] **[EVM-CHAIN-023] Reorgs are more common** _(exploit-pattern; medium)_: Polygon has more frequent chain reorganizations than Ethereum mainnet. Protocols that rely on block finality with fewer confirmations are at risk. Look for: single-block confirmation assumptions. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor

- [ ] **[EVM-CHAIN-024] USDT on Polygon returns bool (unlike Ethereum)** _(exploit-pattern; medium)_: Ethereum USDT has no return value; Polygon USDT returns bool. SafeERC20 handles both, but custom transfer wrappers may not. Look for: custom token interaction code that assumes no return value. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor

## General L2 Considerations

- [ ] **[EVM-CHAIN-026] EIP-1559 parameters differ** _(exploit-pattern; medium)_: Each chain has its own base fee calculation, fee markets, and priority fee handling. Hardcoded gas parameters from mainnet will be wrong. Look for: hardcoded gas prices, base fee assumptions, or priority fee calculations. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor

- [ ] **[EVM-CHAIN-027] Bridged token addresses differ** _(exploit-pattern; medium)_: USDC on Ethereum ≠ USDC on Arbitrum ≠ USDC on Optimism. Each is a different contract address. Native USDC vs bridged USDC.e are completely different contracts. Look for: hardcoded token addresses in multi-chain config. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor

- [ ] **[EVM-CHAIN-028] Pre-deployed contract addresses may differ** _(exploit-pattern; medium)_: OpenZeppelin's `Create2` library, Gnosis Safe singleton, Uniswap factories — their addresses may vary across chains. Look for: hardcoded infrastructure contract addresses. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor

- [ ] **[EVM-CHAIN-029] `block.chainid` must be checked dynamically** _(exploit-pattern; medium)_: After hard forks, `block.chainid` changes. If cached at deploy time and used for signatures, the cached value is wrong on one fork. Look for: `immutable CHAIN_ID` set in constructor vs runtime `block.chainid` check. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor

## Arbitrum Deep Dive (Expanded from Arbitrum Checklist)

- [ ] **[EVM-CHAIN-030] Chainlink price feed staleness thresholds differ on Arbitrum** _(exploit-pattern; medium)_: LINK/ETH feed has 24h heartbeat with 18 decimals, while LINK/USD has 1h heartbeat with 8 decimals. Wrong threshold = stale prices accepted. Look for: hardcoded staleness thresholds or decimal values that don't match the specific Arbitrum feed. [Arbitrum Checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Arbitrum Checklist

- [ ] **[EVM-CHAIN-031] Chainlink minAnswer/maxAnswer on Arbitrum feeds** _(exploit-pattern; medium)_: ETH/USD limited to [$10, $1M], USDC/USD limited to [$0.01, $1000], USDT/USD limited to [$0.01, $1000]. During flash crashes or extreme events, the feed returns min/max instead of real price. Look for: Chainlink integrations without checking `answer > minAnswer && answer < maxAnswer`. [Arbitrum Checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** $10, $1M; $0.01, $1000; Arbitrum Checklist

- [ ] **[EVM-CHAIN-032] Orbit chains with custom fee tokens** _(semantic; high)_: Orbit chains (L3s built on Arbitrum) can use any ERC20 as the fee token instead of ETH. If the fee token has non-18 decimals (e.g., USDC = 6), amounts are scaled between L1 decimals and L2 native currency (18 decimals). Rounding losses occur during conversion. Look for: Orbit chain integrations assuming ETH-denominated fees. [Arbitrum Checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Arbitrum Checklist

- [ ] **[EVM-CHAIN-033] Retryable ticket parameters use mixed denominations on Orbit** _(exploit-pattern; medium)_: `tokenTotalFeeAmount` uses the fee token's decimals (e.g., 6 for USDC), but `l2CallValue`, `maxSubmissionCost`, and `maxFeePerGas` use 18-decimal native currency denomination. Mixing these causes incorrect fee calculations. Look for: retryable ticket creation on Orbit chains where parameters aren't properly denominated. [Arbitrum Checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Arbitrum Checklist

## Multichain Deployment Gotchas (Expanded from Multichain-Auditor)

- [ ] **[EVM-CHAIN-034] `transfer()` and `send()` fail on chains with different gas costs** _(exploit-pattern; medium)_: These forward 2300 gas, which may not be enough on chains with different gas pricing (zkSync Era). Use `.call{value: amount}("")` instead. Look for: `.transfer()` or `.send()` in multichain contracts. [multichain-auditor, beirao MC-04]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor, beirao MC-04

- [ ] **[EVM-CHAIN-035] Frontrunning impossible on some L2s but trivial on others** _(exploit-pattern; medium)_: Optimism has a private mempool making frontrunning very difficult. Polygon has a public mempool making it cheap. Threat models must be chain-specific. Look for: frontrunning protections assumed unnecessary based on single-chain behavior. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor

- [ ] **[EVM-CHAIN-036] Hardcoded WETH/token addresses invalid across chains** _(exploit-pattern; medium)_: WETH is 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 on Ethereum but 0x7ceb23fd6bc0add59e62ac25578270cff1b9f619 on Polygon. Look for: any hardcoded contract address that's assumed same across chains. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor

- [ ] **[EVM-CHAIN-037] zkSync ERA has fundamentally different opcode behavior** _(semantic; high)_: CREATE, CREATE2, CALL, STATICCALL, DELEGATECALL, MSTORE, MLOAD, CALLDATALOAD, CALLDATACOPY all behave differently on zkSync. Direct EVM contract deployment often fails. Look for: contracts deployed to zkSync without ERA-specific adaptation. [multichain-auditor, beirao MC-11]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor, beirao MC-11

- [ ] **[EVM-CHAIN-038] XDai/Gnosis chain token contracts have callbacks** _(exploit-pattern; medium)_: On Gnosis chain, USDC/WBTC/WETH had post-transfer callbacks unlike their Ethereum counterparts. This enabled reentrancy attacks and led to a chain hard fork. Look for: same-name tokens assumed to behave identically across chains. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor

## Supplemental Attack Vectors (SAS-AV)

- [ ] **[EVM-CHAIN-039] L2 Sequencer Downtime in Interest Accrual** _(exploit-pattern; medium)_: Interest rate calculations use `block.timestamp` delta without accounting for L2 sequencer downtime periods. If sequencer is down for hours, the first post-restart block has a massive timestamp gap, compounding interest as if the protocol was operating normally.
  - **FP:** Interest accrual capped per-update (`maxTimeDelta`). Sequencer uptime feed checked before accruing. Rate-limited compounding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-130](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-186
