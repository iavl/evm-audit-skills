# ERC721/ERC1155 Security Checklist

Non-obvious NFT edge cases that break protocols. Based on real-world token behaviors.

## Dual Standard Tokens (ERC721 + ERC1155)

- [ ] **Simultaneous ERC721 and ERC1155 on same contract**: Some NFTs (Sandbox Game Asset, F1 Delta Time) implement BOTH ERC721 and ERC1155. Protocols that auto-detect via `supportsInterface` and route to ERC721 vs ERC1155 transfer logic may transfer incorrect amounts or double-count. Look for: `supportsInterface(0x80ac58cd)` checks that don't also check `supportsInterface(0xd9b67a26)`. [weird-erc721]

- [ ] **Mixed ERC20/ERC721 tokens (ERC404, DN404)**: ERC404 tokens combine ERC20 and ERC721 into one contract but are NOT fully compatible with either standard. Transferring the ERC20 portion can mint/burn NFTs automatically. DN404 (ERC-7631) uses two separate contracts but interlinks them. Look for: protocols assuming clean ERC721 behavior from tokens that also implement ERC20 functions. [weird-erc721]

## Legacy & Wrapped NFTs

- [ ] **CryptoPunks don't implement `transferFrom()`**: CryptoPunks predate the ERC721 standard. They use `offerPunkForSaleToAddress()` + `buyPunk()`. When using CryptoPunks as collateral, the `offerPunkForSaleToAddress()` call can be front-run — someone else calls `buyPunk()` before the vault does. Look for: protocols accepting CryptoPunks that rely on `transferFrom`. [weird-erc721, Decurity CDP]

- [ ] **Wrapped NFTs can be redeemed for originals**: Wrapped CryptoPunks, CryptoKitties etc. can be unwrapped at any time. If a protocol uses a wrapped NFT as collateral, the wrapper could be unwrapped by anyone holding the ERC721 wrapper token, destroying the collateral. Look for: collateral systems accepting wrapped NFTs without tracking redemption risk. [weird-erc721]

## Multiple Collections on One Contract

- [ ] **`setApprovalForAll` grants access to ALL collections on the contract**: When multiple NFT collections share one ERC721 contract (e.g., CyberKongz + CyberKongz Babies), calling `setApprovalForAll` for one collection grants access to ALL NFTs across all collections on that contract. Look for: approval patterns that don't account for multi-collection contracts. [weird-erc721]

- [ ] **`totalSupply()` and `ERC721Enumerable` break with multiple collections**: If a contract hosts multiple collections, `totalSupply()` returns the total across all collections, not per-collection. Look for: protocols using `totalSupply()` to determine collection size or derive pricing. [weird-erc721]

## Token ID Quirks

- [ ] **Large or encoded token IDs**: Some NFTs use very large token IDs (up to `type(uint256).max`) or encode metadata within the ID. Sandbox encodes creator address, NFT type, and data into the token ID. Look for: protocols assuming sequential 0-based token IDs or using token ID in arithmetic. [weird-erc721]

- [ ] **Non-sequential minting**: Not all collections mint from 0 to N. Some start at 1, some skip IDs, some mint random IDs. Look for: iteration patterns like `for (i = 0; i < totalSupply; i++)` that assume contiguous IDs. [weird-erc721]

## Self-Destructing / Auto-Burning NFTs

- [ ] **Tokens that burn on transfer**: The Complex Death collection has a 30% chance of burning the NFT on each transfer. Protocols using such NFTs as collateral can lose them during normal operations. Look for: protocols that call `safeTransferFrom` on arbitrary NFTs without checking post-transfer ownership. [weird-erc721]

- [ ] **Tokens with conditional self-destruct**: Two Degrees collection will burn its token when a global warming threshold is reached. Token IDs that existed at deposit time may cease to exist. Look for: protocols that don't verify `ownerOf(tokenId)` before operations. [weird-erc721]

## Upgradeable and Pausable NFTs

- [ ] **Upgradeable NFT contracts (DeGods, Mocaverse, Neo Tokyo)**: The NFT implementation can change at any time. A compromised upgrade could make all transfers revert, trapping collateral. Look for: protocols accepting upgradeable NFTs as collateral without monitoring for implementation changes. [weird-erc721]

- [ ] **Pausable NFTs (Pudgy Rods)**: Admin can pause all transfers. If used as collateral, users cannot add/remove collateral while paused but may still face liquidation. Look for: same pause-liquidation asymmetry as with ERC20 pausable tokens. [weird-erc721]

- [ ] **NFTs with blacklists (Azuki Elementals, goblintown)**: Registry-based blacklists (ClosedSea, operator-filter-registry) can block specific marketplaces or protocols from transferring tokens. Look for: protocols that don't handle transfer reverts from blacklisted operators. [weird-erc721]

## Reentrancy via Callbacks

