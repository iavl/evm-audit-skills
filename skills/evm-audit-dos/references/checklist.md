<!-- GENERATED FILE: source is ../../../data/canonical-checks.json; do not edit by hand. -->
# DoS & Griefing Security Checklist

Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.
Global FP/proof obligations live in the Review Contract; only check-specific gates and proofs are repeated below.

## Gas Griefing

- [ ] **[EVM-DOS-001] Returndata bombing via external calls** _(exploit-pattern; medium)_: When calling an untrusted address, the callee can return a massive amount of data. The EVM copies all return data to the caller's memory, consuming gas proportional to the return size. Use inline assembly with `returndatasize()` checks or fixed-size return buffers. Look for: `.call()` to user-controlled addresses without capping return data. [beirao E-04, E-12, E-16]
  - **Provenance:** beirao E-04, E-12, E-16

- [ ] **[EVM-DOS-002] Insufficient gas forwarding (SWC-126)** _(heuristic; contextual)_: When a contract calls another contract via `.call{gas: X}()` with a fixed gas amount, the caller can provide just enough gas for the outer function to succeed but not enough for the inner call. The outer function may silently succeed while the inner call fails. Look for: `.call{gas: fixedAmount}()` where the fixed amount may be too low for certain execution paths. [beirao E-03, Tamjid F-08]
  - **Provenance:** beirao E-03, Tamjid F-08

## Unbounded Loops

- [ ] **[EVM-DOS-003] User-growable arrays iterated in a loop** _(exploit-pattern; medium)_: If users can add elements to an array (stakers, depositors, whitelisted addresses) and a function iterates over the entire array, an attacker can DoS the function by adding elements until it exceeds the block gas limit. Look for: `for (i = 0; i < array.length; i++)` where `array` can grow via public functions. [beirao L-02, Decurity LSD, Hacken UniV4]
  - **Provenance:** beirao L-02, Decurity LSD, Hacken UniV4

- [ ] **[EVM-DOS-004] External calls inside loops** _(exploit-pattern; medium)_: Each external call in a loop consumes significant gas and can revert (e.g., blocklisted token transfer). One revert kills the entire transaction. Look for: `token.transfer()` or `.call()` inside a for loop. Fix: use pull-payment pattern. [beirao L-02, G-04]
  - **Provenance:** beirao L-02, G-04

- [ ] **[EVM-DOS-005] On L2s with cheap gas, array-filling attacks are economically viable** _(exploit-pattern; medium)_: What costs $10K on mainnet might cost $10 on Arbitrum. DoS via array filling becomes practical. Look for: any unbounded array on L2 deployments where gas costs don't deter attackers. [multichain-auditor]
  - **Provenance:** multichain-auditor

## Revert-Based DoS

- [ ] **[EVM-DOS-006] ETH receiver with reverting fallback** _(heuristic; contextual)_: If a function sends ETH to an address that reverts on receive (contract without `receive()` or with reverting fallback), the entire transaction fails. Look for: `payable(addr).transfer()` or `.call{value: amt}("")` where `addr` could be a contract. [beirao E-11, G-04]
  - **Provenance:** beirao E-11, G-04

- [ ] **[EVM-DOS-007] Token transfer to blocklisted address** _(exploit-pattern; medium)_: If any recipient in a batch operation is blocklisted by the token (USDC/USDT), the entire batch reverts. Look for: batch distribution functions that iterate over recipients. [Decurity CDP]
  - **Provenance:** Decurity CDP

- [ ] **[EVM-DOS-008] Zero-amount transfer reverts** _(heuristic; contextual)_: Some tokens (LEND) revert on zero transfers. If reward calculations round to zero for some users, their claim reverts. Look for: `transfer(user, rewardAmount)` where `rewardAmount` could be 0. [weird-erc20, beirao FT-12]
  - **Provenance:** weird-erc20, beirao FT-12

## Block Stuffing & Time-Based DoS

