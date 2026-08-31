<!-- GENERATED FILE: source is ../../../data/canonical-checks.json; do not edit by hand. -->
# Signature Security Checklist

Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.
Global FP/proof obligations live in the Review Contract; only check-specific gates and proofs are repeated below.

## Cross-Chain & Cross-Protocol Replay

- [ ] **[EVM-SIG-001] Missing chain ID in signature** _(exploit-pattern; medium)_: A valid signature on Ethereum, an account-abstraction UserOperation, or another supported chain can be replayed on Arbitrum, Polygon, or a fork if the hash omits `block.chainid`. Look for: signature hashes or EIP-712 domains without a dynamic `chainId` binding. [beirao S-01, SWC-121, Dacian — Signature Replay Attacks]
  - **Provenance:** beirao S-01, SWC-121, Dacian — Signature Replay Attacks

- [ ] **[EVM-SIG-002] Missing `address(this)` in signature** _(heuristic; contextual)_: Same contract deployed at the same address on multiple chains (CREATE2 or same nonce) has identical verification. A signature valid for Contract A on chain 1 may be valid for Contract A on chain 2. Even on the SAME chain: if the same contract logic is deployed at two addresses, signatures for one instance replay on the other. Include `verifyingContract: address(this)` in domain separator. Look for: EIP-712 domain separator missing `verifyingContract`. [beirao S-02]
  - **Provenance:** beirao S-02

- [ ] **[EVM-SIG-003] Missing `msg.sender` binding in signature** _(exploit-pattern; medium)_: If the signed message does not include the intended caller or authorized address, anyone who obtains it can use the signature as themselves. Look for: verification that does not bind `msg.sender`/beneficiary to the signed data. [beirao S-06]
  - **Provenance:** beirao S-06

- [ ] **[EVM-SIG-004] Nonce-less signatures are replayable** _(exploit-pattern; medium)_: Without a nonce or equivalent one-time-use state, the same signature can be reused indefinitely, including to restore a revoked privilege. Look for: signed actions without a per-user nonce, consumed nonce, or other replay state. [beirao S-03, Dacian — Signature Replay Attacks, Code4rena Ondo]
  - **Provenance:** beirao S-03, Dacian — Signature Replay Attacks, Code4rena Ondo

- [ ] **[EVM-SIG-005] Missing expiration / deadline in signatures** _(exploit-pattern; medium)_: Signatures without a deadline remain valid forever and can be replayed after the user's circumstances change. Look for: signed message schemas without a `deadline` or `expiry` field. [beirao S-05, Dacian — Signature Replay Attacks, Sherlock NFTPort]
  - **Provenance:** beirao S-05, Dacian — Signature Replay Attacks, Sherlock NFTPort

- [ ] **[EVM-SIG-006] Stale nonce check** _(exploit-pattern; medium)_: If nonce is checked but not incremented BEFORE the action, reentrancy can replay the same nonce. Increment nonce first, then execute. Look for: nonce increment after `call()` or `transfer()`. [beirao S-04]
  - **Provenance:** beirao S-04

## ecrecover Pitfalls

- [ ] **[EVM-SIG-007] Invalid `ecrecover` can return `address(0)`** _(exploit-pattern; medium)_: If `v` is invalid or `s` is out of range, `ecrecover` returns `address(0)` instead of reverting. If the expected signer is unset or the result is not checked, an invalid signature can pass. Look for: `ecrecover(hash, v, r, s)` without `result != address(0)` and expected-signer validation. [beirao S-05, SWC-117, Dacian — Signature Replay Attacks, Code4rena Swivel]
  - **Provenance:** beirao S-05, SWC-117, Dacian — Signature Replay Attacks, Code4rena Swivel

- [ ] **[EVM-SIG-008] Signature malleability** _(exploit-pattern; medium)_: For every valid `(r, s, v)` there can be a second valid signature using the complementary `s` value. If signatures are unique identifiers, the alternate encoding can bypass an “already used” check. Look for: raw `ecrecover()` or signature keys without lower-half-order validation; use OpenZeppelin ECDSA or equivalent. [beirao S-07, SWC-117, Dacian — Signature Replay Attacks]
  - **Provenance:** beirao S-07, SWC-117, Dacian — Signature Replay Attacks

- [ ] **[EVM-SIG-009] Different encoding schemes produce different hashes** _(exploit-pattern; medium)_: `abi.encode` vs `abi.encodePacked` vs `keccak256(abi.encode(keccak256(abi.encode(...))))`. If the signer uses one encoding and the verifier uses another, the signature is invalid. Look for: encoding mismatches between frontend/backend signing and on-chain verification. [beirao S-08]
  - **Provenance:** beirao S-08

- [ ] **[EVM-SIG-010] `abi.encodePacked` collision with dynamic types** _(exploit-pattern; medium)_: `abi.encodePacked` concatenates without padding, so different dynamic inputs can produce the same signature hash. Look for: multiple dynamic-length arguments in signature hashing; use `abi.encode` or an equivalent unambiguous encoding. [SWC-133, beirao G-09, Tamjid C12]
  - **Provenance:** SWC-133, beirao G-09, Tamjid C12

