<!-- GENERATED FILE: source is ../../data/canonical-checks.json; do not edit by hand. -->
# Governance & DAO Security Checklist

Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.
Global FP/proof obligations live in the Review Contract; only check-specific gates and proofs are repeated below.

## Flash Loan Governance Attacks

- [ ] **[EVM-GOV-001] Flash loan voting** _(exploit-pattern; medium)_: An attacker flash-loans governance tokens, delegates to themselves, votes, and returns tokens — all in one block. Classic exploits: Beanstalk ($182M), Build Finance DAO. Mitigation: snapshot-based voting where voting power is recorded at a past block, not current balance. Look for: `balanceOf(msg.sender)` or `getVotes(msg.sender)` checked at current block in voting. [SigmaPrime governance, beirao GOV-01]
  - **Provenance:** SigmaPrime governance, beirao GOV-01

- [ ] **[EVM-GOV-002] Flash loan + proposal creation** _(exploit-pattern; medium)_: Even if voting uses snapshots, proposal CREATION may not. An attacker flash-loans tokens to meet the proposal threshold, creates a malicious proposal, returns tokens. Look for: proposal creation that checks current balance instead of a past snapshot. [SigmaPrime governance]
  - **Provenance:** SigmaPrime governance

- [ ] **[EVM-GOV-003] Vote buying via DeFi composability** _(exploit-pattern; medium)_: Governance tokens deposited in lending protocols can be borrowed by attackers for voting. The original depositor doesn't realize their voting power is being used against them. Look for: governance tokens without delegation exclusion when deposited in DeFi protocols. [SigmaPrime governance]
  - **Provenance:** SigmaPrime governance

## Proposal Execution

- [ ] **[EVM-GOV-004] Proposal execution front-running** _(exploit-pattern; medium)_: After a proposal passes and the timelock expires, the execution transaction is public. An attacker can front-run execution with a transaction that changes state to make the proposal harmful. Look for: proposals that depend on specific protocol state at execution time. [beirao GOV-02]
  - **Provenance:** beirao GOV-02

- [ ] **[EVM-GOV-005] Fake proposals via CREATE/CREATE2 contract substitution** _(exploit-pattern; medium)_: An attacker can submit a benign proposal target, obtain approval, then deploy or redeploy different code at the same address before execution. Verify proposal bytecode/target identity at execution or restrict mutable deployment patterns. Look for: proposals targeting CREATE2-deployed contracts, contracts with `selfdestruct`, or unverified CREATE targets. [SigmaPrime governance, Sigma Prime — Governance & DAOs, Tornado Cash]
  - **Provenance:** SigmaPrime governance, Sigma Prime — Governance & DAOs, Tornado Cash

- [ ] **[EVM-GOV-006] Proposal with block number deadline + different L2 block times** _(exploit-pattern; medium)_: Block numbers vary wildly across chains. A proposal with `endBlock = currentBlock + 40_320` (7 days on mainnet) lasts only ~14 hours on Arbitrum. Look for: governance timeouts measured in blocks on L2s with different block times. [multichain-auditor]
  - **Provenance:** multichain-auditor

- [ ] **[EVM-GOV-007] Proposals without expiry become time bombs** _(exploit-pattern; medium)_: A queued proposal that never expires can be executed months later when conditions have completely changed. Look for: missing expiration/grace period on queued proposals. [beirao GOV-05]
  - **Provenance:** beirao GOV-05

- [ ] **[EVM-GOV-008] Cross-chain proposal execution** _(exploit-pattern; medium)_: In multi-chain DAOs, proposal execution on chain A may need to be propagated to chains B, C. If the bridge message fails or is delayed, execution is inconsistent. Look for: multi-chain proposal execution without confirmation/retry mechanisms. [SigmaPrime governance]
  - **Provenance:** SigmaPrime governance

## Quorum & Voting Thresholds