- [ ] **[EVM-DOS-009] Block stuffing to prevent time-sensitive actions** _(exploit-pattern; medium)_: An attacker fills blocks with spam transactions to prevent liquidations, auction bids, or governance actions within a deadline. More viable on L2s with lower gas costs. Look for: time-limited actions (auctions, liquidation windows, grace periods) that must execute within N blocks. [beirao G-04, multichain-auditor]
  - **Provenance:** beirao G-04, multichain-auditor

- [ ] **[EVM-DOS-010] Timelock-based griefing at no cost** _(exploit-pattern; medium)_: If a protocol has a timelock, an attacker can trigger the timelock repeatedly to prevent actions from ever executing. Look for: timelocked actions that can be restarted by anyone. [beirao G-04]
  - **Provenance:** beirao G-04

## Economic Griefing

- [ ] **[EVM-DOS-011] Front-running liquidation griefing** _(exploit-pattern; medium)_: An attacker front-runs a liquidation by adding a tiny amount of collateral, making the position just healthy enough to avoid liquidation but not enough to protect the borrower. The liquidator's transaction fails, wasting gas. Look for: liquidation functions where slight collateral changes can change the outcome. [beirao LEN-08]
  - **Provenance:** beirao LEN-08

- [ ] **[EVM-DOS-012] Account abstraction DoS via free paymaster** _(exploit-pattern; medium)_: When using paymasters (ERC-4337), transactions are free for users. Attackers can spam thousands of free transactions to DoS the system. Look for: paymaster implementations without rate limiting or anti-spam measures. [beirao AA-01]
  - **Provenance:** beirao AA-01

## Pause-Related DoS

- [ ] **[EVM-DOS-013] Pausing liquidations creates solvency risk** _(exploit-pattern; medium)_: If both user operations AND liquidations are paused, the protocol accumulates bad debt while paused. When unpaused, a cascade of liquidations can cause system insolvency. Look for: pause mechanisms that also block liquidations. [beirao LEN-06, G-09]
  - **Provenance:** beirao LEN-06, G-09

- [ ] **[EVM-DOS-014] Pause can brick contract** _(exploit-pattern; medium)_: If pause is permanent (no unpause mechanism, or unpause requires a condition that can't be met), all paused functions are permanently disabled. Look for: pause without corresponding unpause, or unpause conditions that can become impossible. [beirao G-09]
  - **Provenance:** beirao G-09

## Oracle DoS

- [ ] **[EVM-DOS-015] Chainlink multisig can block price feed access** _(heuristic; contextual)_: Chainlink price feeds are controlled by a multisig. In theory, access could be revoked. Wrap Chainlink calls in try/catch with fallback oracle. Look for: direct `latestRoundData()` calls without try/catch. [Decurity CDP, beirao CL-12]
  - **Provenance:** Decurity CDP, beirao CL-12

- [ ] **[EVM-DOS-016] `balanceOf()` reverting causes DoS** _(exploit-pattern; medium)_: If a token's `balanceOf()` function reverts (e.g., paused token), any function that calls it also reverts. Look for: `balanceOf()` in critical paths without try/catch. [Tamjid X2, S3]
  - **Provenance:** Tamjid X2, S3

## Supplemental Attack Vectors (SAS-AV)

- [ ] **[EVM-DOS-017] Storage Bloat Attack (Unbounded Mapping/Array Growth)** _(exploit-pattern; medium)_: Attacker fills user-controlled mappings/arrays without economic limits (e.g., `userTokens[user].push(attacker_token)` for each of thousands of fake tokens). Functions iterating over this array hit block gas limit.
  - **Specific FP:** Array size bounded (`require(arr.length < MAX)`). Economic deterrent (cost per entry). Pagination for iteration. EnumerableSet with bounded operations.
  - **Provenance:** [SAS-AV-020](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-203

- [ ] **[EVM-DOS-018] Algorithmic Complexity Gas DoS** _(exploit-pattern; medium)_: Nested loops, combinatorial matching, or recursive computation with superlinear gas cost (O(n²), O(2ⁿ)). At production scale, execution exceeds block gas limit, bricking the function.
  - **Specific FP:** O(n) or O(n log n) algorithm. Input capped (`require(n <= MAX)` gas-tested). Computation paginated/batched. Off-chain compute with on-chain verification.
  - **Provenance:** [SAS-AV-023](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-230
