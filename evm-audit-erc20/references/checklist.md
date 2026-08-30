<!-- GENERATED FILE: source is ../../data/canonical-checks.json; do not edit by hand. -->
# Weird ERC20 Security Checklist

Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.
Global FP/proof obligations live in the Review Contract; only check-specific gates and proofs are repeated below.

## Transfer Behavior Anomalies

- [ ] **[EVM-ERC20-001] Fee-on-transfer tokens (USDT on some chains, STA, PAXG, SAFEMOON)** _(exploit-pattern; medium)_: Tokens that deduct a fee on every transfer. The received amount ≠ sent amount. Any protocol that records `amount` from the function parameter instead of measuring `balanceAfter - balanceBefore` will have inflated internal accounting. Look for: `token.transferFrom(user, address(this), amount)` followed by recording `amount` as the deposit. [weird-erc20, beirao FT-06]
  - **Provenance:** weird-erc20, beirao FT-06

- [ ] **[EVM-ERC20-002] Rebasing tokens (stETH, AMPL, aTokens, OHM)** _(exploit-pattern; medium)_: Token balances change automatically without transfers. A protocol holding 100 stETH at time T may hold 101 stETH at time T+1 without any transaction. Internal accounting based on cached balances will drift from actual holdings. Look for: any internal balance tracking that doesn't periodically re-sync with actual `balanceOf`. [weird-erc20, beirao V-01]
  - **Provenance:** weird-erc20, beirao V-01

- [ ] **[EVM-ERC20-003] Tokens that revert on zero-amount transfer (LEND, BNB)** _(heuristic; contextual)_: Some tokens revert when `transfer(to, 0)` is called. If a reward distribution or fee collection computes zero and then transfers, it causes DoS. Look for: transfer calls where the amount could be 0 in edge cases (empty rewards, rounding to zero). [beirao FT-12]
  - **Provenance:** beirao FT-12

- [ ] **[EVM-ERC20-004] Tokens that revert on transfer to specific addresses (LUSD)** _(exploit-pattern; medium)_: LUSD reverts when transferring to certain destinations, including its own address, the zero address, and pool addresses. Look for: protocols that transfer tokens to addresses derived from user input without whitelist checking, such as `token.transfer(address(token), amount)`. [beirao FT-15, weird-erc20]
  - **Provenance:** beirao FT-15, weird-erc20

- [ ] **[EVM-ERC20-005] Multiple-address tokens (Synthetix SNX)** _(exploit-pattern; medium)_: Some tokens are accessible via multiple contract addresses (proxy + implementation, or multiple proxies). If your protocol tracks by token address, the same underlying token appears as different tokens. Look for: allowlists or mappings keyed by token address that could miss an alias. [beirao FT-05]
  - **Provenance:** beirao FT-05

- [ ] **[EVM-ERC20-006] Flash-mintable tokens (DAI, any token with `flashMint`)** _(exploit-pattern; medium)_: Tokens supporting flash minting temporarily inflate `totalSupply` within a transaction. Any pricing formula using `totalSupply` (e.g., `price = reserves / totalSupply`) becomes manipulable. Look for: `totalSupply()` used in price or share calculations. [beirao FT-11]
  - **Provenance:** beirao FT-11

- [ ] **[EVM-ERC20-007] Tokens with blocklists/blacklists (USDC, USDT, cUSDC)** _(exploit-pattern; medium)_: Transfer to/from blocklisted addresses reverts. If your contract or a user gets blocklisted, funds are permanently stuck. Look for: any protocol that holds user funds in a shared vault — if the vault address gets blocklisted, all users lose funds. [weird-erc20, beirao FT-04]
  - **Provenance:** weird-erc20, beirao FT-04

