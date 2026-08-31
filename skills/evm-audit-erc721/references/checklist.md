<!-- GENERATED FILE: source is ../../../data/canonical-checks.json; do not edit by hand. -->
# ERC721/ERC1155 Security Checklist

Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.
Global FP/proof obligations live in the Review Contract; only check-specific gates and proofs are repeated below.

## Dual Standard Tokens (ERC721 + ERC1155)

- [ ] **[EVM-ERC721-001] Simultaneous ERC721 and ERC1155 on same contract** _(exploit-pattern; medium)_: Some NFTs (Sandbox Game Asset, F1 Delta Time) implement BOTH ERC721 and ERC1155. Protocols that auto-detect via `supportsInterface` and route to ERC721 vs ERC1155 transfer logic may transfer incorrect amounts or double-count. Look for: `supportsInterface(0x80ac58cd)` checks that don't also check `supportsInterface(0xd9b67a26)`. [weird-erc721]
  - **Provenance:** weird-erc721

- [ ] **[EVM-ERC721-002] Mixed ERC20/ERC721 tokens (ERC404, DN404)** _(exploit-pattern; medium)_: ERC404 tokens combine ERC20 and ERC721 into one contract but are NOT fully compatible with either standard. Transferring the ERC20 portion can mint/burn NFTs automatically. DN404 (ERC-7631) uses two separate contracts but interlinks them. Look for: protocols assuming clean ERC721 behavior from tokens that also implement ERC20 functions. [weird-erc721]
  - **Provenance:** weird-erc721

## Legacy & Wrapped NFTs

- [ ] **[EVM-ERC721-003] CryptoPunks don't implement `transferFrom()`** _(exploit-pattern; medium)_: CryptoPunks predate the ERC721 standard. They use `offerPunkForSaleToAddress()` + `buyPunk()`. When using CryptoPunks as collateral, the `offerPunkForSaleToAddress()` call can be front-run — someone else calls `buyPunk()` before the vault does. Look for: protocols accepting CryptoPunks that rely on `transferFrom`. [weird-erc721, Decurity CDP]
  - **Provenance:** weird-erc721, Decurity CDP

- [ ] **[EVM-ERC721-004] Wrapped NFTs can be redeemed for originals** _(heuristic; contextual)_: Wrapped CryptoPunks, CryptoKitties etc. can be unwrapped at any time. If a protocol uses a wrapped NFT as collateral, the wrapper could be unwrapped by anyone holding the ERC721 wrapper token, destroying the collateral. Look for: collateral systems accepting wrapped NFTs without tracking redemption risk. [weird-erc721]
  - **Provenance:** weird-erc721

## Multiple Collections on One Contract

- [ ] **[EVM-ERC721-005] `setApprovalForAll` grants access to ALL collections on the contract** _(exploit-pattern; medium)_: When multiple NFT collections share one ERC721 contract (e.g., CyberKongz + CyberKongz Babies), calling `setApprovalForAll` for one collection grants access to ALL NFTs across all collections on that contract. Look for: approval patterns that don't account for multi-collection contracts. [weird-erc721]
  - **Provenance:** weird-erc721

- [ ] **[EVM-ERC721-006] `totalSupply()` and `ERC721Enumerable` break with multiple collections** _(exploit-pattern; medium)_: If a contract hosts multiple collections, `totalSupply()` returns the total across all collections, not per-collection. Look for: protocols using `totalSupply()` to determine collection size or derive pricing. [weird-erc721]
  - **Provenance:** weird-erc721

## Token ID Quirks

- [ ] **[EVM-ERC721-007] Large or encoded token IDs** _(exploit-pattern; medium)_: Some NFTs use very large token IDs (up to `type(uint256).max`) or encode metadata within the ID. Sandbox encodes creator address, NFT type, and data into the token ID. Look for: protocols assuming sequential 0-based token IDs or using token ID in arithmetic. [weird-erc721]
  - **Provenance:** weird-erc721

