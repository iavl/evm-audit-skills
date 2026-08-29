# General Solidity/EVM Security Checklist

Every item here is non-obvious — basic reentrancy, overflow checks, access control patterns are excluded.

## External Calls & Low-Level Interactions

- [ ] **Call to non-existent address returns true**: A low-level `.call()` to an address with no deployed code returns `(true, "")`. If you're relying on call success without verifying target has code via `extcodesize > 0` or `address.code.length > 0`, you'll silently accept no-ops. Look for: any `.call()` where the target address is user-supplied or computed. [beirao E-05]

- [ ] **Grief attack via returndata bombing**: When making `.call()` to an unknown address, the callee can return a massive `bytes` payload. Solidity automatically copies all returndata into memory, consuming gas quadratically. An attacker returns megabytes of data to grief the caller. Fix: use inline assembly to limit returndata copy size. Look for: `.call()` to untrusted addresses without assembly returndata handling. [beirao E-04]

- [ ] **Fixed gas in `.call{gas: X}()`**: Hardcoding gas amounts (e.g., `addr.call{gas: 2300}("")`) breaks when opcode costs change across hard forks (see EIP-1884 which repriced SLOAD). Also breaks on L2s with different gas schedules. Look for: any `.call` or `.send` with explicit gas amounts. [beirao E-03]

- [ ] **`msg.value` persistence in multicall/batch patterns**: In a contract with a `multicall(bytes[] calldata data)` function that loops through delegatecalls, `msg.value` is the SAME in every iteration. An attacker sends 1 ETH and "spends" it N times. Look for: `msg.value` used inside any loop or batch execution pattern. [beirao E-17, L-03]

- [ ] **`msg.value` in a multi-call via delegatecall**: Even without explicit loops, if a function uses `msg.value` and can be reached via `delegatecall` from a multicall, the value is re-readable. Look for: payable functions callable through delegatecall patterns. [beirao G-24]

- [ ] **try/catch always fails with insufficient gas**: Solidity `try/catch` doesn't protect against OOG in the external call. An attacker who controls gas forwarding can force the catch path every time by providing just enough gas to enter but not complete the try block. Look for: security-critical logic that depends on try succeeding vs catching. [beirao G-18]

- [ ] **`abi.encodePacked` with 2+ dynamic types = hash collisions**: `abi.encodePacked(string a, string b)` can collide: `encodePacked("a","bc") == encodePacked("ab","c")`. Look for: `keccak256(abi.encodePacked(...))` with multiple `string`, `bytes`, or dynamic array arguments. Fix: use `abi.encode()`. [beirao G-15, SWC-133]

- [ ] **Delegate calls to non-library contracts**: `delegatecall` to stateful contracts is extremely dangerous — the called contract's code runs in the caller's storage context. Look for: `delegatecall` to any address that isn't a known stateless library. [beirao E-09, E-10]

- [ ] **ETH transfer via `transfer()`/`send()` is 2300 gas**: This fails for contracts with non-trivial `receive()`/`fallback()` functions and fails on some L2s (zkSync). Always use `.call{value: x}("")`. Look for: `.transfer()` or `.send()`. [beirao E-07, multichain-auditor]

- [ ] **Unchecked return of low-level `.call()`**: `(bool success, ) = addr.call(data)` — if `success` isn't checked, the call fails silently. Look for: `.call()` without `require(success)`. [SWC-104]

## Force-Feeding Attacks

- [ ] **Force-feed via `selfdestruct`**: `selfdestruct(payable(target))` sends the contract's ETH balance to `target` regardless of whether target has `receive()`/`fallback()`. This breaks any invariant based on `address(this).balance`. Look for: any comparison or calculation using `address(this).balance`. [beirao G-03]

- [ ] **Force-feed via pre-computed CREATE2 address**: ETH can be sent to a CREATE2 address before the contract is deployed there. The newly deployed contract will have a non-zero ETH balance from block 0 that it didn't expect. Look for: balance assumptions in constructors/initializers. [beirao G-03]

- [ ] **Coinbase force-feeding**: A validator/miner can set their coinbase to any address, force-feeding the block reward. Look for: balance-based invariants in contracts that could be targeted by validators. [beirao G-03]

- [ ] **Direct token transfers bypass accounting**: Sending ERC20 tokens directly via `transfer()` to a contract (not through its deposit function) inflates `balanceOf(address(this))` without updating internal accounting. Look for: any use of `token.balanceOf(address(this))` as a source of truth instead of internal tracking variables. [beirao V-01, V-02, G-07]

## Pause Mechanism Pitfalls

- [ ] **Pausing liquidations = solvency crisis**: If a protocol's pause mechanism freezes liquidations, bad debt accumulates silently. When unpaused, cascading liquidations can drain the protocol. Look for: pause modifiers on liquidation functions. [beirao G-09, LEN-06]

- [ ] **Pause front-running**: If pausing requires an on-chain transaction, an attacker monitoring the mempool can front-run the pause with a malicious transaction. Look for: security-critical state changes that depend on pause being active. [beirao F-04]

- [ ] **`whenNotPaused` missing from critical functions**: Common to add pause to most functions but miss some edge case paths. Look for: functions that modify state or transfer value that lack the pause modifier when other similar functions have it. [beirao G-09]

- [ ] **Pause can permanently brick the contract**: If pause has no unpause mechanism, or if the unpause requires conditions that can't be met while paused, the contract is bricked forever. Look for: circular dependencies in pause/unpause logic. [beirao G-09]

## Reentrancy (Non-Obvious)

- [ ] **ERC721 `safeMint`/`safeTransferFrom` callbacks**: These call `onERC721Received()` on the recipient, creating reentrancy vectors. Same for ERC1155's `_safeTransferFrom` with `onERC1155Received`. Look for: `_safeMint()`, `safeTransferFrom()` without reentrancy guards or CEI pattern. [beirao NFT-02, NFT-03]

- [ ] **ERC777 pre/post transfer hooks**: ERC777 tokens call `tokensToSend()` (before transfer) and `tokensReceived()` (after transfer). Both are reentrancy vectors that bypass `nonReentrant` if the modifier is only on the outer function. Look for: any protocol that accepts arbitrary ERC20 tokens — it might receive an ERC777. [beirao FT-08]

- [ ] **NoReentrancy modifier MUST be first**: If `nonReentrant` is placed after other modifiers, those modifiers' code executes before the lock is set. Look for: modifier ordering on external/public functions. [beirao G-17]

## Merkle Tree Pitfalls

- [ ] **Merkle proofs are front-runnable**: Once a valid proof is submitted on-chain, anyone can copy it. The claim must be bound to `msg.sender` (included in the leaf) to prevent theft. Look for: `claim()` functions where the leaf doesn't include the claimant's address. [beirao MT-01, MT-02, MT-03]

- [ ] **Zero hash as valid proof**: Passing `bytes32(0)` may satisfy poorly constructed Merkle trees where empty nodes are represented as zero. Look for: Merkle verification that doesn't reject zero-hash leaves. [beirao MT-04]

