# Access Control Security Checklist

Non-obvious access control vulnerabilities beyond basic missing modifiers.

## Centralization Risks

- [ ] **Admin can perform token transfers on behalf of users**: If admin functions exist that can move user tokens (e.g., `rescueTokens`, `emergencyWithdraw` with admin-controlled recipient), the admin can rug users. Look for: any admin function that calls `transfer()` or `transferFrom()` with an admin-controlled destination. [beirao A-01, Nascent toolkit]

- [ ] **Instant parameter changes without timelock**: Admin can change critical parameters (fee rates, oracle addresses, collateral factors) instantly. Users have no time to react. Look for: `onlyOwner` setter functions for critical parameters without a timelock delay or event emission. [beirao A-01, G-02]

- [ ] **Total upgradeability**: If the admin can upgrade to any arbitrary implementation, the contract is effectively a multisig-controlled wallet. Look for: UUPS/Transparent proxy where `_authorizeUpgrade` only checks `onlyOwner` with no timelock, governance, or other constraints. [beirao A-01]

- [ ] **Pausing that blocks critical user operations**: If pause can block withdrawals or collateral additions while liquidations remain active, users are unfairly liquidated. Look for: `whenNotPaused` on deposit/withdraw but not on liquidation functions. [beirao A-01, G-09]

- [ ] **Corrupted owner can destroy the protocol**: Evaluate what happens if the owner key is compromised. Can the attacker drain all funds? Can they brick the contract permanently? Look for: single-point-of-failure admin patterns without multisig or timelock. [beirao A-02]

## Privilege Escalation

- [ ] **Missing access controls on sensitive functions**: Functions like `mint()`, `burn()`, `setOracle()`, `setFee()`, `pause()` without access modifiers are callable by anyone. Look for: public/external functions that modify critical state without any access check. [beirao A-03, A-06]

- [ ] **Two-step ownership transfer must validate the pending owner**: Single-step `transferOwnership` to a wrong address can permanently lock out the owner, while an incomplete two-step implementation may accept ownership without a pending transfer or allow an unintended `address(0)` owner. Look for: `Ownable.transferOwnership()` without `Ownable2Step`, or `acceptOwnership()` paths that do not validate the pending owner and non-zero target. [beirao A-05]

- [ ] **Functions operating on other users assume msg.sender is the user**: If a function allows specifying a target user, an attacker can operate on others' positions. Look for: functions with a `user` parameter where operations should only be callable by that user or approved operators. [Tamjid F-16]

- [ ] **Whitelist bypass via proxy tokens**: If a protocol whitelists specific addresses but doesn't check for proxy/alias addresses, users can bypass restrictions using alternate token addresses. Look for: address-based whitelists that don't account for proxy patterns. [beirao A-04]

## Role Management

- [ ] **Roles granted in constructor but not documented**: Critical roles (minter, pauser, admin) granted during deployment may not be obvious to auditors or users. Look for: `_grantRole()` in constructors without clear documentation. [SCSVS, Nascent]

- [ ] **No cap on privileged role count**: If an unlimited number of addresses can be granted a privileged role, governance is diluted or a compromised address can grant itself more roles. Look for: role-granting functions without limits on role member count. [Nascent toolkit]

- [ ] **Renounce ownership can brick contract**: If `renounceOwnership()` is called on a contract that requires an owner for critical operations (upgrades, parameter changes, unpausing), the contract becomes permanently stuck. Look for: contracts that inherit `Ownable` and have owner-only functions critical for operation. [Nascent toolkit]

## Initialization & Deployment

- [ ] **Initializer can be called by anyone on implementation contract**: Without `_disableInitializers()` in the constructor, an attacker can call `initialize()` on the implementation directly, potentially gaining ownership. Look for: upgradeable contracts without `constructor() { _disableInitializers(); }`. [beirao P-06]

- [ ] **Deploy scripts not included in audit scope**: Deployment order, parameter values, and role assignments in deploy scripts are as security-critical as runtime code. An incorrect deployment can leave contracts in a vulnerable state. Look for: deploy scripts that set up permissions or initial state. [Nascent audit-readiness]

## Multi-Agent Access

- [ ] **When all agents are the same person**: In multi-role systems (liquidator, borrower, LP), consider what happens if one entity controls all roles simultaneously. Self-liquidation, self-arbitrage, circular collateral. Look for: cross-role interactions where same-address scenarios aren't tested. [beirao G-22]

## Supplemental Attack Vectors (SAS-AV)

These vectors are merged from sanbir/solidity-auditor-skills; each item retains a detection condition (D), false-positive gate (FP), and source provenance.