- [ ] **[EVM-ERC721-008] Non-sequential minting** _(exploit-pattern; medium)_: Not all collections mint from 0 to N. Some start at 1, some skip IDs, some mint random IDs. Look for: iteration patterns like `for (i = 0; i < totalSupply; i++)` that assume contiguous IDs. [weird-erc721]
  - **Provenance:** weird-erc721

## Self-Destructing / Auto-Burning NFTs

- [ ] **[EVM-ERC721-009] Tokens that burn on transfer** _(exploit-pattern; medium)_: The Complex Death collection has a 30% chance of burning the NFT on each transfer. Protocols using such NFTs as collateral can lose them during normal operations. Look for: protocols that call `safeTransferFrom` on arbitrary NFTs without checking post-transfer ownership. [weird-erc721]
  - **Provenance:** weird-erc721

- [ ] **[EVM-ERC721-010] Tokens with conditional self-destruct** _(exploit-pattern; medium)_: Two Degrees collection will burn its token when a global warming threshold is reached. Token IDs that existed at deposit time may cease to exist. Look for: protocols that don't verify `ownerOf(tokenId)` before operations. [weird-erc721]
  - **Provenance:** weird-erc721

## Upgradeable and Pausable NFTs

- [ ] **[EVM-ERC721-011] Upgradeable NFT contracts (DeGods, Mocaverse, Neo Tokyo)** _(exploit-pattern; medium)_: The NFT implementation can change at any time. A compromised upgrade could make all transfers revert, trapping collateral. Look for: protocols accepting upgradeable NFTs as collateral without monitoring for implementation changes. [weird-erc721]
  - **Provenance:** weird-erc721

- [ ] **[EVM-ERC721-012] Pausable NFTs (Pudgy Rods)** _(exploit-pattern; medium)_: Admin can pause all transfers. If used as collateral, users cannot add/remove collateral while paused but may still face liquidation. Look for: same pause-liquidation asymmetry as with ERC20 pausable tokens. [weird-erc721]
  - **Provenance:** weird-erc721

- [ ] **[EVM-ERC721-013] NFTs with blacklists (Azuki Elementals, goblintown)** _(exploit-pattern; medium)_: Registry-based blacklists (ClosedSea, operator-filter-registry) can block specific marketplaces or protocols from transferring tokens. Look for: protocols that don't handle transfer reverts from blacklisted operators. [weird-erc721]
  - **Provenance:** weird-erc721

## Reentrancy via Callbacks

- [ ] **[EVM-ERC721-014] `safeTransferFrom` and `safeMint` have callbacks** _(exploit-pattern; medium)_: `onERC721Received` is called on the recipient. Attacker can reenter the calling contract during this callback. Look for: state changes after `safeTransferFrom` / `_safeMint` calls. [beirao NFT-02, NFT-03]
  - **Provenance:** beirao NFT-02, NFT-03

- [ ] **[EVM-ERC721-015] ERC1155 batch operations have callbacks** _(exploit-pattern; medium)_: `safeBatchTransferFrom` and `_mintBatch` call `onERC1155BatchReceived`. Same reentrancy risk as ERC721 but with batch operations that may have more complex state. [Decurity CDP]
  - **Provenance:** Decurity CDP

## NFT Permit (ERC-4494)

- [ ] **[EVM-ERC721-016] Uniswap V3 Position NFTs have permit** _(exploit-pattern; medium)_: ERC-4494 brings off-chain approval to ERC721. If a protocol assumes ERC721s have no alternative approval mechanism, an attacker with a permit signature can approve themselves and transfer without on-chain approval tx. Look for: protocols that track ERC721 approvals only via `Approval` events. [weird-erc721]
  - **Provenance:** weird-erc721

## Airdrops and Breeding

- [ ] **[EVM-ERC721-017] Holding an NFT may trigger airdrops** _(exploit-pattern; medium)_: Some NFTs airdrop new tokens to holders. If a vault/protocol holds NFTs, it may receive unexpected airdrops. Without `onERC721Received` implementation, airdropped ERC721s can get stuck. Look for: vault contracts that hold NFTs but don't implement ERC721Receiver for arbitrary tokens. [weird-erc721]
  - **Provenance:** weird-erc721

