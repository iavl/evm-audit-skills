<!-- GENERATED FILE: source is ../../../data/canonical-checks.json; do not edit by hand. -->
# Proxy & Upgrade Security Checklist

Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.
Global FP/proof obligations live in the Review Contract; only check-specific gates and proofs are repeated below.

## UUPS Proxy

- [ ] **[EVM-PROXY-001] `_authorizeUpgrade()` MUST have access control** _(exploit-pattern; medium)_: If `authorizeUpgrade()` has no `onlyOwner` or equivalent check, anyone can upgrade the implementation to a malicious contract. This is the #1 UUPS bug. Look for: `_authorizeUpgrade` function body that's empty or lacks access checks. [beirao P-04]
  - **Provenance:** beirao P-04

- [ ] **[EVM-PROXY-002] Implementation must disable initializers** _(exploit-pattern; medium)_: Without `_disableInitializers()` in the implementation constructor, an attacker can call `initialize()` directly on the implementation and gain its ownership; on vulnerable UUPS versions this can combine with `upgradeToAndCall` and `delegatecall` to `selfdestruct`, bricking proxies. Look for: implementation contracts without `constructor() { _disableInitializers(); }`. [beirao P-06, RareSkills — UUPS Proxy, OpenZeppelin Advisory]
  - **Provenance:** beirao P-06, RareSkills — UUPS Proxy, OpenZeppelin Advisory

- [ ] **[EVM-PROXY-003] No `selfdestruct` or untrusted `delegatecall` in implementation** _(exploit-pattern; medium)_: `selfdestruct` in an implementation can destroy the proxy context, while an untrusted delegatecall can reach a self-destruct target; this combination was especially dangerous for older UUPS implementations. Post-Dencun, selfdestruct semantics differ by chain, so audit target deployment environments explicitly. Look for: `selfdestruct`, untrusted `delegatecall`, or `upgradeToAndCall` paths in implementation code. [beirao P-07, RareSkills — UUPS Proxy]
  - **Provenance:** beirao P-07, RareSkills — UUPS Proxy

- [ ] **[EVM-PROXY-004] Immutable variables lost on upgrade** _(exploit-pattern; medium)_: `immutable` values are embedded in implementation bytecode, not proxy storage. A new implementation can therefore change the value observed through the proxy. Look for: `immutable` declarations in upgradeable contracts that should persist across upgrades. [beirao P-08]
  - **Provenance:** beirao P-08

- [ ] **[EVM-PROXY-005] Storage layout must remain compatible across upgrades** _(exploit-pattern; medium)_: Adding, removing, reordering, or changing variable types between implementations can corrupt existing data; inherited layouts also require storage gaps or namespaced storage. Only append compatible state and verify the full old/new layout. Look for: upgraded implementations with reordered variables, changed types, or missing gap reservations. [beirao P-05, P-09]
  - **Provenance:** beirao P-05, P-09

- [ ] **[EVM-PROXY-006] Storage gaps for inheritance hierarchies** _(exploit-pattern; medium)_: Parent contracts in upgradeable systems MUST declare `uint256[50] private __gap` to reserve slots. Without gaps, adding a variable to a parent shifts all child storage. Look for: inherited contracts without `__gap` declarations. [beirao P-05]
  - **Provenance:** beirao P-05

## Initialization

- [ ] **[EVM-PROXY-007] No constructor state in proxy implementations** _(exploit-pattern; medium)_: Constructors run in the implementation's context, not the proxy's, so constructor-set state is invisible to the proxy. Use an initializer instead. Look for: `constructor()` in proxy implementations that sets proxy state. [beirao P-01]
  - **Provenance:** beirao P-01

- [ ] **[EVM-PROXY-008] Use upgradeable versions of inherited contracts** _(exploit-pattern; medium)_: `ReentrancyGuard`, `Pausable`, `ERC20`, and `Ownable` have constructors; proxy implementations must use their upgradeable variants and initializer functions. Look for: non-upgradeable OZ imports in upgradeable contracts. [beirao P-03]
  - **Provenance:** beirao P-03

- [ ] **[EVM-PROXY-009] Deployer must call initialize atomically** _(exploit-pattern; medium)_: If `initialize()` is not called in the deployment transaction, anyone can front-run and initialize the proxy with attacker-controlled parameters. Look for: deployment scripts that separate proxy deployment and initialization. [beirao P-02]
  - **Provenance:** beirao P-02