- [ ] **[EVM-GOV-009] Quorum based on percentage, not absolute** _(exploit-pattern; medium)_: If quorum = 10% of totalSupply, and totalSupply is infinite (mintable governance token), the quorum can be trivially met by minting. Also: as tokens get locked/lost, 10% of circulating supply becomes >> 10% of active supply, making quorum unreachable. Look for: quorum calculation using `totalSupply()` as denominator. [SigmaPrime governance]
  - **Provenance:** SigmaPrime governance

- [ ] **[EVM-GOV-010] Dynamic quorum calculated at wrong time** _(exploit-pattern; medium)_: If quorum requirement is checked at proposal creation vs execution, it can be manipulated between those times. Look for: quorum threshold computed at execution time, not snapshot time. [beirao GOV-03]
  - **Provenance:** beirao GOV-03

- [ ] **[EVM-GOV-011] Quorum excluding abstentions** _(exploit-pattern; medium)_: If "abstain" votes count toward quorum but not toward approval, an attacker can abstain with enough tokens to reach quorum, ensuring a small number of "for" votes passes the proposal. Look for: quorum counting that includes abstain votes. [SigmaPrime governance]
  - **Provenance:** SigmaPrime governance

- [ ] **[EVM-GOV-012] Voting power from locked/staked tokens still active** _(exploit-pattern; medium)_: If tokens in a staking contract or LP pool still have voting power, the staking contract/LP becomes a super-voter that nobody controls. Look for: voting power delegation that persists after deposit into DeFi protocols. [SigmaPrime governance]
  - **Provenance:** SigmaPrime governance

## Timelock Security

- [ ] **[EVM-GOV-013] Timelock bypass via emergency function** _(heuristic; contextual)_: If the DAO has an "emergency" function that bypasses the timelock, it's a centralization vector. An attacker who gains the emergency role can execute instantly. Look for: any function with `onlyEmergency` that modifies critical state without timelock. [beirao GOV-06]
  - **Provenance:** beirao GOV-06

- [ ] **[EVM-GOV-014] Timelock with too-short delay** _(exploit-pattern; medium)_: Timelocks with delays < 24h don't give users time to exit before a malicious upgrade executes. Standard: 48h minimum for critical changes. Look for: timelock delay configurable below 24 hours. [SigmaPrime governance]
  - **Provenance:** SigmaPrime governance

- [ ] **[EVM-GOV-015] Timelock admin is itself (circular)** _(exploit-pattern; medium)_: If the timelock's admin is the timelock itself, and there's no DAO proposal to change it, the timelock is permanently locked. If the admin is the DAO and the DAO loses quorum capability, same result. Look for: timelock admin address and whether it's changeable. [beirao GOV-07]
  - **Provenance:** beirao GOV-07

## Centralization Risks

- [ ] **[EVM-GOV-016] Multi-sig with insufficient signers** _(exploit-pattern; medium)_: A 1-of-3 multi-sig = single point of failure. For treasuries: minimum 3-of-7. Look for: multi-sig configurations, especially Gnosis Safe `threshold` setting. [beirao GOV-08]
  - **Provenance:** beirao GOV-08

- [ ] **[EVM-GOV-017] Owner renouncement traps** _(exploit-pattern; medium)_: `renounceOwnership()` on a contract that still needs admin functions (pause, upgrade, parameter changes) permanently bricks the contract. Look for: contracts that inherit `Ownable` and call `renounceOwnership` while admin functions still exist. [beirao GOV-09]
  - **Provenance:** beirao GOV-09

- [ ] **[EVM-GOV-018] Gnosis Safe module can bypass signatures** _(exploit-pattern; medium)_: A Safe module can execute transactions WITHOUT threshold signatures. If a module is compromised, the entire Safe is compromised. Look for: active modules on Gnosis Safes with `execTransactionFromModule`. [beirao GOV-10]
  - **Provenance:** beirao GOV-10

- [ ] **[EVM-GOV-019] Gnosis Safe `delegatecall` from module** _(exploit-pattern; medium)_: `execTransactionFromModule` with operation=1 (delegatecall) runs arbitrary code in the Safe's context. A module with delegatecall capability can drain the Safe. Look for: modules that use `operation: 1` in `execTransactionFromModule`. [beirao GOV-11]
  - **Provenance:** beirao GOV-11