## Fractionalized NFTs

- [ ] **[EVM-ERC721-018] Fractional vault gaming** _(exploit-pattern; medium)_: When an NFT is fractionalized into ERC20 tokens, the buyout mechanism can be gamed. An attacker can acquire a fraction and initiate a buyout at manipulated prices. Look for: fractional vault integrations where buyout thresholds or pricing can be manipulated. [weird-erc721]
  - **Provenance:** weird-erc721

## Constructor Minting Without Events

- [ ] **[EVM-ERC721-019] No Transfer events during construction** _(exploit-pattern; medium)_: ERC721 spec allows minting during contract creation without emitting Transfer events. Off-chain indexers and protocols relying on events will miss these tokens. Look for: protocols using Transfer event logs to track ownership of arbitrary NFTs. [weird-erc721]
  - **Provenance:** weird-erc721

## ERC721 `transferFrom` vs `safeTransferFrom`

- [ ] **[EVM-ERC721-020] `transferFrom` doesn't check receiver** _(heuristic; contextual)_: Unlike `safeTransferFrom`, plain `transferFrom` doesn't call `onERC721Received`. NFTs sent to contracts without receiver support are permanently lost. Look for: protocol functions using `transferFrom` where the recipient could be a contract. [beirao NFT-01]
  - **Provenance:** beirao NFT-01

- [ ] **[EVM-ERC721-021] Most `from` parameters should be `msg.sender`** _(exploit-pattern; medium)_: If `nft.transferFrom(from, to, id)` allows arbitrary `from`, attackers can steal from users who have set approvals on the contract. Look for: `transferFrom` where `from` comes from user input rather than being hardcoded to `msg.sender`. [beirao NFT-04]
  - **Provenance:** beirao NFT-04

## Supplemental Attack Vectors (SAS-AV)