- [ ] **[SAS-AV-010] Deployment Transaction Front-Running (Ownership Hijack)**
  - **D:** Deployment tx sent to public mempool. Attacker extracts bytecode and deploys first or front-runs initialization. Pattern: constructor sets `owner = msg.sender`.
  - **FP:** Private relay used. Owner passed as constructor arg, not `msg.sender`. CREATE2 salt tied to deployer.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-95

- [ ] **[SAS-AV-012] Deployer Privilege Retention Post-Deployment**
  - **D:** Deployer EOA retains owner/admin/minter/pauser/upgrader after deployment script completes. Pattern: `Ownable` sets `owner = msg.sender` with no `transferOwnership()`.
  - **FP:** Script includes `transferOwnership(multisig)`. Admin role granted to timelock/governance, deployer renounces. `Ownable2Step` with pending owner set to multisig.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-100

- [ ] **[SAS-AV-034] Existence Check Misused as Ownership Check**
  - **D:** A function calls `_requireOwned(tokenId)` or similar to validate authorization, but the internal function only checks whether the token exists (has a non-zero owner), not whether `msg.sender` is that owner. Any user can call the function for any existing token, enabling unauthorized operations like splitting, burning, or transferring other users' positions.
  - **FP:** The existence check is intentional (function is meant to be callable by anyone for any token). A separate ownership check exists elsewhere in the call path.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-332

## drozer-lite Additions

The checks below are the canonical runtime additions from the EVM-relevant drozer-lite profiles. Each item retains the source profile and pinned commit.

- [ ] **[DROZER-UNI-110] Permissionless Entity Creation Bypasses Protocol-Intended Parameters**
  - **D:** A permissionless function (e.g., create pool, create farm, register market) accepts parameters that affect protocol revenue or user protections. These parameters are stored per-entity and used in subsequent operations. The protocol intended to enforce minimum values (e.g., minimum protocol fee, minimum collateral ratio) but the creation function either has no minimum check or the minimum is 0. Creators can set `protocol_fee = 0`, `collateral_ratio = 0`, or `insurance_fund_share = 0` to attract users while depriving the protocol of revenue or safety margins.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** 1. For every permissionless creation function, enumerate every parameter that is stored per-entity and affects protocol revenue or user protection. 2. For each such parameter, check whether a protocol-level minimum is enforced. If the only validation is `fee.is_valid()` (which may only check `< 100%`), a zero value passes. 3. Check whether the protocol has a global/config-level fee that overrides per-entity fees. If not, the per-entity fee IS the protocol fee. 4. Compare against industry standard: Uniswap charges a protocol fee at the factory level; Curve charges admin fees globally. If this protocol charges fees per-entity with no floor, flag.
  - **Look for:** `create_pool(pool_fees: PoolFee)` where `pool_fees.protocol_fee` can be set to 0 by the creator `is_valid()` only checks `fee < 100%`, not `fee >= MINIMUM_PROTOCOL_FEE` No global fee override exists — the per-entity fee is the only fee Protocol documentation states "fees are collected on every swap" but code allows zero-fee pools Pool/farm/market creator can front-run legitimate creation with a zero-fee version to attract liquidity away from fee-bearing entities
  - **Origin:** [gdroz3r/drozer-lite — checklists/universal.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

## drozer-lite Provenance (deduplicated)

The source checks below are already represented by canonical checks in this domain. These provenance records do not add checklist items.

- `DROZER-UNI-1` **Missing / Incorrect Access Control** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-33` **Permissionless Function Privilege Boundary** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-35` **Role Separation & No Self-Grant** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-36` **Cross-Contract Access Control Consistency** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-37` **Timelock Scope for Parameter Changes** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-38` **Emergency Exit Guarantees** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-66` **Parameter Scope Declaration** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-67` **Retroactive Calculation Prevention** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-68` **Locked-Position Integrity** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-69` **Timing-Adversary Resistance on Admin Changes** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-71` **Boundary Safety on Parameter Updates** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-72` **Privilege Enumeration / Centralization Surface** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-73` **Operation Blocking Powers** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-74` **Irreversible Admin Actions** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
- `DROZER-UNI-75` **Ownership Transfer Two-Step** -> existing domain coverage; [source](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/universal.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

## Auditmos/skills Provenance (deduplicated)

The source patterns below are already represented by canonical checks in this suite. These provenance records retain Auditmos coverage without adding duplicate checklist items.

- `AUDITMOS-STATE-VALIDATION-1` **Unchecked 2-Step Ownership Transfer** -> existing ownership-transfer check; description strengthened; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-state-validation/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
- `AUDITMOS-STATE-VALIDATION-6` **Missing Access Control** -> existing access-control checks; [source](https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/skills/audit-state-validation/reference.md) @ c9583babb0ce189d9f39a05caf94b5a5da655010
