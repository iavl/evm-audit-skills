<!-- GENERATED FILE: source is ../../../data/canonical-checks.json; do not edit by hand. -->
# ERC4337 Account Abstraction Security Checklist

Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.
Global FP/proof obligations live in the Review Contract; only check-specific gates and proofs are repeated below.

## Wallet Account Factory

- [ ] **[EVM-ERC4337-001] Factory must use CREATE2** _(exploit-pattern; medium)_: Factories using CREATE have nonce-dependent deployment. Reorgs change the nonce, deploying the wallet at a different address. Users who sent funds to the pre-computed address lose them. Look for: factory using `new Wallet()` without `salt`. [ERC4337 checklist]
  - **Provenance:** ERC4337 checklist

- [ ] **[EVM-ERC4337-002] Factory must return address even if already deployed** _(exploit-pattern; medium)_: If `createAccount()` reverts when the wallet exists, it breaks bundler workflows. The factory must return the deterministic address whether the wallet exists or not. Look for: factory createAccount that reverts on existing accounts. [ERC4337 checklist]
  - **Provenance:** ERC4337 checklist

- [ ] **[EVM-ERC4337-003] Attacker deploys wallet with different credentials** _(exploit-pattern; medium)_: If the generated wallet address doesn't depend on the initial owner/signature, an attacker can deploy the wallet first with their own keys and control it. The initial signature MUST be part of the CREATE2 salt. Look for: CREATE2 salt that doesn't include owner address or initial signer. [Code4rena/Biconomy H-03]
  - **Provenance:** Code4rena/Biconomy H-03

- [ ] **[EVM-ERC4337-004] Factory stake unstakeDelay griefing** _(exploit-pattern; medium)_: If anyone can add stake to the factory's entrypoint, they can set `unstakeDelay` to `type(uint256).max`, permanently preventing unstaking. Look for: factory stake functions without access control on delay parameter. [ERC4337 checklist]
  - **Provenance:** ERC4337 checklist

## Wallet Account

- [ ] **[EVM-ERC4337-005] Implementation contract initializable by attacker** _(exploit-pattern; medium)_: If the implementation contract's `initialize()` isn't called or protected, an attacker can front-run initialization and gain ownership. On UUPS implementations, this can lead to `selfdestruct` of the implementation, bricking all proxies. Look for: implementation contracts without `_disableInitializers()` in constructor. [Code4rena/Biconomy H-01, Ambire M-05]
  - **Provenance:** Code4rena/Biconomy H-01, Ambire M-05

- [ ] **[EVM-ERC4337-006] Direct execution bypasses EntryPoint** _(exploit-pattern; medium)_: If the wallet can execute transactions directly (not through EntryPoint), it must re-implement all validation (signature, nonce, gas). Missing any check enables arbitrary execution. Look for: `execute()` functions callable without going through EntryPoint that lack full signature validation. [Code4rena/Biconomy H-04]
  - **Provenance:** Code4rena/Biconomy H-04