- [ ] **`safeTransferFrom` and `safeMint` have callbacks**: `onERC721Received` is called on the recipient. Attacker can reenter the calling contract during this callback. Look for: state changes after `safeTransferFrom` / `_safeMint` calls. [beirao NFT-02, NFT-03]

- [ ] **ERC1155 batch operations have callbacks**: `safeBatchTransferFrom` and `_mintBatch` call `onERC1155BatchReceived`. Same reentrancy risk as ERC721 but with batch operations that may have more complex state. [Decurity CDP]

## NFT Permit (ERC-4494)

- [ ] **Uniswap V3 Position NFTs have permit**: ERC-4494 brings off-chain approval to ERC721. If a protocol assumes ERC721s have no alternative approval mechanism, an attacker with a permit signature can approve themselves and transfer without on-chain approval tx. Look for: protocols that track ERC721 approvals only via `Approval` events. [weird-erc721]

## Airdrops and Breeding

- [ ] **Holding an NFT may trigger airdrops**: Some NFTs airdrop new tokens to holders. If a vault/protocol holds NFTs, it may receive unexpected airdrops. Without `onERC721Received` implementation, airdropped ERC721s can get stuck. Look for: vault contracts that hold NFTs but don't implement ERC721Receiver for arbitrary tokens. [weird-erc721]

## Fractionalized NFTs

- [ ] **Fractional vault gaming**: When an NFT is fractionalized into ERC20 tokens, the buyout mechanism can be gamed. An attacker can acquire a fraction and initiate a buyout at manipulated prices. Look for: fractional vault integrations where buyout thresholds or pricing can be manipulated. [weird-erc721]

## Constructor Minting Without Events

- [ ] **No Transfer events during construction**: ERC721 spec allows minting during contract creation without emitting Transfer events. Off-chain indexers and protocols relying on events will miss these tokens. Look for: protocols using Transfer event logs to track ownership of arbitrary NFTs. [weird-erc721]

## ERC721 `transferFrom` vs `safeTransferFrom`

- [ ] **`transferFrom` doesn't check receiver**: Unlike `safeTransferFrom`, plain `transferFrom` doesn't call `onERC721Received`. NFTs sent to contracts without receiver support are permanently lost. Look for: protocol functions using `transferFrom` where the recipient could be a contract. [beirao NFT-01]

- [ ] **Most `from` parameters should be `msg.sender`**: If `nft.transferFrom(from, to, id)` allows arbitrary `from`, attackers can steal from users who have set approvals on the contract. Look for: `transferFrom` where `from` comes from user input rather than being hardcoded to `msg.sender`. [beirao NFT-04]

## Supplemental Attack Vectors (SAS-AV)

These vectors are merged from sanbir/solidity-auditor-skills; each item retains a detection condition (D), false-positive gate (FP), and source provenance.

- [ ] **[SAS-AV-080] ERC721Consecutive Balance Corruption with Single-Token Batch**
  - **D:** OZ `ERC721Consecutive` (< 4.8.2) + `_mintConsecutive(to, 1)` — size-1 batch fails to increment balance. `balanceOf` returns 0 despite ownership.
  - **FP:** OZ >= 4.8.2 (patched). Batch size always >= 2. Standard `ERC721._mint` used.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-2

- [ ] **[SAS-AV-081] ERC1155 safeBatchTransferFrom Unchecked Array Lengths**
  - **D:** Custom `_safeBatchTransferFrom` iterates `ids`/`amounts` without `require(ids.length == amounts.length)`. Assembly-optimized paths may silently read uninitialized memory.
  - **FP:** OZ ERC1155 base used unmodified. Custom override asserts equal lengths as first statement.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-11

- [ ] **[SAS-AV-082] Missing onERC1155BatchReceived Causes Token Lock**
  - **D:** Contract implements `onERC1155Received` but not `onERC1155BatchReceived` (or returns wrong selector). `safeBatchTransferFrom` reverts, blocking batch settlement/distribution.
  - **FP:** Both callbacks implemented correctly, or inherits OZ `ERC1155Holder`. Protocol exclusively uses single-item `safeTransferFrom`.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-14

- [ ] **[SAS-AV-083] ERC1155 uri() Missing {id} Substitution**
  - **D:** `uri(uint256 id)` returns fully resolved URL instead of template with literal `{id}` placeholder per EIP-1155. Clients expect to substitute zero-padded hex ID client-side. Static/empty return collapses all token metadata.
  - **FP:** Returns string containing literal `{id}`. Or per-ID on-chain URI with documented deviation from substitution spec.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-19

- [ ] **[SAS-AV-084] ERC1155 onERC1155Received Return Value Not Validated**
  - **D:** Custom ERC1155 calls `onERC1155Received` but doesn't check returned `bytes4` equals `0xf23a6e61`. Non-compliant recipient silently accepts tokens it can't handle.
  - **FP:** OZ ERC1155 base validates selector. Custom impl explicitly checks return value.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-40