- [ ] **[EVM-GOV-020] Single admin can rug via parameter changes** _(exploit-pattern; medium)_: Even without direct fund access, an admin who can set fees to 100%, change oracle addresses, whitelist malicious tokens, or set exchange rates can effectively rug. Look for: admin-settable parameters without bounds or timelock. [beirao GOV-12]
  - **Provenance:** beirao GOV-12

## Reward Distribution

- [ ] **[EVM-GOV-021] Reward rate too low for totalSupply** _(exploit-pattern; medium)_: If `rewardAmount / duration / totalStaked` rounds to 0, all rewards are permanently lost in the contract. Look for: reward notification with amounts too small relative to staked amounts. [SigmaPrime governance, Dacian]
  - **Provenance:** SigmaPrime governance, Dacian

- [ ] **[EVM-GOV-022] New reward notification before period ends** _(exploit-pattern; medium)_: Calling `notifyRewardAmount()` before the current period ends should add remaining rewards to the new period. If it doesn't, remaining rewards are lost. If it adds them incorrectly, rewards are inflated. Look for: reward notification math when `block.timestamp < periodFinish`. [beirao GOV-13]
  - **Provenance:** beirao GOV-13

- [ ] **[EVM-GOV-023] Reward token same as staking token** _(exploit-pattern; medium)_: If staking token = reward token, and the contract uses `balanceOf(address(this))` to track either, one interferes with the other. Staking inflates apparent rewards, or claiming reduces apparent stakes. Look for: contracts where staking and reward token addresses can be the same. [SigmaPrime governance]
  - **Provenance:** SigmaPrime governance

## Governance Edge Cases (Expanded from Beirao)

- [ ] **[EVM-GOV-024] Gnosis Safe module bypasses Guard hooks** _(exploit-pattern; medium)_: If a Gnosis Safe has a Guard installed (for transaction validation), modules that call `execTransactionFromModule()` bypass the Guard's `checkTransaction()` and `checkAfterExecution()` hooks. A malicious module can execute arbitrary transactions without guard checks. Look for: Safe integrations that rely on Guards for security but also use modules. [beirao GS-01]
  - **Provenance:** beirao GS-01

- [ ] **[EVM-GOV-025] Gnosis Safe nonce not incremented by modules** _(exploit-pattern; medium)_: `execTransactionFromModule()` doesn't increment the Safe's nonce. If signatures or off-chain systems rely on the Safe nonce for uniqueness, module transactions are invisible to them. Look for: systems using Safe nonce for signature replay protection that also use modules. [beirao GS-02]
  - **Provenance:** beirao GS-02

## Merkle Tree Governance (from Beirao)

- [ ] **[EVM-GOV-026] Governance Merkle claim beneficiary must be bound to the payout** _(exploit-pattern; medium)_: A governance Merkle proof can be copied from a pending transaction, but that is exploitable only when the caller can redirect the committed beneficiary's value or voting allocation. Verify the leaf recipient and the final payout/weight recipient independently.
  - **Trigger:** A governance claim accepts a Merkle proof and transfers rewards or voting weight without binding the committed recipient to the final beneficiary.
  - **Risk:** An unbound governance claim can let a front-runner redirect rewards or voting weight; a copied proof that only sponsors gas is not a theft finding.
  - **Detection:** Trace leaf construction, claimant/recipient checks, replay protection, and the final reward or voting-weight recipient.
  - **Specific FP:** The leaf commits the intended recipient and the governance operation uses that recipient, or an independent authorization prevents redirection.
  - **Specific proof:** Replay the proof from a different account and demonstrate changed governance value or reward ownership, or document the recipient-binding invariant.
  - **Provenance:** beirao MT-01, MT-03
  - **Related:** EVM-GEN-021