- [ ] **[EVM-ERC20-008] Tokens with transfer pausing (USDC, USDT, BNB)** _(exploit-pattern; medium)_: The token issuer can pause ALL transfers. If the collateral token is paused, users can't add collateral but can still be liquidated = unfair liquidation. Look for: collateral/debt tokens that have pause functionality and the protocol's behavior when transfers revert. [Decurity CDP checklist]
  - **Provenance:** Decurity CDP checklist

- [ ] **[EVM-ERC20-009] Tokens with admin minting/burning (centralized stablecoins)** _(exploit-pattern; medium)_: Token admins can mint unlimited tokens or burn from any address. A protocol using such a token as collateral faces unbounded dilution risk. Look for: collateral tokens where the admin can inflate supply. [weird-erc20]
  - **Provenance:** weird-erc20

## Approval & Allowance Edge Cases

- [ ] **[EVM-ERC20-010] USDT approve race condition** _(heuristic; contextual)_: USDT requires setting allowance to 0 before changing to a new non-zero value. `approve(spender, newAmount)` reverts if current allowance > 0 and newAmount > 0. Look for: `token.approve()` without first resetting to 0, especially on tokens that could be USDT. Fix: use `safeIncreaseAllowance` / `safeDecreaseAllowance`, or always approve(0) first. [beirao FT-02, weird-erc20]
  - **Provenance:** beirao FT-02, weird-erc20

- [ ] **[EVM-ERC20-011] BNB reverts on zero-amount approval** _(exploit-pattern; medium)_: Unlike USDT, BNB reverts when `approve(spender, 0)` is called. So the "always approve 0 first" pattern fails for BNB. Look for: generic approve-to-zero patterns in protocols supporting multiple tokens. [ERC4626 primer]
  - **Provenance:** ERC4626 primer

- [ ] **[EVM-ERC20-012] Infinite approval can be drained** _(exploit-pattern; medium)_: If a contract holds user approvals (e.g., a router), a bug in any function that calls `transferFrom` using those approvals can drain all approved tokens. Look for: contracts that receive approvals and make arbitrary calls or have complex transfer logic. [beirao FT-13]
  - **Provenance:** beirao FT-13

## Missing Return Values

- [ ] **[EVM-ERC20-013] USDT on Ethereum has no return value on `transfer()`/`transferFrom()`** _(exploit-pattern; medium)_: The ERC20 spec says these should return `bool`, but USDT doesn't. Raw `.transfer()` calls will work, but wrapping in an interface that expects `bool` will revert. Look for: direct `IERC20(token).transfer()` calls without SafeERC20. [weird-erc20, multichain-auditor]
  - **Provenance:** weird-erc20, multichain-auditor

- [ ] **[EVM-ERC20-014] Different interfaces across chains** _(exploit-pattern; medium)_: USDT on Ethereum: no return value. USDT on Polygon: returns bool. Same token, different interface. Look for: hardcoded interface assumptions in multichain deployments. [multichain-auditor]
  - **Provenance:** multichain-auditor

- [ ] **[EVM-ERC20-015] Solmate SafeTransferLib doesn't check contract existence** _(heuristic; contextual)_: Unlike OpenZeppelin's SafeERC20, Solmate's `safeTransfer()` returns success for calls to addresses with no code (EOAs, not-yet-deployed contracts). Look for: `import {SafeTransferLib}` from solmate where the token address could be invalid. [beirao FT-09]
  - **Provenance:** beirao FT-09

## Decimal Quirks

- [ ] **[EVM-ERC20-016] Decimals vary across chains** _(exploit-pattern; medium)_: USDT/USDC can use 6 decimals on Ethereum and 18 on BSC, so a cross-chain protocol hardcoding `10**6`, `1e6`, or `1e18` can miscalculate values. Look for: decimal assumptions instead of querying and validating each token's actual `decimals()`. [multichain-auditor]
  - **Provenance:** multichain-auditor

