<!-- GENERATED FILE: source is ../../../data/canonical-checks.json; do not edit by hand. -->
# General Solidity/EVM Security Checklist

Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.
Global FP/proof obligations live in the Review Contract; only check-specific gates and proofs are repeated below.

## External Calls & Low-Level Interactions

- [ ] **[EVM-GEN-001] Call to non-existent address returns true** _(exploit-pattern; medium)_: A low-level `.call()` to an address with no deployed code returns `(true, "")`. If you're relying on call success without verifying target has code via `extcodesize > 0` or `address.code.length > 0`, you'll silently accept no-ops. Look for: any `.call()` where the target address is user-supplied or computed, including addresses derived from configuration or CREATE2 calculation. [beirao E-05, Tamjid C34]
  - **Provenance:** beirao E-05, Tamjid C34

- [ ] **[EVM-GEN-002] Grief attack via returndata bombing** _(semantic; high)_: When making `.call()` to an unknown address, the callee can return a massive `bytes` payload. Solidity automatically copies all returndata into memory, consuming gas quadratically. An attacker returns megabytes of data to grief the caller. Fix: use inline assembly to limit returndata copy size. Look for: `.call()` to untrusted addresses without assembly returndata handling. [beirao E-04]
  - **Provenance:** beirao E-04

- [ ] **[EVM-GEN-003] Fixed gas in `.call{gas: X}()`** _(semantic; high)_: Hardcoding gas amounts (e.g., `addr.call{gas: 2300}("")`) breaks when opcode costs change across hard forks (see EIP-1884 which repriced SLOAD). Also breaks on L2s with different gas schedules. Look for: any `.call` or `.send` with explicit gas amounts. [beirao E-03]
  - **Provenance:** beirao E-03

- [ ] **[EVM-GEN-004] `msg.value` persistence in loops, multicall, and delegatecall** _(semantic; high)_: `msg.value` remains the original call value throughout a transaction. A `multicall(bytes[] calldata data)` loop, batch executor, or delegatecall-reachable payable function can therefore count the same ETH multiple times; an attacker can send 1 ETH and receive credit for N spends. Look for: `msg.value` used inside loops, batch/multicall execution, or payable functions reachable through delegatecall. [beirao E-17, L-03, G-24, Tamjid C28, C29, RareSkills]
  - **Provenance:** beirao E-17, L-03, G-24, Tamjid C28, C29, RareSkills