- [ ] **[EVM-GOV-027] Zero hash as merkle leaf** _(exploit-pattern; medium)_: If the zero hash (`0x000...000`) is a valid leaf, an attacker can construct a proof for it without being in the original tree. Look for: merkle trees where empty/default values aren't explicitly excluded. [beirao MT-04]
  - **Provenance:** beirao MT-04

- [ ] **[EVM-GOV-028] Duplicate proofs in merkle tree** _(exploit-pattern; medium)_: If the same proof appears twice in the tree, a user can claim twice. Look for: merkle trees without deduplication of leaves and claim-tracking mappings. [beirao MT-05]
  - **Provenance:** beirao MT-05
  - **Notes:** ---

## Dacian — DAO Governance DeFi Attacks (Phase 3)

- [ ] **[EVM-GOV-029] Flash-loan + delegated voting bypasses all flash-loan mitigations** _(exploit-pattern; medium)_: Attacker takes flash loan, deposits to receive voting power, delegates to slave contract, slave votes (reaching quorum), master undelegates and withdraws — all in one tx. The gap: undelegation works while proposal is in Locked state. [Source: Dacian — DAO Governance Attacks, Cyfrin DeXe Audit]
  - **Provenance:** Source: Dacian — DAO Governance Attacks, Cyfrin DeXe Audit

- [ ] **[EVM-GOV-030] Destroy all NFT voting power at powerCalcStartTimestamp** _(exploit-pattern; medium)_: If `getNftPower()` returns 0 when `block.timestamp <= startTime` but `recalculateNftPower()` continues when `block.timestamp < startTime`, calling recalculate at exactly `startTime` sets all NFT powers to 0 and drains totalPower. [Source: Dacian — DAO Governance Attacks, Cyfrin DeXe Audit]
  - **Provenance:** Source: Dacian — DAO Governance Attacks, Cyfrin DeXe Audit

- [ ] **[EVM-GOV-031] Amplify individual voting power via non-existent tokenId** _(exploit-pattern; medium)_: Calling `recalculateNftPower(nonExistentId)` with non-existent token IDs decreases `totalPower` without reducing any real NFT's power, artificially amplifying all existing holders' voting influence. [Source: Dacian — DAO Governance Attacks, Cyfrin DeXe Audit]
  - **Provenance:** Source: Dacian — DAO Governance Attacks, Cyfrin DeXe Audit

- [ ] **[EVM-GOV-032] Incorrect totalPower snapshot at proposal creation** _(exploit-pattern; medium)_: If `ERC721Power.totalPower` isn't refreshed (all individual NFT powers recalculated) before snapshot, the proposal stores a stale totalPower that doesn't match sum of individual powers, incorrectly amplifying or reducing votes. [Source: Dacian — DAO Governance Attacks, Cyfrin DeXe Audit]
  - **Provenance:** Source: Dacian — DAO Governance Attacks, Cyfrin DeXe Audit

- [ ] **[EVM-GOV-033] Static totalPowerInTokens makes quorum impossible** _(exploit-pattern; medium)_: If NFTs lose all voting power but `totalPowerInTokens` (the fixed ERC20 equivalent allocated to NFTs) remains in the quorum denominator, ERC20 voting power is permanently diluted, making quorum unreachable. [Source: Dacian — DAO Governance Attacks, Cyfrin DeXe Audit]
  - **Provenance:** Source: Dacian — DAO Governance Attacks, Cyfrin DeXe Audit

- [ ] **[EVM-GOV-034] Delegated treasury voting power used to acquire more treasury power** _(exploit-pattern; medium)_: Expert users with treasury-delegated voting power should be prohibited from voting on proposals that give them more delegated power or remove existing delegations. [Source: Dacian — DAO Governance Attacks, Cyfrin DeXe Audit]
  - **Provenance:** Source: Dacian — DAO Governance Attacks, Cyfrin DeXe Audit

- [ ] **[EVM-GOV-035] Bypass voting restriction via delegation to slave address** _(exploit-pattern; medium)_: If a user is restricted from voting on a proposal, they can delegate voting power to a second address they control and vote from there. Restrictions must also check delegated power source. [Source: Dacian — DAO Governance Attacks, Cyfrin DeXe Audit]
  - **Provenance:** Source: Dacian — DAO Governance Attacks, Cyfrin DeXe Audit