- [ ] **[EVM-PROXY-010] Initializable storage slot reuse** _(exploit-pattern; medium)_: When converting an account to a different type via proxy (e.g., switching smart wallet implementations), the `_initialized` slot can be reused, allowing re-initialization. Look for: proxy upgrades that change the base contract type. [ERC4337 checklist, OZ issue #4782]
  - **Provenance:** ERC4337 checklist, OZ issue #4782

## Transparent Proxy

- [ ] **[EVM-PROXY-011] Function selector clashing** _(exploit-pattern; medium)_: If a proxy/admin function has the same 4-byte selector as an implementation function, routing precedence can lock the admin out of upgrades or expose unintended management behavior. Look for: transparent proxy admin selectors that collide with implementation or user-facing functions. [beirao P-10]
  - **Provenance:** beirao P-10

## Metamorphic Contracts (CREATE2 + selfdestruct)

- [ ] **[EVM-PROXY-012] CREATE2 + selfdestruct = redeployment with different bytecode** _(exploit-pattern; medium)_: A contract at a CREATE2 address can be self-destructed on chains where the semantics permit it and redeployed with different code. This is a rug-pull vector: deploy a safe contract, get audited, then redeploy malicious code at the same address. Look for: CREATE2-deployed contracts with `selfdestruct` or trust based only on a one-time code check. [mixbytes CREATE2]
  - **Provenance:** mixbytes CREATE2

- [ ] **[EVM-PROXY-013] 4 contract states** _(exploit-pattern; medium)_: Not-yet-deployed → deployed → self-destructed → redeployed. The redeployed contract has fresh storage and can have different logic. Look for: systems that trust contract addresses as identity without verifying code hash. [mixbytes CREATE2]
  - **Provenance:** mixbytes CREATE2

- [ ] **[EVM-PROXY-014] EXTCODESIZE bypass via pre-deployment address** _(exploit-pattern; medium)_: Before CREATE2 deployment, the address exists but has no code (`extcodesize == 0`). An `isContract()` check marks it as EOA. Later, code is deployed there, bypassing the "no contracts" restriction. Look for: `isContract()` or `extcodesize` checks on addresses that could receive CREATE2 deployments. [mixbytes CREATE2]
  - **Provenance:** mixbytes CREATE2

- [ ] **[EVM-PROXY-015] `isContract()` bypass via constructor execution** _(exploit-pattern; medium)_: During constructor execution, `extcodesize(address(this)) == 0`. An attacker deploys a contract whose constructor calls the target, passing the `isContract` check. Look for: `extcodesize`-based access control as the sole defense against contract callers. [mixbytes CREATE2, beirao G-14]
  - **Provenance:** mixbytes CREATE2, beirao G-14

## Storage Collision Patterns

- [ ] **[EVM-PROXY-016] Cross-slot boundary off-by-one** _(exploit-pattern; medium)_: When packing multiple values into 32-byte storage slots, off-by-one at the slot boundary (e.g., `tokenIndex > 4` should be `>= 4` for second slot) causes reading from the wrong slot. Look for: index-based access to packed storage with boundary checks. [ERC4626 primer pattern #64]
  - **Provenance:** ERC4626 primer pattern #64

- [ ] **[EVM-PROXY-017] Multiplier/weight index misalignment** _(exploit-pattern; medium)_: When weights and their multipliers are packed in sequence across slots, the index offset for multipliers must exactly match. Misalignment means wrong multipliers for tokens at boundary positions. Look for: packed storage with paired data (weight + multiplier) across slots. [ERC4626 primer pattern #65]
  - **Provenance:** ERC4626 primer pattern #65

- [ ] **[EVM-PROXY-018] Variable name collisions in FunC/Solidity** _(exploit-pattern; medium)_: In FunC (TON) variables can be redeclared. In Solidity, shadowing inherited state variables creates distinct storage slots while appearing to reference the same variable. Look for: state variable declarations that shadow parent contract variables. [SWC-119]
  - **Provenance:** SWC-119

## Proxy Patterns (Expanded from Beirao/Multichain-Auditor)

- [ ] **[EVM-PROXY-019] Proxy contract upgradability differs across chains** _(heuristic; contextual)_: A contract may be upgradeable on one chain (e.g., USDT on Polygon) but immutable on another (USDT on Ethereum). Cross-chain protocols must account for this asymmetry. Look for: multichain systems that assume consistent upgradability. [multichain-auditor]
  - **Provenance:** multichain-auditor
  - **Notes:** ---

## RareSkills — UUPS Proxy Deep Dive (Phase 3)

- [ ] **[EVM-PROXY-020] Breaking the upgrade chain by deploying non-UUPS implementation** _(exploit-pattern; medium)_: Since UUPS upgrade logic lives in the implementation, upgrading to a contract without `upgradeToAndCall()` or `proxiableUUID()` permanently bricks the proxy — no further upgrades possible. The `proxiableUUID()` check in `_upgradeToAndCallUUPS` exists specifically to prevent this. [Source: RareSkills — UUPS Proxy]
  - **Provenance:** Source: RareSkills — UUPS Proxy

- [ ] **[EVM-PROXY-021] Overriding upgradeToAndCall breaks upgrade functionality** _(exploit-pattern; medium)_: If a developer overrides `upgradeToAndCall()` in a new implementation and introduces bugs (wrong access control, missing UUPS check), the upgrade mechanism itself is compromised. Be extremely careful with any override. [Source: RareSkills — UUPS Proxy]
  - **Provenance:** Source: RareSkills — UUPS Proxy

- [ ] **[EVM-PROXY-022] Authorization schema change loses access during upgrade** _(exploit-pattern; medium)_: Switching from simple owner to multi-sig/voting in new implementation, but the multi-sig hasn't been properly initialized or the previous admin already renounced privileges → permanent lock. Verify authorization continuity across upgrades. [Source: RareSkills — UUPS Proxy]
  - **Provenance:** Source: RareSkills — UUPS Proxy

## Supplemental Attack Vectors (SAS-AV)

- [ ] **[EVM-PROXY-023] Upgrade Race Condition / Front-Running** _(exploit-pattern; medium)_: `upgradeTo(V2)` and post-upgrade config calls are separate txs in public mempool. Window for front-running or sandwiching.
  - **Specific FP:** `upgradeToAndCall()` bundles upgrade + init. Private mempool. V2 safe with V1 state from block 0.
  - **Provenance:** [SAS-AV-009](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-93

- [ ] **[EVM-PROXY-024] Beacon Proxy Single-Point-of-Failure Upgrade** _(exploit-pattern; medium)_: Multiple proxies read implementation from single Beacon. Compromising Beacon owner upgrades all proxies at once. `UpgradeableBeacon.owner()` returns single EOA.
  - **Specific FP:** Beacon owner is multisig + timelock. `Upgraded` events monitored. Per-proxy upgrade authority where isolation required.
  - **Provenance:** [SAS-AV-036](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-6

- [ ] **[EVM-PROXY-025] Re-initialization Attack** _(exploit-pattern; medium)_: V2 uses `initializer` instead of `reinitializer(2)`. Or upgrade resets initialized counter / storage-collides bool to false. Ref: AllianceBlock (2024).
  - **Specific FP:** `reinitializer(version)` with correctly incrementing versions for V2+. Tests verify `initialize()` reverts after first call.
  - **Provenance:** [SAS-AV-037](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-18

- [ ] **[EVM-PROXY-026] Immutable Variable Context Mismatch** _(exploit-pattern; medium)_: Implementation uses `immutable` variables (embedded in bytecode, not storage). Proxy `delegatecall` gets implementation's hardcoded values regardless of per-proxy needs. E.g., `immutable WETH` — every proxy gets same address.
  - **Specific FP:** Immutable values intentionally identical across all proxies. Per-proxy config uses storage via `initialize()`.
  - **Provenance:** [SAS-AV-038](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-20

- [ ] **[EVM-PROXY-027] Cross-Chain Deployment Replay** _(exploit-pattern; medium)_: Deployment tx replayed on another chain. Same deployer nonce on both chains produces same CREATE address under different control. No EIP-155 chain ID protection. Ref: Wintermute.
  - **Specific FP:** EIP-155 signatures. `CREATE2` via deterministic factory at same address on all chains. Per-chain deployer EOAs.
  - **Provenance:** [SAS-AV-039](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-24

- [ ] **[EVM-PROXY-028] CREATE2 Address Squatting (Counterfactual Front-Running)** _(exploit-pattern; medium)_: CREATE2 salt not bound to `msg.sender`. Attacker precomputes address and deploys first. For AA wallets: attacker deploys wallet to user's counterfactual address with attacker as owner.
  - **Specific FP:** Salt incorporates `msg.sender`: `keccak256(abi.encodePacked(msg.sender, userSalt))`. Factory restricts deployer. Different owner in constructor produces different address.
  - **Provenance:** [SAS-AV-040](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-29

- [ ] **[EVM-PROXY-029] Diamond Proxy Cross-Facet Storage Collision** _(exploit-pattern; medium)_: EIP-2535 Diamond facets declare storage variables without EIP-7201 namespaced storage. Multiple facets independently start at slot 0, writing to same slots.
  - **Specific FP:** All facets use single `DiamondStorage` struct at namespaced position (EIP-7201). No top-level state variables in facets.
  - **Provenance:** [SAS-AV-041](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-52

- [ ] **[EVM-PROXY-030] Minimal Proxy (EIP-1167) Implementation Destruction** _(exploit-pattern; medium)_: EIP-1167 clones `delegatecall` a fixed implementation. If implementation is destroyed, all clones become no-ops with locked funds.
  - **Specific FP:** No `selfdestruct` in implementation. `_disableInitializers()` in constructor. Post-Dencun: code not destroyed.
  - **Provenance:** [SAS-AV-042](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-122

- [ ] **[EVM-PROXY-031] Diamond Proxy Facet Selector Collision** _(exploit-pattern; medium)_: EIP-2535 Diamond where two facets register same 4-byte selector. Malicious facet via `diamondCut` hijacks calls to critical functions.
  - **Specific FP:** `diamondCut` validates no selector collisions. `DiamondLoupeFacet` enumerates/verifies selectors post-cut.
  - **Provenance:** [SAS-AV-043](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-129

- [ ] **[EVM-PROXY-032] OpenZeppelin Version Confusion (v4 vs v5)** _(exploit-pattern; medium)_: Contract overrides `_beforeTokenTransfer` (OZ v4 hook) while importing OZ v5, where the hook was replaced with `_update`. Override silently never executes — access control, transfer restrictions, or enumerable tracking bypassed.
  - **Specific FP:** Confirmed OZ version consistency. Contract uses `_update` override for v5. No OZ token base inherited.
  - **Provenance:** [SAS-AV-044](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-200
