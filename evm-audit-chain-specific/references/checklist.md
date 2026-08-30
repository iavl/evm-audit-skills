<!-- GENERATED FILE: source is ../../data/canonical-checks.json; do not edit by hand. -->
# Chain-Specific Security Checklist

Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.
Global FP/proof obligations live in the Review Contract; only check-specific gates and proofs are repeated below.

## Compiler & EVM Version Quirks

- [ ] **[EVM-ASM-025] `PUSH0` availability depends on compiler target and chain fork**: Shared canonical check; apply the primary definition and evidence requirements for `evm-audit-assembly`.

## Arbitrum

- [ ] **[EVM-CHAIN-001] `block.number` returns L1 block number on Arbitrum** _(semantic; high)_: On Arbitrum, `block.number` returns the approximate L1 block number, not the L2 block number; it can update in jumps and has much lower short-term resolution than expected. Use the Arbitrum system contract for L2 block number when required. Look for: `block.number` used for timing, deadlines, uniqueness, or block-frequency calculations on Arbitrum. [multichain-auditor, beirao ARB-01, Arbitrum Checklist]
  - **Provenance:** multichain-auditor, beirao ARB-01, Arbitrum Checklist; [Arbitrum block numbers and time](https://docs.arbitrum.io/arbitrum-essentials/arbitrum-vs-ethereum/block-numbers-and-time)

- [ ] **[EVM-CHAIN-002] Multiple L2 transactions per L1 block** _(semantic; high)_: Unlike mainnet (1 tx can change `block.number`), many Arbitrum transactions share the same `block.number`. This breaks assumptions like "different block = different transaction". Look for: `require(block.number > lastBlock)` for uniqueness checks. [multichain-auditor]
  - **Provenance:** multichain-auditor; [Arbitrum block numbers and time](https://docs.arbitrum.io/arbitrum-essentials/arbitrum-vs-ethereum/block-numbers-and-time)

- [ ] **[EVM-CHAIN-003] Arbitrum L2 base fee and parent-chain data fee are separate** _(exploit-pattern; medium)_: On Arbitrum, the child-chain base fee used for L2 execution is distinct from the estimated parent-chain base fee used for data-posting costs. Use NodeInterface or ArbGasInfo components rather than treating `block.basefee` as the L1 base fee.
  - **Trigger:** Arbitrum code uses `block.basefee` as an L1 data-price input or assumes one base-fee value covers both components.
  - **Risk:** Conflating the two fee components produces incorrect gas estimation, reimbursement, or fee caps.
  - **Detection:** Trace each fee variable to its documented L2 execution or parent-chain posting component and verify units before combining them.
  - **Specific FP:** The formula intentionally consumes the child-chain base fee and obtains parent-chain components from the documented interface.
  - **Specific proof:** Compare the contract's computed fee with NodeInterface or ArbGasInfo component values for the same transaction.
  - **Provenance:** multichain-auditor; [Arbitrum gas and fees](https://docs.arbitrum.io/how-arbitrum-works/deep-dives/gas-and-fees)
  - **Notes:** ### Sequencer & Retryable Tickets

- [ ] **[EVM-CHAIN-004] Gate L2 liquidations and auctions on sequencer status and recovery** _(exploit-pattern; medium)_: A sequencer outage can prevent timely user and keeper transactions while external markets continue moving. On recovery, stale state and queued actions can make immediate liquidations or auctions unsafe. Use the target network's supported uptime signal and a documented recovery grace period when the protocol depends on continuous sequencing.
  - **Trigger:** An L2 liquidation, auction, or time-sensitive keeper path assumes continuous sequencer availability.
  - **Risk:** Outage and recovery can concentrate stale liquidations, auctions, or keeper actions into the first executable blocks and violate assumptions about timely intervention.
  - **Detection:** Trace the target chain's sequencer status signal, recovery behavior, oracle updates, and the first executable liquidation or auction after recovery.
  - **Specific FP:** The target has no centralized sequencer dependency, or the operation remains safe under a bounded outage and documented recovery procedure.
  - **Specific proof:** Simulate an outage and recovery with adverse external price movement and show whether the first executable actions preserve the protocol invariant.
  - **Provenance:** multichain-auditor, beirao ARB-02; [Chainlink L2 sequencer uptime feeds](https://docs.chain.link/data-feeds/l2-sequencer-feeds)

- [ ] **[EVM-CHAIN-005] Retryable ticket failure, expiry, and refunds require explicit handling** _(exploit-pattern; medium)_: An Arbitrum retryable ticket can fail automatic redemption and require manual redemption before its configured lifetime expires. Expiry and refund destinations are part of the value-flow model; do not summarize every failed auto-redeem as permanent fund loss.
  - **Trigger:** A parent-to-child flow assumes auto-redemption always succeeds or does not track the ticket lifecycle and refund addresses.
  - **Risk:** Ignoring retry, expiry, and refund ownership can leave messages unexecuted or make refunds inaccessible to the intended party.
  - **Detection:** Trace ticket creation, auto-redeem status, manual redemption, lifetime extension, expiry, and both refund addresses.
  - **Specific FP:** The integration monitors the complete lifecycle and proves that execution or refunds remain recoverable by the intended owner.
  - **Specific proof:** Force auto-redemption failure and record the manual redemption and expiry/refund outcomes on the target Arbitrum configuration.
  - **Provenance:** Arbitrum docs; [Arbitrum parent-to-child messaging](https://docs.arbitrum.io/how-arbitrum-works/deep-dives/l1-to-l2-messaging)

- [ ] **[EVM-CHAIN-006] Arbitrum L2-to-L1 delay is deployment- and bridge-specific** _(exploit-pattern; medium)_: Arbitrum withdrawals and L2-to-L1 messages can be subject to a configured challenge or finality period; the historical Arbitrum One window is commonly described as about a week. Do not hardcode a universal seven-day value across Arbitrum chains or bridge providers.
  - **Trigger:** A protocol treats an Arbitrum L2-to-L1 message as finalized after a hardcoded duration or without reading the bridge state.
  - **Risk:** Assuming a shorter or fixed finality period can release funds or advance state before the selected bridge's security window has elapsed.
  - **Detection:** Resolve the exact chain, bridge, challenge configuration, and finality signal used by the withdrawal path.
  - **Specific FP:** The integration consumes the bridge's current finality state and separately handles configured expiry and retry behavior.
  - **Specific proof:** Measure the message lifecycle on the declared chain and bridge and compare the release condition with the configured finality requirement.
  - **Provenance:** Arbitrum docs; [Arbitrum child-to-parent messaging](https://docs.arbitrum.io/how-arbitrum-works/deep-dives/l2-to-l1-messaging)
  - **Notes:** ### Address Aliasing

- [ ] **[EVM-CHAIN-007] L1→L2 msg.sender is aliased** _(exploit-pattern; medium)_: When an L1 contract sends a message to L2, the `msg.sender` on L2 is `L1_address + 0x1111000000000000000000000000000000001111`. If access control on L2 checks the raw L1 address, it will ALWAYS fail. Must un-alias the sender. Look for: L1→L2 access control that compares `msg.sender` directly with an L1 contract address. [multichain-auditor, beirao ARB-03]
  - **Provenance:** multichain-auditor, beirao ARB-03; [Arbitrum parent-to-child messaging](https://docs.arbitrum.io/how-arbitrum-works/deep-dives/l1-to-l2-messaging)

## Optimism / Base / OP Stack

- [ ] **[EVM-CHAIN-008] OP Stack `block.number` is an L2 block number with deployment-specific cadence** _(semantic; high)_: On OP Stack chains, `block.number` identifies the L2 block. Do not convert L2 block counts to elapsed time using an Ethereum or historically observed OP cadence; protocol upgrades and chain configuration can change block production behavior.
  - **Trigger:** Time-sensitive logic on an OP Stack deployment derives elapsed time from `block.number` deltas.
  - **Risk:** Block-count deadlines, accrual, and cooldowns can run for the wrong wall-clock duration when calibrated to a fixed cadence.
  - **Detection:** Identify every block-count-to-time conversion and compare it with the target deployment's current documented cadence and upgrade policy.
  - **Specific FP:** The logic intentionally measures L2 blocks rather than elapsed time, or uses timestamp-based bounds with documented drift assumptions.
  - **Specific proof:** Run the logic against the declared OP Stack deployment parameters and show the resulting wall-clock window across relevant upgrades.
  - **Provenance:** multichain-auditor; [OP Stack opcode differences](https://docs.optimism.io/op-stack/protocol/differences)

- [ ] **[EVM-CHAIN-009] OP Stack execution and L1 data fees are separate components** _(exploit-pattern; medium)_: OP Stack transactions account for L2 execution gas and an L1 data-posting component whose formula and parameters are deployment-specific. Do not use a fixed percentage or `gasleft()` alone to estimate the total fee.
  - **Trigger:** Gas accounting on OP Stack derives a total cost solely from L2 execution gas or a historical percentage of the total.
  - **Risk:** Ignoring or mispricing the parent-chain component can underfund relayed calls, misallocate reimbursements, or make a supposedly bounded operation fail.
  - **Detection:** Trace the Gas Price Oracle or equivalent fee parameters and verify units, compression, and the target chain's current formula.
  - **Specific FP:** The integration uses the chain's documented fee oracle or RPC estimate for the exact transaction payload.
  - **Specific proof:** Compare the implementation's estimate with the target chain's fee components for representative calldata sizes and parameter changes.
  - **Provenance:** multichain-auditor; [OP Stack transaction fees](https://docs.optimism.io/stack/transactions/fees)

- [ ] **[EVM-CHAIN-010] OP Stack PREVRANDAO reflects the current L1 origin** _(exploit-pattern; medium)_: On OP Stack, `block.prevrandao` returns the PREVRANDAO value from the current L1 origin block rather than an independently generated per-L2-block randomness source. Do not assume that it provides fresh entropy for every L2 block.
  - **Trigger:** An OP Stack deployment uses `block.prevrandao` or `block.difficulty` for randomness, uniqueness, lotteries, or commit selection.
  - **Risk:** Several L2 blocks can inherit the same or predictably related L1-origin value, breaking uniqueness or randomness assumptions.
  - **Detection:** Trace the L1 origin used by each relevant L2 block and determine whether repeated or known PREVRANDAO values let an actor influence the outcome.
  - **Specific FP:** The value is mixed with an independent, manipulation-resistant randomness source and no per-L2-block entropy assumption remains.
  - **Specific proof:** Demonstrate repeated L1-origin PREVRANDAO across the relevant L2 sequence or prove that independent entropy preserves the security invariant.
  - **Provenance:** multichain-auditor; [OP Stack opcode differences](https://docs.optimism.io/op-stack/protocol/differences)

## zkSync Era

- [ ] **[EVM-CHAIN-011] `msg.sender == tx.origin` is not an EOA proof on L2s** _(exploit-pattern; medium)_: zkSync Era has native account abstraction, and L2 message paths on other stacks can also make `tx.origin == msg.sender` appear true for a contract-originated action. This breaks EOA-only checks. Look for: `require(msg.sender == tx.origin)` as a contract-blocking mechanism on any supported L2. [multichain-auditor]
  - **Provenance:** multichain-auditor; [ZKsync native account abstraction](https://docs.zksync.io/zksync-protocol/account-abstraction)

- [ ] **[EVM-CHAIN-012] `EXTCODESIZE` returns 0 for non-EVM contracts** _(exploit-pattern; medium)_: zkSync has system contracts and native AA accounts that are contracts but return 0 for `extcodesize`. Look for: `extcodesize`-based contract detection. [multichain-auditor]
  - **Provenance:** multichain-auditor; [ZKsync Era EVM instruction differences](https://docs.zksync.io/zksync-protocol/era-vm/differences/evm-instructions)

- [ ] **[EVM-CHAIN-013] ZKsync contract-address derivation depends on the execution environment** _(exploit-pattern; medium)_: Native EraVM and ContractDeployer deployments use ZKsync-specific CREATE/CREATE2 derivation. EVM-bytecode contracts executed through the EVM Bytecode Interpreter use Ethereum-compatible CREATE/CREATE2 address derivation. Determine the deployed bytecode and runtime before flagging counterfactual-address logic.
  - **Trigger:** Code computes, predicts, validates, or authorizes a contract address for a ZKsync deployment.
  - **Risk:** Applying the Ethereum formula to native EraVM deployment, or the EraVM formula to EVM-interpreter deployment, yields the wrong counterfactual address.
  - **Detection:** Determine whether the deployed artifact is native EraVM bytecode or EVM bytecode, then compare its CREATE/CREATE2 calculation with the matching documented derivation.
  - **Specific FP:** The runtime is identified and the address formula matches that execution environment.
  - **Specific proof:** Deploy the exact artifact with the relevant CREATE/CREATE2 path and compare the observed address with the predicted address.
  - **Provenance:** multichain-auditor; [ZKsync Era EVM instruction differences](https://docs.zksync.io/zksync-protocol/era-vm/differences/evm-instructions); [ZKsync EVM Interpreter contract deployment](https://docs.zksync.io/zksync-protocol/era-vm/evm-interpreter/deployment-execution)

- [ ] **[EVM-CHAIN-014] Opcode support and SELFDESTRUCT semantics are chain- and fork-specific** _(semantic; high)_: Do not assume that an opcode's availability or behavior is identical across EVM-compatible chains. In particular, SELFDESTRUCT behavior depends on the chain's adopted fork rules, while custom execution environments may differ in supported opcodes or precompiles.
  - **Trigger:** The contract uses an opcode whose support or semantics may differ on the declared target chain.
  - **Risk:** A deployment that relies on unsupported or differently specified opcode behavior can fail or violate a code/lifecycle invariant.
  - **Detection:** Compare the bytecode and opcode behavior with the target chain's documented fork and execution environment.
  - **Specific FP:** The target chain explicitly supports the opcode and the implementation's assumptions match its documented semantics.
  - **Specific proof:** Execute the relevant opcode path against the target chain or a matching fork and record the observed result.
  - **Provenance:** multichain-auditor; [EIP-6780 SELFDESTRUCT](https://eips.ethereum.org/EIPS/eip-6780)

- [ ] **[EVM-CHAIN-015] Native-value reception paths are chain- and system-contract-specific** _(exploit-pattern; medium)_: Native-value delivery on zkSync and other execution environments can involve system contracts, account abstraction, or bridge-specific paths. Do not assume that a Solidity `receive()` or `fallback()` path is the only way funds arrive or that it has identical behavior on every chain.
  - **Trigger:** A multichain contract assumes all native ETH/POL/ETH-like value arrives through one ordinary EVM entry point.
  - **Risk:** A missing or misclassified reception path can strand native value, bypass accounting, or make a bridge callback fail.
  - **Detection:** Enumerate direct calls, system-contract transfers, bridge callbacks, and account-abstraction paths on the declared deployment.
  - **Specific FP:** The target environment documents the exact reception path and the contract accounts for every reachable native-value source.
  - **Specific proof:** Execute each documented value-delivery path and compare balances, events, and accounting state with the intended invariant.
  - **Provenance:** multichain-auditor

## Blast

- [ ] **[EVM-CHAIN-016] Blast contract ETH yield depends on the configured yield mode** _(exploit-pattern; medium)_: Blast smart contracts default to Void yield, so their ETH balance does not rebase. A contract balance grows only after configuring Automatic yield; Claimable mode accrues yield separately. Accounting and governor logic must match the configured mode rather than assuming every contract balance grows.
  - **Trigger:** A Blast deployment relies on ETH yield, stable native balances, or asynchronous yield claims.
  - **Risk:** Accounting can drift or promised yield can disappear when the implementation assumes a different ETH yield mode than the deployed configuration.
  - **Detection:** Read the deployed contract's yield mode and governor, then trace whether accounting uses rebasing balances or separately claimable yield.
  - **Specific FP:** The deployment remains in Void mode and assumes no yield, or its accounting and access control explicitly implement the selected mode.
  - **Specific proof:** Exercise Void, Automatic, and Claimable configurations and show that balance and claim accounting match the selected mode.
  - **Provenance:** Blast docs; [Blast ETH yield modes](https://docs.blast.io/building/guides/eth-yield)

- [ ] **[EVM-CHAIN-017] USDB/WETH rebasing** _(exploit-pattern; medium)_: Blast-native tokens (USDB, WETH) are rebasing by default. Protocols that assume stable balances will have accounting errors. Opt for non-rebasing mode via `IERC20Rebasing(token).configure(YieldMode.CLAIMABLE)` or `YieldMode.VOID`. Look for: Blast deployments using USDB/WETH without configuring yield mode. [Blast docs]
  - **Provenance:** Blast docs; [Blast WETH and USDB yield modes](https://docs.blast.io/building/guides/weth-yield)

- [ ] **[EVM-CHAIN-018] Blast gas fees require claimable mode and deliberate governor control** _(exploit-pattern; medium)_: Blast contracts default to Void gas mode, which leaves fees with the sequencer operator. Gas fees are claimable only after configuring Claimable mode, and the governor controls configuration and claims. Treat unclaimed gas as an optional revenue decision, not automatically stuck protocol funds.
  - **Trigger:** A Blast deployment promises gas-fee revenue or exposes gas-mode and governor configuration.
  - **Risk:** A mismatched gas mode or governor can invalidate promised revenue or give an unintended party control over gas-fee claims.
  - **Detection:** Inspect gas mode, governor assignment, claim authorization, recipient selection, and whether the product actually promises gas revenue.
  - **Specific FP:** Void mode is intentional, or Claimable mode and governor permissions match the documented revenue policy.
  - **Specific proof:** Exercise configuration and claim paths from authorized and unauthorized callers and reconcile claimed value with the documented policy.
  - **Provenance:** Blast docs; [Blast gas modes](https://docs.blast.io/building/guides/gas-fees)

## BNB Chain (BSC)

- [ ] **[EVM-CHAIN-019] BEP-20 allowance behavior is token-specific** _(exploit-pattern; medium)_: BNB Smart Chain does not make all BEP-20 tokens share one allowance-reset behavior. Some deployed tokens may reject zero-to-nonzero or nonzero-to-nonzero approvals, so inspect the actual token instead of attributing a universal rule to BNB.
  - **Trigger:** A BSC integration applies one approval sequence to arbitrary BEP-20 tokens.
  - **Risk:** A generic approval wrapper can revert, strand funds, or leave an unexpected allowance when used with a token-specific implementation.
  - **Detection:** Inspect the deployed token bytecode and exercise zero, nonzero, and repeated approval transitions.
  - **Specific FP:** The token set is allowlisted and each allowance path is tested against its deployed implementation.
  - **Specific proof:** Run the wrapper against every supported token and record return data, reverts, and final allowance state.
  - **Provenance:** weird-erc20

- [ ] **[EVM-CHAIN-020] Do not hardcode BNB Chain block cadence** _(exploit-pattern; medium)_: BNB Smart Chain block cadence has changed across protocol upgrades. Time-sensitive logic must not hardcode a historical block interval; use timestamp-based constraints or deployment-specific documented parameters when the operation truly depends on elapsed time.
  - **Trigger:** A BNB Chain deployment converts blocks to seconds or embeds a fixed number of blocks for a wall-clock requirement.
  - **Risk:** A later network upgrade can shorten or lengthen block-count-based windows, changing cooldowns, auctions, rewards, or governance timing without a contract change.
  - **Detection:** Locate fixed block-time constants and compare the intended duration with current BNB Chain documentation and the deployment's upgrade assumptions.
  - **Specific FP:** The invariant is explicitly block-count based, or elapsed-time logic uses timestamps with documented tolerance.
  - **Specific proof:** Calculate the effective window under the current and at least one historical cadence and show whether the security requirement still holds.
  - **Provenance:** multichain-auditor; [BNB Smart Chain introduction](https://docs.bnbchain.org/bnb-smart-chain/introduction/)

- [ ] **[EVM-CHAIN-021] Precompile addresses differ across chains** _(exploit-pattern; medium)_: BSC and other chains may add or relocate precompiles, so a hardcoded address can call an empty account or different contract. Look for: precompile address assumptions in multi-chain deployments. [multichain-auditor]
  - **Provenance:** multichain-auditor

## Polygon

- [ ] **[EVM-CHAIN-022] Polygon PoS native gas token is POL** _(exploit-pattern; medium)_: Polygon PoS has migrated its native gas and staking token from MATIC to POL. Integrations must distinguish native POL, POL on Ethereum, legacy MATIC, and wrapped or bridged token contracts instead of treating the migration as pending.
  - **Trigger:** A Polygon PoS integration hardcodes MATIC/WMATIC symbols, addresses, bridge behavior, or migration-state branches.
  - **Risk:** Stale symbols, addresses, bridge assumptions, or accounting branches can route funds incorrectly or reject the current native asset.
  - **Detection:** Trace native and ERC-20 asset identifiers on every supported chain and verify current POL bridge and wrapping behavior against the deployed contracts.
  - **Specific FP:** The integration intentionally supports a legacy Ethereum-side MATIC migration path and separately handles Polygon PoS native POL.
  - **Specific proof:** Exercise native and token paths on the declared Polygon deployment and show that every address, symbol, and accounting branch resolves to the intended asset.
  - **Provenance:** multichain-auditor; [Polygon POL documentation](https://docs.polygon.technology/pos/concepts/tokens/pol)

- [ ] **[EVM-CHAIN-023] Confirmation depth and reorg risk are chain-specific** _(exploit-pattern; medium)_: Reorganization frequency, finality signals, validator/sequencer behavior, and confirmation recommendations differ across chains and deployments. Do not label one chain universally more or less reorganizable than another without a declared observation window and finality model.
  - **Trigger:** A bridge, indexer, or protocol uses one hardcoded confirmation depth across chains.
  - **Risk:** A fixed confirmation count can accept reversible state or delay safe settlement beyond the intended liveness bound.
  - **Detection:** Document the target chain's probabilistic/economic finality and use its finalized tag or deployment-specific threshold where available.
  - **Specific FP:** The operation waits for the documented finality signal and handles reorg/replay recovery.
  - **Specific proof:** Simulate a reorg or delayed finality event and verify that the state transition remains safe and recoverable.
  - **Provenance:** multichain-auditor

- [ ] **[EVM-CHAIN-024] Token return conventions are deployment-specific on Polygon** _(exploit-pattern; medium)_: A token's return-data convention is a property of the deployed token contract, not a guaranteed consequence of its chain or symbol. Polygon deployments can include tokens and proxies whose transfer methods return data, omit it, or change through upgrades.
  - **Trigger:** A Polygon integration branches on a token symbol or chain rather than handling the deployed call's return-data convention.
  - **Risk:** A wrapper that assumes one return shape can treat a failed transfer as success or revert on a valid token implementation.
  - **Detection:** Inspect the exact token implementation and use a wrapper with an explicit success and return-data policy.
  - **Specific FP:** The supported token addresses are immutable and their return behavior is covered by integration tests.
  - **Specific proof:** Call transfer and transferFrom against each supported deployment and verify state deltas for empty, boolean, and malformed return data.
  - **Provenance:** multichain-auditor

## General L2 Considerations

- [ ] **[EVM-CHAIN-026] EIP-1559 parameters differ** _(exploit-pattern; medium)_: Each chain has its own base fee calculation, fee markets, and priority fee handling. Hardcoded gas parameters from mainnet will be wrong. Look for: hardcoded gas prices, base fee assumptions, or priority fee calculations. [multichain-auditor]
  - **Provenance:** multichain-auditor; [EIP-1559 fee market](https://eips.ethereum.org/EIPS/eip-1559)

- [ ] **[EVM-CHAIN-027] Bridged token addresses differ** _(exploit-pattern; medium)_: USDC on Ethereum ≠ USDC on Arbitrum ≠ USDC on Optimism. Each is a different contract address. Native USDC vs bridged USDC.e are completely different contracts. Look for: hardcoded token addresses in multi-chain config. [multichain-auditor]
  - **Provenance:** multichain-auditor

- [ ] **[EVM-CHAIN-028] Pre-deployed contract addresses may differ** _(exploit-pattern; medium)_: OpenZeppelin's `Create2` library, Gnosis Safe singleton, Uniswap factories — their addresses may vary across chains. Look for: hardcoded infrastructure contract addresses. [multichain-auditor]
  - **Provenance:** multichain-auditor

- [ ] **[EVM-CHAIN-029] Signature domains must handle a possible chain ID change** _(exploit-pattern; medium)_: `block.chainid` exposes the current chain ID. A contentious split or governance decision can change chain identity; a cached EIP-712 domain separator must either be intentionally fixed or rebuilt when the runtime chain ID differs. Ordinary hard forks do not inherently change the chain ID.
  - **Trigger:** A signature domain caches the deployment chain ID without defining behavior for a later runtime mismatch.
  - **Risk:** A stale cached chain ID can enable cross-fork replay or invalidate signatures after a chain identity change.
  - **Detection:** Compare cached and runtime chain IDs in the signing and verification paths and document the intended fork/replay policy.
  - **Specific FP:** The domain separator is recomputed on mismatch, or the protocol intentionally pins one chain identity and safely rejects the other.
  - **Specific proof:** Simulate a chain ID mismatch and show whether signatures replay, fail safely, or rebuild the expected domain.
  - **Provenance:** multichain-auditor; [EIP-1344 ChainID opcode](https://eips.ethereum.org/EIPS/eip-1344)

## Arbitrum Deep Dive (Expanded from Arbitrum Checklist)

- [ ] **[EVM-CHAIN-030] Chainlink feed heartbeat and staleness are feed-specific** _(exploit-pattern; medium)_: Chainlink heartbeat, deviation threshold, decimals, and sequencer behavior are properties of the selected feed and deployment. Do not copy a historical Arbitrum heartbeat or decimal value into another feed or assume it remains unchanged.
  - **Trigger:** An integration hardcodes one Chainlink freshness interval or decimal scale for multiple chains or feeds.
  - **Risk:** A fixed threshold can accept stale prices or reject fresh ones, distorting collateral, liquidation, or settlement logic.
  - **Detection:** Read the selected feed's current metadata and compare `updatedAt`, decimals, heartbeat, and deviation policy with the use case.
  - **Specific FP:** The feed address is allowlisted and its current parameters are validated at deployment and monitored for change.
  - **Specific proof:** Exercise the price path at the feed's heartbeat, deviation, and stale boundaries and verify the protocol's fail-safe behavior.
  - **Provenance:** Arbitrum Checklist; [Chainlink selecting data feeds](https://docs.chain.link/data-feeds/selecting-data-feeds)

- [ ] **[EVM-CHAIN-031] Chainlink answer bounds are feed- and deployment-specific** _(exploit-pattern; medium)_: Chainlink answer bounds and circuit-breaker configuration are feed-specific and may change with aggregator or proxy updates. Do not hardcode minAnswer/maxAnswer values from one Arbitrum feed; inspect the selected aggregator and define behavior for bounded or invalid answers.
  - **Trigger:** The protocol uses a Chainlink answer without reading or validating the selected feed's current bounds and status.
  - **Risk:** A stale bound can accept a clipped price, reject a valid extreme price, or make liquidation and solvency checks behave incorrectly.
  - **Detection:** Resolve the proxy and aggregator, inspect bounds and answer status, and test negative, zero, clipped, and extreme values.
  - **Specific FP:** The feed's current bounds are enforced by a trusted adapter with monitoring and an explicit fallback policy.
  - **Specific proof:** Inject or observe boundary answers on a fork and show the resulting accounting, liquidation, or pause behavior.
  - **Provenance:** $10, $1M; $0.01, $1000; Arbitrum Checklist; [Chainlink selecting data feeds](https://docs.chain.link/data-feeds/selecting-data-feeds)

- [ ] **[EVM-CHAIN-032] Orbit chains with custom fee tokens** _(semantic; high)_: Orbit chains (L3s built on Arbitrum) can use any ERC20 as the fee token instead of ETH. If the fee token has non-18 decimals (e.g., USDC = 6), amounts are scaled between L1 decimals and L2 native currency (18 decimals). Rounding losses occur during conversion. Look for: Orbit chain integrations assuming ETH-denominated fees. [Arbitrum Checklist]
  - **Provenance:** Arbitrum Checklist; [Arbitrum custom gas token chains](https://docs.arbitrum.io/arbitrum-essentials/bridging/custom-gas-token-chains)

- [ ] **[EVM-CHAIN-033] Retryable ticket parameters use mixed denominations on Orbit** _(exploit-pattern; medium)_: `tokenTotalFeeAmount` uses the fee token's decimals (e.g., 6 for USDC), but `l2CallValue`, `maxSubmissionCost`, and `maxFeePerGas` use 18-decimal native currency denomination. Mixing these causes incorrect fee calculations. Look for: retryable ticket creation on Orbit chains where parameters aren't properly denominated. [Arbitrum Checklist]
  - **Provenance:** Arbitrum Checklist; [Arbitrum custom gas token chains](https://docs.arbitrum.io/arbitrum-essentials/bridging/custom-gas-token-chains)

## Multichain Deployment Gotchas (Expanded from Multichain-Auditor)

- [ ] **[EVM-CHAIN-034] The 2300-gas stipend is not portable across execution environments** _(exploit-pattern; medium)_: Solidity `transfer()` and `send()` forward a fixed 2300-gas stipend. Whether that stipend is sufficient depends on the target chain's gas schedule and the recipient's execution path; use an explicit call pattern with checked success when portability is required.
  - **Trigger:** A multichain path relies on `transfer()` or `send()` for recipients whose fallback or receive logic may vary.
  - **Risk:** A recipient that needs more than the stipend can make withdrawals or callbacks fail, creating a denial of service or stuck funds.
  - **Detection:** Trace the recipient code, gas schedule, and failure handling on every target chain.
  - **Specific FP:** The recipient is code-free or intentionally stipend-compatible and failed sends are handled without corrupting state.
  - **Specific proof:** Execute the transfer against a recipient that consumes the target stipend and verify success handling and accounting rollback.
  - **Provenance:** multichain-auditor, beirao MC-04

- [ ] **[EVM-CHAIN-035] Transaction ordering and order-flow visibility are chain-specific** _(exploit-pattern; medium)_: Mempool visibility, sequencer policy, private order flow, forced inclusion, and proposer capabilities vary by chain and can change over time. Never classify front-running or ordering manipulation as impossible solely because one public mempool is absent.
  - **Trigger:** A protocol omits slippage, commit-reveal, or ordering defenses based on an assumed private or nonexistent mempool.
  - **Risk:** An incomplete ordering threat model can miss sequencer, builder, RPC, or delayed-inclusion strategies that reorder security-sensitive transactions.
  - **Detection:** Document every party that can observe, delay, insert, or reorder transactions on the target deployment and its fallback paths.
  - **Specific FP:** The invariant is order-independent or a deployment-specific mechanism cryptographically prevents the relevant ordering attack.
  - **Specific proof:** Construct the strongest ordering capability available to sequencers, builders, RPC operators, and users and test the protected operation.
  - **Provenance:** multichain-auditor

- [ ] **[EVM-CHAIN-036] Wrapped-native and token addresses are chain-specific** _(exploit-pattern; medium)_: Wrapped-native assets and token representations use deployment-specific addresses. Do not copy an Ethereum or historical Polygon WETH address into a multichain configuration; resolve and validate the address for each chain and environment.
  - **Trigger:** A multichain deployment embeds one wrapped-native or token address in shared logic or configuration.
  - **Risk:** A stale address can send funds to an unintended contract, an empty account, or a token with different decimals and trust assumptions.
  - **Detection:** Compare every configured address with the target chain's official deployment registry and verify code, decimals, and role configuration.
  - **Specific FP:** Addresses are chain-keyed, immutable after review, and checked for code and expected interface before use.
  - **Specific proof:** Run deposits, withdrawals, and balance reads against every configured chain and compare the resolved contract with the intended asset.
  - **Provenance:** multichain-auditor

- [ ] **[EVM-CHAIN-037] ZKsync EraVM compatibility must be checked per instruction and deployment path** _(semantic; high)_: ZKsync EraVM is source-compatible with much Solidity code but differs from the EVM in documented instruction, bytecode, address-derivation, and deployment behavior. Do not claim that every common opcode behaves differently; review only the documented differences reached by the target code and toolchain.
  - **Trigger:** A deployment targets ZKsync Era and uses low-level instructions, bytecode inspection, CREATE/CREATE2, system contracts, or EVM-specific tooling.
  - **Risk:** EVM-specific bytecode, factory dependencies, address calculations, or call assumptions can fail or produce different results on EraVM.
  - **Detection:** Map the reached instructions and deployment artifacts to the current EraVM differences documentation and compiler mode.
  - **Specific FP:** The target uses the supported EVM interpreter path or the reached instructions are documented as equivalent under the declared compiler and protocol version.
  - **Specific proof:** Compile and execute the exact artifact on the declared ZKsync environment and compare each relied-upon behavior with the EVM baseline.
  - **Provenance:** multichain-auditor, beirao MC-11; [ZKsync Era EVM instruction differences](https://docs.zksync.io/zksync-protocol/era-vm/differences/evm-instructions)

- [ ] **[EVM-CHAIN-038] Same-name tokens can have different callback behavior** _(exploit-pattern; medium)_: Token callback behavior is a property of the deployed token and its upgrade history, not its symbol or chain label. Inspect the exact contract and protect accounting around arbitrary token callbacks.
  - **Trigger:** A multichain integration grants trust based on a token symbol or origin chain without checking callback-capable behavior.
  - **Risk:** Assuming a same-name token is callback-free can expose reentrancy, unexpected control flow, or transfer-accounting errors.
  - **Detection:** Inspect bytecode, interfaces, hooks, proxy implementation, and transfer traces for every supported token address.
  - **Specific FP:** The token set is immutable/allowlisted and all external control paths are protected by checks-effects-interactions or reentrancy guards.
  - **Specific proof:** Use a callback-capable fixture or the deployed token trace to demonstrate whether transfer control can reenter before accounting finalizes.
  - **Provenance:** multichain-auditor

## Supplemental Attack Vectors (SAS-AV)

- [ ] **[EVM-CHAIN-039] L2 Sequencer Downtime in Interest Accrual** _(exploit-pattern; medium)_: Interest rate calculations use `block.timestamp` delta without accounting for L2 sequencer downtime periods. If sequencer is down for hours, the first post-restart block has a massive timestamp gap, compounding interest as if the protocol was operating normally.
  - **Specific FP:** Interest accrual capped per-update (`maxTimeDelta`). Sequencer uptime feed checked before accruing. Rate-limited compounding.
  - **Provenance:** [SAS-AV-130](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-186
