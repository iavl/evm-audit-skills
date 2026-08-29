<!-- GENERATED FILE: source is ../../data/canonical-checks.json; do not edit by hand. -->
# Access Control Security Checklist

Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.

## Centralization Risks

- [ ] **[EVM-ACCESS-001] Admin can perform token transfers on behalf of users** _(exploit-pattern; medium)_: If admin functions exist that can move user tokens (e.g., `rescueTokens`, `emergencyWithdraw` with admin-controlled recipient), the admin can rug users. Look for: any admin function that calls `transfer()` or `transferFrom()` with an admin-controlled destination. [beirao A-01, Nascent toolkit]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao A-01, Nascent toolkit

- [ ] **[EVM-ACCESS-002] Instant parameter changes without timelock** _(exploit-pattern; medium)_: Admin can change critical parameters (fee rates, oracle addresses, collateral factors) instantly. Users have no time to react. Look for: `onlyOwner` setter functions for critical parameters without a timelock delay or event emission. [beirao A-01, G-02]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao A-01, G-02

- [ ] **[EVM-ACCESS-003] Total upgradeability** _(exploit-pattern; medium)_: If the admin can upgrade to any arbitrary implementation, the contract is effectively a multisig-controlled wallet. Look for: UUPS/Transparent proxy where `_authorizeUpgrade` only checks `onlyOwner` with no timelock, governance, or other constraints. [beirao A-01]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao A-01

- [ ] **[EVM-ACCESS-004] Pausing that blocks critical user operations** _(exploit-pattern; medium)_: If pause can block withdrawals or collateral additions while liquidations remain active, users are unfairly liquidated. Look for: `whenNotPaused` on deposit/withdraw but not on liquidation functions. [beirao A-01, G-09]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao A-01, G-09

- [ ] **[EVM-ACCESS-005] Corrupted owner can destroy the protocol** _(exploit-pattern; medium)_: Evaluate what happens if the owner key is compromised. Can the attacker drain all funds? Can they brick the contract permanently? Look for: single-point-of-failure admin patterns without multisig or timelock. [beirao A-02]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao A-02

- [ ] **[EVM-ACCESS-006] Off-chain signer, frontend, or multisig supply-chain compromise** _(exploit-pattern; medium)_: A compromised UI, RPC/relayer, build artifact, signer, or multisig module can present benign intent while submitting a malicious target, calldata, chain, or delegate. Look for: privileged workflows without independent transaction simulation, clear target/chain display, signer isolation, reproducible release checks, or an allowlist for multisig modules. [OWASP Smart Contract Security guidance, operational security]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** OWASP Smart Contract Security guidance, operational security

## Privilege Escalation

- [ ] **[EVM-ACCESS-007] Missing access controls on sensitive functions** _(exploit-pattern; medium)_: Functions like `mint()`, `burn()`, `setOracle()`, `setFee()`, `pause()`, `selfdestruct()`, or arbitrary withdrawal/upgrade entry points without access modifiers are callable by anyone. Look for: public/external functions that modify critical state, destroy code, or transfer value without an appropriate access check. [beirao A-03, A-06]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao A-03, A-06

- [ ] **[EVM-ACCESS-008] `tx.origin` used for authorization** _(exploit-pattern; medium)_: Authorization based on `tx.origin` lets an attacker-controlled intermediary contract act with the user's authority after the user is induced to call it. Look for: `require(tx.origin == owner)`, `tx.origin` compared with a privileged address, or `tx.origin` used as the authenticated actor instead of `msg.sender` or a verified signature. [SWC-115]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** SWC-115

- [ ] **[EVM-ACCESS-009] Two-step ownership transfer must validate the pending owner** _(exploit-pattern; medium)_: Single-step `transferOwnership` to a wrong address can permanently lock out the owner, while an incomplete two-step implementation may accept ownership without a pending transfer or allow an unintended `address(0)` owner. Look for: `Ownable.transferOwnership()` without `Ownable2Step`, or `acceptOwnership()` paths that do not validate the pending owner and non-zero target. [beirao A-05]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao A-05

- [ ] **[EVM-ACCESS-010] Functions operating on other users assume msg.sender is the user** _(exploit-pattern; medium)_: If a function allows specifying a target user, an attacker can operate on others' positions. Look for: functions with a `user` parameter where operations should only be callable by that user or approved operators. [Tamjid F-16]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Tamjid F-16

- [ ] **[EVM-ACCESS-011] Whitelist bypass via proxy tokens** _(exploit-pattern; medium)_: If a protocol whitelists specific addresses but doesn't check for proxy/alias addresses, users can bypass restrictions using alternate token addresses. Look for: address-based whitelists that don't account for proxy patterns. [beirao A-04]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao A-04

## Role Management

- [ ] **[EVM-ACCESS-012] Roles granted in constructor but not documented** _(exploit-pattern; medium)_: Critical roles (minter, pauser, admin) granted during deployment may not be obvious to auditors or users. Look for: `_grantRole()` in constructors without clear documentation. [SCSVS, Nascent]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** SCSVS, Nascent

- [ ] **[EVM-ACCESS-013] No cap on privileged role count** _(exploit-pattern; medium)_: If an unlimited number of addresses can be granted a privileged role, governance is diluted or a compromised address can grant itself more roles. Look for: role-granting functions without limits on role member count. [Nascent toolkit]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Nascent toolkit