- [ ] **[EVM-ERC20-017] Tokens with 0 decimals** _(exploit-pattern; medium)_: Some tokens use 0 decimals (indivisible). Math that divides by `10**decimals` divides by 1 (no-op) but rounding issues appear in share calculations. Look for: vault/share math that doesn't handle 0-decimal tokens. [weird-erc20]
  - **Provenance:** weird-erc20

- [ ] **[EVM-ERC20-018] Tokens with >18 decimals (e.g., YAM-V2 has 24)** _(exploit-pattern; medium)_: Multiplication of two such values can overflow uint256. Look for: `amount * price` or `amount * rate` calculations without overflow protection for high-decimal tokens. [weird-erc20]
  - **Provenance:** weird-erc20

- [ ] **[EVM-ERC20-019] `IERC20(address(0)).decimals()` reverts** _(exploit-pattern; medium)_: Calling `decimals()` on the zero address reverts. If a token address hasn't been set yet, this causes DoS. Look for: `decimals()` calls on potentially-unset token addresses. [beirao FT-10]
  - **Provenance:** beirao FT-10

## ERC777 & Hook-Based Tokens

- [ ] **[EVM-ERC20-020] ERC777 tokens disguised as ERC20** _(exploit-pattern; medium)_: ERC777 is backward-compatible with ERC20. A protocol accepting "any ERC20" may receive an ERC777, enabling reentrancy via `tokensToSend` (before transfer) and `tokensReceived` (after transfer) hooks. Look for: protocols with open token allowlists that don't explicitly block ERC777. [beirao FT-08, Decurity AMM checklist]
  - **Provenance:** beirao FT-08, Decurity AMM checklist

- [ ] **[EVM-ERC20-021] ERC677 `transferAndCall` hooks** _(exploit-pattern; medium)_: Similar to ERC777, ERC677 tokens (like LINK) have a `transferAndCall` that triggers a callback. Look for: protocols interacting with LINK or other ERC677 tokens without reentrancy protection. [Decurity AMM checklist]
  - **Provenance:** Decurity AMM checklist

## Permit (ERC-2612) Edge Cases

- [ ] **[EVM-ERC20-022] DAI permit uses non-standard signature** _(exploit-pattern; medium)_: DAI's permit function has a different parameter ordering than ERC-2612. Code that assumes standard permit will fail on DAI. Look for: generic `permit()` wrappers that don't handle DAI's variant. [ERC4626 primer]
  - **Provenance:** ERC4626 primer

- [ ] **[EVM-ERC20-023] Missing `DOMAIN_SEPARATOR()` function** _(exploit-pattern; medium)_: Some tokens implementing permit lack the `DOMAIN_SEPARATOR()` getter. Look for: code that queries `DOMAIN_SEPARATOR()` on arbitrary tokens. [beirao FT-14]
  - **Provenance:** beirao FT-14

- [ ] **[EVM-ERC20-024] Permit front-running griefing** _(exploit-pattern; medium)_: An attacker can front-run a permit transaction by copying the signature and submitting the permit themselves. The original user's subsequent `transferFrom` then succeeds (because allowance is set), but if the user's transaction was `permit + transferFrom` in one call, the permit part reverts with "invalid nonce". Look for: contracts that call permit in the same transaction as other operations. [weird-erc20]
  - **Provenance:** weird-erc20

## Protocol-Specific Token Behaviors

- [ ] **[EVM-ERC20-025] USDT is upgradeable on Polygon but immutable on Ethereum** _(heuristic; contextual)_: The same token may behave differently on different chains due to proxy status. Look for: assumptions about token immutability in multichain deployments. [multichain-auditor]
  - **Provenance:** multichain-auditor

- [ ] **[EVM-ERC20-026] Gnosis Chain USDC/WETH/WBTC have post-transfer callbacks** _(exploit-pattern; medium)_: On Gnosis (formerly xDai), these tokens had transfer callbacks enabling reentrancy. The chain hard-forked to fix it. Look for: token interaction patterns that assume no callbacks exist for standard tokens on non-mainnet chains. [multichain-auditor]
  - **Provenance:** multichain-auditor