- [ ] **Duplicate leaves enable double-claim**: If the same data appears as two leaves in the tree, the same proof may allow claiming twice. Look for: trees constructed without deduplication. [beirao MT-05]

## Reveal-Gap Steering (value public before it's consumed)

- [ ] **A value revealed before the tx that consumes it can steer the outcome**: Any two-phase flow where a value becomes public before the code that acts on it runs — a VRF word sitting in the mempool, an oracle answer, a commit-reveal reveal, any request-then-fulfill — is exploitable if the consuming step reads *mutable* state to decide the outcome. The value can be provably unbiasable and the callback sender-authenticated and it is still exploitable, because the bias is not in the value — it is in the state the code reads *after* the value is already known. Rule to verify: the outcome must be a pure function of state committed at or before the moment the value was fixed. If any actor can change that state in the gap (deposit, mint, withdraw, reprice, reorder), the outcome is steerable. Check both directions of any window-lock, and confirm that a smooth price/amount guard is not being trusted to protect a discontinuous selection (`% N`). Look for: a callback / step-2 whose result depends on storage that an external function can mutate between reveal and execution. [Source: FWA / TokenWorks CryptoPunk #5450 incident, 2026]

## Code Structure Issues

- [ ] **Withdraw should undo ALL deposit state changes**: For every state variable modified during `deposit()`, there should be a symmetric reversal in `withdraw()`. Asymmetries cause accounting drift. Look for: compare `deposit` and `withdraw` functions line by line for state variable coverage. [beirao G-26]

- [ ] **Inconsistent logic across duplicated implementations**: When the same logic is implemented in multiple places (e.g., calculating fees in both `deposit` and `withdraw`), they may diverge over time. Look for: duplicated business logic that should be a shared internal function. [beirao G-01]

- [ ] **Documentation-code mismatch**: Comments describing one thing while code does another. Particularly dangerous when the comment matches the spec but the code doesn't. Look for: NatSpec/comments that describe different behavior than the implementation. [beirao F-07, G-12]

- [ ] **Deployment scripts not checked**: Bugs in deployment scripts (wrong constructor args, missing initialization calls, wrong chain configs) are as dangerous as bugs in contracts. Look for: deployment scripts that aren't tested or reviewed. [beirao G-13]

## Array and Loop Hazards

- [ ] **Unbounded loops with external calls = DoS**: If a loop iterates over a user-growable array and makes external calls (especially transfers), an attacker can grow the array until the function exceeds block gas limit. Look for: `for` loops over dynamic arrays that contain `.call()`, `.transfer()`, or `safeTransfer()`. [beirao G-04, L-02]

- [ ] **Duplicate addresses in calldata arrays**: When a function takes `address[] calldata addresses` and processes each one, duplicates can cause double-counting or double-payment. Look for: functions that iterate over user-provided address arrays without dedup checks. [beirao F-10]

- [ ] **First iteration edge case**: The first iteration of a loop may behave differently (e.g., empty state, uninitialized variables). Look for: loop body logic that assumes prior iterations have run. [beirao L-01]

- [ ] **[AUDITMOS-STATE-VALIDATION-7] Parallel arrays must have matching lengths**: Functions that process related arrays must reject mismatched lengths before indexing or applying values. Otherwise callers can trigger out-of-bounds reverts or leave only part of a state transition applied. Look for: functions accepting `ids` and `amounts`, or any paired arrays, without an explicit equality check. [Source: Auditmos `audit-state-validation`, pattern #7](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-state-validation/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010

## Block/Time Assumptions

- [ ] **`block.timestamp` only reliable for long intervals**: Validators can manipulate timestamps by several seconds. Don't use for intervals shorter than ~15 minutes. Look for: time-sensitive logic with sub-minute precision. [beirao G-28]

- [ ] **Block time varies across chains**: `block.number` as a time proxy: 12s on mainnet, ~2s on Optimism, ~0.25s on Arbitrum. A value of `7200` blocks = 1 day on mainnet but only hours elsewhere. Look for: hardcoded block counts used as time proxies. [multichain-auditor, beirao MC-01]

- [ ] **Block production may not be constant**: Arbitrum `block.number` reflects L1 blocks, updating in ~5-block jumps per minute. On Optimism, `block.number` is the L2 block. Look for: code that assumes monotonically incrementing `block.number` with constant intervals. [multichain-auditor, Arbitrum checklist]

## Comparison & Logic Operators

- [ ] **Off-by-one in comparisons**: `<` vs `<=`, `>` vs `>=` — especially in liquidation thresholds, fee boundaries, and time windows. A single off-by-one can make a position unliquidatable or skip fee collection. Look for: boundary comparisons in critical math. [beirao G-29, M-11]

- [ ] **Incorrect logical operators**: `&&` vs `||`, `==` vs `!=`, `!` applied to wrong subexpression. Look for: complex conditional expressions, especially negated ones. [beirao G-30]

## Multi-Agent Systems

- [ ] **All agents could be the same person**: In any system with multiple roles (buyer/seller, borrower/liquidator, proposer/voter), check what happens if one person controls all roles. Self-liquidation for profit, self-trading for rewards, etc. Look for: role-based systems without Sybil resistance. [beirao G-22]

- [ ] **Receiver address pointing to another system contract**: If a function takes a `receiver` parameter, what happens if the receiver is another contract in the same system? Look for: user-provided address parameters that could target internal system contracts. [beirao G-31]

## Solidity Compiler

- [ ] **PUSH0 opcode (Solidity ≥0.8.20)**: The `push0` opcode emitted by default in ≥0.8.20 isn't supported on many L2s and alt-chains. Look for: `pragma solidity ^0.8.20` or higher in multichain deployments. [multichain-auditor, beirao MC-03]

- [ ] **Unchecked blocks need validation**: Code in `unchecked { }` bypasses overflow/underflow checks. Every unchecked block must be manually verified for safety. Look for: `unchecked` blocks, especially around user-influenced values. [beirao M-10]

- [ ] **Assigning negative value to uint reverts**: In Solidity ≥0.8.0, casting a negative `int` to `uint` reverts. In `unchecked`, it wraps. Look for: signed-to-unsigned conversions near `unchecked` blocks. [beirao M-09]

- [ ] **Regular time expressions are uint24**: `1 days`, `1 hours` etc. are `uint24` in some contexts. Operations mixing these with larger types may silently truncate. Look for: arithmetic involving Solidity time literals cast to larger types. [beirao M-04]

## General Solidity Footguns (Expanded from Beirao/Tamjid/Multichain-Auditor)

- [ ] **Force-feeding ETH to a contract**: Three methods bypass `receive()`/`fallback()`: (1) `selfdestruct(target)` sends ETH without calling any function. (2) Pre-computed CREATE2 addresses can receive ETH before deployment. (3) Block coinbase rewards go to the miner/validator address. Contracts using `address(this).balance` for logic are vulnerable. Look for: `address(this).balance` used in invariant checks or pricing. [beirao G-03]

- [ ] **Deleting a struct doesn't delete its nested mappings**: `delete myStruct` zeros out the struct fields but any mappings inside persist in storage. Look for: `delete` on structs containing mappings, where the mapping data should also be cleared. [beirao G-06]

- [ ] **`msg.value` in a loop or multicall**: If `msg.value` is checked inside a loop or in a `Multicall`/`Batchable` with `delegatecall`, the same `msg.value` is counted for every iteration. An attacker can deposit 1 ETH but get credit for N ETH across N calls. Look for: `msg.value` referenced in any function callable via multicall or batch. [beirao E-17, L-03, Tamjid C28, C29]

- [ ] **Call to address that doesn't exist returns true**: Low-level `.call()` to an address with no code returns `success = true` with empty returndata. This can silently skip operations if the target hasn't been deployed yet. Look for: `.call()` to addresses derived from configuration or computation without checking `extcodesize > 0`. [beirao E-05, Tamjid C34]

- [ ] **Semantic overloading**: Using the same variable or return value for multiple meanings (e.g., 0 means "not found" AND "zero balance") creates ambiguity that leads to logic errors. Look for: functions where a zero return could mean success, failure, or absence. [beirao G-11]

- [ ] **[AUDITMOS-STATE-VALIDATION-5] Non-existent IDs must not use default state**: Functions accepting an ID must verify that its record exists before reading or mutating it. Mapping defaults can make a nonexistent entry look valid, corrupt counters, mark debt as repaid, or apply state changes to an empty record. Look for: `mapping[id]` reads followed by accounting updates without an existence flag or equivalent check. [Source: Auditmos `audit-state-validation`, pattern #5](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-state-validation/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010

- [ ] **Code asymmetry — withdraw doesn't undo deposit state**: If `deposit()` updates state variables A, B, C, the `withdraw()` function should reverse ALL of A, B, C. Missing one creates an inconsistent state. Look for: deposit/withdraw function pairs where state modifications aren't symmetric. [beirao G-26]

- [ ] **`if (receiver == caller)` unexpected behavior**: Self-transfers or self-operations may skip important logic (e.g., fee charging, balance validation). Look for: functions where `from == to` or `sender == receiver` isn't handled as a special case. [beirao G-08]

- [ ] **Providing a system address as a user input**: A user passes the contract's own address, a pool address, or another system contract as the "receiver" parameter. This can bypass balance checks or create circular dependencies. Look for: user-supplied address parameters without validation against known system addresses. [beirao G-31]

- [ ] **`NoReentrant` modifier must be FIRST**: If reentrancy guard is placed after other modifiers, the other modifiers execute before the guard, potentially allowing reentry during modifier execution. Look for: `nonReentrant` not being the first modifier in the modifier chain. [beirao G-17]

- [ ] **Cross-contract reentrancy**: Two contracts share state. Contract A calls external contract, which reenters Contract B. B reads stale state from the shared storage because A hasn't finished updating it. `nonReentrant` on individual contracts doesn't prevent this. Look for: multiple contracts sharing storage (via diamond pattern, delegatecall, or direct storage access) without a global reentrancy lock. [beirao G-20]

- [ ] **Read-only reentrancy**: A view function on contract A is called during a callback from contract A's state-modifying function. The view returns stale data because the state hasn't been committed yet. Other protocols reading A's view during this window get incorrect prices/balances. Look for: view functions that can be called during callbacks from the same contract's mutating functions. [beirao G-21]

- [ ] **Reorgs change CREATE-deployed addresses**: On chains with reorgs (Polygon, rollup chains), a CREATE deployment may end up at a different address post-reorg if the nonce changes. Users who sent funds to the pre-reorg address lose them. Look for: `new Contract()` (CREATE) where the address is pre-computed and funds are sent to it. [beirao G-19]

- [ ] **Compiler version, pragma, and known-bug risk**: Floating or overly broad pragmas can produce different bytecode across builds, while outdated compiler versions may contain security-relevant bugs. Check the exact compiler version and its known-bug list, then verify the deployed artifact was built from that version. Look for: `pragma solidity ^...`/`>=...`, unpinned compiler settings, or a compiler release with a relevant known bug. [beirao G-16, SWC-102, SWC-103]

- [ ] **Updating memory struct/array doesn't update storage**: Copying a storage struct/array to memory creates a local copy. Modifying the memory copy doesn't persist. Look for: struct assignments like `MyStruct memory s = storageStruct; s.field = newValue;` without writing back. [Tamjid C17]

- [ ] **State variable shadowing**: A child contract declares a variable with the same name as a parent's. The child's variable shadows the parent's, leading to two different storage slots for what appears to be the same variable. Look for: variables in child contracts with the same name as parent contract variables. [Tamjid C18]

- [ ] **Uninitialized local storage pointer in legacy Solidity**: In compiler versions that accept an uninitialized local `storage` reference, it can alias an unintended storage slot and overwrite unrelated state. Look for: local storage variables declared without an assignment, and confirm whether the compiler version is vulnerable. [SWC-109]

- [ ] **Bidirectional Unicode control characters can disguise source logic**: RTL/LTR override and isolate characters can make reviewed source appear to execute in a different order than the compiler sees. Look for: hidden bidirectional control characters in Solidity source, comments, identifiers, or generated diffs. [SWC-130]

- [ ] **C3 inheritance and override order changes security semantics**: Solidity linearization determines which base implementation, modifier, or `super` call executes; an unintended order can bypass a guard or select the wrong initialization/accounting logic. Look for: multiple inheritance with overlapping overrides or `super` calls whose linearization is not explicitly checked. [SWC-125]

- [ ] **`private` state is not secret on-chain**: Solidity visibility only restricts source-level access; storage slots and historical values remain readable by anyone. Look for: private variables containing keys, passwords, salts, unrevealed bids, or other data whose secrecy is part of the security model. [SWC-136]

- [ ] **`block.timestamp` should only be used for long intervals**: Miners/validators can manipulate timestamps by a few seconds. Using it for sub-minute precision is unreliable. Look for: `block.timestamp` in calculations where seconds matter (e.g., interest calculations per second). [Tamjid C4, beirao G-28]

- [ ] **Don't assume specific ETH balance**: Contracts can receive ETH via selfdestruct, coinbase, or pre-deployment sends. `require(address(this).balance == expectedAmount)` will break. Look for: exact balance assertions or calculations dependent on a specific ETH balance. [Tamjid C14]

---

## RareSkills — Smart Contract Security Comprehensive (Phase 3)

- [ ] **Solidity doesn't upcast to final uint size in expressions**: `uint8 a * uint8 b` assigned to `uint256 product` will still revert if result > 255. Each operand must be individually upcast: `uint256(a) * uint256(b)`. Especially dangerous with struct-packed small types. [Source: RareSkills — Smart Contract Security]

- [ ] **Ternary operator silently returns uint8**: `(condition ? 1 : 0)` in expressions returns uint8. Adding to uint256(255) overflows and reverts. Cast explicitly: `(condition ? uint256(1) : uint256(0))`. [Source: RareSkills — Smart Contract Security]

- [ ] **Solidity downcasting doesn't revert on overflow**: `int8(value + 1)` silently truncates without reverting in Solidity ≥0.8. Use SafeCast library for all type narrowing. [Source: RareSkills — Smart Contract Security]

- [ ] **Writes to storage pointers don't save new data**: `Foo storage foo = myArray[0]; foo = myArray[1];` does NOT copy myArray[1] to myArray[0]. The pointer reassignment is a no-op on the underlying storage. [Source: RareSkills — Smart Contract Security]

- [ ] **Deleting structs with dynamic types doesn't delete the inner mappings**: `delete buzz[i]` removes the struct but inner `mapping(uint256 => uint256) bar` retains its data. `getFromFoo(1)` still returns 6 after deletion. [Source: RareSkills — Smart Contract Security]

- [ ] **Mixed accounting between balance variable and introspection**: If a contract tracks balances via `myBalance` variable AND uses `address(this).balance`, forced ETH via `selfdestruct` or direct ERC20 transfers create inconsistency. Pick one accounting method. [Source: RareSkills — Smart Contract Security]

- [ ] **Merkle proof treated as password — leaf not tied to msg.sender**: If the merkle leaf is just the address (not hashed with msg.sender binding), anyone who knows the tree can create valid proofs. Also: unhashed leaf == merkle root passes verification. And: valid proofs can be front-run. [Source: RareSkills — Smart Contract Security]

- [ ] **msg.value reused in loops (payable multicalls)**: In multicall patterns, `msg.value` is constant throughout the loop, allowing the same ETH to be "spent" multiple times. Root cause of the Opyn hack. [Source: RareSkills — Smart Contract Security]

- [ ] **Returning large memory arrays for gas griefing**: External calls that return unbounded `bytes memory` force the caller to allocate quadratic gas for memory > 724 bytes. Use assembly with `returndatacopy()` to control copied data size. [Source: RareSkills — Smart Contract Security]

- [ ] **ERC20 fee-on-transfer breaks balance accounting**: If `balancesInContract[msg.sender] += amount` but actual received amount is `amount * 99/100`, the recorded balance exceeds actual balance. Last withdrawer gets short-changed or reverts. Check balance before/after transfer. [Source: RareSkills — Smart Contract Security]

- [ ] **Rebasing tokens break stored balance accounting**: Rebasing tokens change everyone's balance automatically. If a contract stores `balanceHeld[user] = amount` at deposit time, the actual balance may differ at withdrawal. Either disallow rebasing tokens or use `balanceOf(address(this))` checks. [Source: RareSkills — Smart Contract Security]

- [ ] **ERC4626 inflation attack — front-running first depositor**: First depositor donates assets to inflate share price, causing subsequent depositors to receive 0 shares due to rounding. Combination of front-running + rounding error. Mitigate with virtual shares/assets or minimum first deposit. [Source: RareSkills — Smart Contract Security]

## Devdacian — Base AI Auditor Primer Additions (Phase 3)

- [ ] **Auction can be seized during active period — off-by-one in timestamp**: If auction end check uses `>` instead of `>=`, the auction can be seized at exactly `auctionStartTimestamp + auctionLength`, one second early. [Source: Devdacian — Base Primer]

- [ ] **Loan state manipulation via refinancing to cancel auctions indefinitely**: Borrowers can cancel liquidation auctions by refinancing the loan, then allow it to become liquidatable again, repeating the cycle to extend loans indefinitely. [Source: Devdacian — Base Primer]

- [ ] **Double debt subtraction during refinancing**: If refinancing subtracts the old debt from pool balance and also subtracts it again during loan transfer, the pool balance becomes understated, potentially blocking future operations. [Source: Devdacian — Base Primer]

- [ ] **Griefing with dust loans below minLoanSize**: If `minLoanSize` is only checked at loan creation but not on refinancing/splitting, attackers can create compliant loans then split them into dust, forcing unwanted small positions onto lenders. [Source: Devdacian — Base Primer]

## Supplemental Attack Vectors (SAS-AV)

These vectors are merged from sanbir/solidity-auditor-skills; each item retains a detection condition (D), false-positive gate (FP), and source provenance.

- [ ] **[SAS-AV-001] Same-Block Deposit-Withdraw Exploiting Snapshot-Based Benefits**
  - **D:** Protocol calculates yield, rewards, voting power, or insurance coverage based on balance at a single snapshot point. No minimum lock period between deposit and withdrawal. Attacker flash-loans tokens, deposits, triggers snapshot (or waits for same-block snapshot), claims benefit, withdraws — all in one tx/block.
  - **FP:** `getPastVotes(block.number - 1)` or equivalent past-block snapshot. Minimum holding period enforced (`require(block.number > depositBlock)`). Reward accrual requires multi-block time passage.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-3/315

- [ ] **[SAS-AV-002] Invariant or Cap Enforced on One Code Path But Not Another**
  - **D:** A constraint (pool cap, max supply, position limit, collateral ratio) is enforced during normal operation (e.g., `deposit()`) but not during settlement, reward distribution, interest accrual, or emergency paths. Constraint violated through the unguarded path.
  - **FP:** Invariant check applied in a shared modifier/internal function called by all relevant paths. Post-condition assertion validates invariant after every state change.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-8/206/339

- [ ] **[SAS-AV-003] Immutable / Constructor Argument Misconfiguration**
  - **D:** Constructor sets `immutable` values (admin, fee, oracle, token) that can't change post-deploy. Multiple same-type `address` params where order can be silently swapped. No post-deploy verification.
  - **FP:** Deployment script reads back and asserts every configured value. Constructor validates: `require(admin != address(0))`, `require(feeBps <= 10000)`.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-31

- [ ] **[SAS-AV-005] Commit-Reveal Scheme Not Bound to msg.sender**
  - **D:** Commitment hash does not include `msg.sender`: `commit = keccak256(abi.encodePacked(value, salt))`. Attacker copies a victim's commitment from the chain/mempool and submits their own reveal for the same hash from a different address. Affects auctions, governance votes, randomness.
  - **FP:** Commitment includes sender: `keccak256(abi.encodePacked(msg.sender, value, salt))`. Reveal validates `msg.sender` matches stored committer.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-37

- [ ] **[SAS-AV-006] Block Number as Timestamp Approximation**
  - **D:** Time computed as `(block.number - startBlock) * 13` assuming fixed block times. Variable across chains/post-Merge. Wrong interest/vesting/rewards.
  - **FP:** `block.timestamp` used for all time-sensitive calculations.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-56

- [ ] **[SAS-AV-007] Nonce Gap from Reverted Transactions (CREATE Address Mismatch)**
  - **D:** Deployment script uses `CREATE` and pre-computes addresses from deployer nonce. Reverted/extra tx advances nonce — subsequent deployments land at wrong addresses.
  - **FP:** `CREATE2` used (nonce-independent). Script reads nonce from chain before computing. Addresses captured from deployment receipts.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-71

- [ ] **[SAS-AV-008] Array `delete` Leaves Zero-Value Gap Instead of Removing Element**
  - **D:** `delete array[index]` resets element to zero but does not shrink the array or shift subsequent elements. Iteration logic treats the zeroed slot as a valid entry.
  - **FP:** Swap-and-pop pattern used. Iteration skips zero entries explicitly. EnumerableSet or similar library used.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-88

- [ ] **[SAS-AV-011] Transient Storage Low-Gas Reentrancy (EIP-1153)**
  - **D:** Contract uses `transfer()`/`send()` (2300-gas) as reentrancy guard + uses `TSTORE`/`TLOAD`. Post-Cancun, `TSTORE` succeeds under 2300 gas. Also: transient reentrancy lock not cleared at call end — persists for entire tx, DoS via multicall.
  - **FP:** `nonReentrant` backed by regular storage slot (or transient mutex properly cleared). CEI followed unconditionally.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-97

- [ ] **[SAS-AV-013] Non-Atomic Multi-Contract Deployment (Partial System Bootstrap)**
  - **D:** Deployment script deploys interdependent contracts across separate transactions. Midway failure leaves half-deployed state.
  - **FP:** Single `vm.startBroadcast()`/`vm.stopBroadcast()` block. Factory deploys+wires all in one tx. Script is idempotent.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-101

- [ ] **[SAS-AV-015] Front-Running Zero Balance Check with Dust Transfer**
  - **D:** `require(token.balanceOf(address(this)) == 0)` gates a state transition. Dust transfer makes balance non-zero, DoS-ing the function.
  - **FP:** Threshold check (`<= DUST_THRESHOLD`) instead of `== 0`. Access-controlled function. Internal accounting ignores direct transfers.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-128

- [ ] **[SAS-AV-016] Cross-Function Reentrancy**
  - **D:** Two functions share state variable. Function A makes external call before updating shared state; Function B reads that state. `nonReentrant` on A but not B.
  - **FP:** Both functions share same contract-level mutex. Shared state updated before any external call.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-151

- [ ] **[SAS-AV-018] Calldata Input Malleability**
  - **D:** Contract hashes raw calldata for uniqueness. Dynamic-type ABI encoding uses offset pointers — multiple distinct layouts decode to identical values. Attacker bypasses dedup.
  - **FP:** Uniqueness check hashes decoded parameters: `keccak256(abi.encode(decodedParams))`. Nonce-based replay protection.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-167

- [ ] **[SAS-AV-022] Sender Confusion Under Multicall / Forwarder Context**
  - **D:** Code that should reason about the original signer uses raw `msg.sender` inside multicall, relayer, or trusted-forwarder flows. Hooks, accounting, authz, or recipient attribution then execute against the batching contract / forwarder instead of the real user. Common pattern: helper libraries like `_msgSender()` / `LibMulticaller.senderOrSigner()` exist, but one or more internal paths bypass them.
  - **FP:** Every authorization- or attribution-sensitive path consistently uses the canonical sender abstraction for the architecture (`_msgSender()`, trusted forwarder context, multicaller helper). Tests cover direct call, multicall, and forwarded execution paths and assert identical authorization semantics.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-228

- [ ] **[SAS-AV-024] False Existence Detection via Balance Check at Computed Address**
  - **D:** Contract checks pool/pair existence via `balanceOf()` at computed CREATE2 address. Pre-sent tokens make `balanceOf > 0` before deployment — logic assumes pool exists, attempts swap, reverts.
  - **FP:** Existence via factory: `factory.getPair(A, B) != address(0)`. `code.length > 0` checked. Pool verified by calling pool-specific function (`getReserves()`, `token0()`).
  - **Origin:** `sanbir/solidity-auditor-skills` AV-244

- [ ] **[SAS-AV-025] State Record Overwrite Without Existence Check**
  - **D:** Mapping entry (refund, withdrawal, order) written without checking if key occupied. Overwrites legitimate user's record — blocks claim, redirects funds, or poisons state. Pattern: `records[key] = newData` without `require(records[key].amount == 0)`.
  - **FP:** Existence check before write. Nonce/hash-based keys prevent collision. Append-only structure. Old entry processed before overwrite.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-282

- [ ] **[SAS-AV-026] Sentinel / Placeholder Address Operations**
  - **D:** Code branches on sentinel (`address(0)`, `0xEeEe...`, `type(uint256).max`) for ETH/special cases. Special branch omits validations the normal branch performs. Also: ERC20 calls on sentinel — high-level reverts (no code), low-level succeeds silently.
  - **FP:** Sentinel branch has equivalent validation. No ERC20 calls on sentinels. WETH wrapping instead of dual-path. Early detection routes to independent handler.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-295

- [ ] **[SAS-AV-028] msg.value vs Computed Amount Mismatch**
  - **D:** Payable function computes `netAmount` after fees but forwards full `msg.value` downstream. Or trusts user-supplied `amount` without `require(msg.value == amount)`.
  - **FP:** `require(msg.value == expectedAmount)` at entry. Fee-adjusted amount used consistently. Excess refunded.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-307

- [ ] **[SAS-AV-029] Namespace / ID Reuse Across Subsystems**
  - **D:** Multiple subsystems populate the same identifier space (`positionId`, `vaultId`, `requestId`, `orderId`), but authorization and state transitions only validate the ID, not the originating subsystem. An ID created in subsystem A is accepted by subsystem B, bypassing assumptions about ownership or lifecycle.
  - **FP:** IDs are namespaced per subsystem, or every call validates both `id` and subsystem/type discriminator. Cross-subsystem direction table reviewed and impossible states rejected.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-322

- [ ] **[SAS-AV-030] Sentinel Collision on Exhausted Quota**
  - **D:** `0` or another sentinel means "unset" / "unlimited", but the same value is also reachable through normal exhaustion (`remaining = 0`). Once a finite quota decrements to the sentinel value, the contract interprets the exhausted state as unlimited and re-enables access.
  - **FP:** Exhausted state is represented separately from unset state (extra boolean, distinct enum, non-zero sentinel). Decrement path cannot transition into the meaning of "unlimited".
  - **Origin:** `sanbir/solidity-auditor-skills` AV-324

- [ ] **[SAS-AV-031] Mapping Default Value State Ambiguity**
  - **D:** Mapping default values (`0`, `false`, empty struct) are treated as "never initialized", but those same values are also valid initialized states. Attackers reset or route execution through the default state to re-trigger initialization, bypass one-time checks, or claim resources repeatedly.
  - **FP:** Initialization tracked with an explicit boolean / version field. Default value is never used as the sole signal for state existence. Distinct-state collision tests cover `never set` vs `set to zero`.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-325

- [ ] **[SAS-AV-032] Swap-and-Pop Moved Index Stale Reference**
  - **D:** List deletion uses swap-and-pop, but auxiliary state still points to the moved element's old index. Subsequent reads, deletes, or authorization checks operate on the wrong record, enabling corruption or unauthorized access to the moved item.
  - **FP:** Every swap-and-pop updates both the removed item's metadata and the moved item's index mapping atomically. No external references depend on unstable indices, or stable IDs are used instead.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-328

- [ ] **[SAS-AV-033] Tautology in Require (Self-Comparison Validation Bypass)**
  - **D:** A `require()` statement compares a variable to itself (`require(sourceAddressesRoot == sourceAddressesRoot)`), which always evaluates to true. This is a copy-paste or typo error where the right-hand side should be a different variable (e.g., the computed/expected root). The validation is completely bypassed, allowing arbitrary inputs to pass proof verification.
  - **FP:** The comparison is intentionally tautological as a placeholder. The function is not security-critical.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-331

- [ ] **[SAS-AV-035] Override/Extension Mismatch (Inherited Security Property Loss)**
  - **D:** When a contract overrides or wraps a base contract's function, the override may preserve explicit guards (`require`, `revert`, access control) but silently drop implicit structural properties (storage key schemes, ordering assumptions, aggregation granularity). For example, a base contract uses composite storage keys `keccak256(user, epoch)` for isolation, but the override switches to `mapping(user => value)`, losing epoch isolation. Explicit checks all pass but the structural security property is gone.
  - **FP:** Override was intentionally designed to change the structural property (documented). The structural property is not security-relevant in the derived context.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-340

## drozer-lite Additions

The checks below are the canonical runtime additions from the EVM-relevant drozer-lite profiles. Each item retains the source profile and pinned commit.

- [ ] **[DROZER-GAME-2] Finite-Pool Selection & Depletion Fallback**
  - **D:** A finite prize pool selects items with a fallback when the pool is empty; the attacker depletes the pool to force the fallback outcome. Alternatively, the depletion state is observable before action, letting attackers choose when to commit.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** For every finite-pool selection, enumerate the depletion state and the fallback outcome. Ask whether the attacker can (a) observe the depletion state atomically and skip, (b) intentionally deplete the pool to force the fallback, or (c) time their action around another's commitment. Verify the fallback does not provide a profitable alternative.
  - **Look for:** `if (remainingPrizes == 0) return consolationPrize;` where consolation is valuable enough to target Attacker can call `peek()` view functions to check pool state atomically Prize pool re-filled mid-round from an attacker-influenced source
  - **Origin:** [gdroz3r/drozer-lite — checklists/gaming.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/gaming.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-RE-4] Read-After-Call for Security Decisions**
  - **D:** A variable read after an external call is used for access control, balance checking, or amount calculation. The callee can manipulate that state during the call.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** For every external call, audit what is read after. Any security-critical read after an external call must either be re-validated or moved before the call.
  - **Look for:** `balance = balanceOf(user); target.call(...); if (balance > X) { ... }` (but balance was captured before call) — worse: re-read after call `require(owner == msg.sender)` read after an untrusted call
  - **Origin:** [gdroz3r/drozer-lite — checklists/reentrancy.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/reentrancy.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-UNI-51] Atomic Value Transfer**
  - **D:** Sender's balance decreases by X but receiver's increases by Y != X (minus fees).
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** For each transfer, verify source debit == destination credit + documented fee.
  - **Look for:** No source-specific red flags listed; trace the invariant and caller-controlled inputs described above.
  - **Origin:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-UNI-53] No Free Extraction**
  - **D:** A sequence of calls allows withdrawing more value than deposited (net of fees and yield).
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** Model the protocol as a closed economy. Attempt to construct a cycle that produces profit without external input.
  - **Look for:** No source-specific red flags listed; trace the invariant and caller-controlled inputs described above.
  - **Origin:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-UNI-98] receive()/fallback() Auto-Route Balance Invariant Break**
  - **D:** A contract has a `receive()` or `fallback()` payable function that unconditionally forwards `msg.value` into a state-mutating function in the same contract (deposit, wrap, stake, mint, buy). Another function in the same contract uses `address(this).balance` as part of an invariant check (e.g., `require(address(this).balance >= amount)` before a refund / withdraw / return / claim). Because the auto-route consumes incoming native value before it can accumulate, the balance-based invariant can be permanently unsatisfiable, or at minimum becomes dependent on chain-specific semantics for how native value can enter the contract without invoking `receive()`.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** For every `receive()` and `fallback()` function in the cluster: 1. Check whether it unconditionally forwards `msg.value` into a state-mutating function (one that writes storage, mints tokens, or calls an external contract with value). 2. Grep the entire cluster for any `address(this).balance` read used in a `require`, arithmetic, or branch that affects a user-visible decision (refund, withdraw, claim, redeem, rescue). 3. If both conditions hold, trace whether there is ANY path by which native value can enter the contract WITHOUT invoking `receive()` (e.g., `selfdestruct(to)` from another contract, direct balance credit from a privileged precompile, block reward to COINBASE if the contract is a miner/proposer, chain-specific system transfers). If no such path exists, the invariant is permanently broken. If one exists, the invariant is brittle and subject to operational assumptions outside the source.
  - **Look for:** `receive() external payable { f(); }` where `f()` is any state-mutating function in the same contract `fallback() external payable { ... f(); }` similarly Any function with `require(address(this).balance >= amount, ...)` whose sibling contract has an auto-routing `receive()`/`fallback()` A "rescued" or "cancelled" accumulator variable whose only payout path depends on contract balance growing via future external transfers Comments or docs saying "buffer provides liquidity" or "accumulated value drains to users" but no actual code path produces non-auto-routed inbound value *Severity rule (HARD)**: When the balance-based invariant is read in a user-facing function (withdraw, refund, claim, redeem, rescue, confirm, settle), this check MUST be rated at least HIGH. Do NOT downgrade to MEDIUM due to uncertainty about chain-specific native-transfer semantics — the correct finding is HIGH with a note that exploitability depends on operational assumptions the auditor should flag and verify with the protocol team. Severity miscalibration on this pattern is itself a finding-quality bug.
  - **Origin:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-UNI-100] Asymmetric Settlement Across Parallel Transfer Paths**
  - **D:** A system has two or more functions that transfer ownership or move the same asset (e.g., `transfer` vs `send`, `transferFrom` vs `safeTransferFrom`, `withdraw` vs `emergencyWithdraw`, `redeem` vs `rescue`). One path includes settlement logic (payment to seller, fee deduction, accounting update, reward distribution). Another path transfers the asset without performing the same settlement, creating a bypass.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** 1. Enumerate every function that changes ownership of an asset or moves value out of the contract. 2. Group these functions by the asset class they operate on. 3. For each group, build a comparison table: function name | settlement logic present? | fee deducted? | accounting updated? | events emitted? 4. If ANY function in the group skips settlement that another function performs, flag. Pay special attention to wrapper functions that call a shared internal `_transfer` without the outer settlement layer.
  - **Look for:** `transfer()` includes payment settlement but `send()` calls `_transfer()` directly without settlement `withdraw()` updates accounting but `emergencyWithdraw()` does not Public `_transfer_nft()` helper is callable by approved addresses and bypasses the sale/auction settlement in `transfer_nft()` A function that takes a `recipient` parameter (allowing caller to send to another address) and a parallel function that forces `msg.sender` as recipient — the first may skip payment checks the second enforces Two functions that both call `check_can_send()` but only one settles the associated financial obligation (bid, deposit, escrow)
  - **Origin:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-UNI-101] Destructive Operation Without Obligation Settlement**
  - **D:** A destructive operation (burn, delete, remove, close, self-destruct, deactivate) destroys an entity that carries active obligations — deposits held against it, active rentals or leases, pending reward claims, locked collateral, open orders, or unresolved escrows. The destruction erases the entity's records from storage, but the funds associated with those obligations remain in the contract with no recovery path. Affected users can no longer call cancel/refund/claim because the entity no longer exists.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** For every destructive function (burn, remove, close, delete, deactivate, self-destruct): 1. Identify what data is erased (the entity's full storage record, including nested structs, vectors, mappings). 2. Check whether any of the erased data includes: deposit amounts, active rental/lease records, pending claims, locked collateral, open bids, escrowed funds. 3. Verify the function checks for zero active obligations BEFORE allowing destruction. Acceptable patterns: `require(obligations.length == 0)`, `require(deposit_amount == 0)`, iterating obligations and refunding each before deletion. 4. If the function only checks ownership/approval but not obligation status, flag.
  - **Look for:** `burn()` checks `check_can_send()` (ownership) but not whether `rentals.len() > 0` or `bids.len() > 0` `closePosition()` deletes the position record without checking `pendingRewards > 0` `deleteAccount()` while staking/delegation entries still reference the account `remove(tokenId)` erases a token struct that contains a Vec of deposit records Any destructive function where the authorization check is ownership/approval only, without an obligation-settlement check
  - **Origin:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-UNI-102] Heterogeneous Collection Without Type Discrimination**
  - **D:** A collection (Vec, array, mapping, linked list) stores items of different subtypes, distinguished by a type flag, enum field, or discriminant. Operations that search, iterate, cancel, settle, or finalize items in the collection match by identity fields (address, ID, period) but do NOT filter by the type discriminant. This allows an operation designed for subtype A to match and operate on a subtype B item that has different economic parameters (denomination, rate, fee structure, cancellation policy).
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** 1. Identify every collection that stores items with a type discriminant field (e.g., `item_type: bool`, `order_side: enum`, `position_type: u8`, `category: u8`). 2. For every function that searches/iterates the collection, check whether the search predicate includes the type discriminant. 3. If the search matches by (address + period) or (address + id) but ignores (type), verify whether the matched item's economic parameters (denomination, rate, terms) could differ from what the calling function assumes. 4. If a function reads denomination/rate/terms from a TYPE-LEVEL config (e.g., `shortterm_rental.denom`) but the matched item was created under a DIFFERENT type's config (e.g., `longterm_rental.denom`), flag as HIGH — this enables cross-denomination value extraction.
  - **Look for:** A `rentals` Vec stores both short-term and long-term entries with a `type` flag, but cancel/finalize functions search by `(address, period)` without checking `type` An order book stores buy and sell orders in the same array with a `side` field, but settlement iterates without filtering by side A positions collection mixes collateralized and uncollateralized positions, but liquidation logic applies uniformly A function reads the denomination from a type-level config struct but the matched item in the shared collection was created under a different type's denomination Cancel function for type A matches a type B item and refunds using type A's denomination instead of the item's stored denomination
  - **Origin:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-UNI-103] Payment-Gated Transfer Allows Beneficiary Mismatch**
  - **D:** A function combines asset transfer with payment settlement. The payment amount is looked up from a mapping or list keyed by the recipient address (e.g., bids, deposits, escrow entries). The caller can freely specify the recipient parameter. If the recipient has no entry in the payment mapping, the amount defaults to zero and the transfer proceeds without payment to the previous owner. Alternatively, the caller specifies a recipient different from themselves to avoid their own payment being consumed, then cancels their payment entry for a full refund.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** 1. For every function that transfers an asset AND looks up a payment amount by a caller-supplied address parameter: a. Check whether the function reverts when no payment entry exists for the specified recipient (amount == 0 case). b. Check whether the function validates that the payment amount meets the listed/required price. c. Check whether the caller is constrained to specify themselves as the recipient, or can specify any address. 2. If the function proceeds with transfer when `amount == 0` (no matching payment), flag as HIGH — the asset is transferred for free. 3. If the function does not validate `amount >= listed_price`, flag as HIGH — the asset can be transferred for less than the listed price.
  - **Look for:** `amount = bids[recipient].offer` defaults to 0 when no bid exists, and the function has a branch that proceeds with transfer when `amount == 0` Transfer function accepts `recipient` as a parameter (not forced to `msg.sender`), allowing the caller to route the transfer to an address with no active bid Caller can: (1) place a bid to gain approval, (2) call transfer with a DIFFERENT recipient who has no bid (zero payment), (3) cancel their own bid for full refund No `require(amount >= listed_price)` check between the payment lookup and the ownership transfer The `amount > 0` branch sends payment to the previous owner, but the `amount == 0` branch still transfers ownership
  - **Origin:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-UNI-105] Stored Constraint Not Enforced at Consumption Point**
  - **D:** A configuration or listing function accepts and stores a constraint parameter (available period, whitelist, max participants, allowed tokens, deadline, minimum amount, geographic restriction). The consuming function that should enforce this constraint (reservation, deposit, bid, claim, register) operates on the same entity but never reads or validates the stored constraint. The constraint exists in storage but has zero enforcement — users can bypass it simply by never encountering a check.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** 1. For every configuration/listing function, enumerate every field it writes to storage. 2. For each stored field, classify it as: (a) data field (description, name, URI — informational), or (b) constraint field (period, whitelist, max, min, deadline, rate — should restrict behavior). 3. For each constraint field, find ALL consuming functions that operate on the same entity. Verify the constraint field is READ and produces a REVERT or behavioral change in each consumer. 4. If a constraint field is stored but never read by any consuming function, flag as MEDIUM — the feature is broken, not just missing.
  - **Look for:** `available_period` set in listing function but reservation function checks `minimum_stay` only, ignoring `available_period` entirely `max_participants` stored on entity creation but join function has no cap check `allowed_tokens` whitelist stored but deposit function accepts any denomination `deadline` stored but claim function checks `block.timestamp` against a different value `auto_approve` flag stored for one rental type but the approval function for that type never reads it Any field in a config struct that is written in the setter and read ONLY in query/view functions (never in state-changing functions)
  - **Origin:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-UNI-106] Listing-Gate Bypass on Unlisted Entities**
  - **D:** An entity has a listing status field (`is_listed`, `active`, `status`, `enabled`) that is set by a listing function and cleared by an unlisting function. Consumer functions (bid, reserve, purchase, deposit, subscribe) that should only operate on listed entities do not check the listing status. This allows: (1) operations on entities that were never listed, (2) operations on entities that were explicitly delisted, (3) exploitation of stale configuration (e.g., `auto_approve` from a previous listing) on a currently unlisted entity.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** 1. For every entity with a listing/status flag, enumerate: (a) the function that sets it to active/listed, (b) the function that sets it to inactive/unlisted, (c) all consumer functions that operate on the entity. 2. For each consumer function, verify it checks the listing status flag early in execution (before accepting funds, granting approvals, or modifying state). 3. Pay special attention to configuration fields that PERSIST across list/unlist cycles. If `auto_approve`, `price`, `denomination`, or other economic parameters are set during listing and NOT cleared during unlisting, check whether consumers of these fields are guarded by the listing status. 4. If a consumer function accepts funds or grants permissions without checking listing status, flag. Severity depends on whether the stale configuration enables value extraction.
  - **Look for:** `bid()` function does not check `is_listed == true` before accepting funds and granting approval `reserve()` function accepts deposits for unlisted properties/assets `purchase()` function operates on delisted items using stale price/denomination from a prior listing Unlisting function sets `is_listed = false` but does NOT clear `auto_approve`, `price`, or `denomination` — these persist and are used by consumer functions that skip the listing check Any consumer function that reads economic parameters (price, denomination, approval mode) from the entity without first verifying the entity is currently listed
  - **Origin:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-UNI-108] Temporal Parameter Allows Retroactive / Past Values at Creation**
  - **D:** An entity with a time-based lifecycle (farm, vesting schedule, auction, subscription, rental) accepts a `start_time` or `start_epoch` parameter at creation. The parameter is validated for basic sanity (> 0, < end) but is NOT validated against the current time/epoch. This allows creating entities that "started in the past," retroactively assigning rewards, obligations, or access to historical periods that other participants have already settled.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** 1. For every creation function that accepts a start_time/start_epoch parameter, verify it is enforced as `>= current_time + 1` or `>= current_epoch + 1`. 2. Check the default value when the parameter is omitted — if it defaults to `current + 1`, verify the explicit path has the same constraint. 3. Trace what happens if start is set to a past value: are rewards retroactively assigned? Do billing periods extend into the past? Can the creator claim historical periods?
  - **Look for:** `start_epoch = params.start_epoch.unwrap_or(current_epoch + 1)` but no `ensure!(start_epoch >= current_epoch + 1)` for the explicit case Validation checks `start < end` and `end > current` but not `start > current` A farm/schedule created with past start_epoch assigns emissions to epochs where participants already claimed, creating unfair distribution Default path is safe (`current + 1`) but explicit path bypasses the constraint
  - **Origin:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- [ ] **[DROZER-UNI-109] Self-Call Identity Confusion**
  - **D:** A function performs a two-step operation by calling itself: step 1 initiates (stores context in a buffer), step 2 is triggered via a self-call (SubMsg or wasm_execute to self). The second step's `info.sender` is the contract's own address, not the original user. If step 2 has an authorization check like `require(sender == receiver)` or `require(sender == user)`, it fails because sender is the contract. Conversely, if step 2 has an authorization check like `require(sender == admin || sender == contract)`, the self-call bypasses user-level restrictions.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** 1. For every SubMsg or wasm_execute that targets the contract's own address (`env.contract.address`), identify the function being called. 2. Check what `info.sender` is used for in the called function. If it's used for authorization, it will be the contract address, not the original caller. 3. Check whether any receiver/beneficiary validation compares against `info.sender` — this will fail for the self-call case. 4. Check whether any privilege check accepts the contract's own address — this could be a bypass vector.
  - **Look for:** `wasm_execute(env.contract.address, &ExecuteMsg::ProvideLiquidity { receiver: user, ... }, funds)` where `ProvideLiquidity` checks `ensure!(receiver == info.sender)` — fails because info.sender is the contract Two-step LP provision: step 1 swaps half, step 2 provides balanced LP. Step 2's sender check rejects the self-call. A singleton buffer stores context for the reply handler — if two users trigger step 1 in the same block, the second overwrites the first's buffer Any function with `if info.sender == env.contract.address { /* special path */ }` that grants elevated privileges
  - **Origin:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