- [ ] **[EVM-ACCESS-014] Renounce ownership can brick contract** _(exploit-pattern; medium)_: If `renounceOwnership()` is called on a contract that requires an owner for critical operations (upgrades, parameter changes, unpausing), the contract becomes permanently stuck. Look for: contracts that inherit `Ownable` and have owner-only functions critical for operation. [Nascent toolkit]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Nascent toolkit

## Initialization & Deployment

- [ ] **[EVM-ACCESS-015] Initializer can be called by anyone on implementation contract** _(exploit-pattern; medium)_: Without `_disableInitializers()` in the constructor, an attacker can call `initialize()` on the implementation directly, potentially gaining ownership. Look for: upgradeable contracts without `constructor() { _disableInitializers(); }`. [beirao P-06]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao P-06

- [ ] **[EVM-ACCESS-016] Deploy scripts not included in audit scope** _(exploit-pattern; medium)_: Deployment order, parameter values, and role assignments in deploy scripts are as security-critical as runtime code. An incorrect deployment can leave contracts in a vulnerable state. Look for: deploy scripts that set up permissions or initial state. [Nascent audit-readiness]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** Nascent audit-readiness

## Multi-Agent Access

- [ ] **[EVM-ACCESS-017] When all agents are the same person** _(exploit-pattern; medium)_: In multi-role systems (liquidator, borrower, LP), consider what happens if one entity controls all roles simultaneously. Self-liquidation, self-arbitrage, circular collateral. Look for: cross-role interactions where same-address scenarios aren't tested. [beirao G-22]
  - **FP:** Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** beirao G-22

## Supplemental Attack Vectors (SAS-AV)

- [ ] **[EVM-ACCESS-018] Deployment Transaction Front-Running (Ownership Hijack)** _(exploit-pattern; medium)_: Deployment tx sent to public mempool. Attacker extracts bytecode and deploys first or front-runs initialization. Pattern: constructor sets `owner = msg.sender`.
  - **FP:** Private relay used. Owner passed as constructor arg, not `msg.sender`. CREATE2 salt tied to deployer.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-010](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-95

- [ ] **[EVM-ACCESS-019] Deployer Privilege Retention Post-Deployment** _(exploit-pattern; medium)_: Deployer EOA retains owner/admin/minter/pauser/upgrader after deployment script completes. Pattern: `Ownable` sets `owner = msg.sender` with no `transferOwnership()`.
  - **FP:** Script includes `transferOwnership(multisig)`. Admin role granted to timelock/governance, deployer renounces. `Ownable2Step` with pending owner set to multisig.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-012](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-100

- [ ] **[EVM-ACCESS-020] Existence Check Misused as Ownership Check** _(exploit-pattern; medium)_: A function calls `_requireOwned(tokenId)` or similar to validate authorization, but the internal function only checks whether the token exists (has a non-zero owner), not whether `msg.sender` is that owner. Any user can call the function for any existing token, enabling unauthorized operations like splitting, burning, or transferring other users' positions.
  - **FP:** The existence check is intentional (function is meant to be callable by anyone for any token). A separate ownership check exists elsewhere in the call path.
  - **Proof:** Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.
  - **Provenance:** [SAS-AV-034](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-332

## drozer-lite Additions

- [ ] **[EVM-ACCESS-021] Permissionless Entity Creation Bypasses Protocol-Intended Parameters** _(exploit-pattern; medium)_: A permissionless function (e.g., create pool, create farm, register market) accepts parameters that affect protocol revenue or user protections. These parameters are stored per-entity and used in subsequent operations. The protocol intended to enforce minimum values (e.g., minimum protocol fee, minimum collateral ratio) but the creation function either has no minimum check or the minimum is 0. Creators can set `protocol_fee = 0`, `collateral_ratio = 0`, or `insurance_fund_share = 0` to attract users while depriving the protocol of revenue or safety margins.
  - **Trigger:** A permissionless function (e.g., create pool, create farm, register market) accepts parameters that affect protocol revenue or user protections. These parameters are stored per-entity and used in subsequent operations. The protocol intended to enforce minimum values (e.g., minimum protocol fee, minimum collateral ratio) but the creation function either has no minimum check or the minimum is 0. Creators can set `protocol_fee = 0`, `collateral_ratio = 0`, or `insurance_fund_share = 0` to attract users while depriving the protocol of revenue or safety margins. `create_pool(pool_fees: PoolFee)` where `pool_fees.protocol_fee` can be set to 0 by the creator `is_valid()` only checks `fee < 100%`, not `fee >= MINIMUM_PROTOCOL_FEE` No global fee override exists — the per-entity fee is the only fee Protocol documentation states "fees are collected on every swap" but code allows zero-fee pools Pool/farm/market creator can front-run legitimate creation with a zero-fee version to attract liquidity away from fee-bearing entities
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Proof:** 1. For every permissionless creation function, enumerate every parameter that is stored per-entity and affects protocol revenue or user protection. 2. For each such parameter, check whether a protocol-level minimum is enforced. If the only validation is `fee.is_valid()` (which may only check `< 100%`), a zero value passes. 3. Check whether the protocol has a global/config-level fee that overrides per-entity fees. If not, the per-entity fee IS the protocol fee. 4. Compare against industry standard: Uniswap charges a protocol fee at the factory level; Curve charges admin fees globally. If this protocol charges fees per-entity with no floor, flag.
  - **Provenance:** [DROZER-UNI-110](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md); gdroz3r/drozer-lite — checklists/universal.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