- [ ] **[EVM-ERC20-027] Rebasing tokens in AMMs** _(exploit-pattern; medium)_: If a rebasing token is in an AMM pool, the pool doesn't update reserves on rebase. This creates an arbitrage opportunity where someone can extract the rebase yield from the pool. Look for: AMMs or vaults holding rebasing tokens without rebase tracking. [beirao AMM-04]
  - **Provenance:** beirao AMM-04

## Additional Weird ERC20 Behaviors (Expanded)

- [ ] **[EVM-ERC20-028] Tether Gold returns `false` even on success** _(exploit-pattern; medium)_: Some tokens declare `bool` return but return `false` regardless of transfer success. SafeERC20 patterns checking for `false` return will incorrectly revert. This makes it impossible to build a correct generic transfer wrapper for ALL tokens. Look for: protocols that treat `return false` as failure for all tokens. [weird-erc20]
  - **Provenance:** weird-erc20

- [ ] **[EVM-ERC20-029] UNI/COMP revert on amounts > uint96** _(exploit-pattern; medium)_: UNI and COMP use uint96 for internal balance tracking. `transfer()` and `approve()` revert if amount exceeds `type(uint96).max`. However, `approve(uint256(-1))` sets allowance to `type(uint96).max` as a special case. Look for: protocols that approve `type(uint256).max` and expect it to be reflected exactly in `allowance()`. [weird-erc20]
  - **Provenance:** weird-erc20

- [ ] **[EVM-ERC20-030] `transferFrom` with src==msg.sender has inconsistent behavior** _(exploit-pattern; medium)_: DSToken-style tokens skip allowance deduction when `from == msg.sender`, making `transferFrom(address(this), dst, amt)` equivalent to `transfer(dst, amt)`. OpenZeppelin/Uniswap always deducts allowance. Look for: contracts relying on consistent `transferFrom` allowance behavior. [weird-erc20]
  - **Provenance:** weird-erc20

- [ ] **[EVM-ERC20-031] cUSDCv3 `transfer(type(uint256).max)` only sends balance** _(exploit-pattern; medium)_: Some tokens treat `amount == type(uint256).max` as "transfer all my balance". A protocol that transfers a user-supplied `type(uint256).max` amount and credits the full value in storage will have inflated accounting. Look for: vault systems that don't verify received amounts via balance difference. [weird-erc20]
  - **Provenance:** weird-erc20

- [ ] **[EVM-ERC20-032] ERC20 representation of native currency (CELO, POL, zkSync ETH)** _(exploit-pattern; medium)_: Some chains have ERC20 wrappers for their native token at fixed addresses. A protocol interacting with both native ETH and ERC20 tokens on these chains must guard against double-spending where the same asset can be used as both native and ERC20. Led to critical Uniswap V4 vulnerability on Celo. Look for: protocols on Celo/Polygon/zkSync that accept both native + ERC20 without deduplication. [weird-erc20]
  - **Provenance:** weird-erc20

- [ ] **[EVM-ERC20-033] Non-string metadata fields (MKR uses bytes32)** _(exploit-pattern; medium)_: MKR's `name()` and `symbol()` return `bytes32` not `string`. Contracts that decode metadata as string will get garbage or revert. Look for: `IERC20Metadata(token).name()` calls on arbitrary tokens without try/catch. [weird-erc20]
  - **Provenance:** weird-erc20

- [ ] **[EVM-ERC20-034] Phantom functions on tokens without permit** _(exploit-pattern; medium)_: Tokens that don't implement `permit()` won't revert on low-level calls — the call succeeds as a no-op (phantom function). Code that calls `permit()` then `transferFrom()` may silently skip the permit. Look for: `try token.permit(...)` patterns that don't verify the permit actually set allowance. [weird-erc20]
  - **Provenance:** weird-erc20

