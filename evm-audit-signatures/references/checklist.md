# Signature Security Checklist

## Cross-Chain & Cross-Protocol Replay

- [ ] **Missing chain ID in signature**: A valid signature on Ethereum, an account-abstraction UserOperation, or another supported chain can be replayed on Arbitrum, Polygon, or a fork if the hash omits `block.chainid`. Look for: signature hashes or EIP-712 domains without a dynamic `chainId` binding. [beirao S-01, SWC-121, Dacian — Signature Replay Attacks]

- [ ] **Missing `address(this)` in signature**: Same contract deployed at the same address on multiple chains (CREATE2 or same nonce) has identical verification. A signature valid for Contract A on chain 1 may be valid for Contract A on chain 2. Even on the SAME chain: if the same contract logic is deployed at two addresses, signatures for one instance replay on the other. Include `verifyingContract: address(this)` in domain separator. Look for: EIP-712 domain separator missing `verifyingContract`. [beirao S-02]

- [ ] **Missing `msg.sender` binding in signature**: If the signed message does not include the intended caller or authorized address, anyone who obtains it can use the signature as themselves. Look for: verification that does not bind `msg.sender`/beneficiary to the signed data. [beirao S-06]

- [ ] **Nonce-less signatures are replayable**: Without a nonce or equivalent one-time-use state, the same signature can be reused indefinitely, including to restore a revoked privilege. Look for: signed actions without a per-user nonce, consumed nonce, or other replay state. [beirao S-03, Dacian — Signature Replay Attacks, Code4rena Ondo]

- [ ] **Missing expiration / deadline in signatures**: Signatures without a deadline remain valid forever and can be replayed after the user's circumstances change. Look for: signed message schemas without a `deadline` or `expiry` field. [beirao S-05, Dacian — Signature Replay Attacks, Sherlock NFTPort]

- [ ] **Stale nonce check**: If nonce is checked but not incremented BEFORE the action, reentrancy can replay the same nonce. Increment nonce first, then execute. Look for: nonce increment after `call()` or `transfer()`. [beirao S-04]

## ecrecover Pitfalls

- [ ] **Invalid `ecrecover` can return `address(0)`**: If `v` is invalid or `s` is out of range, `ecrecover` returns `address(0)` instead of reverting. If the expected signer is unset or the result is not checked, an invalid signature can pass. Look for: `ecrecover(hash, v, r, s)` without `result != address(0)` and expected-signer validation. [beirao S-05, SWC-117, Dacian — Signature Replay Attacks, Code4rena Swivel]

- [ ] **Signature malleability**: For every valid `(r, s, v)` there can be a second valid signature using the complementary `s` value. If signatures are unique identifiers, the alternate encoding can bypass an “already used” check. Look for: raw `ecrecover()` or signature keys without lower-half-order validation; use OpenZeppelin ECDSA or equivalent. [beirao S-07, SWC-117, Dacian — Signature Replay Attacks]

- [ ] **Different encoding schemes produce different hashes**: `abi.encode` vs `abi.encodePacked` vs `keccak256(abi.encode(keccak256(abi.encode(...))))`. If the signer uses one encoding and the verifier uses another, the signature is invalid. Look for: encoding mismatches between frontend/backend signing and on-chain verification. [beirao S-08]

- [ ] **`abi.encodePacked` collision with dynamic types**: `abi.encodePacked` concatenates without padding, so different dynamic inputs can produce the same signature hash. Look for: multiple dynamic-length arguments in signature hashing; use `abi.encode` or an equivalent unambiguous encoding. [SWC-133, beirao G-09, Tamjid C12]

## EIP-712 Typed Signatures

- [ ] **`DOMAIN_SEPARATOR` cached at deployment**: If the domain is computed once with the deployment chain's `block.chainid`, it can become invalid after a fork or chain-context change. Recompute dynamically or use an equivalent runtime chain-ID check. Look for: immutable/cached domain separators without fork handling. [beirao S-09, multichain-auditor]

- [ ] **Struct hash must include ALL fields**: Omitting a field from the struct hash means it's not signed. An attacker can change the unsigned field freely. Look for: EIP-712 type hash that doesn't include all struct fields. [beirao S-10]

- [ ] **EIP-712 salt for unintended cross-protocol replay**: Two protocols using the same EIP-712 struct types can have signature replay between them. Using a unique `salt` in the domain separator prevents this. Look for: protocols with identical struct types and no differentiating domain parameter. [beirao S-11]

## Permit (ERC-2612) Specific

- [ ] **Permit front-running griefing (DoS)**: User creates permit signature → submits `permit()` + `transferFrom()` in one transaction → attacker front-runs by extracting the signature and calling `permit()` first → user's transaction reverts because the nonce was consumed. Fix: wrap permit in try/catch, or use separate transactions. Look for: `permit()` followed by `transferFrom()` in the same function without try/catch on permit. [beirao S-12, weird-erc20]

- [ ] **DAI non-standard permit**: DAI's permit function signature differs from ERC-2612: `permit(holder, spender, nonce, expiry, allowed, v, r, s)` vs `permit(owner, spender, value, deadline, v, r, s)`. Code calling standard permit on DAI will revert. Look for: generic permit wrappers without DAI special-casing. [beirao S-13]

- [ ] **Not all ERC20s support permit**: Tokens without EIP-2612 have no `permit()` function. Calling it reverts. Look for: mandatory permit calls on user-provided tokens. [beirao S-14]

## Meta-Transactions & Gas Abstraction

- [ ] **Trusted forwarder in ERC-2771**: When using meta-transactions, `_msgSender()` extracts the real sender from the last 20 bytes of calldata (appended by the trusted forwarder). If the forwarder doesn't properly validate signatures, anyone can forge the appended address. Look for: ERC-2771 recipient contracts with misconfigured or untrusted forwarders. [beirao S-15]

- [ ] **Gas griefing on relayed transactions**: A relayer can provide just enough gas to execute the outer call but not the inner forwarded call. The inner call fails silently, but the outer call succeeds and the nonce is consumed. The user's action didn't execute but can't be retried. Look for: relayed calls without gas sufficiency checks (EIP-150's 1/64th rule). [SWC-126]

## Smart Contract Signatures (ERC-1271)

- [ ] **`isValidSignature` called on non-contract address**: If `isValidSignature()` is called on an EOA (no code), the call returns empty data which may be interpreted as success. Look for: `isValidSignature` calls without `extcodesize` check on the verifying address. [ERC4337 checklist]

- [ ] **`isValidSignature` can be upgraded to accept anything**: If the contract implementing `isValidSignature` is upgradeable, a future upgrade could change the validation logic. Don't treat ERC-1271 signatures as permanently valid. Look for: timestamped or cached ERC-1271 validations that don't re-verify. [ERC4337 checklist]

## Signature Edge Cases (Expanded from Beirao/Multichain-Auditor)

The edge cases from this source section are covered by the canonical signature entries above; this section adds no separate runtime rows.

---

## Dacian — Signature Replay Attacks (Phase 3)

- [ ] **Missing parameter in signature allows fund drainage**: If `tokenGasPriceFactor` is used in refund calculation but not included in the signed message, the transaction submitter can set it to an arbitrarily large value to drain user funds while passing signature verification. [Source: Dacian — Signature Replay Attacks, Code4rena Biconomy]

## drozer-lite Additions

The checks below are the canonical runtime additions from the EVM-relevant drozer-lite profiles. Each item retains the source profile and pinned commit.