- [ ] **[EVM-GEN-005] `try/catch` does not make external-call failure harmless** _(semantic; high)_: A failure in an external call, including an out-of-gas failure in that call, can enter a catch block when the caller retains enough gas to execute it. `try/catch` only covers the external call or contract creation expression; errors in surrounding expressions, return-data decoding, or the catch block itself are not automatically handled.
  - **Trigger:** Security-sensitive behavior depends on the success or catch branch of an external call.
  - **Risk:** Security-critical logic can still fail open or run out of gas if it assumes the success branch, ignores catch behavior, or performs unsafe work before or inside the catch path.
  - **Detection:** Trace gas forwarding, external-call failure, return-data decoding, and every statement in the success and catch paths.
  - **Specific FP:** The catch branch preserves the required invariant, has enough bounded gas, and all errors outside the covered external expression are handled separately.
  - **Specific proof:** Use a controlled callee to trigger revert and out-of-gas cases and verify state deltas and post-catch behavior.
  - **Provenance:** beirao G-18; [Solidity Language Reference](https://docs.soliditylang.org/en/latest/control-structures.html#try-catch)

- [ ] **[EVM-GEN-006] `abi.encodePacked` with 2+ dynamic types = hash collisions** _(exploit-pattern; medium)_: `abi.encodePacked(string a, string b)` can collide: `encodePacked("a","bc") == encodePacked("ab","c")`. Look for: `keccak256(abi.encodePacked(...))` with multiple `string`, `bytes`, or dynamic array arguments. Fix: use `abi.encode()`. [beirao G-15, SWC-133]
  - **Provenance:** beirao G-15, SWC-133

- [ ] **[EVM-GEN-007] Delegatecall to mutable or storage-incompatible targets** _(exploit-pattern; medium)_: Delegatecall executes target code in the caller's storage and execution context. The security question is whether the target is mutable or untrusted, whether upgrades are authorized, whether storage layouts are compatible, and whether selector/context assumptions remain valid.
  - **Trigger:** The implementation executes delegatecall to a target whose code, upgrade path, storage layout, or caller context is not fully constrained.
  - **Risk:** An attacker-controlled or incorrectly upgraded delegatecall target can overwrite caller state, bypass authorization, expose selectors, or violate storage and execution-context invariants.
  - **Detection:** Trace target address controllability, implementation trust and upgrade authorization, storage compatibility, selector exposure, and msg.sender/msg.value assumptions.
  - **Specific FP:** A proxy or library use is explicitly authorized, the implementation identity and storage layout are compatible, and all reachable upgrade paths preserve the invariant.
  - **Specific proof:** Demonstrate a reachable target change, storage collision, authorization bypass, or context mismatch with a deterministic trace or executable PoC.
  - **Provenance:** beirao E-09, E-10

- [ ] **[EVM-GEN-008] ETH transfer via `transfer()`/`send()` is 2300 gas** _(exploit-pattern; medium)_: This fails for contracts with non-trivial `receive()`/`fallback()` functions and fails on some L2s (zkSync). Always use `.call{value: x}("")`. Look for: `.transfer()` or `.send()`. [beirao E-07, multichain-auditor]
  - **Provenance:** beirao E-07, multichain-auditor

- [ ] **[EVM-GEN-009] Unchecked return of low-level `.call()`** _(exploit-pattern; medium)_: `(bool success, ) = addr.call(data)` — if `success` isn't checked, the call fails silently. Look for: `.call()` without `require(success)`. [SWC-104]
  - **Provenance:** SWC-104

## Force-Feeding Attacks

- [ ] **[EVM-GEN-010] Force-feed via `selfdestruct`** _(exploit-pattern; medium)_: `selfdestruct(payable(target))` sends the contract's ETH balance to `target` regardless of whether target has `receive()`/`fallback()`. This breaks any invariant based on `address(this).balance`. Look for: any comparison or calculation using `address(this).balance`. [beirao G-03]
  - **Provenance:** beirao G-03

- [ ] **[EVM-GEN-011] Force-feed via pre-computed CREATE2 address** _(exploit-pattern; medium)_: ETH can be sent to a CREATE2 address before the contract is deployed there. The newly deployed contract will have a non-zero ETH balance from block 0 that it didn't expect. Look for: balance assumptions in constructors/initializers. [beirao G-03]
  - **Provenance:** beirao G-03

- [ ] **[EVM-GEN-012] Coinbase force-feeding** _(heuristic; contextual)_: A validator/miner can set their coinbase to any address, force-feeding the block reward. Look for: balance-based invariants in contracts that could be targeted by validators. [beirao G-03]
  - **Provenance:** beirao G-03

- [ ] **[EVM-GEN-013] Direct token transfers bypass accounting** _(exploit-pattern; medium)_: Sending ERC20 tokens directly via `transfer()` to a contract (not through its deposit function) inflates `balanceOf(address(this))` without updating internal accounting. Look for: any use of `token.balanceOf(address(this))` as a source of truth instead of internal tracking variables. [beirao V-01, V-02, G-07]
  - **Provenance:** beirao V-01, V-02, G-07

## Pause Mechanism Pitfalls

- [ ] **[EVM-GEN-014] Pausing liquidations = solvency crisis** _(exploit-pattern; medium)_: If a protocol's pause mechanism freezes liquidations, bad debt accumulates silently. When unpaused, cascading liquidations can drain the protocol. Look for: pause modifiers on liquidation functions. [beirao G-09, LEN-06]
  - **Provenance:** beirao G-09, LEN-06

- [ ] **[EVM-GEN-015] Pause front-running** _(exploit-pattern; medium)_: If pausing requires an on-chain transaction, an attacker monitoring the mempool can front-run the pause with a malicious transaction. Look for: security-critical state changes that depend on pause being active. [beirao F-04]
  - **Provenance:** beirao F-04

- [ ] **[EVM-GEN-016] `whenNotPaused` missing from critical functions** _(exploit-pattern; medium)_: Common to add pause to most functions but miss some edge case paths. Look for: functions that modify state or transfer value that lack the pause modifier when other similar functions have it. [beirao G-09]
  - **Provenance:** beirao G-09

- [ ] **[EVM-GEN-017] Pause can permanently brick the contract** _(exploit-pattern; medium)_: If pause has no unpause mechanism, or if the unpause requires conditions that can't be met while paused, the contract is bricked forever. Look for: circular dependencies in pause/unpause logic. [beirao G-09]
  - **Provenance:** beirao G-09

## Reentrancy (Non-Obvious)

- [ ] **[EVM-GEN-018] ERC721 `safeMint`/`safeTransferFrom` callbacks** _(exploit-pattern; medium)_: These call `onERC721Received()` on the recipient, creating reentrancy vectors. Same for ERC1155's `_safeTransferFrom` with `onERC1155Received`. Look for: `_safeMint()`, `safeTransferFrom()` without reentrancy guards or CEI pattern. [beirao NFT-02, NFT-03]
  - **Provenance:** beirao NFT-02, NFT-03

- [ ] **[EVM-GEN-019] ERC777 pre/post transfer hooks** _(exploit-pattern; medium)_: ERC777 tokens call `tokensToSend()` (before transfer) and `tokensReceived()` (after transfer). Both are reentrancy vectors that bypass `nonReentrant` if the modifier is only on the outer function. Look for: any protocol that accepts arbitrary ERC20 tokens — it might receive an ERC777. [beirao FT-08]
  - **Provenance:** beirao FT-08

- [ ] **[EVM-GEN-020] Reentrancy guard must precede modifiers that can yield control** _(exploit-pattern; medium)_: A nonReentrant guard must be established before any preceding modifier can yield external control or mutate reentrancy-sensitive state. Modifier order is not itself a vulnerability when earlier modifiers are purely local and non-yielding.
  - **Trigger:** An externally reachable function combines nonReentrant with other modifiers whose expanded code may call out, invoke callbacks, or mutate reentrancy-sensitive state.
  - **Risk:** A yielding or state-changing modifier before the guard can create a reentrant path before the lock is set and violate the protected invariant.
  - **Detection:** Expand modifiers in execution order and identify external control flow or sensitive state mutation before the guard is established.
  - **Specific FP:** Every modifier before nonReentrant is local, non-yielding, and does not mutate state relied on by the guarded operation.
  - **Specific proof:** Use a callback-capable callee or a deterministic trace to show whether control can reenter before the lock and whether the protected invariant changes.
  - **Provenance:** beirao G-17

## Merkle Tree Pitfalls

- [ ] **[EVM-GEN-021] Merkle claim beneficiary must be bound to the payout** _(exploit-pattern; medium)_: A publicly submitted Merkle proof can be copied, but copying is exploitable only when the caller can redirect the beneficiary's value. Bind the authorized recipient into the leaf or use the committed recipient for payout; a copied proof that merely lets another account pay gas is not a theft finding.
  - **Trigger:** A claim path accepts a Merkle proof and an amount or recipient without proving that the caller is the committed beneficiary or that payout uses the committed recipient.
  - **Risk:** If the proof does not bind the beneficiary and payout follows msg.sender or another attacker-controlled address, a front-runner can claim another user's allocation.
  - **Detection:** Trace leaf construction, proof verification, claimant/recipient checks, and the final token recipient; separate gas sponsorship from value redirection.
  - **Specific FP:** The leaf commits an immutable recipient and payout uses that recipient, or an independent authorization prevents a copied proof from redirecting value.
  - **Specific proof:** Submit the same valid proof from a different account and show a changed beneficiary or asset transfer; otherwise document the recipient-binding invariant.
  - **Provenance:** beirao MT-01, RareSkills
  - **Related:** EVM-GEN-109

- [ ] **[EVM-GEN-022] Zero hash as valid proof** _(exploit-pattern; medium)_: Passing `bytes32(0)` may satisfy poorly constructed Merkle trees where empty nodes are represented as zero. Look for: Merkle verification that doesn't reject zero-hash leaves. [beirao MT-04]
  - **Provenance:** beirao MT-04

- [ ] **[EVM-GEN-023] Duplicate leaves enable double-claim** _(exploit-pattern; medium)_: If the same data appears as two leaves in the tree, the same proof may allow claiming twice. Look for: trees constructed without deduplication. [beirao MT-05]
  - **Provenance:** beirao MT-05

- [ ] **[EVM-GEN-109] Merkle leaf encoding must be domain-separated** _(exploit-pattern; medium)_: Merkle verification must use an unambiguous, domain-separated leaf encoding. Unhashed leaves, leaves that can equal an internal node or the root, and ambiguous concatenation can admit alternate interpretations even when claimant binding is correct.
  - **Trigger:** A Merkle tree hashes leaves without an explicit domain separator or accepts a leaf encoding that can collide with an internal node or root.
  - **Risk:** Ambiguous leaf/node encodings can make a proof valid for an unintended claim or tree structure and defeat the intended authorization invariant.
  - **Detection:** Inspect leaf hashing, field boundaries, domain separation, sorted-pair handling, and rejection of degenerate leaf/root constructions.
  - **Specific FP:** The tree construction specifies an unambiguous hash domain and field encoding, and verification enforces the same construction for every proof.
  - **Specific proof:** Construct an alternate leaf or node interpretation accepted by the verifier, or provide a deterministic encoding proof that the ambiguity is impossible.
  - **Provenance:** beirao MT-02, MT-03, RareSkills
  - **Related:** EVM-GEN-021

## Reveal-Gap Steering (value public before it's consumed)

- [ ] **[EVM-GEN-024] A value revealed before the tx that consumes it can steer the outcome** _(exploit-pattern; medium)_: Any two-phase flow where a value becomes public before the code that acts on it runs — a VRF word sitting in the mempool, an oracle answer, a commit-reveal reveal, any request-then-fulfill — is exploitable if the consuming step reads *mutable* state to decide the outcome. The value can be provably unbiasable and the callback sender-authenticated and it is still exploitable, because the bias is not in the value — it is in the state the code reads *after* the value is already known. Rule to verify: the outcome must be a pure function of state committed at or before the moment the value was fixed. If any actor can change that state in the gap (deposit, mint, withdraw, reprice, reorder), the outcome is steerable. Check both directions of any window-lock, and confirm that a smooth price/amount guard is not being trusted to protect a discontinuous selection (`% N`). Look for: a callback / step-2 whose result depends on storage that an external function can mutate between reveal and execution. [Source: FWA / TokenWorks CryptoPunk #5450 incident, 2026]
  - **Provenance:** Source: FWA / TokenWorks CryptoPunk #5450 incident, 2026

## Code Structure Issues

- [ ] **[EVM-GEN-025] Withdraw should undo ALL deposit state changes** _(exploit-pattern; medium)_: For every state variable modified during `deposit()`, there should be a symmetric reversal in `withdraw()`. Asymmetries cause accounting drift. Look for: compare `deposit` and `withdraw` functions line by line for state variable coverage. [beirao G-26]
  - **Provenance:** beirao G-26

- [ ] **[EVM-GEN-026] Inconsistent logic across duplicated implementations** _(exploit-pattern; medium)_: When the same logic is implemented in multiple places (e.g., calculating fees in both `deposit` and `withdraw`), they may diverge over time. Look for: duplicated business logic that should be a shared internal function. [beirao G-01]
  - **Provenance:** beirao G-01

- [ ] **[EVM-GEN-027] Documentation-code mismatch** _(exploit-pattern; medium)_: Comments describing one thing while code does another. Particularly dangerous when the comment matches the spec but the code doesn't. Look for: NatSpec/comments that describe different behavior than the implementation. [beirao F-07, G-12]
  - **Provenance:** beirao F-07, G-12

- [ ] **[EVM-GEN-028] Deployment scripts not checked** _(exploit-pattern; medium)_: Bugs in deployment scripts (wrong constructor args, missing initialization calls, wrong chain configs) are as dangerous as bugs in contracts. Look for: deployment scripts that aren't tested or reviewed. [beirao G-13]
  - **Provenance:** beirao G-13

## Array and Loop Hazards

- [ ] **[EVM-GEN-029] Unbounded loops with external calls = DoS** _(exploit-pattern; medium)_: If a loop iterates over a user-growable array and makes external calls (especially transfers), an attacker can grow the array until the function exceeds block gas limit. Look for: `for` loops over dynamic arrays that contain `.call()`, `.transfer()`, or `safeTransfer()`. [beirao G-04, L-02]
  - **Provenance:** beirao G-04, L-02

- [ ] **[EVM-GEN-030] Duplicate addresses in calldata arrays** _(exploit-pattern; medium)_: When a function takes `address[] calldata addresses` and processes each one, duplicates can cause double-counting or double-payment. Look for: functions that iterate over user-provided address arrays without dedup checks. [beirao F-10]
  - **Provenance:** beirao F-10

- [ ] **[EVM-GEN-031] First iteration edge case** _(heuristic; contextual)_: The first iteration of a loop may behave differently (e.g., empty state, uninitialized variables). Look for: loop body logic that assumes prior iterations have run. [beirao L-01]
  - **Provenance:** beirao L-01

- [ ] **[EVM-GEN-032] Parallel arrays must have matching lengths** _(exploit-pattern; medium)_: Functions that process related arrays must reject mismatched lengths before indexing or applying values. Otherwise callers can trigger out-of-bounds reverts or leave only part of a state transition applied. Look for: functions accepting `ids` and `amounts`, or any paired arrays, without an explicit equality check. [Source: Auditmos `audit-state-validation`, pattern #7](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-state-validation/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
  - **Provenance:** [AUDITMOS-STATE-VALIDATION-7](https://github.com/auditmos/skills); [https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-state-validation/reference.md](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-state-validation/reference.md); Source: Auditmos `audit-state-validation`, pattern #7

## Block/Time Assumptions

- [ ] **[EVM-GEN-033] `block.timestamp` only reliable for long intervals** _(exploit-pattern; medium)_: Validators can manipulate timestamps by several seconds. Don't use for intervals shorter than ~15 minutes. Look for: time-sensitive logic with sub-minute precision. [beirao G-28]
  - **Provenance:** beirao G-28

- [ ] **[EVM-GEN-034] Block cadence varies across chains and upgrades** _(semantic; high)_: Block production cadence and the relationship between block numbers and wall-clock time differ across chains and can change with protocol upgrades. Do not encode a chain's observed interval as a universal time unit.
  - **Trigger:** The implementation converts block-number deltas into seconds or selects a fixed block count to represent elapsed time.
  - **Risk:** A block-count time proxy can shorten or extend deadlines, accrual periods, auctions, or cooldowns beyond the intended security window.
  - **Detection:** Compare every block-based duration with the target chain's documented execution model, upgrade policy, and required timestamp tolerance.
  - **Specific FP:** The requirement is deliberately measured in blocks, or timestamp-based bounds make cadence changes harmless.
  - **Specific proof:** Evaluate the effective wall-clock interval under the declared deployment and plausible cadence changes, then test the security invariant.
  - **Provenance:** multichain-auditor, beirao MC-01; [BNB Smart Chain introduction](https://docs.bnbchain.org/bnb-smart-chain/introduction/)

- [ ] **[EVM-GEN-035] Block production and timestamp progress are not uniform** _(semantic; high)_: Block numbers, timestamps, sequencer batches, and parent-chain origins advance according to chain-specific execution rules rather than a universal constant interval. Treat monotonicity, resolution, and liveness as separate assumptions.
  - **Trigger:** Logic uses block numbers or timestamps as if every chain emits one regularly spaced block.
  - **Risk:** A design that assumes constant block progress can accept stale state, skip required observations, or make liveness windows unpredictable.
  - **Detection:** Map the value to its source chain, parent origin, sequencer behavior, and documented timestamp constraints before relying on its resolution or rate.
  - **Specific FP:** The invariant tolerates documented drift and does not depend on a fixed block frequency.
  - **Specific proof:** Replay the relevant path with delayed, batched, or irregular block production and compare the observed state transition with the intended invariant.
  - **Provenance:** multichain-auditor, Arbitrum checklist; [Arbitrum block numbers and time](https://docs.arbitrum.io/arbitrum-essentials/arbitrum-vs-ethereum/block-numbers-and-time)

## Comparison & Logic Operators

- [ ] **[EVM-GEN-036] Off-by-one in comparisons** _(exploit-pattern; medium)_: `<` vs `<=`, `>` vs `>=` — especially in liquidation thresholds, fee boundaries, and time windows. A single off-by-one can make a position unliquidatable or skip fee collection. Look for: boundary comparisons in critical math. [beirao G-29, M-11]
  - **Provenance:** beirao G-29, M-11

- [ ] **[EVM-GEN-037] Incorrect logical operators** _(exploit-pattern; medium)_: `&&` vs `||`, `==` vs `!=`, `!` applied to wrong subexpression. Look for: complex conditional expressions, especially negated ones. [beirao G-30]
  - **Provenance:** beirao G-30

## Multi-Agent Systems

- [ ] **[EVM-GEN-038] All agents could be the same person** _(heuristic; contextual)_: In any system with multiple roles (buyer/seller, borrower/liquidator, proposer/voter), check what happens if one person controls all roles. Self-liquidation for profit, self-trading for rewards, etc. Look for: role-based systems without Sybil resistance. [beirao G-22]
  - **Provenance:** beirao G-22

- [ ] **[EVM-GEN-039] Receiver address pointing to another system contract** _(exploit-pattern; medium)_: If a function takes a `receiver` parameter, what happens if the receiver is another contract in the same system? Look for: user-provided address parameters that could target internal system contracts. [beirao G-31]
  - **Provenance:** beirao G-31

## Solidity Compiler

- [ ] **[EVM-GEN-040] Unchecked blocks need validation** _(exploit-pattern; medium)_: Code in `unchecked { }` bypasses overflow/underflow checks. Every unchecked block must be manually verified for safety. Look for: `unchecked` blocks, especially around user-influenced values. [beirao M-10]
  - **Provenance:** beirao M-10

## General Solidity Footguns (Expanded from Beirao/Tamjid/Multichain-Auditor)

- [ ] **[EVM-GEN-043] Deleting a struct doesn't delete its nested mappings** _(exploit-pattern; medium)_: `delete myStruct` zeros out the struct fields but any mappings or other dynamic members inside persist in storage. Look for: `delete` on structs containing mappings, where the nested data should also be cleared. [beirao G-06, RareSkills]
  - **Provenance:** beirao G-06, RareSkills

- [ ] **[EVM-GEN-044] Semantic overloading** _(exploit-pattern; medium)_: Using the same variable or return value for multiple meanings (e.g., 0 means "not found" AND "zero balance") creates ambiguity that leads to logic errors. Look for: functions where a zero return could mean success, failure, or absence. [beirao G-11]
  - **Provenance:** beirao G-11

- [ ] **[EVM-GEN-045] Non-existent IDs must not use default state** _(exploit-pattern; medium)_: Functions accepting an ID must verify that its record exists before reading or mutating it. Mapping defaults can make a nonexistent entry look valid, corrupt counters, mark debt as repaid, or apply state changes to an empty record. Look for: `mapping[id]` reads followed by accounting updates without an existence flag or equivalent check. [Source: Auditmos `audit-state-validation`, pattern #5](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-state-validation/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
  - **Provenance:** [AUDITMOS-STATE-VALIDATION-5](https://github.com/auditmos/skills); [https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-state-validation/reference.md](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-state-validation/reference.md); Source: Auditmos `audit-state-validation`, pattern #5

- [ ] **[EVM-GEN-046] `if (receiver == caller)` unexpected behavior** _(exploit-pattern; medium)_: Self-transfers or self-operations may skip important logic (e.g., fee charging, balance validation). Look for: functions where `from == to` or `sender == receiver` isn't handled as a special case. [beirao G-08]
  - **Provenance:** beirao G-08

- [ ] **[EVM-GEN-047] Providing a system address as a user input** _(exploit-pattern; medium)_: A user passes the contract's own address, a pool address, or another system contract as the "receiver" parameter. This can bypass balance checks or create circular dependencies. Look for: user-supplied address parameters without validation against known system addresses. [beirao G-31]
  - **Provenance:** beirao G-31

- [ ] **[EVM-GEN-048] Cross-contract reentrancy** _(semantic; high)_: Two contracts share state. Contract A calls external contract, which reenters Contract B. B reads stale state from the shared storage because A hasn't finished updating it. `nonReentrant` on individual contracts doesn't prevent this. Look for: multiple contracts sharing storage (via diamond pattern, delegatecall, or direct storage access) without a global reentrancy lock. [beirao G-20]
  - **Provenance:** beirao G-20

- [ ] **[EVM-GEN-049] Read-only reentrancy** _(exploit-pattern; medium)_: A view function on contract A is called during a callback from contract A's state-modifying function. The view returns stale data because the state hasn't been committed yet. Other protocols reading A's view during this window get incorrect prices/balances. Look for: view functions that can be called during callbacks from the same contract's mutating functions. [beirao G-21]
  - **Provenance:** beirao G-21

- [ ] **[EVM-GEN-050] Reorgs change CREATE-deployed addresses** _(exploit-pattern; medium)_: On chains with reorgs (Polygon, rollup chains), a CREATE deployment may end up at a different address post-reorg if the nonce changes. Users who sent funds to the pre-reorg address lose them. Look for: `new Contract()` (CREATE) where the address is pre-computed and funds are sent to it. [beirao G-19]
  - **Provenance:** beirao G-19

- [ ] **[EVM-GEN-051] Compiler version, pragma, and known-bug risk** _(semantic; high)_: Floating or overly broad pragmas can produce different bytecode across builds, while outdated compiler versions may contain security-relevant bugs. Check the exact compiler version and its known-bug list, then verify the deployed artifact was built from that version. Look for: `pragma solidity ^...`/`>=...`, unpinned compiler settings, or a compiler release with a relevant known bug. [beirao G-16, SWC-102, SWC-103]
  - **Provenance:** beirao G-16, SWC-102, SWC-103; [Solidity known bugs](https://docs.soliditylang.org/en/latest/bugs.html)

- [ ] **[EVM-GEN-052] Updating memory struct/array doesn't update storage** _(exploit-pattern; medium)_: Copying a storage struct/array to memory creates a local copy. Modifying the memory copy doesn't persist. Look for: struct assignments like `MyStruct memory s = storageStruct; s.field = newValue;` without writing back. [Tamjid C17]
  - **Provenance:** Tamjid C17

- [ ] **[EVM-GEN-053] State variable shadowing** _(exploit-pattern; medium)_: A child contract declares a variable with the same name as a parent's. The child's variable shadows the parent's, leading to two different storage slots for what appears to be the same variable. Look for: variables in child contracts with the same name as parent contract variables. [Tamjid C18]
  - **Provenance:** Tamjid C18

- [ ] **[EVM-GEN-054] Uninitialized local storage pointer in legacy Solidity** _(semantic; high)_: In compiler versions that accept an uninitialized local `storage` reference, it can alias an unintended storage slot and overwrite unrelated state. Look for: local storage variables declared without an assignment, and confirm whether the compiler version is vulnerable. [SWC-109]
  - **Provenance:** SWC-109; [Solidity 0.5.0 breaking changes](https://docs.soliditylang.org/en/latest/050-breaking-changes.html)

- [ ] **[EVM-GEN-055] Bidirectional Unicode control characters can disguise source logic** _(semantic; high)_: RTL/LTR override and isolate characters can make reviewed source appear to execute in a different order than the compiler sees. Look for: hidden bidirectional control characters in Solidity source, comments, identifiers, or generated diffs. [SWC-130]
  - **Provenance:** SWC-130; [Solidity Unicode literals](https://docs.soliditylang.org/en/latest/layout-of-source-files.html#unicode-literals)

- [ ] **[EVM-GEN-056] C3 inheritance and override order changes security semantics** _(semantic; high)_: Solidity linearization determines which base implementation, modifier, or `super` call executes; an unintended order can bypass a guard or select the wrong initialization/accounting logic. Look for: multiple inheritance with overlapping overrides or `super` calls whose linearization is not explicitly checked. [SWC-125]
  - **Provenance:** SWC-125

- [ ] **[EVM-GEN-057] `private` state is not secret on-chain** _(semantic; high)_: Solidity visibility only restricts source-level access; storage slots and historical values remain readable by anyone. Look for: private variables containing keys, passwords, salts, unrevealed bids, or other data whose secrecy is part of the security model. [SWC-136]
  - **Provenance:** SWC-136; [Solidity private information and randomness](https://docs.soliditylang.org/en/latest/security-considerations.html#private-information-and-randomness)

- [ ] **[EVM-GEN-058] Don't assume specific ETH balance** _(exploit-pattern; medium)_: Contracts can receive ETH via selfdestruct, coinbase, or pre-deployment sends. `require(address(this).balance == expectedAmount)` will break. Look for: exact balance assertions or calculations dependent on a specific ETH balance. [Tamjid C14]
  - **Provenance:** Tamjid C14
  - **Notes:** ---

## RareSkills — Smart Contract Security Comprehensive (Phase 3)

- [ ] **[EVM-GEN-059] Solidity doesn't upcast to final uint size in expressions** _(semantic; high)_: `uint8 a * uint8 b` assigned to `uint256 product` will still revert if result > 255. Each operand must be individually upcast: `uint256(a) * uint256(b)`. Especially dangerous with struct-packed small types. [Source: RareSkills — Smart Contract Security]
  - **Provenance:** Source: RareSkills — Smart Contract Security

- [ ] **[EVM-GEN-060] Ternary operator silently returns uint8** _(exploit-pattern; medium)_: `(condition ? 1 : 0)` in expressions returns uint8. Adding to uint256(255) overflows and reverts. Cast explicitly: `(condition ? uint256(1) : uint256(0))`. [Source: RareSkills — Smart Contract Security]
  - **Provenance:** Source: RareSkills — Smart Contract Security

- [ ] **[EVM-GEN-061] Solidity downcasting doesn't revert on overflow** _(semantic; high)_: `int8(value + 1)` silently truncates without reverting in Solidity ≥0.8. Use SafeCast library for all type narrowing. [Source: RareSkills — Smart Contract Security]
  - **Provenance:** Source: RareSkills — Smart Contract Security

- [ ] **[EVM-GEN-062] Writes to storage pointers don't save new data** _(exploit-pattern; medium)_: `Foo storage foo = myArray[0]; foo = myArray[1];` does NOT copy myArray[1] to myArray[0]. The pointer reassignment is a no-op on the underlying storage. [Source: RareSkills — Smart Contract Security]
  - **Provenance:** Source: RareSkills — Smart Contract Security

- [ ] **[EVM-GEN-063] Deleting structs with dynamic types doesn't delete the inner mappings** _(exploit-pattern; medium)_: `delete buzz[i]` removes the struct but inner `mapping(uint256 => uint256) bar` retains its data. `getFromFoo(1)` still returns 6 after deletion. [Source: RareSkills — Smart Contract Security]
  - **Provenance:** Source: RareSkills — Smart Contract Security

- [ ] **[EVM-GEN-064] Mixed accounting between balance variable and introspection** _(exploit-pattern; medium)_: If a contract tracks balances via `myBalance` variable AND uses `address(this).balance`, forced ETH via `selfdestruct` or direct ERC20 transfers create inconsistency. Pick one accounting method. [Source: RareSkills — Smart Contract Security]
  - **Provenance:** Source: RareSkills — Smart Contract Security

- [ ] **[EVM-GEN-065] Returning large memory arrays for gas griefing** _(semantic; high)_: External calls that return unbounded `bytes memory` force the caller to allocate quadratic gas for memory > 724 bytes. Use assembly with `returndatacopy()` to control copied data size. [Source: RareSkills — Smart Contract Security]
  - **Provenance:** Source: RareSkills — Smart Contract Security

- [ ] **[EVM-GEN-066] ERC20 fee-on-transfer breaks balance accounting** _(exploit-pattern; medium)_: If `balancesInContract[msg.sender] += amount` but actual received amount is `amount * 99/100`, the recorded balance exceeds actual balance. Last withdrawer gets short-changed or reverts. Check balance before/after transfer. [Source: RareSkills — Smart Contract Security]
  - **Provenance:** Source: RareSkills — Smart Contract Security

- [ ] **[EVM-GEN-067] Rebasing tokens break stored balance accounting** _(exploit-pattern; medium)_: Rebasing tokens change everyone's balance automatically. If a contract stores `balanceHeld[user] = amount` at deposit time, the actual balance may differ at withdrawal. Either disallow rebasing tokens or use `balanceOf(address(this))` checks. [Source: RareSkills — Smart Contract Security]
  - **Provenance:** Source: RareSkills — Smart Contract Security

- [ ] **[EVM-GEN-068] ERC4626 inflation attack — front-running first depositor** _(exploit-pattern; medium)_: First depositor donates assets to inflate share price, causing subsequent depositors to receive 0 shares due to rounding. Combination of front-running + rounding error. Mitigate with virtual shares/assets or minimum first deposit. [Source: RareSkills — Smart Contract Security]
  - **Provenance:** Source: RareSkills — Smart Contract Security

## Devdacian — Base AI Auditor Primer Additions (Phase 3)

- [ ] **[EVM-GEN-069] Auction can be seized during active period — off-by-one in timestamp** _(exploit-pattern; medium)_: If auction end check uses `>` instead of `>=`, the auction can be seized at exactly `auctionStartTimestamp + auctionLength`, one second early. [Source: Devdacian — Base Primer]
  - **Provenance:** Source: Devdacian — Base Primer

- [ ] **[EVM-GEN-070] Loan state manipulation via refinancing to cancel auctions indefinitely** _(exploit-pattern; medium)_: Borrowers can cancel liquidation auctions by refinancing the loan, then allow it to become liquidatable again, repeating the cycle to extend loans indefinitely. [Source: Devdacian — Base Primer]
  - **Provenance:** Source: Devdacian — Base Primer

- [ ] **[EVM-GEN-071] Double debt subtraction during refinancing** _(exploit-pattern; medium)_: If refinancing subtracts the old debt from pool balance and also subtracts it again during loan transfer, the pool balance becomes understated, potentially blocking future operations. [Source: Devdacian — Base Primer]
  - **Provenance:** Source: Devdacian — Base Primer

- [ ] **[EVM-GEN-072] Griefing with dust loans below minLoanSize** _(exploit-pattern; medium)_: If `minLoanSize` is only checked at loan creation but not on refinancing/splitting, attackers can create compliant loans then split them into dust, forcing unwanted small positions onto lenders. [Source: Devdacian — Base Primer]
  - **Provenance:** Source: Devdacian — Base Primer

## Supplemental Attack Vectors (SAS-AV)

- [ ] **[EVM-GEN-073] Same-Block Deposit-Withdraw Exploiting Snapshot-Based Benefits** _(exploit-pattern; medium)_: Protocol calculates yield, rewards, voting power, or insurance coverage based on balance at a single snapshot point. No minimum lock period between deposit and withdrawal. Attacker flash-loans tokens, deposits, triggers snapshot (or waits for same-block snapshot), claims benefit, withdraws — all in one tx/block.
  - **Specific FP:** `getPastVotes(block.number - 1)` or equivalent past-block snapshot. Minimum holding period enforced (`require(block.number > depositBlock)`). Reward accrual requires multi-block time passage.
  - **Provenance:** [SAS-AV-001](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-3/315

- [ ] **[EVM-GEN-074] Invariant or Cap Enforced on One Code Path But Not Another** _(exploit-pattern; medium)_: A constraint (pool cap, max supply, position limit, collateral ratio) is enforced during normal operation (e.g., `deposit()`) but not during settlement, reward distribution, interest accrual, or emergency paths. Constraint violated through the unguarded path.
  - **Specific FP:** Invariant check applied in a shared modifier/internal function called by all relevant paths. Post-condition assertion validates invariant after every state change.
  - **Provenance:** [SAS-AV-002](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-8/206/339

- [ ] **[EVM-GEN-075] Immutable / Constructor Argument Misconfiguration** _(exploit-pattern; medium)_: Constructor sets `immutable` values (admin, fee, oracle, token) that can't change post-deploy. Multiple same-type `address` params where order can be silently swapped. No post-deploy verification.
  - **Specific FP:** Deployment script reads back and asserts every configured value. Constructor validates: `require(admin != address(0))`, `require(feeBps <= 10000)`.
  - **Provenance:** [SAS-AV-003](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-31

- [ ] **[EVM-GEN-076] Commit-Reveal Scheme Not Bound to msg.sender** _(exploit-pattern; medium)_: Commitment hash does not include `msg.sender`: `commit = keccak256(abi.encodePacked(value, salt))`. Attacker copies a victim's commitment from the chain/mempool and submits their own reveal for the same hash from a different address. Affects auctions, governance votes, randomness.
  - **Specific FP:** Commitment includes sender: `keccak256(abi.encodePacked(msg.sender, value, salt))`. Reveal validates `msg.sender` matches stored committer.
  - **Provenance:** [SAS-AV-005](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-37

- [ ] **[EVM-GEN-077] Block number is not a timestamp** _(semantic; high)_: Multiplying a block-number delta by a fixed seconds-per-block constant is not a reliable elapsed-time measurement across chains, sequencers, or upgrades. Use `block.timestamp` with an explicit drift tolerance when the requirement is time-based.
  - **Trigger:** Time is computed from `(block.number - startBlock) * constant` or an equivalent fixed cadence assumption.
  - **Risk:** Hardcoded block-time arithmetic can release, accrue, or expire state earlier or later than the protocol's stated wall-clock requirement.
  - **Detection:** Identify the source of every duration and compare the required wall-clock bound with the target chain's timestamp and block-number semantics.
  - **Specific FP:** The protocol intentionally counts blocks and documents that its invariant is independent of elapsed wall-clock time.
  - **Specific proof:** Run boundary cases across delayed and accelerated block production and show whether the time-based invariant still holds.
  - **Provenance:** [SAS-AV-006](https://github.com/sanbir/solidity-auditor-skills); [Arbitrum block numbers and time](https://docs.arbitrum.io/arbitrum-essentials/arbitrum-vs-ethereum/block-numbers-and-time)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-56

- [ ] **[EVM-GEN-078] Nonce Gap from Reverted Transactions (CREATE Address Mismatch)** _(exploit-pattern; medium)_: Deployment script uses `CREATE` and pre-computes addresses from deployer nonce. Reverted/extra tx advances nonce — subsequent deployments land at wrong addresses.
  - **Specific FP:** `CREATE2` used (nonce-independent). Script reads nonce from chain before computing. Addresses captured from deployment receipts.
  - **Provenance:** [SAS-AV-007](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-71

- [ ] **[EVM-GEN-079] Array `delete` Leaves Zero-Value Gap Instead of Removing Element** _(exploit-pattern; medium)_: `delete array[index]` resets element to zero but does not shrink the array or shift subsequent elements. Iteration logic treats the zeroed slot as a valid entry.
  - **Specific FP:** Swap-and-pop pattern used. Iteration skips zero entries explicitly. EnumerableSet or similar library used.
  - **Provenance:** [SAS-AV-008](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-88

- [ ] **[EVM-GEN-080] Transient Storage Low-Gas Reentrancy (EIP-1153)** _(exploit-pattern; medium)_: Contract uses `transfer()`/`send()` (2300-gas) as reentrancy guard + uses `TSTORE`/`TLOAD`. Post-Cancun, `TSTORE` succeeds under 2300 gas. Also: transient reentrancy lock not cleared at call end — persists for entire tx, DoS via multicall.
  - **Specific FP:** `nonReentrant` backed by regular storage slot (or transient mutex properly cleared). CEI followed unconditionally.
  - **Provenance:** [SAS-AV-011](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-97

- [ ] **[EVM-GEN-081] Non-Atomic Multi-Contract Deployment (Partial System Bootstrap)** _(exploit-pattern; medium)_: Deployment script deploys interdependent contracts across separate transactions. Midway failure leaves half-deployed state.
  - **Specific FP:** Single `vm.startBroadcast()`/`vm.stopBroadcast()` block. Factory deploys+wires all in one tx. Script is idempotent.
  - **Provenance:** [SAS-AV-013](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-101

- [ ] **[EVM-GEN-082] Front-Running Zero Balance Check with Dust Transfer** _(exploit-pattern; medium)_: `require(token.balanceOf(address(this)) == 0)` gates a state transition. Dust transfer makes balance non-zero, DoS-ing the function.
  - **Specific FP:** Threshold check (`<= DUST_THRESHOLD`) instead of `== 0`. Access-controlled function. Internal accounting ignores direct transfers.
  - **Provenance:** [SAS-AV-015](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-128

- [ ] **[EVM-GEN-083] Cross-Function Reentrancy** _(exploit-pattern; medium)_: Two functions share state variable. Function A makes external call before updating shared state; Function B reads that state. `nonReentrant` on A but not B.
  - **Specific FP:** Both functions share same contract-level mutex. Shared state updated before any external call.
  - **Provenance:** [SAS-AV-016](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-151

- [ ] **[EVM-GEN-084] Calldata Input Malleability** _(exploit-pattern; medium)_: Contract hashes raw calldata for uniqueness. Dynamic-type ABI encoding uses offset pointers — multiple distinct layouts decode to identical values. Attacker bypasses dedup.
  - **Specific FP:** Uniqueness check hashes decoded parameters: `keccak256(abi.encode(decodedParams))`. Nonce-based replay protection.
  - **Provenance:** [SAS-AV-018](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-167

- [ ] **[EVM-GEN-085] Sender Confusion Under Multicall / Forwarder Context** _(exploit-pattern; medium)_: Code that should reason about the original signer uses raw `msg.sender` inside multicall, relayer, or trusted-forwarder flows. Hooks, accounting, authz, or recipient attribution then execute against the batching contract / forwarder instead of the real user. Common pattern: helper libraries like `_msgSender()` / `LibMulticaller.senderOrSigner()` exist, but one or more internal paths bypass them.
  - **Specific FP:** Every authorization- or attribution-sensitive path consistently uses the canonical sender abstraction for the architecture (`_msgSender()`, trusted forwarder context, multicaller helper). Tests cover direct call, multicall, and forwarded execution paths and assert identical authorization semantics.
  - **Provenance:** [SAS-AV-022](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-228

- [ ] **[EVM-GEN-086] False Existence Detection via Balance Check at Computed Address** _(exploit-pattern; medium)_: Contract checks pool/pair existence via `balanceOf()` at computed CREATE2 address. Pre-sent tokens make `balanceOf > 0` before deployment — logic assumes pool exists, attempts swap, reverts.
  - **Specific FP:** Existence via factory: `factory.getPair(A, B) != address(0)`. `code.length > 0` checked. Pool verified by calling pool-specific function (`getReserves()`, `token0()`).
  - **Provenance:** [SAS-AV-024](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-244

- [ ] **[EVM-GEN-087] State Record Overwrite Without Existence Check** _(exploit-pattern; medium)_: Mapping entry (refund, withdrawal, order) written without checking if key occupied. Overwrites legitimate user's record — blocks claim, redirects funds, or poisons state. Pattern: `records[key] = newData` without `require(records[key].amount == 0)`.
  - **Specific FP:** Existence check before write. Nonce/hash-based keys prevent collision. Append-only structure. Old entry processed before overwrite.
  - **Provenance:** [SAS-AV-025](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-282

- [ ] **[EVM-GEN-088] Sentinel / Placeholder Address Operations** _(exploit-pattern; medium)_: Code branches on sentinel (`address(0)`, `0xEeEe...`, `type(uint256).max`) for ETH/special cases. Special branch omits validations the normal branch performs. Also: ERC20 calls on sentinel — high-level reverts (no code), low-level succeeds silently.
  - **Specific FP:** Sentinel branch has equivalent validation. No ERC20 calls on sentinels. WETH wrapping instead of dual-path. Early detection routes to independent handler.
  - **Provenance:** [SAS-AV-026](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-295

- [ ] **[EVM-GEN-089] msg.value vs Computed Amount Mismatch** _(exploit-pattern; medium)_: Payable function computes `netAmount` after fees but forwards full `msg.value` downstream. Or trusts user-supplied `amount` without `require(msg.value == amount)`.
  - **Specific FP:** `require(msg.value == expectedAmount)` at entry. Fee-adjusted amount used consistently. Excess refunded.
  - **Provenance:** [SAS-AV-028](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-307

- [ ] **[EVM-GEN-090] Namespace / ID Reuse Across Subsystems** _(exploit-pattern; medium)_: Multiple subsystems populate the same identifier space (`positionId`, `vaultId`, `requestId`, `orderId`), but authorization and state transitions only validate the ID, not the originating subsystem. An ID created in subsystem A is accepted by subsystem B, bypassing assumptions about ownership or lifecycle.
  - **Specific FP:** IDs are namespaced per subsystem, or every call validates both `id` and subsystem/type discriminator. Cross-subsystem direction table reviewed and impossible states rejected.
  - **Provenance:** [SAS-AV-029](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-322

- [ ] **[EVM-GEN-091] Sentinel Collision on Exhausted Quota** _(exploit-pattern; medium)_: `0` or another sentinel means "unset" / "unlimited", but the same value is also reachable through normal exhaustion (`remaining = 0`). Once a finite quota decrements to the sentinel value, the contract interprets the exhausted state as unlimited and re-enables access.
  - **Specific FP:** Exhausted state is represented separately from unset state (extra boolean, distinct enum, non-zero sentinel). Decrement path cannot transition into the meaning of "unlimited".
  - **Provenance:** [SAS-AV-030](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-324

- [ ] **[EVM-GEN-092] Mapping Default Value State Ambiguity** _(exploit-pattern; medium)_: Mapping default values (`0`, `false`, empty struct) are treated as "never initialized", but those same values are also valid initialized states. Attackers reset or route execution through the default state to re-trigger initialization, bypass one-time checks, or claim resources repeatedly.
  - **Specific FP:** Initialization tracked with an explicit boolean / version field. Default value is never used as the sole signal for state existence. Distinct-state collision tests cover `never set` vs `set to zero`.
  - **Provenance:** [SAS-AV-031](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-325

- [ ] **[EVM-GEN-093] Swap-and-Pop Moved Index Stale Reference** _(exploit-pattern; medium)_: List deletion uses swap-and-pop, but auxiliary state still points to the moved element's old index. Subsequent reads, deletes, or authorization checks operate on the wrong record, enabling corruption or unauthorized access to the moved item.
  - **Specific FP:** Every swap-and-pop updates both the removed item's metadata and the moved item's index mapping atomically. No external references depend on unstable indices, or stable IDs are used instead.
  - **Provenance:** [SAS-AV-032](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-328

- [ ] **[EVM-GEN-094] Tautology in Require (Self-Comparison Validation Bypass)** _(exploit-pattern; medium)_: A `require()` statement compares a variable to itself (`require(sourceAddressesRoot == sourceAddressesRoot)`), which always evaluates to true. This is a copy-paste or typo error where the right-hand side should be a different variable (e.g., the computed/expected root). The validation is completely bypassed, allowing arbitrary inputs to pass proof verification.
  - **Specific FP:** The comparison is intentionally tautological as a placeholder. The function is not security-critical.
  - **Provenance:** [SAS-AV-033](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-331

- [ ] **[EVM-GEN-095] Override/Extension Mismatch (Inherited Security Property Loss)** _(exploit-pattern; medium)_: When a contract overrides or wraps a base contract's function, the override may preserve explicit guards (`require`, `revert`, access control) but silently drop implicit structural properties (storage key schemes, ordering assumptions, aggregation granularity). For example, a base contract uses composite storage keys `keccak256(user, epoch)` for isolation, but the override switches to `mapping(user => value)`, losing epoch isolation. Explicit checks all pass but the structural security property is gone.
  - **Specific FP:** Override was intentionally designed to change the structural property (documented). The structural property is not security-relevant in the derived context.
  - **Provenance:** [SAS-AV-035](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-340

## drozer-lite Additions

- [ ] **[EVM-GEN-096] Finite-Pool Selection & Depletion Fallback** _(exploit-pattern; medium)_: A finite prize pool selects items with a fallback when the pool is empty; the attacker depletes the pool to force the fallback outcome. Alternatively, the depletion state is observable before action, letting attackers choose when to commit.
  - **Trigger:** A finite prize pool selects items with a fallback when the pool is empty; the attacker depletes the pool to force the fallback outcome. Alternatively, the depletion state is observable before action, letting attackers choose when to commit. `if (remainingPrizes == 0) return consolationPrize;` where consolation is valuable enough to target Attacker can call `peek()` view functions to check pool state atomically Prize pool re-filled mid-round from an attacker-influenced source
  - **Specific proof:** For every finite-pool selection, enumerate the depletion state and the fallback outcome. Ask whether the attacker can (a) observe the depletion state atomically and skip, (b) intentionally deplete the pool to force the fallback, or (c) time their action around another's commitment. Verify the fallback does not provide a profitable alternative.
  - **Provenance:** [DROZER-GAME-2](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/gaming.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/gaming.md); gdroz3r/drozer-lite — checklists/gaming.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/gaming.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/gaming.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-GEN-097] Read-After-Call for Security Decisions** _(exploit-pattern; medium)_: A variable read after an external call is used for access control, balance checking, or amount calculation. The callee can manipulate that state during the call.
  - **Trigger:** A variable read after an external call is used for access control, balance checking, or amount calculation. The callee can manipulate that state during the call. `balance = balanceOf(user); target.call(...); if (balance > X) { ... }` (but balance was captured before call) — worse: re-read after call `require(owner == msg.sender)` read after an untrusted call
  - **Specific proof:** For every external call, audit what is read after. Any security-critical read after an external call must either be re-validated or moved before the call.
  - **Provenance:** [DROZER-RE-4](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/reentrancy.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/reentrancy.md); gdroz3r/drozer-lite — checklists/reentrancy.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/reentrancy.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/reentrancy.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-GEN-098] Atomic Value Transfer** _(exploit-pattern; medium)_: Sender's balance decreases by X but receiver's increases by Y != X (minus fees).
  - **Trigger:** Sender's balance decreases by X but receiver's increases by Y != X (minus fees). No source-specific red flags listed; trace the invariant and caller-controlled inputs described above.
  - **Specific proof:** For each transfer, verify source debit == destination credit + documented fee.
  - **Provenance:** [DROZER-UNI-51](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md); gdroz3r/drozer-lite — checklists/universal.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-GEN-099] No Free Extraction** _(exploit-pattern; medium)_: A sequence of calls allows withdrawing more value than deposited (net of fees and yield).
  - **Trigger:** A sequence of calls allows withdrawing more value than deposited (net of fees and yield). No source-specific red flags listed; trace the invariant and caller-controlled inputs described above.
  - **Specific proof:** Model the protocol as a closed economy. Attempt to construct a cycle that produces profit without external input.
  - **Provenance:** [DROZER-UNI-53](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md); gdroz3r/drozer-lite — checklists/universal.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-GEN-100] receive()/fallback() Auto-Route Balance Invariant Break** _(exploit-pattern; medium)_: A contract has a `receive()` or `fallback()` payable function that unconditionally forwards `msg.value` into a state-mutating function in the same contract (deposit, wrap, stake, mint, buy). Another function in the same contract uses `address(this).balance` as part of an invariant check (e.g., `require(address(this).balance >= amount)` before a refund / withdraw / return / claim). Because the auto-route consumes incoming native value before it can accumulate, the balance-based invariant can be permanently unsatisfiable, or at minimum becomes dependent on chain-specific semantics for how native value can enter the contract without invoking `receive()`.
  - **Trigger:** A contract has a `receive()` or `fallback()` payable function that unconditionally forwards `msg.value` into a state-mutating function in the same contract (deposit, wrap, stake, mint, buy). Another function in the same contract uses `address(this).balance` as part of an invariant check (e.g., `require(address(this).balance >= amount)` before a refund / withdraw / return / claim). Because the auto-route consumes incoming native value before it can accumulate, the balance-based invariant can be permanently unsatisfiable, or at minimum becomes dependent on chain-specific semantics for how native value can enter the contract without invoking `receive()`. `receive() external payable { f(); }` where `f()` is any state-mutating function in the same contract `fallback() external payable { ... f(); }` similarly Any function with `require(address(this).balance >= amount, ...)` whose sibling contract has an auto-routing `receive()`/`fallback()` A "rescued" or "cancelled" accumulator variable whose only payout path depends on contract balance growing via future external transfers Comments or docs saying "buffer provides liquidity" or "accumulated value drains to users" but no actual code path produces non-auto-routed inbound value *Severity rule (HARD)**: When the balance-based invariant is read in a user-facing function (withdraw, refund, claim, redeem, rescue, confirm, settle), this check MUST be rated at least HIGH. Do NOT downgrade to MEDIUM due to uncertainty about chain-specific native-transfer semantics — the correct finding is HIGH with a note that exploitability depends on operational assumptions the auditor should flag and verify with the protocol team. Severity miscalibration on this pattern is itself a finding-quality bug.
  - **Specific proof:** For every `receive()` and `fallback()` function in the cluster: 1. Check whether it unconditionally forwards `msg.value` into a state-mutating function (one that writes storage, mints tokens, or calls an external contract with value). 2. Grep the entire cluster for any `address(this).balance` read used in a `require`, arithmetic, or branch that affects a user-visible decision (refund, withdraw, claim, redeem, rescue). 3. If both conditions hold, trace whether there is ANY path by which native value can enter the contract WITHOUT invoking `receive()` (e.g., `selfdestruct(to)` from another contract, direct balance credit from a privileged precompile, block reward to COINBASE if the contract is a miner/proposer, chain-specific system transfers). If no such path exists, the invariant is permanently broken. If one exists, the invariant is brittle and subject to operational assumptions outside the source.
  - **Provenance:** [DROZER-UNI-98](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md); gdroz3r/drozer-lite — checklists/universal.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-GEN-101] Asymmetric Settlement Across Parallel Transfer Paths** _(exploit-pattern; medium)_: A system has two or more functions that transfer ownership or move the same asset (e.g., `transfer` vs `send`, `transferFrom` vs `safeTransferFrom`, `withdraw` vs `emergencyWithdraw`, `redeem` vs `rescue`). One path includes settlement logic (payment to seller, fee deduction, accounting update, reward distribution). Another path transfers the asset without performing the same settlement, creating a bypass.
  - **Trigger:** A system has two or more functions that transfer ownership or move the same asset (e.g., `transfer` vs `send`, `transferFrom` vs `safeTransferFrom`, `withdraw` vs `emergencyWithdraw`, `redeem` vs `rescue`). One path includes settlement logic (payment to seller, fee deduction, accounting update, reward distribution). Another path transfers the asset without performing the same settlement, creating a bypass. `transfer()` includes payment settlement but `send()` calls `_transfer()` directly without settlement `withdraw()` updates accounting but `emergencyWithdraw()` does not Public `_transfer_nft()` helper is callable by approved addresses and bypasses the sale/auction settlement in `transfer_nft()` A function that takes a `recipient` parameter (allowing caller to send to another address) and a parallel function that forces `msg.sender` as recipient — the first may skip payment checks the second enforces Two functions that both call `check_can_send()` but only one settles the associated financial obligation (bid, deposit, escrow)
  - **Specific proof:** 1. Enumerate every function that changes ownership of an asset or moves value out of the contract. 2. Group these functions by the asset class they operate on. 3. For each group, build a comparison table: function name | settlement logic present? | fee deducted? | accounting updated? | events emitted? 4. If ANY function in the group skips settlement that another function performs, flag. Pay special attention to wrapper functions that call a shared internal `_transfer` without the outer settlement layer.
  - **Provenance:** [DROZER-UNI-100](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md); gdroz3r/drozer-lite — checklists/universal.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-GEN-102] Destructive Operation Without Obligation Settlement** _(exploit-pattern; medium)_: A destructive operation (burn, delete, remove, close, self-destruct, deactivate) destroys an entity that carries active obligations — deposits held against it, active rentals or leases, pending reward claims, locked collateral, open orders, or unresolved escrows. The destruction erases the entity's records from storage, but the funds associated with those obligations remain in the contract with no recovery path. Affected users can no longer call cancel/refund/claim because the entity no longer exists.
  - **Trigger:** A destructive operation (burn, delete, remove, close, self-destruct, deactivate) destroys an entity that carries active obligations — deposits held against it, active rentals or leases, pending reward claims, locked collateral, open orders, or unresolved escrows. The destruction erases the entity's records from storage, but the funds associated with those obligations remain in the contract with no recovery path. Affected users can no longer call cancel/refund/claim because the entity no longer exists. `burn()` checks `check_can_send()` (ownership) but not whether `rentals.len() > 0` or `bids.len() > 0` `closePosition()` deletes the position record without checking `pendingRewards > 0` `deleteAccount()` while staking/delegation entries still reference the account `remove(tokenId)` erases a token struct that contains a Vec of deposit records Any destructive function where the authorization check is ownership/approval only, without an obligation-settlement check
  - **Specific proof:** For every destructive function (burn, remove, close, delete, deactivate, self-destruct): 1. Identify what data is erased (the entity's full storage record, including nested structs, vectors, mappings). 2. Check whether any of the erased data includes: deposit amounts, active rental/lease records, pending claims, locked collateral, open bids, escrowed funds. 3. Verify the function checks for zero active obligations BEFORE allowing destruction. Acceptable patterns: `require(obligations.length == 0)`, `require(deposit_amount == 0)`, iterating obligations and refunding each before deletion. 4. If the function only checks ownership/approval but not obligation status, flag.
  - **Provenance:** [DROZER-UNI-101](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md); gdroz3r/drozer-lite — checklists/universal.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-GEN-103] Heterogeneous Collection Without Type Discrimination** _(exploit-pattern; medium)_: A collection (Vec, array, mapping, linked list) stores items of different subtypes, distinguished by a type flag, enum field, or discriminant. Operations that search, iterate, cancel, settle, or finalize items in the collection match by identity fields (address, ID, period) but do NOT filter by the type discriminant. This allows an operation designed for subtype A to match and operate on a subtype B item that has different economic parameters (denomination, rate, fee structure, cancellation policy).
  - **Trigger:** A collection (Vec, array, mapping, linked list) stores items of different subtypes, distinguished by a type flag, enum field, or discriminant. Operations that search, iterate, cancel, settle, or finalize items in the collection match by identity fields (address, ID, period) but do NOT filter by the type discriminant. This allows an operation designed for subtype A to match and operate on a subtype B item that has different economic parameters (denomination, rate, fee structure, cancellation policy). A `rentals` Vec stores both short-term and long-term entries with a `type` flag, but cancel/finalize functions search by `(address, period)` without checking `type` An order book stores buy and sell orders in the same array with a `side` field, but settlement iterates without filtering by side A positions collection mixes collateralized and uncollateralized positions, but liquidation logic applies uniformly A function reads the denomination from a type-level config struct but the matched item in the shared collection was created under a different type's denomination Cancel function for type A matches a type B item and refunds using type A's denomination instead of the item's stored denomination
  - **Specific proof:** 1. Identify every collection that stores items with a type discriminant field (e.g., `item_type: bool`, `order_side: enum`, `position_type: u8`, `category: u8`). 2. For every function that searches/iterates the collection, check whether the search predicate includes the type discriminant. 3. If the search matches by (address + period) or (address + id) but ignores (type), verify whether the matched item's economic parameters (denomination, rate, terms) could differ from what the calling function assumes. 4. If a function reads denomination/rate/terms from a TYPE-LEVEL config (e.g., `shortterm_rental.denom`) but the matched item was created under a DIFFERENT type's config (e.g., `longterm_rental.denom`), flag as HIGH — this enables cross-denomination value extraction.
  - **Provenance:** [DROZER-UNI-102](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md); gdroz3r/drozer-lite — checklists/universal.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-GEN-104] Payment-Gated Transfer Allows Beneficiary Mismatch** _(exploit-pattern; medium)_: A function combines asset transfer with payment settlement. The payment amount is looked up from a mapping or list keyed by the recipient address (e.g., bids, deposits, escrow entries). The caller can freely specify the recipient parameter. If the recipient has no entry in the payment mapping, the amount defaults to zero and the transfer proceeds without payment to the previous owner. Alternatively, the caller specifies a recipient different from themselves to avoid their own payment being consumed, then cancels their payment entry for a full refund.
  - **Trigger:** A function combines asset transfer with payment settlement. The payment amount is looked up from a mapping or list keyed by the recipient address (e.g., bids, deposits, escrow entries). The caller can freely specify the recipient parameter. If the recipient has no entry in the payment mapping, the amount defaults to zero and the transfer proceeds without payment to the previous owner. Alternatively, the caller specifies a recipient different from themselves to avoid their own payment being consumed, then cancels their payment entry for a full refund. `amount = bids[recipient].offer` defaults to 0 when no bid exists, and the function has a branch that proceeds with transfer when `amount == 0` Transfer function accepts `recipient` as a parameter (not forced to `msg.sender`), allowing the caller to route the transfer to an address with no active bid Caller can: (1) place a bid to gain approval, (2) call transfer with a DIFFERENT recipient who has no bid (zero payment), (3) cancel their own bid for full refund No `require(amount >= listed_price)` check between the payment lookup and the ownership transfer The `amount > 0` branch sends payment to the previous owner, but the `amount == 0` branch still transfers ownership
  - **Specific proof:** 1. For every function that transfers an asset AND looks up a payment amount by a caller-supplied address parameter: a. Check whether the function reverts when no payment entry exists for the specified recipient (amount == 0 case). b. Check whether the function validates that the payment amount meets the listed/required price. c. Check whether the caller is constrained to specify themselves as the recipient, or can specify any address. 2. If the function proceeds with transfer when `amount == 0` (no matching payment), flag as HIGH — the asset is transferred for free. 3. If the function does not validate `amount >= listed_price`, flag as HIGH — the asset can be transferred for less than the listed price.
  - **Provenance:** [DROZER-UNI-103](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md); gdroz3r/drozer-lite — checklists/universal.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-GEN-105] Stored Constraint Not Enforced at Consumption Point** _(exploit-pattern; medium)_: A configuration or listing function accepts and stores a constraint parameter (available period, whitelist, max participants, allowed tokens, deadline, minimum amount, geographic restriction). The consuming function that should enforce this constraint (reservation, deposit, bid, claim, register) operates on the same entity but never reads or validates the stored constraint. The constraint exists in storage but has zero enforcement — users can bypass it simply by never encountering a check.
  - **Trigger:** A configuration or listing function accepts and stores a constraint parameter (available period, whitelist, max participants, allowed tokens, deadline, minimum amount, geographic restriction). The consuming function that should enforce this constraint (reservation, deposit, bid, claim, register) operates on the same entity but never reads or validates the stored constraint. The constraint exists in storage but has zero enforcement — users can bypass it simply by never encountering a check. `available_period` set in listing function but reservation function checks `minimum_stay` only, ignoring `available_period` entirely `max_participants` stored on entity creation but join function has no cap check `allowed_tokens` whitelist stored but deposit function accepts any denomination `deadline` stored but claim function checks `block.timestamp` against a different value `auto_approve` flag stored for one rental type but the approval function for that type never reads it Any field in a config struct that is written in the setter and read ONLY in query/view functions (never in state-changing functions)
  - **Specific proof:** 1. For every configuration/listing function, enumerate every field it writes to storage. 2. For each stored field, classify it as: (a) data field (description, name, URI — informational), or (b) constraint field (period, whitelist, max, min, deadline, rate — should restrict behavior). 3. For each constraint field, find ALL consuming functions that operate on the same entity. Verify the constraint field is READ and produces a REVERT or behavioral change in each consumer. 4. If a constraint field is stored but never read by any consuming function, flag as MEDIUM — the feature is broken, not just missing.
  - **Provenance:** [DROZER-UNI-105](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md); gdroz3r/drozer-lite — checklists/universal.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-GEN-106] Listing-Gate Bypass on Unlisted Entities** _(exploit-pattern; medium)_: An entity has a listing status field (`is_listed`, `active`, `status`, `enabled`) that is set by a listing function and cleared by an unlisting function. Consumer functions (bid, reserve, purchase, deposit, subscribe) that should only operate on listed entities do not check the listing status. This allows: (1) operations on entities that were never listed, (2) operations on entities that were explicitly delisted, (3) exploitation of stale configuration (e.g., `auto_approve` from a previous listing) on a currently unlisted entity.
  - **Trigger:** An entity has a listing status field (`is_listed`, `active`, `status`, `enabled`) that is set by a listing function and cleared by an unlisting function. Consumer functions (bid, reserve, purchase, deposit, subscribe) that should only operate on listed entities do not check the listing status. This allows: (1) operations on entities that were never listed, (2) operations on entities that were explicitly delisted, (3) exploitation of stale configuration (e.g., `auto_approve` from a previous listing) on a currently unlisted entity. `bid()` function does not check `is_listed == true` before accepting funds and granting approval `reserve()` function accepts deposits for unlisted properties/assets `purchase()` function operates on delisted items using stale price/denomination from a prior listing Unlisting function sets `is_listed = false` but does NOT clear `auto_approve`, `price`, or `denomination` — these persist and are used by consumer functions that skip the listing check Any consumer function that reads economic parameters (price, denomination, approval mode) from the entity without first verifying the entity is currently listed
  - **Specific proof:** 1. For every entity with a listing/status flag, enumerate: (a) the function that sets it to active/listed, (b) the function that sets it to inactive/unlisted, (c) all consumer functions that operate on the entity. 2. For each consumer function, verify it checks the listing status flag early in execution (before accepting funds, granting approvals, or modifying state). 3. Pay special attention to configuration fields that PERSIST across list/unlist cycles. If `auto_approve`, `price`, `denomination`, or other economic parameters are set during listing and NOT cleared during unlisting, check whether consumers of these fields are guarded by the listing status. 4. If a consumer function accepts funds or grants permissions without checking listing status, flag. Severity depends on whether the stale configuration enables value extraction.
  - **Provenance:** [DROZER-UNI-106](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md); gdroz3r/drozer-lite — checklists/universal.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-GEN-107] Temporal Parameter Allows Retroactive / Past Values at Creation** _(exploit-pattern; medium)_: An entity with a time-based lifecycle (farm, vesting schedule, auction, subscription, rental) accepts a `start_time` or `start_epoch` parameter at creation. The parameter is validated for basic sanity (> 0, < end) but is NOT validated against the current time/epoch. This allows creating entities that "started in the past," retroactively assigning rewards, obligations, or access to historical periods that other participants have already settled.
  - **Trigger:** An entity with a time-based lifecycle (farm, vesting schedule, auction, subscription, rental) accepts a `start_time` or `start_epoch` parameter at creation. The parameter is validated for basic sanity (> 0, < end) but is NOT validated against the current time/epoch. This allows creating entities that "started in the past," retroactively assigning rewards, obligations, or access to historical periods that other participants have already settled. `start_epoch = params.start_epoch.unwrap_or(current_epoch + 1)` but no `ensure!(start_epoch >= current_epoch + 1)` for the explicit case Validation checks `start < end` and `end > current` but not `start > current` A farm/schedule created with past start_epoch assigns emissions to epochs where participants already claimed, creating unfair distribution Default path is safe (`current + 1`) but explicit path bypasses the constraint
  - **Specific proof:** 1. For every creation function that accepts a start_time/start_epoch parameter, verify it is enforced as `>= current_time + 1` or `>= current_epoch + 1`. 2. Check the default value when the parameter is omitted — if it defaults to `current + 1`, verify the explicit path has the same constraint. 3. Trace what happens if start is set to a past value: are rewards retroactively assigned? Do billing periods extend into the past? Can the creator claim historical periods?
  - **Provenance:** [DROZER-UNI-108](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md); gdroz3r/drozer-lite — checklists/universal.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-GEN-108] Self-Call Identity Confusion** _(exploit-pattern; medium)_: A function performs a two-step operation by calling itself: step 1 initiates (stores context in a buffer), step 2 is triggered via a self-call (SubMsg or wasm_execute to self). The second step's `info.sender` is the contract's own address, not the original user. If step 2 has an authorization check like `require(sender == receiver)` or `require(sender == user)`, it fails because sender is the contract. Conversely, if step 2 has an authorization check like `require(sender == admin || sender == contract)`, the self-call bypasses user-level restrictions.
  - **Trigger:** A function performs a two-step operation by calling itself: step 1 initiates (stores context in a buffer), step 2 is triggered via a self-call (SubMsg or wasm_execute to self). The second step's `info.sender` is the contract's own address, not the original user. If step 2 has an authorization check like `require(sender == receiver)` or `require(sender == user)`, it fails because sender is the contract. Conversely, if step 2 has an authorization check like `require(sender == admin || sender == contract)`, the self-call bypasses user-level restrictions. `wasm_execute(env.contract.address, &ExecuteMsg::ProvideLiquidity { receiver: user, ... }, funds)` where `ProvideLiquidity` checks `ensure!(receiver == info.sender)` — fails because info.sender is the contract Two-step LP provision: step 1 swaps half, step 2 provides balanced LP. Step 2's sender check rejects the self-call. A singleton buffer stores context for the reply handler — if two users trigger step 1 in the same block, the second overwrites the first's buffer Any function with `if info.sender == env.contract.address { /* special path */ }` that grants elevated privileges
  - **Specific proof:** 1. For every SubMsg or wasm_execute that targets the contract's own address (`env.contract.address`), identify the function being called. 2. Check what `info.sender` is used for in the called function. If it's used for authorization, it will be the contract address, not the original caller. 3. Check whether any receiver/beneficiary validation compares against `info.sender` — this will fail for the self-call case. 4. Check whether any privilege check accepts the contract's own address — this could be a bypass vector.
  - **Provenance:** [DROZER-UNI-109](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md); gdroz3r/drozer-lite — checklists/universal.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

## Integer Overflow/Underflow (Even with Solidity ≥0.8)

- [ ] **[EVM-TYPE-001] Signed-to-unsigned explicit conversion preserves the bit pattern**: Shared canonical check; apply the primary definition and evidence requirements for `evm-audit-precision-math`.

## Precision Loss Patterns (Expanded from Beirao/Tamjid)

- [ ] **[EVM-TIME-001] Time-unit arithmetic inherits operand and destination type**: Shared canonical check; apply the primary definition and evidence requirements for `evm-audit-precision-math`.
