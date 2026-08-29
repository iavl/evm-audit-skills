<!-- GENERATED FILE: source is ../../data/canonical-checks.json; do not edit by hand. -->
# Bridge & Cross-Chain Security Checklist

Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.

## LayerZero V2

- [ ] **[EVM-BRIDGE-001] `lzReceive` OOG from lazy nonce loop** _(exploit-pattern; medium)_: `_clearPayload` loops from `lazyInboundNonce` to current nonce. If many messages are verified but not received, the loop causes OOG. Fix: process messages with lower nonces first to keep the gap small. Look for: large gaps between `lazyInboundNonce` and current nonce in message processing. [LayerZeroV2 checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** LayerZeroV2 checklist

- [ ] **[EVM-BRIDGE-002] `lzCompose` must validate `from` AND `msg.sender`** _(exploit-pattern; medium)_: In composed messages, `from` must match the expected OFT contract (the one that queued the message via `sendCompose`). `msg.sender` must be EndpointV2. Missing either check allows unauthorized execution with arbitrary composed message data. Look for: `lzCompose` implementations without both validations. [LayerZeroV2 checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** LayerZeroV2 checklist

- [ ] **[EVM-BRIDGE-003] Gas limit and msg.value from options are NOT enforced on-chain** _(exploit-pattern; medium)_: The options metadata is an off-chain agreement with the Executor. ANYONE can call `lzReceive` with different gas/value than specified in options. Look for: receiving contracts that assume msg.value or gas matches what was specified on sending side. Fix: encode expected values in the message payload and check on receive. [LayerZeroV2 checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** LayerZeroV2 checklist

- [ ] **[EVM-BRIDGE-004] Un-ordered execution is the DEFAULT** _(exploit-pattern; medium)_: If nonce 4 fails, nonces 5 and 6 still execute. If you need ordered execution, implement `nextNonce()` AND ensure no reverting transactions (they permanently block all subsequent nonces). Look for: state-dependent cross-chain operations that assume ordering. [LayerZeroV2 checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** LayerZeroV2 checklist

- [ ] **[EVM-BRIDGE-005] Native airdrop cap per chain** _(exploit-pattern; medium)_: The default LayerZero Executor limits native token airdrops per destination chain (e.g., 1500 MATIC for Polygon). Exceeding this silently fails. Look for: `lzSend` with native airdrop amounts near chain limits. [LayerZeroV2 checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** LayerZeroV2 checklist
  - **Notes:** ### OFT Standard

- [ ] **[EVM-BRIDGE-006] Dust removal strips 12 digits by default** _(exploit-pattern; medium)_: Default OFT uses 6 shared decimals. Sending `1.234567890123456789` tokens results in receiving `1.234567000000000000`. The 12 least significant digits are stripped. Dust isn't lost — it's cleaned from the input amount. Look for: custom fee logic that should call `_removeDust` after fee deduction, not before. [LayerZeroV2 checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** LayerZeroV2 checklist

- [ ] **[EVM-BRIDGE-007] `_toSD` truncates to uint64 silently** _(exploit-pattern; medium)_: When `localDecimals == sharedDecimals == 18`, the conversion rate is 1, and `_toSD` casts to `uint64`. Any amount > `uint64.max` (~18.4e18) is silently truncated, losing value. Look for: OFT implementations that override `sharedDecimals` to match `localDecimals`. [LayerZeroV2 checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** LayerZeroV2 checklist
  - **Notes:** ### Configuration

- [ ] **[EVM-BRIDGE-008] Default libraries controlled by LayerZero team** _(exploit-pattern; medium)_: If your OApp doesn't explicitly configure send/receive libraries, it uses system defaults. LayerZero can change defaults at any time, potentially bricking your protocol. ALWAYS explicitly set your library configuration. Look for: OApp deployments without `setSendLibrary`/`setReceiveLibrary` calls. [LayerZeroV2 checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** LayerZeroV2 checklist

- [ ] **[EVM-BRIDGE-009] `allowInitializePath` must be implemented for non-default receivers** _(exploit-pattern; medium)_: Without this, the first DVN verification fails silently. Default OApp checks if sender is a trusted peer. Custom receivers must implement their own logic. Look for: custom OApp receivers without `allowInitializePath`. [LayerZeroV2 checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** LayerZeroV2 checklist

- [ ] **[EVM-BRIDGE-010] Pausing one direction** _(exploit-pattern; medium)_: `setPeer` enables bidirectional communication. To disable sending from one direction only, set `maxMessageSize` to 1 byte on the send library config — all sends revert. Look for: protocols that need unidirectional communication. [LayerZeroV2 checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** LayerZeroV2 checklist
  - **Notes:** ### LayerZero Read

- [ ] **[EVM-BRIDGE-011] Reverting read functions block all subsequent messages** _(exploit-pattern; medium)_: If `readCount`, `lzMap`, or `lzReduce` revert, DVNs can't verify that nonce. All messages with higher nonces are blocked until that nonce is resolved (via `EndpointV2::skip`). Look for: any revert possibility in read/compute functions. [LayerZeroV2 checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** LayerZeroV2 checklist

## Chainlink CCIP

- [ ] **[EVM-BRIDGE-012] Default gas limit is 200,000** _(exploit-pattern; medium)_: If `gasLimit` isn't specified in `extraArgs`, CCIP uses 200K gas. Complex `ccipReceive()` implementations easily exceed this and silently fail. Unspent gas is NOT refunded. Look for: CCIP messages without explicit gas limit in extraArgs. [CCIP checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** CCIP checklist

- [ ] **[EVM-BRIDGE-013] Out-of-order execution flag is REQUIRED on some lanes** _(exploit-pattern; medium)_: When `allowOutOfOrderExecution` is Required (not Optional), setting it to `false` causes the message to revert entirely. Look for: CCIP messages to lanes with Required out-of-order execution that hardcode `false`. [CCIP checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** CCIP checklist

- [ ] **[EVM-BRIDGE-014] 8-hour Smart Execution window** _(exploit-pattern; medium)_: If a message can't execute within 8 hours, ALL subsequent messages on that lane fail until the failing one succeeds (via manual execution). Look for: any scenario where `ccipReceive()` could permanently revert. [CCIP checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** CCIP checklist

- [ ] **[EVM-BRIDGE-015] Token pool gas limit of 90,000** _(exploit-pattern; medium)_: `balanceOf` + `releaseOrMint` + `balanceOf` on destination must not exceed 90K gas combined. Custom tokens with complex mint/release logic easily exceed this. Look for: custom token pools with gas-intensive operations. [CCIP checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** CCIP checklist

- [ ] **[EVM-BRIDGE-016] Use mutable `extraArgs`, not hardcoded** _(exploit-pattern; medium)_: Hardcoded extraArgs prevent adapting to protocol changes. Look for: `Client.EVMExtraArgsV2({gasLimit: 200_000, ...})` as constants. [CCIP checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** CCIP checklist

- [ ] **[EVM-BRIDGE-017] Validate CCIP inputs before state changes** _(exploit-pattern; medium)_: If `ccipSend()` is callable by users and state changes occur before the send, wrong inputs can lock funds in the contract. Look for: state mutations before `ccipSend()` without input validation. [CCIP checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** CCIP checklist

- [ ] **[EVM-BRIDGE-018] Rate limits are per-token AND aggregate per-lane** _(exploit-pattern; medium)_: Both individual token limits and aggregate USD value limits apply. A large transfer of one token can block transfers of all tokens on a lane. Look for: protocols that assume independent per-token rate limits. [CCIP checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** CCIP checklist

## Wormhole

- [ ] **[EVM-BRIDGE-019] Always use `messageFee()`, never hardcode** _(exploit-pattern; medium)_: Wormhole's `publishMessage()` requires the current fee. Hardcoding 0 or any fixed value will fail when fees change. Look for: `publishMessage()` or `transferTokensWithPayload()` without dynamic fee lookup. [Wormhole checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Wormhole checklist

- [ ] **[EVM-BRIDGE-020] Validate both `isRegisteredSender` AND `msg.sender == wormholeRelayer`** _(exploit-pattern; medium)_: Missing either check allows spoofed messages. The modifier validates source chain/sender, the msg.sender check validates the delivery mechanism. Look for: `receiveWormholeMessages` without both checks. [Wormhole checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Wormhole checklist

- [ ] **[EVM-BRIDGE-021] Normalize/denormalize creates stuck dust** _(exploit-pattern; medium)_: Wormhole token bridge strips precision (normalizes to 8 decimals). If you transfer the raw amount but bridge the normalized amount, the difference stays stuck in your contract. Fix: denormalize first, then only transfer the denormalized amount. Look for: transferFrom(amount) where bridge receives normalize(amount). [Wormhole checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Wormhole checklist

- [ ] **[EVM-BRIDGE-022] Double normalization/denormalization** _(exploit-pattern; medium)_: If a value is already normalized, normalizing again causes massive precision loss. Look for: multiple normalize/denormalize calls on the same value through call chains. [Wormhole checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Wormhole checklist

- [ ] **[EVM-BRIDGE-023] Guardian set transition needs `>=` not `==`** _(exploit-pattern; medium)_: During transitions, both old and new guardian sets must be valid. Using `==` for set index breaks verification when the new set is active but the old set signed a pending message. Look for: strict equality checks on guardian set index. [Wormhole checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Wormhole checklist

- [ ] **[EVM-BRIDGE-024] Duplicate guardian signatures bypass quorum** _(exploit-pattern; medium)_: If signature uniqueness per guardian index isn't enforced, one guardian's signature can be submitted multiple times to meet the 2/3+1 quorum. Look for: signature verification loops without guardian index deduplication. [Wormhole checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Wormhole checklist

## Across Protocol

- [ ] **[EVM-BRIDGE-025] Relayers can spoof `handleV3AcrossMessage()` parameters** _(exploit-pattern; medium)_: Across does NOT guarantee message integrity. A malicious relayer won't be repaid, but if the handler unlocks external funds, damage is done. ALL parameters (tokenSent, amount, message) must be independently validated. Look for: `handleV3AcrossMessage` that trusts parameters without validation. [Across checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Across checklist

- [ ] **[EVM-BRIDGE-026] `handleV3AcrossMessage` must check `msg.sender == acrossSpokePool`** _(exploit-pattern; medium)_: Without this check, anyone can call with arbitrary data. Look for: missing sender validation in Across message handlers. [Across checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Across checklist

- [ ] **[EVM-BRIDGE-027] No origin sender in Across messages** _(exploit-pattern; medium)_: Across doesn't send the origin sender address, making messages inherently spoofable. Include depositor signatures in the message for verification. Look for: message handling that assumes knowledge of origin sender. [Across checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Across checklist

- [ ] **[EVM-BRIDGE-028] Excessive `outputAmount` locks funds** _(exploit-pattern; medium)_: If output > input × (1 - fees), no rational relayer fills the order. Funds are locked until expiry (hours). Look for: user-provided outputAmount without bounds validation. [Across checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Across checklist

## Bridge Security Fundamentals

- [ ] **[EVM-BRIDGE-029] Signed bridge messages must bind all execution-affecting fields** _(exploit-pattern; medium)_: Include token identity, source and destination chain IDs, receiver, amount, nonce, and a complete EIP-712 domain separator. Omitting any field enables replay, spoofing, or misdirected funds. Look for: bridge message encodings that omit a value later used in execution. [Spearbit bridge checklist C6.1]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Spearbit bridge checklist C6.1

- [ ] **[EVM-BRIDGE-030] Used bridge signatures must be invalidated** _(exploit-pattern; medium)_: After execution, the signature or message hash must be marked as spent atomically with the state transition to prevent replay. Look for: relay paths that do not consume the message before external effects. [Spearbit bridge checklist C6.2]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Spearbit bridge checklist C6.2

- [ ] **[EVM-BRIDGE-031] Bridge chain identifiers cannot be spoofed** _(exploit-pattern; medium)_: Source and destination chain IDs must be signed and verified against the configured source, destination, and actual execution chain. Look for: relayers that accept caller-supplied chain IDs without endpoint/peer validation. [Spearbit bridge checklist C6.4, C6.5]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Spearbit bridge checklist C6.4, C6.5

- [ ] **[EVM-BRIDGE-032] Challenge window long enough for human response** _(exploit-pattern; medium)_: For optimistic bridges, the challenge period must allow incident response (30+ min minimum). Consider per-chain based on weakest chain's finality. [Spearbit bridge checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Spearbit bridge checklist

## Bridge Security Verification (Expanded from Spearbit)

- [ ] **[EVM-BRIDGE-033] Message hash collision resistance** _(exploit-pattern; medium)_: If message hashing uses `abi.encodePacked` with variable-length fields, hash collisions are possible. Use `abi.encode` instead. Look for: `keccak256(abi.encodePacked(...))` in bridge message hashing with multiple dynamic types. [Spearbit Bridge C6.3]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Spearbit Bridge C6.3

- [ ] **[EVM-BRIDGE-034] Nonce required for duplicate operations** _(exploit-pattern; medium)_: Without a nonce, identical operations (same sender, receiver, amount) can't be distinguished, potentially blocking legitimate duplicate transfers. Look for: bridge message schemas without nonce field. [Spearbit Bridge C6.6]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Spearbit Bridge C6.6

- [ ] **[EVM-BRIDGE-035] EIP-712 domain separator for bridge messages** _(exploit-pattern; medium)_: Bridge signed messages should use EIP-712 domain separator to prevent cross-protocol replay. Look for: bridge signatures without domain separator or with incomplete domain parameters. [Spearbit Bridge C6.7]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Spearbit Bridge C6.7

## Arbitrum Retryable Ticket Pitfalls (from Arbitrum Checklist)

- [ ] **[EVM-BRIDGE-036] Out-of-order retryable ticket execution** _(exploit-pattern; medium)_: If multiple retryable tickets are created in one L1 tx, they may execute in different order on L2. If gas price spikes and auto-redemption fails, anyone can manually redeem tickets in any order. Look for: L1 contracts that create multiple retryable tickets with ordering dependencies. [Arbitrum Checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Arbitrum Checklist

- [ ] **[EVM-BRIDGE-037] Address aliasing in cross-chain auth** _(exploit-pattern; medium)_: When L1 contracts send messages to L2, `msg.sender` on L2 is the aliased address (`L1_address + 0x1111000000000000000000000000000000001111`). Auth checks on L2 must use `AddressAliasHelper.applyL1ToL2Alias()`. Look for: L2 contracts checking `msg.sender == L1_counterpart` without aliasing. [Arbitrum Checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Arbitrum Checklist

- [ ] **[EVM-BRIDGE-038] Burned nonce from failed auto-redemption** _(exploit-pattern; medium)_: If a retryable ticket fails auto-redemption (out of gas), the sender's nonce is spent. If the L1 contract predicted a deployment address based on nonce 0, the actual deployment (via manual redemption) will use nonce 1, creating a different address. Look for: L1 contracts that predict L2 contract addresses based on nonce. [Arbitrum Checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Arbitrum Checklist

- [ ] **[EVM-BRIDGE-039] `callValueRefundAddress` can cancel tickets** _(exploit-pattern; medium)_: The `callValueRefundAddress` parameter in `createRetryableTicket` gets permission to cancel the ticket permanently. A malicious actor can set themselves as refund address, intentionally set gas too low, then cancel the ticket before anyone redeems it. Look for: permissionless L1 functions where users control `callValueRefundAddress`. [Arbitrum Checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Arbitrum Checklist

- [ ] **[EVM-BRIDGE-040] `unsafeCreateRetryableTicket` doesn't alias refund addresses** _(exploit-pattern; medium)_: The unsafe version doesn't apply aliasing to `excessFeeRefundAddress` and `callValueRefundAddress`. If these are L1 contract addresses, the L2 contract at the same address may not control the refunded funds. Look for: usage of `unsafeCreateRetryableTicket` with L1 contract addresses as refund recipients. [Arbitrum Checklist]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Arbitrum Checklist

## Cross-Chain Message Security (from Beirao/Multichain-Auditor)

- [ ] **[EVM-BRIDGE-041] Unsupported chain whitelisting** _(exploit-pattern; medium)_: If a protocol accepts cross-chain messages from any chain, an attacker can deploy on an unsupported chain and send malicious messages. All compatible source chains must be whitelisted. Look for: cross-chain receivers without source chain validation. [beirao MC-10]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao MC-10

- [ ] **[EVM-BRIDGE-042] Bridge contract upgradability differs across chains** _(heuristic; contextual)_: A bridge contract may be immutable on one chain but upgradeable on another. A compromised upgrade on one chain can affect the entire bridge. Look for: cross-chain systems where upgrade authority differs per chain. [multichain-auditor]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** multichain-auditor

## Supplemental Attack Vectors (SAS-AV)

- [ ] **[EVM-BRIDGE-043] Delegate Privilege Escalation** _(exploit-pattern; medium)_: `setDelegate()` appoints an address that can manage OApp configurations including DVNs, Executors, message libraries, and can skip/clear payloads. If delegate is set to an insecure address (EOA, unrelated contract) or differs from owner without governance controls, the delegate can silently reconfigure the OApp's entire security stack.
  - **FP:** Delegate == owner. Delegate is a governance timelock or multisig. `setDelegate` protected by the same access controls as `setPeer`.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-045](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-38

- [ ] **[EVM-BRIDGE-044] Cross-Chain Supply Accounting Invariant Violation** _(exploit-pattern; medium)_: The fundamental invariant `total_locked_source >= total_minted_destination` is violated. Can occur through: decimal conversion errors between chains, `_credit` callable without corresponding `_debit`, race conditions in multi-chain deployments, or any bug that allows minting without locking. Minted tokens become partially or fully unbacked.
  - **FP:** Invariant verified via monitoring/alerting. `_credit` only callable from verified `lzReceive` path. Decimal conversion tested across all supported chains. Rate limits cap maximum exposure per time window.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-046](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-39

- [ ] **[EVM-BRIDGE-045] State-Time Lag Exploitation (lzRead Stale State)** _(exploit-pattern; medium)_: `lzRead` queries state on a remote chain, but there is a latency window between query and delivery of the result via `lzReceive`. During this window, the queried state may change (token transferred, position closed, price moved). Protocol makes irreversible decisions based on the stale read result.
  - **FP:** Read targets immutable or slowly-changing state (contract code, historical data). Read result treated as a hint with on-chain re-validation. Time-sensitive operations require fresh on-chain state, not cross-chain reads.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-047](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-44

- [ ] **[EVM-BRIDGE-046] Cross-Chain Address Ownership Variance** _(exploit-pattern; medium)_: Same address has different owners on different chains (EOA private key not used on all chains, or `CREATE`-deployed contract at same nonce but different deployer). Cross-chain logic that assumes `address(X) on Chain A == address(X) on Chain B` implies same owner enables impersonation.
  - **FP:** `CREATE2`-deployed contracts with same factory + salt are safe. Peer mapping explicitly binds (chainId, address) pairs. Authorization uses cross-chain messaging (not address equality) to prove ownership.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-048](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-58

- [ ] **[EVM-BRIDGE-047] Insufficient Block Confirmations / Reorg Double-Spend** _(exploit-pattern; medium)_: DVN relays cross-chain message before source chain reaches finality. Attacker deposits on source, gets minted on destination, then reorg reverses the deposit.
  - **FP:** Confirmation count matches chain-specific finality guarantees. Chain has fast finality. DVN waits for finalized blocks.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-049](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-113

- [ ] **[EVM-BRIDGE-048] Cross-Chain Message Spoofing (Missing Endpoint/Peer Validation)** _(exploit-pattern; medium)_: Receiver contract accepts cross-chain messages without verifying `msg.sender == endpoint` and `_origin.sender == registeredPeer[srcChainId]`. Ref: CrossCurve bridge exploit (Jan 2026).
  - **FP:** `onlyPeer` modifier checks both endpoint and peer. Standard `OAppReceiver._acceptNonce` validates origin.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-050](https://github.com/sanbir/solidity-auditor-skills); srcChainId
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-116

- [ ] **[EVM-BRIDGE-049] Unauthorized Peer Initialization (Fake Peer Attack)** _(exploit-pattern; medium)_: `setPeer()` sets the remote peer address that a cross-chain contract trusts. If `setPeer` lacks proper access control, attacker registers fraudulent peer. Ref: GAIN token exploit (Sep 2025).
  - **FP:** `setPeer` protected by multisig + timelock. `allowInitializePath()` properly implemented.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-051](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-118

- [ ] **[EVM-BRIDGE-050] DVN Collusion or Insufficient DVN Diversity** _(exploit-pattern; medium)_: OApp configured with a single DVN (`1/1/1` security stack) or multiple DVNs controlled by the same entity. Compromising one entity approves fraudulent messages.
  - **FP:** Diverse DVN set with `2/3+` threshold. DVNs use independent verification methods. Protocol runs its own required DVN.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-052](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-141

- [ ] **[EVM-BRIDGE-051] Missing Cross-Chain Rate Limits / Circuit Breakers** _(exploit-pattern; medium)_: Bridge or OFT contract has no per-transaction or time-window transfer caps. A single exploit can drain the entire locked asset pool. Ref: Ronin hack.
  - **FP:** Per-tx and per-window rate limits. `whenNotPaused` modifier. Guardian/emergency multisig can freeze.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-053](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-142

- [ ] **[EVM-BRIDGE-052] Cross-Chain Reentrancy via Safe Transfer Callbacks** _(exploit-pattern; medium)_: Cross-chain receive function calls `_safeMint`/`_safeTransfer` before updating supply/ownership counters. Callback re-enters to initiate another cross-chain send.
  - **FP:** State updates committed before any safe transfer. `nonReentrant` on receive path. `_mint` used instead of `_safeMint`.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-054](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-154

- [ ] **[EVM-BRIDGE-053] Missing `_debit` / `_debitFrom` Authorization in OFT** _(exploit-pattern; medium)_: Custom OFT override of `_debit` omits authorization check. Anyone can bridge tokens from any holder's balance.
  - **FP:** Standard LayerZero OFT implementation used without override. Custom `_debit` includes proper authorization.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-055](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-157

- [ ] **[EVM-BRIDGE-054] Cross-Chain Sandwich via Bridge Parameter Exposure** _(exploit-pattern; medium)_: Bridge tx on source chain exposes destination swap params (`amountOutMin`, token, amount) in plaintext. Attacker frontruns on destination L2 to manipulate pool, backruns after bridge tx executes.
  - **FP:** Encrypted/committed bridge payloads. Destination swap recalculates slippage via oracle. Intent-based bridge (solver fills off-chain).
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-056](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-232

- [ ] **[EVM-BRIDGE-055] Bridge Global Rate Limit Griefing** _(exploit-pattern; medium)_: Bridge enforces global throughput cap not segmented by user. Attacker fills limit bridging cheap tokens back and forth, blocking all legitimate users during cooldown.
  - **FP:** Per-user rate limits. Segmented by token/route. Whitelist for high-value transfers.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-057](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-269

- [ ] **[EVM-BRIDGE-056] Cross-Message Token Identity Mismatch** _(exploit-pattern; medium)_: Multi-hop/cross-chain flow uses user-controlled token fields per leg without cross-validation. Attacker deposits token A but encodes token B — destination withdraws contract's balance of B. Pattern: `depositedToken`, `swapFromToken`, `swapToToken`, `withdrawalToken` specified independently.
  - **FP:** `require(depositedToken == message.fromToken)` at deposit. Swap output validated against withdrawal token. Stateless relay holds no funds. Fields derived from on-chain state.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-058](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-290

- [ ] **[EVM-BRIDGE-057] Pending Async Callback with Dependency Swap** _(exploit-pattern; medium)_: Contract requests async operation (randomness, oracle, cross-chain message) fulfilled via callback. Dependency swapped before callback arrives — new provider can't fulfill old request, old rejected as unregistered. Request stuck permanently. Pattern: `setProvider(new)` while `pendingRequestId != 0`.
  - **FP:** Swap blocked while requests pending. Callback validates request ID, not sender. Transition fulfills/cancels pending before registering new provider. Timeout for stuck requests.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-059](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-313

## drozer-lite Additions

- [ ] **[EVM-BRIDGE-058] LP Protection (Liquidity-Network Bridges)** _(exploit-pattern; medium)_: A liquidity-network bridge allows LPs to be drained via fake claims or sandwich attacks on deposits.
  - **Trigger:** A liquidity-network bridge allows LPs to be drained via fake claims or sandwich attacks on deposits. No source-specific red flags listed; trace the invariant and caller-controlled inputs described above.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Proof:** For each LP deposit and withdrawal path, check for delay mechanisms and sandwich protection. Verify fee distribution is pro-rata and cannot be gamed.
  - **Provenance:** [DROZER-XCHAIN-9](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/cross-chain.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/cross-chain.md); gdroz3r/drozer-lite — checklists/cross-chain.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/cross-chain.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/cross-chain.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