- [ ] **[EVM-ERC4337-007] UserOperation hash must bind every execution-affecting field** _(exploit-pattern; medium)_: Custom hashing that omits sender, nonce, chain ID, calldata, gas limits, paymaster data, or uses ambiguous packing can make different operations share a digest. Look for: hand-rolled `getHash()` implementations instead of the EntryPoint-defined hash, `abi.encodePacked` over dynamic fields, or fields used during execution but absent from the signed digest. [ERC-4337](https://eips.ethereum.org/EIPS/eip-4337)
  - **Provenance:** [https://eips.ethereum.org/EIPS/eip-4337](https://eips.ethereum.org/EIPS/eip-4337); ERC-4337

- [ ] **[EVM-ERC4337-008] Bundler ordering, censorship, and liveness are adversarial** _(exploit-pattern; medium)_: Bundlers can delay, reorder, or omit UserOperations and may expose profitable operations to MEV. Protocol correctness must not rely on a particular bundler, FIFO ordering, or guaranteed inclusion. Look for: state transitions keyed only by arrival order, timing assumptions tied to one bundler, or no nonce/expiry/replay handling for delayed operations. [ERC-4337](https://eips.ethereum.org/EIPS/eip-4337)
  - **Provenance:** [https://eips.ethereum.org/EIPS/eip-4337](https://eips.ethereum.org/EIPS/eip-4337); ERC-4337

- [ ] **[EVM-ERC4337-009] `validateUserOp` must return SIG_VALIDATION_FAILED, not revert** _(exploit-pattern; medium)_: Per spec, signature mismatches should return the sentinel value `SIG_VALIDATION_FAILED`. Reverting breaks bundler behavior and wastes gas. Look for: `revert` in `validateUserOp` for invalid signatures. [ERC4337 checklist]
  - **Provenance:** ERC4337 checklist

- [ ] **[EVM-ERC4337-010] ERC-1271 cross-account signature replay** _(exploit-pattern; medium)_: If `isValidSignature()` checks that "any owner has signed the hash" without binding to the specific account (via EIP-712 with `verifyingContract = address(this)`), signatures can be replayed across accounts that share owners. Look for: `isValidSignature` that doesn't alter the hash with the account address. [ERC4337 checklist]
  - **Provenance:** ERC4337 checklist

- [ ] **[EVM-ERC4337-011] `tx.origin` breaks for smart wallets** _(exploit-pattern; medium)_: Applications that use `require(tx.origin == msg.sender)` to block contracts will block all smart wallets. Applications must not rely on this pattern. Look for: `tx.origin == msg.sender` checks. [ERC4337 checklist]
  - **Provenance:** ERC4337 checklist

- [ ] **[EVM-ERC4337-012] Fixed gas assumptions (21000 for transfer)** _(exploit-pattern; medium)_: Smart wallet transactions cost more than 21000 gas. Applications relying on exact gas costs will underestimate for AA wallets. Look for: hardcoded gas estimates like 21000. [ERC4337 checklist]
  - **Provenance:** ERC4337 checklist

## Paymaster

- [ ] **[EVM-ERC4337-013] VerifyingPaymaster signature replay** _(exploit-pattern; medium)_: If the paymaster's signed approval doesn't include nonce, chain ID, and sender, the signature can be replayed to drain the paymaster's deposit. Look for: paymaster validation hash that omits any of: sender, nonce, chainid, validUntil, validAfter. [Code4rena/Biconomy H-05]
  - **Provenance:** Code4rena/Biconomy H-05

- [ ] **[EVM-ERC4337-014] Cross-chain paymaster replay** _(exploit-pattern; medium)_: If the paymaster signature doesn't include chain ID, it can be used on any chain where the paymaster is deployed. Look for: missing `block.chainid` in paymaster signature hash. [Code4rena/Biconomy M-03]
  - **Provenance:** Code4rena/Biconomy M-03

- [ ] **[EVM-ERC4337-015] EntryPoint v0.6 postOp bug** _(exploit-pattern; medium)_: A bug in v0.6 causes short revert messages in `postOp()` to revert the entire bundle instead of calling the second `postOp()`. Look for: v0.6 entrypoint integration with custom postOp logic. [ERC4337 checklist]
  - **Provenance:** ERC4337 checklist

- [ ] **[EVM-ERC4337-016] DoS via free transactions** _(exploit-pattern; medium)_: Paymasters enable gas-free transactions. An attacker can spam transactions through the paymaster to drain its deposit. Look for: paymasters without rate limiting or sender validation. [beirao AA-01]
  - **Provenance:** beirao AA-01

## Session Keys & Modules

- [ ] **[EVM-ERC4337-017] Session key exposure on frontend** _(exploit-pattern; medium)_: Session signer wallet private keys exposed in frontend JavaScript allow account takeover (Cardex compromise). Look for: session key generation or storage in client-side code. [ERC4337 checklist]
  - **Provenance:** ERC4337 checklist

- [ ] **[EVM-ERC4337-018] Module storage overlap with delegatecall** _(exploit-pattern; medium)_: If the wallet uses `delegatecall`-based modules, module storage must not overlap with wallet storage. Look for: modules using storage slots that conflict with ERC1967 proxy slots or wallet state. [ERC4337 checklist]
  - **Provenance:** ERC4337 checklist

- [ ] **[EVM-ERC4337-019] Fallback handler set to `address(this)`** _(exploit-pattern; medium)_: If the wallet's fallback handler can be set to the wallet itself, it creates a self-referencing loop that can be exploited. Look for: fallback handler setter without `handler != address(this)` check. [Code4rena/Ambire L-02]
  - **Provenance:** Code4rena/Ambire L-02

## ERC-6492 & Predeploy Signatures

- [ ] **[EVM-ERC4337-020] Predeploy contract signature validation** _(exploit-pattern; medium)_: Applications verifying signatures from smart wallets should support ERC-6492 for wallets not yet deployed. Without it, counterfactual wallet signatures fail verification. Look for: `isValidSignature` callers that don't handle ERC-6492 wrapper format. [ERC4337 checklist]
  - **Provenance:** ERC4337 checklist

## Supplemental Attack Vectors (SAS-AV)

- [ ] **[EVM-ERC4337-021] validateUserOp Signature Not Bound to nonce or chainId** _(exploit-pattern; medium)_: `validateUserOp` reconstructs digest manually (not via `entryPoint.getUserOpHash`) omitting `userOp.nonce` or `block.chainid`. Enables cross-chain or in-chain replay.
  - **Specific FP:** Digest from `entryPoint.getUserOpHash(userOp)` (includes sender, nonce, chainId). Custom digest explicitly includes both.
  - **Provenance:** [SAS-AV-060](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-21

- [ ] **[EVM-ERC4337-022] Banned Opcode in Validation Phase (Simulation-Execution Divergence)** _(exploit-pattern; medium)_: `validateUserOp`/`validatePaymasterUserOp` references `block.timestamp`, `block.number`, `block.coinbase`, etc. Per ERC-7562, banned in validation.
  - **Specific FP:** Banned opcodes only in execution phase. Entity is staked under ERC-7562 reputation system.
  - **Provenance:** [SAS-AV-061](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-99

- [ ] **[EVM-ERC4337-023] Paymaster Gas Penalty Undercalculation** _(exploit-pattern; medium)_: Paymaster prefund formula omits 10% EntryPoint penalty on unused execution gas (`postOpUnusedGasPenalty`). Large `executionGasLimit` with low usage drains paymaster deposit.
  - **Specific FP:** Prefund explicitly adds unused-gas penalty. Conservative overestimation covers worst case.
  - **Provenance:** [SAS-AV-062](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-107

- [ ] **[EVM-ERC4337-024] Paymaster ERC-20 Payment Deferred to postOp Without Pre-Validation** _(exploit-pattern; medium)_: `validatePaymasterUserOp` doesn't transfer/lock tokens — payment deferred to `postOp`. User can revoke allowance between validation and execution.
  - **Specific FP:** Tokens transferred/locked during `validatePaymasterUserOp`. `postOp` only refunds excess.
  - **Provenance:** [SAS-AV-063](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-121

- [ ] **[EVM-ERC4337-025] validateUserOp Missing EntryPoint Caller Restriction** _(exploit-pattern; medium)_: `validateUserOp` is `public`/`external` without `require(msg.sender == entryPoint)`.
  - **Specific FP:** `require(msg.sender == address(_entryPoint))` or `onlyEntryPoint` modifier present.
  - **Provenance:** [SAS-AV-064](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-149

- [ ] **[EVM-ERC4337-026] EIP-7702 Cross-Chain Delegation Replay** _(exploit-pattern; medium)_: EIP-7702 authorization signatures for EOA-to-contract delegation miss `chainId` in the signed tuple. Attacker replays the same delegation signature on another chain, hijacking the EOA's execution context on chains the user never intended to delegate on.
  - **Specific FP:** `chainId` included in EIP-7702 authorization tuple. Wallet UI displays target chain before signing. Per-chain delegation with separate signatures.
  - **Provenance:** [SAS-AV-065](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-208/316

- [ ] **[EVM-ERC4337-027] EIP-7702 Delegate Hijacking** _(exploit-pattern; medium)_: Malicious contract becomes an EOA's delegate via social engineering or phishing. Once delegated, all transactions to the EOA execute the malicious contract's code in the EOA's context — draining funds, approving tokens, or modifying state. Persists until the user explicitly revokes delegation.
  - **Specific FP:** Delegation target is a well-known, audited contract (e.g., Safe module). Wallet prompts clearly distinguish delegation from normal signing. Revocation mechanism is accessible and documented. Time-limited delegation with automatic expiry.
  - **Provenance:** [SAS-AV-066](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-209/210

- [ ] **[EVM-ERC4337-028] EIP-7702 EOA Nested Reentrancy** _(exploit-pattern; medium)_: With EIP-7702, EOAs can have code. A delegated EOA receiving ETH or tokens triggers fallback/receive in the delegate contract, creating new reentrancy surfaces that didn't exist when the counterparty was a plain EOA. Protocols assuming EOAs can't have callbacks are vulnerable.
  - **Specific FP:** `nonReentrant` on all external-call-bearing functions regardless of counterparty type. No assumption that `tx.origin == msg.sender` means "safe EOA." CEI pattern followed universally.
  - **Provenance:** [SAS-AV-067](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-211

- [ ] **[EVM-ERC4337-029] ERC-4337 Paymaster Drain via Crafted UserOperations** _(exploit-pattern; medium)_: Attacker crafts UserOperations that pass paymaster validation but consume maximum gas during execution. Paymaster pays for gas but the operation accomplishes nothing useful for the paymaster's business model. Repeated submissions drain the paymaster's deposit in the EntryPoint.
  - **Specific FP:** Paymaster validates operation purpose (not just signature). Gas limits per UserOperation and per-user rate limits enforced. Paymaster deposit monitored with automatic pause at low threshold. Off-chain simulation before on-chain validation.
  - **Provenance:** [SAS-AV-068](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-212

- [ ] **[EVM-ERC4337-030] ERC-4337 Validation-Execution Phase Confusion** _(exploit-pattern; medium)_: Logic that should only run during validation phase (signature checks, nonce verification) executes during the execution phase or vice versa. Banned opcodes in validation (ERC-7562) cause bundler rejection, while missing validation in execution allows unauthorized operations.
  - **Specific FP:** Clear separation between `validateUserOp` and execution functions. No storage access in validation beyond sender's associated storage. Compliance with ERC-7562 opcode restrictions verified. Bundler simulation tests pass.
  - **Provenance:** [SAS-AV-069](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-213

- [ ] **[EVM-ERC4337-031] EIP-7702 Code Inspection Opcode Invalidation** _(exploit-pattern; medium)_: `extcodesize`, `extcodehash`, `extcodecopy` on delegated EOA operate on the 23-byte `0xef0100` delegation stub, not the delegate's code. `isContract()` checks misroute delegated EOAs. `extcodehash` comparisons against known implementation hashes fail. Proxy detection and ERC-1167 clone verification return unexpected results.
  - **Specific FP:** No security-critical branching on `extcodesize`/`extcodehash`. Uses `CODESIZE`/`CODECOPY` within execution context (which follow delegation) rather than `EXT*` variants.
  - **Provenance:** [SAS-AV-070](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-236

- [ ] **[EVM-ERC4337-032] EIP-7702 Dual Signature Validation Confusion** _(exploit-pattern; medium)_: Delegated EOA supports both ECDSA (private key) and ERC-1271 (`isValidSignature` from delegate). Protocol checking only one path lets attacker exploit the other. Signature replay across redelegation — message signed under Delegate A interpreted differently by Delegate B.
  - **Specific FP:** OZ `SignatureChecker.isValidSignatureNow` used. ERC-1271 checked first for accounts with code, ECDSA fallback for codeless. Signatures include delegate address in EIP-712 domain.
  - **Provenance:** [SAS-AV-071](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-237

- [ ] **[EVM-ERC4337-033] EIP-7702 ERC-721/ERC-1155 Callback Revert on Delegated EOA** _(exploit-pattern; medium)_: `safeTransferFrom` to delegated EOA triggers `onERC721Received`/`onERC1155Received` (recipient has code). If delegate doesn't implement callback, transfer reverts — breaks distribution loops and airdrops.
  - **Specific FP:** Uses `transferFrom` (no callback). Fallback path on callback failure. Skip-and-accrue pattern.
  - **Provenance:** [SAS-AV-072](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-238

- [ ] **[EVM-ERC4337-034] EIP-7702 tx.origin == msg.sender Bypass** _(exploit-pattern; medium)_: `require(tx.origin == msg.sender)` as EOA gate or reentrancy guard. Delegated EOA passes check while executing arbitrary contract logic — enables flash loans, atomic governance manipulation, and reentrancy through "EOA-only" functions.
  - **Specific FP:** Additional `require(msg.sender.code.length == 0)` check (delegated EOAs have 23-byte `0xef0100` stub). Function protected by time-lock, multi-sig, or past-block snapshot.
  - **Provenance:** [SAS-AV-073](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-239

- [ ] **[EVM-ERC4337-035] EIP-7702 Whitelist / Allowlist Privilege Borrowing** _(exploit-pattern; medium)_: Whitelisted address signs EIP-7702 delegation. Attacker includes that authorization in their tx, calls the delegated address — target contract sees `msg.sender == whitelisted_address`. One phished signature becomes a permanent gateway for unlimited actors.
  - **Specific FP:** Access control rejects delegation designator prefix (`0xef0100`). Whitelist requires per-call signature, not just address check.
  - **Provenance:** [SAS-AV-074](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-284

- [ ] **[EVM-ERC4337-036] Nonce Not Incremented on Reverted Execution** _(exploit-pattern; medium)_: Meta-tx nonce checked before execution but incremented only on success. Reverted inner call leaves nonce unchanged — same signed message replayable until it succeeds.
  - **Specific FP:** Nonce incremented before execution (CEI). Incremented in both success/failure paths. Deadline-based expiry.
  - **Provenance:** [SAS-AV-075](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-286

- [ ] **[EVM-ERC4337-037] EIP-7702 Delegation Persists on Transaction Revert** _(exploit-pattern; medium)_: Delegation designator is set BEFORE transaction execution. If tx body reverts, delegation is NOT rolled back — EOA permanently has new code despite reverted state changes.
  - **Specific FP:** Delegation requires EOA holder's explicit signature. Wallet UI shows active delegation status.
  - **Provenance:** [SAS-AV-076](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-296

- [ ] **[EVM-ERC4337-038] Delegation to address(0) Blocks Token Transfers** _(exploit-pattern; medium)_: Delegating to `address(0)` causes `_update` hooks to revert modifying zero-address checkpoint. All transfers/burns for that holder permanently revert.
  - **Specific FP:** Delegation to `address(0)` treated as undelegation. Hook skips checkpoint when delegate is zero. OZ Votes handles this.
  - **Provenance:** [SAS-AV-077](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-309

- [ ] **[EVM-ERC4337-039] EIP-7702 Storage Collision on Redelegation** _(exploit-pattern; medium)_: EOA redelegates from Contract A to Contract B. Storage persists and is reinterpreted under B's layout — corruption, privilege escalation, or fund loss.
  - **Specific FP:** ERC-7201 namespaced storage used. ERC-7779 redelegation process followed. Delegate has no persistent storage dependency.
  - **Provenance:** [SAS-AV-078](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-317

- [ ] **[EVM-ERC4337-040] EIP-7702 Delegation Initialization Front-Run** _(exploit-pattern; medium)_: EOA delegates to smart wallet requiring separate `initialize(owner)` call. Attacker front-runs with victim's authorization, calls `initialize()` first — takes ownership of EOA's wallet and assets.
  - **Specific FP:** Delegation and initialization bundled atomically. Owner derived from authorization signature via `ecrecover`. No permissionless `initialize()` step.
  - **Provenance:** [SAS-AV-079](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-321