- [ ] **[EVM-GOV-036] Vote with same tokens multiple times via transfer** _(exploit-pattern; medium)_: If voting uses `balanceOf()` without locking or snapshotting, users vote, transfer tokens to another address, vote again. Also: vetoing may lack the same protections as voting. [Source: Dacian — DAO Governance Attacks]
  - **Provenance:** Source: Dacian — DAO Governance Attacks

- [ ] **[EVM-GOV-037] Voting tokens locked forever in proposals without deadlines** _(exploit-pattern; medium)_: If proposals don't have expiration deadlines and quorum is never reached, voters' tokens remain locked indefinitely. Proposals must auto-expire with a Defeated state. [Source: Dacian — DAO Governance Attacks, Code4rena Olympus]
  - **Provenance:** Source: Dacian — DAO Governance Attacks, Code4rena Olympus

- [ ] **[EVM-GOV-038] Anyone can pass proposals before voting tokens are minted** _(exploit-pattern; medium)_: When `totalSupply == 0`, checks like `balance * 10000 < totalSupply * threshold` become `0 < 0` which is false, failing to revert. Anyone can create, endorse, and execute proposals before first mint. [Source: Dacian — DAO Governance Attacks, Code4rena Olympus]
  - **Provenance:** Source: Dacian — DAO Governance Attacks, Code4rena Olympus

- [ ] **[EVM-GOV-039] Token sale proposal — from18() returns 0 for non-18-decimal purchase tokens** _(exploit-pattern; medium)_: If sale expects 18-decimal input but purchase token has 6 decimals, `from18()` conversion returns 0, allowing attacker to "buy" DAO tokens for free. Validate conversion result > 0. [Source: Dacian — DAO Governance Attacks, Cyfrin DeXe Audit]
  - **Provenance:** Source: Dacian — DAO Governance Attacks, Cyfrin DeXe Audit

## Sigma Prime — Governance & DAO Vulnerabilities (Phase 3)

- [ ] **[EVM-GOV-040] Proposal execution order not enforced in multi-step proposals** _(exploit-pattern; medium)_: If anyone can trigger proposal execution and individual steps can be executed separately, attacker can include the market-opening tx but skip the safety-initialization tx, then exploit the empty market. Package multi-step proposals into one Multicall. [Source: Sigma Prime — Governance & DAOs, Sonne Finance]
  - **Provenance:** Source: Sigma Prime — Governance & DAOs, Sonne Finance

- [ ] **[EVM-GOV-041] Multi-sig quorum failure from unresponsive signers** _(exploit-pattern; medium)_: If multi-sig signers become unavailable (arrested, lost keys, hostile), the DAO becomes permanently unable to execute operations. Have backup slow-path governance via token voting. [Source: Sigma Prime — Governance & DAOs, Swerve Finance]
  - **Provenance:** Source: Sigma Prime — Governance & DAOs, Swerve Finance

- [ ] **[EVM-GOV-042] Abandoned project governance takeover** _(exploit-pattern; medium)_: Attacker buys cheap governance tokens of abandoned project, creates vote to redirect accrued fees and liquidity to their address. Monitor token accumulation, restrict vote power over user funds, use timelocks. [Source: Sigma Prime — Governance & DAOs, Swerve Finance]
  - **Provenance:** Source: Sigma Prime — Governance & DAOs, Swerve Finance

- [ ] **[EVM-GOV-043] Timelock prevents emergency response to buggy proposals** _(exploit-pattern; medium)_: Compound's `>` vs `>=` bug caused $147M in erroneous COMP distribution, but the timelock prevented any swift fix. Consider multiple governance speeds — instant pause mechanisms with shorter timelocks for emergencies. [Source: Sigma Prime — Governance & DAOs, Compound Finance]
  - **Provenance:** Source: Sigma Prime — Governance & DAOs, Compound Finance

## Supplemental Attack Vectors (SAS-AV)