## EIP-712 Typed Signatures

- [ ] **[EVM-SIG-011] `DOMAIN_SEPARATOR` cached at deployment** _(exploit-pattern; medium)_: If the domain is computed once with the deployment chain's `block.chainid`, it can become invalid after a fork or chain-context change. Recompute dynamically or use an equivalent runtime chain-ID check. Look for: immutable/cached domain separators without fork handling. [beirao S-09, multichain-auditor]
  - **Provenance:** beirao S-09, multichain-auditor

- [ ] **[EVM-SIG-012] Struct hash must include ALL fields** _(exploit-pattern; medium)_: Omitting a field from the struct hash means it's not signed. An attacker can change the unsigned field freely. Look for: EIP-712 type hash that doesn't include all struct fields. [beirao S-10]
  - **Provenance:** beirao S-10

- [ ] **[EVM-SIG-013] EIP-712 salt for unintended cross-protocol replay** _(exploit-pattern; medium)_: Two protocols using the same EIP-712 struct types can have signature replay between them. Using a unique `salt` in the domain separator prevents this. Look for: protocols with identical struct types and no differentiating domain parameter. [beirao S-11]
  - **Provenance:** beirao S-11

## Permit (ERC-2612) Specific

- [ ] **[EVM-SIG-014] Permit front-running griefing (DoS)** _(exploit-pattern; medium)_: User creates permit signature → submits `permit()` + `transferFrom()` in one transaction → attacker front-runs by extracting the signature and calling `permit()` first → user's transaction reverts because the nonce was consumed. Fix: wrap permit in try/catch, or use separate transactions. Look for: `permit()` followed by `transferFrom()` in the same function without try/catch on permit. [beirao S-12, weird-erc20]
  - **Provenance:** beirao S-12, weird-erc20

- [ ] **[EVM-SIG-015] DAI non-standard permit** _(exploit-pattern; medium)_: DAI's permit function signature differs from ERC-2612: `permit(holder, spender, nonce, expiry, allowed, v, r, s)` vs `permit(owner, spender, value, deadline, v, r, s)`. Code calling standard permit on DAI will revert. Look for: generic permit wrappers without DAI special-casing. [beirao S-13]
  - **Provenance:** beirao S-13

- [ ] **[EVM-SIG-016] Not all ERC20s support permit** _(exploit-pattern; medium)_: Tokens without EIP-2612 have no `permit()` function. Calling it reverts. Look for: mandatory permit calls on user-provided tokens. [beirao S-14]
  - **Provenance:** beirao S-14

## Meta-Transactions & Gas Abstraction

- [ ] **[EVM-SIG-017] Trusted forwarder in ERC-2771** _(exploit-pattern; medium)_: When using meta-transactions, `_msgSender()` extracts the real sender from the last 20 bytes of calldata (appended by the trusted forwarder). If the forwarder doesn't properly validate signatures, anyone can forge the appended address. Look for: ERC-2771 recipient contracts with misconfigured or untrusted forwarders. [beirao S-15]
  - **Provenance:** beirao S-15

- [ ] **[EVM-SIG-018] Gas griefing on relayed transactions** _(exploit-pattern; medium)_: A relayer can provide just enough gas to execute the outer call but not the inner forwarded call. The inner call fails silently, but the outer call succeeds and the nonce is consumed. The user's action didn't execute but can't be retried. Look for: relayed calls without gas sufficiency checks (EIP-150's 1/64th rule). [SWC-126]
  - **Provenance:** SWC-126

## Smart Contract Signatures (ERC-1271)

- [ ] **[EVM-SIG-019] `isValidSignature` called on non-contract address** _(heuristic; contextual)_: If `isValidSignature()` is called on an EOA (no code), the call returns empty data which may be interpreted as success. Look for: `isValidSignature` calls without `extcodesize` check on the verifying address. [ERC4337 checklist]
  - **Provenance:** ERC4337 checklist

- [ ] **[EVM-SIG-020] `isValidSignature` can be upgraded to accept anything** _(exploit-pattern; medium)_: If the contract implementing `isValidSignature` is upgradeable, a future upgrade could change the validation logic. Don't treat ERC-1271 signatures as permanently valid. Look for: timestamped or cached ERC-1271 validations that don't re-verify. [ERC4337 checklist]
  - **Provenance:** ERC4337 checklist

## Dacian — Signature Replay Attacks (Phase 3)

- [ ] **[EVM-SIG-021] Missing parameter in signature allows fund drainage** _(exploit-pattern; medium)_: If `tokenGasPriceFactor` is used in refund calculation but not included in the signed message, the transaction submitter can set it to an arbitrarily large value to drain user funds while passing signature verification. [Source: Dacian — Signature Replay Attacks, Code4rena Biconomy]
  - **Provenance:** Source: Dacian — Signature Replay Attacks, Code4rena Biconomy
