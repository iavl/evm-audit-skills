# ERC4337 Account Abstraction Security Checklist

## Wallet Account Factory

- [ ] **Factory must use CREATE2**: Factories using CREATE have nonce-dependent deployment. Reorgs change the nonce, deploying the wallet at a different address. Users who sent funds to the pre-computed address lose them. Look for: factory using `new Wallet()` without `salt`. [ERC4337 checklist]

- [ ] **Factory must return address even if already deployed**: If `createAccount()` reverts when the wallet exists, it breaks bundler workflows. The factory must return the deterministic address whether the wallet exists or not. Look for: factory createAccount that reverts on existing accounts. [ERC4337 checklist]

- [ ] **Attacker deploys wallet with different credentials**: If the generated wallet address doesn't depend on the initial owner/signature, an attacker can deploy the wallet first with their own keys and control it. The initial signature MUST be part of the CREATE2 salt. Look for: CREATE2 salt that doesn't include owner address or initial signer. [Code4rena/Biconomy H-03]

- [ ] **Factory stake unstakeDelay griefing**: If anyone can add stake to the factory's entrypoint, they can set `unstakeDelay` to `type(uint256).max`, permanently preventing unstaking. Look for: factory stake functions without access control on delay parameter. [ERC4337 checklist]

## Wallet Account

- [ ] **Implementation contract initializable by attacker**: If the implementation contract's `initialize()` isn't called or protected, an attacker can front-run initialization and gain ownership. On UUPS implementations, this can lead to `selfdestruct` of the implementation, bricking all proxies. Look for: implementation contracts without `_disableInitializers()` in constructor. [Code4rena/Biconomy H-01, Ambire M-05]

- [ ] **Direct execution bypasses EntryPoint**: If the wallet can execute transactions directly (not through EntryPoint), it must re-implement all validation (signature, nonce, gas). Missing any check enables arbitrary execution. Look for: `execute()` functions callable without going through EntryPoint that lack full signature validation. [Code4rena/Biconomy H-04]