## Supplemental Attack Vectors (SAS-AV)

- [ ] **[EVM-ERC20-035] Approval to Arbitrary User-Supplied Address (Aggregator/Router Pattern)** _(exploit-pattern; medium)_: Router/aggregator calls `token.approve(userSuppliedPool, MAX_UINT)` where pool address comes from user calldata without allowlist validation. Attacker supplies malicious "pool" that calls `transferFrom` to drain all approved tokens.
  - **Specific FP:** Pool addresses validated against factory or hardcoded allowlist. Approval limited to exact amount per operation (`approve(pool, amountIn)` followed by `approve(pool, 0)`). No persistent approvals.
  - **Provenance:** [SAS-AV-097](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-201

- [ ] **[EVM-ERC20-036] Blacklist and Whitelist Not Mutually Exclusive** _(exploit-pattern; medium)_: Address holds both `BLACKLISTED` and `WHITELISTED` roles. Whitelist-gated paths don't check blacklist — blacklisted address bypasses restrictions via whitelist.
  - **Specific FP:** Adding to one auto-removes from other. Single enum role per address. Both checks applied on every restricted path.
  - **Provenance:** [SAS-AV-098](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-231

- [ ] **[EVM-ERC20-037] Self-Transfer Accounting / Delegation Distortion** _(exploit-pattern; medium)_: Code assumes `src != dst` during transfer or delegation accounting. When sender and receiver are the same address, before/after balance reconstruction, voting checkpoints, or fee logic updates both sides asymmetrically, minting phantom voting power or corrupting accounting.
  - **Specific FP:** Self-transfer is an explicit no-op or has dedicated logic. Tests cover `from == to` for token, staking, and delegation flows. Balance / checkpoint deltas collapse to zero in the self-transfer case.
  - **Provenance:** [SAS-AV-099](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-326

- [ ] **[EVM-ERC20-038] Dual ETH/WETH Input Path Ambiguity** _(exploit-pattern; medium)_: Function accepts native ETH (`msg.value > 0`) and also accepts WETH / wrapped-asset transfers on the same path. If both are provided simultaneously, accounting may credit both, wrap twice, or process inconsistent slippage / refund branches.
  - **Specific FP:** ETH and WETH paths are mutually exclusive (`require(msg.value == 0 || tokenIn != WETH)`, etc.). Native path wraps exactly once, ERC20 path rejects non-zero `msg.value`, and tests cover both-supplied input.
  - **Provenance:** [SAS-AV-100](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-327

- [ ] **[EVM-ERC20-039] ERC-1363 transferAndCall Reentrancy** _(exploit-pattern; medium)_: ERC-1363 tokens implement `transferAndCall`/`transferFromAndCall` which invoke `onTransferReceived` on the recipient. Protocols guarding only against ERC-777 hooks remain vulnerable to the same reentrancy surface via ERC-1363 callbacks, as the token standard is distinct and its hooks are not covered by ERC-777-specific guards.
  - **Specific FP:** Protocol does not accept arbitrary ERC-20 tokens. `nonReentrant` covers all state-changing paths regardless of callback source. CEI pattern followed throughout.
  - **Provenance:** [SAS-AV-101](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-329

- [ ] **[EVM-ERC20-040] Zero-Value Token Transfer Phishing (Address Poisoning)** _(exploit-pattern; medium)_: Attacker calls `transferFrom(victim, spoofedAddress, 0)` on an ERC-20 token, which succeeds without approval because the amount is zero. This injects a fake transaction into the victim's history showing a transfer to a vanity address that closely resembles a legitimate recipient (same first/last characters). Victims who copy-paste addresses from transaction history send funds to the attacker's lookalike address.
  - **Specific FP:** Token reverts on zero-amount transfers (see vector #10). Wallet/explorer filters zero-value `transferFrom` events from transaction history display.
  - **Provenance:** [SAS-AV-102](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-338