## drozer-lite Provenance (deduplicated)

The source checks below are already represented by canonical checks in this domain. These provenance records do not add checklist items.

- `DROZER-RE-1` **CEI Pattern Violation (Classic Reentrancy)** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/reentrancy.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-RE-2` **Guard Coverage Gap (Missing nonReentrant)** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/reentrancy.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-RE-3` **Cross-Function Reentrancy** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/reentrancy.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-2` **State Machine / Lifecycle Bypass** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-3` **Classic Reentrancy** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-4` **Cross-Function / Read-Only Reentrancy** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-5` **Missing Zero-Address / Zero-Amount Checks** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-7` **Unchecked External Call Return Values** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-10` **Timestamp Dependence for Security Decisions** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-11` **Missing Event Emission on State Changes** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-16` **Array Boundary Edge Cases** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-17` **Post-Commitment State Mutation** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-18` **Uninitialized-State Guard Bypass** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-19` **Temporal Constraint Incompatibility** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-21` **Derived-Value Domain Bounds** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-22` **Work-Reward Decoupling** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-23` **Identifier Namespace Collisions** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-24` **Spec Exhaustive Compliance** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-25` **Error-State Asymmetry in Adversarial Protocols** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-29` **Aggregate State Removal Consistency** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-30` **Stale-Snapshot After Collection Mutation** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-31` **Prerequisite Update Before Participant Change** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-32` **Last-Element Array+Mapping Removal** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-39` **Monotonic State Progression** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-40` **Past-Epoch Immutability** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-41` **Cooldown Bypass** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-42` **Deadline Validity** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-43` **Sequence / Step Ordering** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-57` **Mapping Key Uniqueness (encodePacked Pitfalls)** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-60` **Taint Boundary at External Returns** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539domain=general EVM=44 new=13 provenance=31

- `DROZER-UNI-99` **Approval / Permission Persistence After Action Reversal** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

## Auditmos/skills Provenance (deduplicated)

The source patterns below are already represented by canonical checks in this suite. These provenance records retain Auditmos coverage without adding duplicate checklist items.

- `AUDITMOS-AUCTION-4` **Auction Can Be Seized During Active Period** -> existing auction timestamp boundary check; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-auction/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-REENTRANCY-1` **Token Transfer Reentrancy** -> existing canonical coverage in evm-audit-general; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-reentrancy/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-REENTRANCY-2` **State Update After External Call** -> existing canonical coverage in evm-audit-general; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-reentrancy/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-REENTRANCY-3` **Cross-Function Reentrancy** -> existing canonical coverage in evm-audit-general; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-reentrancy/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-REENTRANCY-4` **Read-Only Reentrancy** -> existing canonical coverage in evm-audit-general; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-reentrancy/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-STATE-VALIDATION-2` **Unexpected Matching Inputs** -> existing canonical coverage in evm-audit-general; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-state-validation/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-STATE-VALIDATION-3` **Unexpected Empty Inputs** -> existing canonical coverage in evm-audit-general; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-state-validation/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-STATE-VALIDATION-4` **Unchecked Return Values** -> existing canonical coverage in evm-audit-general; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-state-validation/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-STATE-VALIDATION-8` **Improper Pause Mechanism** -> existing canonical coverage in evm-audit-general; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-state-validation/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