- [ ] **UserOperation hash must bind every execution-affecting field**: Custom hashing that omits sender, nonce, chain ID, calldata, gas limits, paymaster data, or uses ambiguous packing can make different operations share a digest. Look for: hand-rolled `getHash()` implementations instead of the EntryPoint-defined hash, `abi.encodePacked` over dynamic fields, or fields used during execution but absent from the signed digest. [ERC-4337](https://eips.ethereum.org/EIPS/eip-4337)

- [ ] **Bundler ordering, censorship, and liveness are adversarial**: Bundlers can delay, reorder, or omit UserOperations and may expose profitable operations to MEV. Protocol correctness must not rely on a particular bundler, FIFO ordering, or guaranteed inclusion. Look for: state transitions keyed only by arrival order, timing assumptions tied to one bundler, or no nonce/expiry/replay handling for delayed operations. [ERC-4337](https://eips.ethereum.org/EIPS/eip-4337)

- [ ] **`validateUserOp` must return SIG_VALIDATION_FAILED, not revert**: Per spec, signature mismatches should return the sentinel value `SIG_VALIDATION_FAILED`. Reverting breaks bundler behavior and wastes gas. Look for: `revert` in `validateUserOp` for invalid signatures. [ERC4337 checklist]

- [ ] **ERC-1271 cross-account signature replay**: If `isValidSignature()` checks that "any owner has signed the hash" without binding to the specific account (via EIP-712 with `verifyingContract = address(this)`), signatures can be replayed across accounts that share owners. Look for: `isValidSignature` that doesn't alter the hash with the account address. [ERC4337 checklist]

- [ ] **`tx.origin` breaks for smart wallets**: Applications that use `require(tx.origin == msg.sender)` to block contracts will block all smart wallets. Applications must not rely on this pattern. Look for: `tx.origin == msg.sender` checks. [ERC4337 checklist]

- [ ] **Fixed gas assumptions (21000 for transfer)**: Smart wallet transactions cost more than 21000 gas. Applications relying on exact gas costs will underestimate for AA wallets. Look for: hardcoded gas estimates like 21000. [ERC4337 checklist]

## Paymaster

- [ ] **VerifyingPaymaster signature replay**: If the paymaster's signed approval doesn't include nonce, chain ID, and sender, the signature can be replayed to drain the paymaster's deposit. Look for: paymaster validation hash that omits any of: sender, nonce, chainid, validUntil, validAfter. [Code4rena/Biconomy H-05]

- [ ] **Cross-chain paymaster replay**: If the paymaster signature doesn't include chain ID, it can be used on any chain where the paymaster is deployed. Look for: missing `block.chainid` in paymaster signature hash. [Code4rena/Biconomy M-03]

- [ ] **EntryPoint v0.6 postOp bug**: A bug in v0.6 causes short revert messages in `postOp()` to revert the entire bundle instead of calling the second `postOp()`. Look for: v0.6 entrypoint integration with custom postOp logic. [ERC4337 checklist]

- [ ] **DoS via free transactions**: Paymasters enable gas-free transactions. An attacker can spam transactions through the paymaster to drain its deposit. Look for: paymasters without rate limiting or sender validation. [beirao AA-01]

## Session Keys & Modules

- [ ] **Session key exposure on frontend**: Session signer wallet private keys exposed in frontend JavaScript allow account takeover (Cardex compromise). Look for: session key generation or storage in client-side code. [ERC4337 checklist]

- [ ] **Module storage overlap with delegatecall**: If the wallet uses `delegatecall`-based modules, module storage must not overlap with wallet storage. Look for: modules using storage slots that conflict with ERC1967 proxy slots or wallet state. [ERC4337 checklist]

- [ ] **Fallback handler set to `address(this)`**: If the wallet's fallback handler can be set to the wallet itself, it creates a self-referencing loop that can be exploited. Look for: fallback handler setter without `handler != address(this)` check. [Code4rena/Ambire L-02]

## ERC-6492 & Predeploy Signatures

- [ ] **Predeploy contract signature validation**: Applications verifying signatures from smart wallets should support ERC-6492 for wallets not yet deployed. Without it, counterfactual wallet signatures fail verification. Look for: `isValidSignature` callers that don't handle ERC-6492 wrapper format. [ERC4337 checklist]

## Supplemental Attack Vectors (SAS-AV)

These vectors are merged from sanbir/solidity-auditor-skills; each item retains a detection condition (D), false-positive gate (FP), and source provenance.

- [ ] **[SAS-AV-060] validateUserOp Signature Not Bound to nonce or chainId**
  - **D:** `validateUserOp` reconstructs digest manually (not via `entryPoint.getUserOpHash`) omitting `userOp.nonce` or `block.chainid`. Enables cross-chain or in-chain replay.
  - **FP:** Digest from `entryPoint.getUserOpHash(userOp)` (includes sender, nonce, chainId). Custom digest explicitly includes both.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-21

- [ ] **[SAS-AV-061] Banned Opcode in Validation Phase (Simulation-Execution Divergence)**
  - **D:** `validateUserOp`/`validatePaymasterUserOp` references `block.timestamp`, `block.number`, `block.coinbase`, etc. Per ERC-7562, banned in validation.
  - **FP:** Banned opcodes only in execution phase. Entity is staked under ERC-7562 reputation system.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-99

- [ ] **[SAS-AV-062] Paymaster Gas Penalty Undercalculation**
  - **D:** Paymaster prefund formula omits 10% EntryPoint penalty on unused execution gas (`postOpUnusedGasPenalty`). Large `executionGasLimit` with low usage drains paymaster deposit.
  - **FP:** Prefund explicitly adds unused-gas penalty. Conservative overestimation covers worst case.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-107

- [ ] **[SAS-AV-063] Paymaster ERC-20 Payment Deferred to postOp Without Pre-Validation**
  - **D:** `validatePaymasterUserOp` doesn't transfer/lock tokens — payment deferred to `postOp`. User can revoke allowance between validation and execution.
  - **FP:** Tokens transferred/locked during `validatePaymasterUserOp`. `postOp` only refunds excess.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-121

- [ ] **[SAS-AV-064] validateUserOp Missing EntryPoint Caller Restriction**
  - **D:** `validateUserOp` is `public`/`external` without `require(msg.sender == entryPoint)`.
  - **FP:** `require(msg.sender == address(_entryPoint))` or `onlyEntryPoint` modifier present.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-149

- [ ] **[SAS-AV-065] EIP-7702 Cross-Chain Delegation Replay**
  - **D:** EIP-7702 authorization signatures for EOA-to-contract delegation miss `chainId` in the signed tuple. Attacker replays the same delegation signature on another chain, hijacking the EOA's execution context on chains the user never intended to delegate on.
  - **FP:** `chainId` included in EIP-7702 authorization tuple. Wallet UI displays target chain before signing. Per-chain delegation with separate signatures.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-208/316

- [ ] **[SAS-AV-066] EIP-7702 Delegate Hijacking**
  - **D:** Malicious contract becomes an EOA's delegate via social engineering or phishing. Once delegated, all transactions to the EOA execute the malicious contract's code in the EOA's context — draining funds, approving tokens, or modifying state. Persists until the user explicitly revokes delegation.
  - **FP:** Delegation target is a well-known, audited contract (e.g., Safe module). Wallet prompts clearly distinguish delegation from normal signing. Revocation mechanism is accessible and documented. Time-limited delegation with automatic expiry.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-209/210

- [ ] **[SAS-AV-067] EIP-7702 EOA Nested Reentrancy**
  - **D:** With EIP-7702, EOAs can have code. A delegated EOA receiving ETH or tokens triggers fallback/receive in the delegate contract, creating new reentrancy surfaces that didn't exist when the counterparty was a plain EOA. Protocols assuming EOAs can't have callbacks are vulnerable.
  - **FP:** `nonReentrant` on all external-call-bearing functions regardless of counterparty type. No assumption that `tx.origin == msg.sender` means "safe EOA." CEI pattern followed universally.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-211

- [ ] **[SAS-AV-068] ERC-4337 Paymaster Drain via Crafted UserOperations**
  - **D:** Attacker crafts UserOperations that pass paymaster validation but consume maximum gas during execution. Paymaster pays for gas but the operation accomplishes nothing useful for the paymaster's business model. Repeated submissions drain the paymaster's deposit in the EntryPoint.
  - **FP:** Paymaster validates operation purpose (not just signature). Gas limits per UserOperation and per-user rate limits enforced. Paymaster deposit monitored with automatic pause at low threshold. Off-chain simulation before on-chain validation.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-212

- [ ] **[SAS-AV-069] ERC-4337 Validation-Execution Phase Confusion**
  - **D:** Logic that should only run during validation phase (signature checks, nonce verification) executes during the execution phase or vice versa. Banned opcodes in validation (ERC-7562) cause bundler rejection, while missing validation in execution allows unauthorized operations.
  - **FP:** Clear separation between `validateUserOp` and execution functions. No storage access in validation beyond sender's associated storage. Compliance with ERC-7562 opcode restrictions verified. Bundler simulation tests pass.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-213

- [ ] **[SAS-AV-070] EIP-7702 Code Inspection Opcode Invalidation**
  - **D:** `extcodesize`, `extcodehash`, `extcodecopy` on delegated EOA operate on the 23-byte `0xef0100` delegation stub, not the delegate's code. `isContract()` checks misroute delegated EOAs. `extcodehash` comparisons against known implementation hashes fail. Proxy detection and ERC-1167 clone verification return unexpected results.
  - **FP:** No security-critical branching on `extcodesize`/`extcodehash`. Uses `CODESIZE`/`CODECOPY` within execution context (which follow delegation) rather than `EXT*` variants.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-236

- [ ] **[SAS-AV-071] EIP-7702 Dual Signature Validation Confusion**
  - **D:** Delegated EOA supports both ECDSA (private key) and ERC-1271 (`isValidSignature` from delegate). Protocol checking only one path lets attacker exploit the other. Signature replay across redelegation — message signed under Delegate A interpreted differently by Delegate B.
  - **FP:** OZ `SignatureChecker.isValidSignatureNow` used. ERC-1271 checked first for accounts with code, ECDSA fallback for codeless. Signatures include delegate address in EIP-712 domain.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-237

- [ ] **[SAS-AV-072] EIP-7702 ERC-721/ERC-1155 Callback Revert on Delegated EOA**
  - **D:** `safeTransferFrom` to delegated EOA triggers `onERC721Received`/`onERC1155Received` (recipient has code). If delegate doesn't implement callback, transfer reverts — breaks distribution loops and airdrops.
  - **FP:** Uses `transferFrom` (no callback). Fallback path on callback failure. Skip-and-accrue pattern.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-238

- [ ] **[SAS-AV-073] EIP-7702 tx.origin == msg.sender Bypass**
  - **D:** `require(tx.origin == msg.sender)` as EOA gate or reentrancy guard. Delegated EOA passes check while executing arbitrary contract logic — enables flash loans, atomic governance manipulation, and reentrancy through "EOA-only" functions.
  - **FP:** Additional `require(msg.sender.code.length == 0)` check (delegated EOAs have 23-byte `0xef0100` stub). Function protected by time-lock, multi-sig, or past-block snapshot.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-239

- [ ] **[SAS-AV-074] EIP-7702 Whitelist / Allowlist Privilege Borrowing**
  - **D:** Whitelisted address signs EIP-7702 delegation. Attacker includes that authorization in their tx, calls the delegated address — target contract sees `msg.sender == whitelisted_address`. One phished signature becomes a permanent gateway for unlimited actors.
  - **FP:** Access control rejects delegation designator prefix (`0xef0100`). Whitelist requires per-call signature, not just address check.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-284

- [ ] **[SAS-AV-075] Nonce Not Incremented on Reverted Execution**
  - **D:** Meta-tx nonce checked before execution but incremented only on success. Reverted inner call leaves nonce unchanged — same signed message replayable until it succeeds.
  - **FP:** Nonce incremented before execution (CEI). Incremented in both success/failure paths. Deadline-based expiry.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-286

- [ ] **[SAS-AV-076] EIP-7702 Delegation Persists on Transaction Revert**
  - **D:** Delegation designator is set BEFORE transaction execution. If tx body reverts, delegation is NOT rolled back — EOA permanently has new code despite reverted state changes.
  - **FP:** Delegation requires EOA holder's explicit signature. Wallet UI shows active delegation status.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-296

- [ ] **[SAS-AV-077] Delegation to address(0) Blocks Token Transfers**
  - **D:** Delegating to `address(0)` causes `_update` hooks to revert modifying zero-address checkpoint. All transfers/burns for that holder permanently revert.
  - **FP:** Delegation to `address(0)` treated as undelegation. Hook skips checkpoint when delegate is zero. OZ Votes handles this.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-309

- [ ] **[SAS-AV-078] EIP-7702 Storage Collision on Redelegation**
  - **D:** EOA redelegates from Contract A to Contract B. Storage persists and is reinterpreted under B's layout — corruption, privilege escalation, or fund loss.
  - **FP:** ERC-7201 namespaced storage used. ERC-7779 redelegation process followed. Delegate has no persistent storage dependency.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-317

- [ ] **[SAS-AV-079] EIP-7702 Delegation Initialization Front-Run**
  - **D:** EOA delegates to smart wallet requiring separate `initialize(owner)` call. Attacker front-runs with victim's authorization, calls `initialize()` first — takes ownership of EOA's wallet and assets.
  - **FP:** Delegation and initialization bundled atomically. Owner derived from authorization signature via `ecrecover`. No permissionless `initialize()` step.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-321