- [ ] **[EVM-ERC721-022] ERC721Consecutive Balance Corruption with Single-Token Batch** _(exploit-pattern; medium)_: OZ `ERC721Consecutive` (< 4.8.2) + `_mintConsecutive(to, 1)` — size-1 batch fails to increment balance. `balanceOf` returns 0 despite ownership.
  - **Specific FP:** OZ >= 4.8.2 (patched). Batch size always >= 2. Standard `ERC721._mint` used.
  - **Provenance:** [SAS-AV-080](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-2

- [ ] **[EVM-ERC721-023] ERC1155 safeBatchTransferFrom Unchecked Array Lengths** _(exploit-pattern; medium)_: Custom `_safeBatchTransferFrom` iterates `ids`/`amounts` without `require(ids.length == amounts.length)`. Assembly-optimized paths may silently read uninitialized memory.
  - **Specific FP:** OZ ERC1155 base used unmodified. Custom override asserts equal lengths as first statement.
  - **Provenance:** [SAS-AV-081](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-11

- [ ] **[EVM-ERC721-024] Missing onERC1155BatchReceived Causes Token Lock** _(exploit-pattern; medium)_: Contract implements `onERC1155Received` but not `onERC1155BatchReceived` (or returns wrong selector). `safeBatchTransferFrom` reverts, blocking batch settlement/distribution.
  - **Specific FP:** Both callbacks implemented correctly, or inherits OZ `ERC1155Holder`. Protocol exclusively uses single-item `safeTransferFrom`.
  - **Provenance:** [SAS-AV-082](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-14

- [ ] **[EVM-ERC721-025] ERC1155 uri() Missing {id} Substitution** _(exploit-pattern; medium)_: `uri(uint256 id)` returns fully resolved URL instead of template with literal `{id}` placeholder per EIP-1155. Clients expect to substitute zero-padded hex ID client-side. Static/empty return collapses all token metadata.
  - **Specific FP:** Returns string containing literal `{id}`. Or per-ID on-chain URI with documented deviation from substitution spec.
  - **Provenance:** [SAS-AV-083](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-19

- [ ] **[EVM-ERC721-026] ERC1155 onERC1155Received Return Value Not Validated** _(exploit-pattern; medium)_: Custom ERC1155 calls `onERC1155Received` but doesn't check returned `bytes4` equals `0xf23a6e61`. Non-compliant recipient silently accepts tokens it can't handle.
  - **Specific FP:** OZ ERC1155 base validates selector. Custom impl explicitly checks return value.
  - **Provenance:** [SAS-AV-084](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-40

- [ ] **[EVM-ERC721-027] ERC721 onERC721Received Arbitrary Caller Spoofing** _(exploit-pattern; medium)_: `onERC721Received` uses parameters (`from`, `tokenId`) to update state without verifying `msg.sender` is the expected NFT contract. Anyone calls directly with fabricated parameters.
  - **Specific FP:** `require(msg.sender == address(nft))` before state update. Function is view-only or reverts unconditionally.
  - **Provenance:** [SAS-AV-085](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-48

- [ ] **[EVM-ERC721-028] ERC1155 totalSupply Inflation via Reentrancy Before Supply Update** _(exploit-pattern; medium)_: `totalSupply[id]` incremented AFTER `_mint` callback. During `onERC1155Received`, `totalSupply` is stale-low, inflating caller's share in any supply-dependent formula. Ref: OZ GHSA-9c22-pwxw-p6hx (2021).
  - **Specific FP:** OZ >= 4.3.2 (patched ordering). `nonReentrant` on all mint functions. No supply-dependent logic callable from mint callback.
  - **Provenance:** [SAS-AV-086](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-49

- [ ] **[EVM-ERC721-029] ERC1155 Custom Burn Without Caller Authorization** _(exploit-pattern; medium)_: Public `burn(address from, uint256 id, uint256 amount)` callable by anyone without verifying `msg.sender == from` or operator approval. Any caller burns another user's tokens.
  - **Specific FP:** `require(from == msg.sender || isApprovedForAll(from, msg.sender))` before `_burn`. OZ `ERC1155Burnable` used.
  - **Provenance:** [SAS-AV-087](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-62

- [ ] **[EVM-ERC721-030] ERC1155 Fungible / Non-Fungible Token ID Collision** _(exploit-pattern; medium)_: ERC1155 represents both fungible and unique items with no enforcement: missing `require(totalSupply(id) == 0)` before NFT mint, or no cap preventing additional copies of supply-1 IDs.
  - **Specific FP:** `require(totalSupply(id) + amount <= maxSupply(id))` with `maxSupply=1` for NFTs. Fungible/NFT ID ranges disjoint and enforced.
  - **Provenance:** [SAS-AV-088](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-64

- [ ] **[EVM-ERC721-031] ERC1155 Batch Transfer Partial-State Callback Window** _(exploit-pattern; medium)_: Custom batch mint/transfer updates `_balances` and calls `onERC1155Received` per ID in loop, instead of committing all updates first then calling `onERC1155BatchReceived` once.
  - **Specific FP:** All balance updates committed before any callback (OZ pattern). `nonReentrant` on all transfer/mint entry points.
  - **Provenance:** [SAS-AV-089](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-67

- [ ] **[EVM-ERC721-032] ERC721Enumerable Index Corruption on Burn or Transfer** _(exploit-pattern; medium)_: Override of `_beforeTokenTransfer` (OZ v4) or `_update` (OZ v5) without calling `super`. Index structures become stale.
  - **Specific FP:** Override always calls `super` as first statement. Contract doesn't inherit `ERC721Enumerable`.
  - **Provenance:** [SAS-AV-090](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-80

- [ ] **[EVM-ERC721-033] EIP-2981 Royalty Signaled But Never Enforced** _(exploit-pattern; medium)_: `royaltyInfo()` implemented and `supportsInterface(0x2a55205a)` returns true, but transfer/settlement logic never calls `royaltyInfo()` or routes payment.
  - **Specific FP:** Settlement contract reads `royaltyInfo()` and transfers royalty on-chain. Royalties intentionally zero and documented.
  - **Provenance:** [SAS-AV-091](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-106

- [ ] **[EVM-ERC721-034] ERC721 Approval Not Cleared in Custom Transfer Override** _(exploit-pattern; medium)_: Custom `transferFrom` override skips `super._transfer()`, missing the `delete _tokenApprovals[tokenId]` step. Previous approval persists under new owner.
  - **Specific FP:** Override calls `super.transferFrom` or `super._transfer` internally. Or explicitly deletes approval.
  - **Provenance:** [SAS-AV-092](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-108

- [ ] **[EVM-ERC721-035] ERC721A Lazy Ownership — ownerOf Uninitialized in Batch Range** _(exploit-pattern; medium)_: ERC721A batch mint: only first token has ownership written. `ownerOf(id)` for mid-batch IDs may return `address(0)` before any transfer.
  - **Specific FP:** Explicit transfer initializes packed slot before ownership check. Standard OZ `ERC721` writes per mint.
  - **Provenance:** [SAS-AV-093](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-115

- [ ] **[EVM-ERC721-036] NFT Staking Records msg.sender Instead of ownerOf** _(exploit-pattern; medium)_: `depositor[tokenId] = msg.sender` without checking `nft.ownerOf(tokenId)`. Approved operator credited as depositor.
  - **Specific FP:** Reads `nft.ownerOf(tokenId)` before transfer and records actual owner.
  - **Provenance:** [SAS-AV-094](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-125

- [ ] **[EVM-ERC721-037] ERC1155 ID-Based Role Access Control With Publicly Mintable Role Tokens** _(exploit-pattern; medium)_: Access control via `require(balanceOf(msg.sender, ROLE_ID) > 0)` where `mint` for those IDs is not separately gated. Role tokens transferable by default.
  - **Specific FP:** Minting role-token IDs gated behind separate access control. Role tokens non-transferable.
  - **Provenance:** [SAS-AV-095](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-133

- [ ] **[EVM-ERC721-038] ERC1155 setApprovalForAll Grants All-Token-All-ID Access** _(exploit-pattern; medium)_: Protocol requires `setApprovalForAll(protocol, true)` for deposits/staking. No per-ID or per-amount granularity.
  - **Specific FP:** Protocol uses direct `safeTransferFrom` with user as `msg.sender`. Operator is immutable contract with escrow-only logic.
  - **Provenance:** [SAS-AV-096](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-147

## drozer-lite Additions

- [ ] **[EVM-ERC721-039] ERC-165 Inherited Interface Coverage** _(exploit-pattern; medium)_: A contract's `supportsInterface(bytes4)` only reports the interface it was explicitly registered for, not every interface its parent contracts implement. Downstream integrators who check `supportsInterface(ParentInterface.selector)` get false and refuse integration.
  - **Trigger:** A contract's `supportsInterface(bytes4)` only reports the interface it was explicitly registered for, not every interface its parent contracts implement. Downstream integrators who check `supportsInterface(ParentInterface.selector)` get false and refuse integration. `supportsInterface` returns `interfaceId == type(IThis).interfaceId` only, not OR'd with `super` New interface added to the contract but supportsInterface not updated AccessControl + Enumerable + custom interface but only one is reported Interface-detection-based integration docs (e.g., marketplaces) not tested against actual supportsInterface
  - **Specific proof:** For every `supportsInterface` override, enumerate every ancestor contract's interface (including upgradeable/proxy libraries). Verify the override returns true for each. Prefer `return super.supportsInterface(interfaceId) || interfaceId == type(IThis).interfaceId` to the fully-enumerated OR chain to avoid drift on future inheritance changes.
  - **Provenance:** [DROZER-UNI-96](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md); gdroz3r/drozer-lite — checklists/universal.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