- [ ] **[SAS-AV-085] ERC721 onERC721Received Arbitrary Caller Spoofing**
  - **D:** `onERC721Received` uses parameters (`from`, `tokenId`) to update state without verifying `msg.sender` is the expected NFT contract. Anyone calls directly with fabricated parameters.
  - **FP:** `require(msg.sender == address(nft))` before state update. Function is view-only or reverts unconditionally.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-48

- [ ] **[SAS-AV-086] ERC1155 totalSupply Inflation via Reentrancy Before Supply Update**
  - **D:** `totalSupply[id]` incremented AFTER `_mint` callback. During `onERC1155Received`, `totalSupply` is stale-low, inflating caller's share in any supply-dependent formula. Ref: OZ GHSA-9c22-pwxw-p6hx (2021).
  - **FP:** OZ >= 4.3.2 (patched ordering). `nonReentrant` on all mint functions. No supply-dependent logic callable from mint callback.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-49

- [ ] **[SAS-AV-087] ERC1155 Custom Burn Without Caller Authorization**
  - **D:** Public `burn(address from, uint256 id, uint256 amount)` callable by anyone without verifying `msg.sender == from` or operator approval. Any caller burns another user's tokens.
  - **FP:** `require(from == msg.sender || isApprovedForAll(from, msg.sender))` before `_burn`. OZ `ERC1155Burnable` used.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-62

- [ ] **[SAS-AV-088] ERC1155 Fungible / Non-Fungible Token ID Collision**
  - **D:** ERC1155 represents both fungible and unique items with no enforcement: missing `require(totalSupply(id) == 0)` before NFT mint, or no cap preventing additional copies of supply-1 IDs.
  - **FP:** `require(totalSupply(id) + amount <= maxSupply(id))` with `maxSupply=1` for NFTs. Fungible/NFT ID ranges disjoint and enforced.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-64

- [ ] **[SAS-AV-089] ERC1155 Batch Transfer Partial-State Callback Window**
  - **D:** Custom batch mint/transfer updates `_balances` and calls `onERC1155Received` per ID in loop, instead of committing all updates first then calling `onERC1155BatchReceived` once.
  - **FP:** All balance updates committed before any callback (OZ pattern). `nonReentrant` on all transfer/mint entry points.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-67

- [ ] **[SAS-AV-090] ERC721Enumerable Index Corruption on Burn or Transfer**
  - **D:** Override of `_beforeTokenTransfer` (OZ v4) or `_update` (OZ v5) without calling `super`. Index structures become stale.
  - **FP:** Override always calls `super` as first statement. Contract doesn't inherit `ERC721Enumerable`.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-80

- [ ] **[SAS-AV-091] EIP-2981 Royalty Signaled But Never Enforced**
  - **D:** `royaltyInfo()` implemented and `supportsInterface(0x2a55205a)` returns true, but transfer/settlement logic never calls `royaltyInfo()` or routes payment.
  - **FP:** Settlement contract reads `royaltyInfo()` and transfers royalty on-chain. Royalties intentionally zero and documented.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-106

- [ ] **[SAS-AV-092] ERC721 Approval Not Cleared in Custom Transfer Override**
  - **D:** Custom `transferFrom` override skips `super._transfer()`, missing the `delete _tokenApprovals[tokenId]` step. Previous approval persists under new owner.
  - **FP:** Override calls `super.transferFrom` or `super._transfer` internally. Or explicitly deletes approval.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-108

- [ ] **[SAS-AV-093] ERC721A Lazy Ownership — ownerOf Uninitialized in Batch Range**
  - **D:** ERC721A batch mint: only first token has ownership written. `ownerOf(id)` for mid-batch IDs may return `address(0)` before any transfer.
  - **FP:** Explicit transfer initializes packed slot before ownership check. Standard OZ `ERC721` writes per mint.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-115

- [ ] **[SAS-AV-094] NFT Staking Records msg.sender Instead of ownerOf**
  - **D:** `depositor[tokenId] = msg.sender` without checking `nft.ownerOf(tokenId)`. Approved operator credited as depositor.
  - **FP:** Reads `nft.ownerOf(tokenId)` before transfer and records actual owner.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-125

- [ ] **[SAS-AV-095] ERC1155 ID-Based Role Access Control With Publicly Mintable Role Tokens**
  - **D:** Access control via `require(balanceOf(msg.sender, ROLE_ID) > 0)` where `mint` for those IDs is not separately gated. Role tokens transferable by default.
  - **FP:** Minting role-token IDs gated behind separate access control. Role tokens non-transferable.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-133

- [ ] **[SAS-AV-096] ERC1155 setApprovalForAll Grants All-Token-All-ID Access**
  - **D:** Protocol requires `setApprovalForAll(protocol, true)` for deposits/staking. No per-ID or per-amount granularity.
  - **FP:** Protocol uses direct `safeTransferFrom` with user as `msg.sender`. Operator is immutable contract with escrow-only logic.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-147