- [ ] **[EVM-GOV-044] Governance Spam Proposals via Low Deposit Threshold** _(exploit-pattern; medium)_: Governance proposal creation requires a deposit or token threshold too low relative to token supply. Attacker floods governance with spam proposals, overwhelming voters and hiding malicious proposals among noise. Legitimate governance activity becomes impractical. Combined with voter apathy, a malicious proposal may pass unnoticed.
  - **Specific FP:** Proposal deposit proportional to token supply (e.g., 1% of total supply). Proposal rate limiting per address. Quorum requirements filter out low-engagement proposals. Proposal screening by guardians/council before on-chain vote. Deposit forfeited if proposal doesn't reach quorum.
  - **Provenance:** [SAS-AV-159](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-224

- [ ] **[EVM-GOV-045] Quorum Computed from Live Supply, Not Snapshot** _(exploit-pattern; medium)_: `quorum = totalSupply() * quorumBps / 10000` reads current supply. Attacker inflates supply after proposal creation, lowering effective quorum percentage.
  - **Specific FP:** Quorum snapshotted at proposal creation. Fixed absolute quorum. Supply changes don't affect active proposals.
  - **Provenance:** [SAS-AV-160](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-253

- [ ] **[EVM-GOV-046] Timelock Anchored to Deployment, Not Action** _(exploit-pattern; medium)_: Timelock measured from deployment, not action queue time. Once initial delay elapses, all future actions execute instantly — permanent bypass.
  - **Specific FP:** `executeAfter = block.timestamp + delay` set at queue time. OZ TimelockController.
  - **Provenance:** [SAS-AV-161](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-255

- [ ] **[EVM-GOV-047] Governance Proposal Executable Before Voting Period Ends** _(exploit-pattern; medium)_: `execute()` checks quorum/majority but not `block.timestamp >= proposal.endTime`. Once quorum met, proposal executable immediately — cuts voting window short.
  - **Specific FP:** `require(block.timestamp >= proposal.endTime)`. OZ Governor enforces `ProposalState.Succeeded`.
  - **Provenance:** [SAS-AV-162](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-270

- [ ] **[EVM-GOV-048] Governance Precondition Manipulation** _(exploit-pattern; medium)_: Parameter updates have preconditions based on manipulable state (TVL, liquidity). Adversary inflates/deflates state to block updates — DoS on governance prevents critical changes (fee adjustments, security patches, oracle swaps).
  - **Specific FP:** Preconditions use time-weighted/snapshot values. No state-dependent preconditions. Admin emergency override. Absolute thresholds, not relative to manipulable state.
  - **Provenance:** [SAS-AV-163](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-288

- [ ] **[EVM-GOV-049] Self-Delegation Doubles Voting Power** _(exploit-pattern; medium)_: Self-delegation adds votes to delegate (self) without subtracting undelegated balance — power counted twice: held tokens + delegated votes.
  - **Specific FP:** Delegation subtracts from holder's direct balance. Self-delegation is no-op or explicitly handled. OZ Votes used.
  - **Provenance:** [SAS-AV-164](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-292

- [ ] **[EVM-GOV-050] Checkpoint Overwrite on Same-Block Operations** _(exploit-pattern; medium)_: Multiple delegate/transfer operations in same block overwrite `_writeCheckpoint()` at same key — binary search returns incomplete checkpoint, losing intermediate state.
  - **Specific FP:** Same-block operations accumulate into existing checkpoint. Off-chain indexer used.
  - **Provenance:** [SAS-AV-165](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-306

- [ ] **[EVM-GOV-051] Timelock Queue Observation Exploit Window** _(exploit-pattern; medium)_: When a governance proposal to change a parameter (interest rate, collateral factor, oracle source, fee rate) is queued in a timelock, the window between queuing and execution is exploitable. Attackers monitor the timelock queue and front-run the parameter change — borrowing at the old collateral factor before it tightens, or depositing before a fee increase. Timelock queue flooding can also delay legitimate governance actions.
  - **Specific FP:** The timelock delay is shorter than practical front-running opportunity. The parameter change has no user-exploitable arbitrage. Affected positions are automatically settled at new parameters upon execution.
  - **Provenance:** [SAS-AV-166](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-335

## drozer-lite Additions

- [ ] **[EVM-GOV-052] Aggregate State Consistency on Removal** _(exploit-pattern; medium)_: When a nominee/voter/delegate/lock is removed, some aggregates are updated (bias, totalWeight) but not others (slope, changesSum), so future time-weighted extrapolation returns corrupted values.
  - **Trigger:** When a nominee/voter/delegate/lock is removed, some aggregates are updated (bias, totalWeight) but not others (slope, changesSum), so future time-weighted extrapolation returns corrupted values. `remove()` updates `totalBias` but not `totalSlope` Two-step removal where users never complete step 2, leaving inflated aggregate Division by zero when all participants removed
  - **Specific proof:** For each add/remove function, enumerate every aggregate variable. Verify every aggregate is decremented on removal. For time-weighted aggregates (bias -= slope * time), verify the slope is also corrected. For two-step removal flows (admin + user cleanup), verify the aggregate updates in at least one step, ideally the admin step. Test the zero-aggregate edge case.
  - **Provenance:** [DROZER-GOV-4](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/governance.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/governance.md); gdroz3r/drozer-lite — checklists/governance.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/governance.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/governance.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-GOV-053] Checkpoint MAX_WEEKS / Loop Coverage** _(exploit-pattern; medium)_: A checkpoint loop bounded by `MAX_NUM_WEEKS` is smaller than the maximum lock period divided by `WEEK`, so inactive nominees beyond the window return zero weight (loss of voting power) or the loop exits early with stale state.
  - **Trigger:** A checkpoint loop bounded by `MAX_NUM_WEEKS` is smaller than the maximum lock period divided by `WEEK`, so inactive nominees beyond the window return zero weight (loss of voting power) or the loop exits early with stale state. `uint256 public constant MAX_NUM_WEEKS = 52;` with 4-year lock support `if (weeksPassed > MAX_NUM_WEEKS) return 0` in critical weight calculation
  - **Specific proof:** Verify `MAX_NUM_WEEKS >= maxLockPeriod / WEEK` (e.g., 4-year lock needs >= 209 weeks). Verify nominees inactive for > `MAX_NUM_WEEKS` still return correct weight or explicitly return zero with a migration path. Verify permissionless nominee creation cannot spam entries that become stale and waste gas.
  - **Provenance:** [DROZER-GOV-5](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/governance.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/governance.md); gdroz3r/drozer-lite — checklists/governance.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/governance.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/governance.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539

- [ ] **[EVM-GOV-054] Exit-Function Balance Manipulation (AC-12 / AC-13)** _(exploit-pattern; medium)_: `ragequit`/`withdraw` reads `balanceOf(treasury)` as the payout source; MEV searchers sandwich the exit with treasury-draining proposals. Also covers access-control gaps on exit: anyone can trigger another member's exit, or exit is callable outside the member's expected lifecycle window.
  - **Trigger:** `ragequit`/`withdraw` reads `balanceOf(treasury)` as the payout source; MEV searchers sandwich the exit with treasury-draining proposals. Also covers access-control gaps on exit: anyone can trigger another member's exit, or exit is callable outside the member's expected lifecycle window. `payout = treasury.balanceOf() * shares / totalShares` `ragequit(address member)` permissionless and caller unrelated to member Time delay between exit request and execution creates a sandwich window
  - **Specific proof:** Verify exits use internal accounting, not `balanceOf` live reads. Verify exit-access control restricts callers to the owning member (or an approved delegate). Check whether proposals spending treasury can be timed against exit windows.
  - **Provenance:** [DROZER-GOV-6](https://github.com/gdroz3r/drozer-lite); [https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/governance.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/governance.md); gdroz3r/drozer-lite — checklists/governance.md
  - **Source detail:** [gdroz3r/drozer-lite — checklists/governance.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/governance.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
