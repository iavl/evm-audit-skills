<!-- GENERATED FILE: source is ../../../data/canonical-checks.json; do not edit by hand. -->
# Staking & LSD Security Checklist

Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.
Global FP/proof obligations live in the Review Contract; only check-specific gates and proofs are repeated below.

## Liquid Staking Derivative (LSD) Integration

- [ ] **[EVM-STK-001] stETH is a rebasing token** _(exploit-pattern; medium)_: Balance changes on every oracle report (~daily). DeFi protocols should use wstETH instead, which is a non-rebasing wrapper. If a protocol holds stETH, internal accounting will drift from actual balance. Look for: `stETH` in contract imports/addresses without wstETH wrapping logic. [beirao LSD-01]
  - **Provenance:** beirao LSD-01

- [ ] **[EVM-STK-002] stETH→wstETH conversion must handle rebasing** _(exploit-pattern; medium)_: When converting between stETH and wstETH, the rebase that occurs between wrapping and unwrapping must be accounted for. Look for: wrap/unwrap logic without balance-difference checks. [beirao LSD-02]
  - **Provenance:** beirao LSD-02

- [ ] **[EVM-STK-003] stETH/wstETH withdrawal has a queue** _(exploit-pattern; medium)_: Withdrawing from Lido involves a queue (days-weeks), receiving an NFT, and withdrawal amount limits. Protocols assuming instant withdrawal will fail. Look for: withdrawal functions that assume immediate liquidity. [beirao LSD-03]
  - **Provenance:** beirao LSD-03
  - **Notes:** ### rETH (Rocket Pool)

- [ ] **[EVM-STK-004] rETH `burn()` reverts if RocketDepositPool is empty** _(exploit-pattern; medium)_: If the Rocket Pool deposit pool has no ETH, burning rETH to get ETH reverts. Protocols must handle this gracefully. Look for: `rETH.burn()` without try/catch or a fallback path. [beirao LSD-04]
  - **Provenance:** beirao LSD-04

- [ ] **[EVM-STK-005] rETH/ETH rate CAN decrease** _(exploit-pattern; medium)_: Unlike common belief, rETH's exchange rate can decrease during validator slashing. Do not assume monotonically increasing value. Look for: share-price or collateral logic that assumes rETH only appreciates. [beirao LSD-05]
  - **Provenance:** beirao LSD-05

- [ ] **[EVM-STK-006] Consensus attack on RPL nodes** _(exploit-pattern; medium)_: Malicious Rocket Pool node operators can submit incorrect exchange-rate data. Look for: rETH rate used without sanity bounds or an independent validation source. [beirao LSD-06]
  - **Provenance:** beirao LSD-06
  - **Notes:** ### cbETH (Coinbase)

- [ ] **[EVM-STK-007] cbETH has full blacklisting** _(exploit-pattern; medium)_: The blacklist applies to transfers, approvals, mints, and burns. If a protocol address is blacklisted, all cbETH held there can be frozen. Look for: cbETH held in shared vaults without a blacklist-aware recovery path. [beirao LSD-07]
  - **Provenance:** beirao LSD-07

- [ ] **[EVM-STK-008] cbETH/ETH rate changeable by oracle** _(exploit-pattern; medium)_: A small set of addresses protected by `onlyOracle` can change the exchange rate, and the rate can decrease. Look for: cbETH rate used without deviation checks or a policy for non-monotonic rates. [beirao LSD-08, LSD-09]
  - **Provenance:** beirao LSD-08, LSD-09
  - **Notes:** ### sfrxETH (Frax)

- [ ] **[EVM-STK-009] sfrxETH can temporarily detach from frxETH** _(exploit-pattern; medium)_: During reward transfers by Frax's multisig, the sfrxETH/frxETH rate can temporarily deviate. An attacker can exploit this timing. Look for: sfrxETH rate used in MEV-sensitive operations without deviation checks. [beirao LSD-10]
  - **Provenance:** beirao LSD-10

## LSD Protocol Design

- [ ] **[EVM-STK-010] WithdrawCredentials front-running** _(exploit-pattern; medium)_: When staking ETH to a validator, a malicious validator can front-run the deposit transaction to set their own WithdrawCredentials, stealing all future withdrawals. The credentials are immutable once set. Look for: `DepositContract.deposit()` flows that do not verify withdrawal credentials after registration. [Decurity LSD]
  - **Provenance:** Decurity LSD

- [ ] **[EVM-STK-011] Derivative must handle slashing/burn** _(exploit-pattern; medium)_: If a validator is slashed, the derivative token's backing decreases. The protocol must support burning proportional derivative tokens or adjusting the rate. Look for: derivative token implementations without burn capability or rate decrease handling. [Decurity LSD]
  - **Provenance:** Decurity LSD

- [ ] **[EVM-STK-012] DepositContract.deposit() gas limit** _(exploit-pattern; medium)_: If the protocol accumulates large ETH balances and calls `deposit()` in a loop, too many iterations hit the block gas limit. Look for: batch deposit functions without iteration limits or per-iteration gas controls. [Decurity LSD]
  - **Provenance:** Decurity LSD

- [ ] **[EVM-STK-013] Validator array iteration gas** _(exploit-pattern; medium)_: Operations iterating over all validators (for example, rewards or slashing) can hit gas limits as the set grows. Look for: unbounded loops over validator data arrays. [Decurity LSD]
  - **Provenance:** Decurity LSD

- [ ] **[EVM-STK-014] Inflation attack on empty LSD pool** _(exploit-pattern; medium)_: When creating a new staking pool, if no initial deposit is made, an attacker can manipulate the share price. Look for: pool creation without initial deposit or virtual shares. [Decurity LSD]
  - **Provenance:** Decurity LSD

- [ ] **[EVM-STK-015] Slashing penalty exceeds operator balance** _(exploit-pattern; medium)_: If the slashing penalty is larger than the operator's staked balance, the excess comes from user funds or leaves accounting insolvent. Look for: slashing math that does not cap the penalty at operator collateral or define loss coverage. [Decurity LSD]
  - **Provenance:** Decurity LSD

## Staking Rewards

- [ ] **[EVM-STK-016] Reward rate dilution attack** _(exploit-pattern; medium)_: Calling `notifyRewardAmount(0)` extends the reward period, diluting the rate by ~20% each call. Repeated calls compound the dilution. Look for: `notifyRewardAmount` callable with zero amount without rate floor. [ERC4626 primer pattern #39]
  - **Provenance:** ERC4626 primer pattern #39

- [ ] **[EVM-STK-017] Expired vault tokens earning rewards** _(exploit-pattern; medium)_: After an epoch ends, worthless vault tokens still earn staking rewards because the staking contract doesn't know about epoch expiry. Look for: staking contracts that don't validate token expiry/value. [ERC4626 primer pattern #40]
  - **Provenance:** ERC4626 primer pattern #40

- [ ] **[EVM-STK-018] Missing totalSupply sync before reward claims** _(exploit-pattern; medium)_: If fee shares are minted or totalSupply changes between updating reward integrals and claiming, rewards are miscalculated. Look for: reward claim functions that don't sync totalSupply first. [ERC4626 primer pattern #9]
  - **Provenance:** ERC4626 primer pattern #9

- [ ] **[EVM-STK-019] Disabled emissions receivers lose allocated rewards** _(exploit-pattern; medium)_: If a rewards receiver is disabled but doesn't call `allocateNewEmissions`, the allocated tokens are lost forever. Allow anyone to trigger allocation for disabled receivers. Look for: emission systems where disabled receivers block token distribution. [ERC4626 primer pattern #19]
  - **Provenance:** ERC4626 primer pattern #19

## Staking Lock Mechanisms

- [ ] **[EVM-STK-020] Staking for others reduces lock time** _(exploit-pattern; medium)_: If user A can stake on behalf of user B, a tiny stake may reset or alter B's lock timer differently than intended. Look for: `stake(address onBehalfOf)` functions that affect another user's lock timing. [beirao LS-01]
  - **Provenance:** beirao LS-01

- [ ] **[EVM-STK-021] Liquid wrapper bypasses lock entirely** _(exploit-pattern; medium)_: A smart contract can wrap locked/staked tokens and issue liquid receipt tokens, completely defeating the time-lock. Look for: token interfaces that allow third-party wrapping of locked positions. [beirao LS-02]
  - **Provenance:** beirao LS-02

- [ ] **[EVM-STK-022] Early/delayed reward claims** _(exploit-pattern; medium)_: Can rewards be claimed before they vest or delayed beyond the intended payout schedule? Look for: claim functions without proper vesting schedule enforcement. [beirao LS-03]
  - **Provenance:** beirao LS-03

- [ ] **[EVM-STK-023] Deposited assets stuck in protocol** _(exploit-pattern; medium)_: Can assets get stuck (partially or fully) or be improperly delayed in withdrawal? Look for: withdrawal functions with external dependencies that could permanently block. [beirao LS-04]
  - **Provenance:** beirao LS-04

- [ ] **[EVM-STK-024] Reward token value manipulation** _(exploit-pattern; medium)_: If rewards are paid in a protocol-minted token, the reward value can be manipulated within the protocol scope. Look for: reward tokens minted by the same protocol without external price anchoring. [beirao LS-05]
  - **Provenance:** beirao LS-05

## Vault Strategy Risks

- [ ] **[EVM-STK-025] Flash deposit-harvest-withdraw** _(exploit-pattern; medium)_: An attacker deposits right before a harvest/compound, captures the yield, then withdraws immediately. Look for: yield distribution that doesn't use time-weighted accounting. [beirao V-07]
  - **Provenance:** beirao V-07

- [ ] **[EVM-STK-026] Strategy loss handling** _(exploit-pattern; medium)_: Strategies MUST handle losses (negative yield). If they don't, withdrawal may revert or return wrong amounts. Look for: strategy withdraw functions that assume `received >= expected`. [beirao V-07]
  - **Provenance:** beirao V-07

- [ ] **[EVM-STK-027] Black swan: integrated protocol gets hacked** _(exploit-pattern; medium)_: If a yield strategy deposits into Protocol X and Protocol X is exploited, the vault must handle total loss gracefully. Look for: strategy emergency withdrawal and loss socialization mechanisms. [beirao V-07]
  - **Provenance:** beirao V-07

- [ ] **[EVM-STK-028] Locked funds in strategy** _(exploit-pattern; medium)_: When vault funds are deployed to a strategy, what happens if the strategy locks funds (e.g., lending market at 100% utilization)? Look for: vault withdrawal paths that fail when strategies can't return funds. [beirao V-07]
  - **Provenance:** beirao V-07

## LSD Protocol-Level Risks (Expanded from Decurity LSD)

- [ ] **[EVM-STK-029] Slashing-induced depeg** _(exploit-pattern; medium)_: If validators are slashed, the derivative token should be worth less than 1:1 with ETH. If the protocol doesn't support burning derivatives to reflect the loss, a depeg occurs. Look for: LSD protocols without burning mechanisms or slashing loss distribution. [Decurity LSD]
  - **Provenance:** Decurity LSD

- [ ] **[EVM-STK-030] Operator withdraws collateral while still validating** _(exploit-pattern; medium)_: If an operator can withdraw their staked collateral while their validators are still active, there's no penalty for misbehavior. Look for: operator withdrawal functions without checking validator exit status. [Decurity LSD]
  - **Provenance:** Decurity LSD

- [ ] **[EVM-STK-031] Derivative price oracle manipulation via sandwich** _(exploit-pattern; medium)_: When the derivative token price is updated by oracles (e.g., rETH/ETH rate), an attacker can sandwich the price update transaction. Look for: price update transactions that can be sandwiched for profit. [Decurity LSD]
  - **Provenance:** Decurity LSD

## Staking Lock-time Issues (from Beirao)

- [ ] **[EVM-STK-032] Wrapper contracts for liquid staked positions** _(exploit-pattern; medium)_: A contract can wrap locked staking positions and issue liquid tokens against them, defeating the purpose of the lock. Look for: staking contracts without anti-wrapping mechanisms (e.g., transfer restrictions on staked positions). [beirao LS-02]
  - **Provenance:** beirao LS-02
  - **Notes:** ---

## Sigma Prime — Liquid Restaking Protocol Vulnerabilities (Phase 3)

- [ ] **[EVM-STK-033] Incorrect accounting for stakedButUnverifiedNativeETH** _(exploit-pattern; medium)_: When 32 ETH is staked, `stakedButUnverifiedNativeETH += 32 ether`. During verification, the protocol subtracts `effectiveBalance` (which can be < 32 ETH) instead of 32 ETH, leaving phantom ETH in the accounting that overstates TVL and inflates token price. [Source: Sigma Prime — Liquid Restaking, Kelp LRT KLP2-01]
  - **Provenance:** Source: Sigma Prime — Liquid Restaking, Kelp LRT KLP2-01

- [ ] **[EVM-STK-034] Infinite loop from strategy not in _strategyParams** _(exploit-pattern; medium)_: If `_getSelfDelegations()` iterates strategies and uses `continue` when a strategy isn't found in `_strategyParams`, but doesn't increment the outer loop counter `i`, the same incompatible strategy is checked forever → DoS. [Source: Sigma Prime — Liquid Restaking, Omni OMNI-01]
  - **Provenance:** Source: Sigma Prime — Liquid Restaking, Omni OMNI-01

- [ ] **[EVM-STK-035] Beacon Chain proof verification breaks after Deneb upgrade** _(exploit-pattern; medium)_: BeaconChainProofs assumes constant tree height of 4 for ExecutionPayload. Deneb added 2 fields (EIP-4844 blobs), increasing tree height to 5. Post-Deneb: valid withdrawal proofs fail, and second pre-image attacks can fabricate false proofs. [Source: Sigma Prime — Liquid Restaking, EigenLayer EGN3-01]
  - **Provenance:** Source: Sigma Prime — Liquid Restaking, EigenLayer EGN3-01

- [ ] **[EVM-STK-036] Malicious validator front-running — withdrawal credential hijack** _(exploit-pattern; medium)_: Node operator generates two deposit data instances with same pubkey but different withdrawal credentials. Deposits 1 ETH with attacker-controlled credentials first (setting them permanently), then the pool's 32 ETH deposit becomes a balance increase for the attacker's credentials. Attacker receives 33 ETH on exit. [Source: Sigma Prime — Liquid Restaking, RocketPool/Lido Immunefi]
  - **Provenance:** Source: Sigma Prime — Liquid Restaking, RocketPool/Lido Immunefi

- [ ] **[EVM-STK-037] Deterministic address calculation broken by metadata changes** _(exploit-pattern; medium)_: `create2()` addresses depend on bytecode including the metadata hash. Compiler version updates, settings changes, or source file modifications change metadata → different address → users can't withdraw funds from expected contract address. [Source: Sigma Prime — Liquid Restaking]
  - **Provenance:** Source: Sigma Prime — Liquid Restaking

- [ ] **[EVM-STK-038] Cooldown period exploitation to evade slashing** _(exploit-pattern; medium)_: If deposit/stake amounts are only validated at deposit time and can be reduced later without invalidating the node, operators can drain their deposit to zero, making slashing ineffective. [Source: Sigma Prime — Liquid Restaking, Mantle Network]
  - **Provenance:** Source: Sigma Prime — Liquid Restaking, Mantle Network

- [ ] **[EVM-STK-039] Double rounding loss in mint amount calculation** _(exploit-pattern; medium)_: Computing `inflationPercentage` and `newEzETHSupply` as two separate multiply-divide operations causes two rounding losses. Restructure as single calculation to minimize precision loss. [Source: Sigma Prime — Liquid Restaking]
  - **Provenance:** Source: Sigma Prime — Liquid Restaking

- [ ] **[EVM-STK-040] TVL manipulation via forced delegation share tracking flaw** _(exploit-pattern; medium)_: If share tracking after forced undelegations has accounting errors, attacker can manipulate TVL → manipulate token exchange rate → drain value via flash loan deposit/withdrawal. [Source: Sigma Prime — Liquid Restaking]
  - **Provenance:** Source: Sigma Prime — Liquid Restaking

## Supplemental Attack Vectors (SAS-AV)

- [ ] **[EVM-STK-041] Staking Reward Front-Run by New Depositor** _(exploit-pattern; medium)_: Reward checkpoint (`rewardPerTokenStored`) updated AFTER new stake recorded: `_balances[user] += amount` before `updateReward()`. New staker earns rewards for unstaked period.
  - **Specific FP:** `updateReward(account)` executes before any balance update. `rewardPerTokenPaid[user]` tracks per-user checkpoint.
  - **Provenance:** [SAS-AV-142](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-143

- [ ] **[EVM-STK-042] First Depositor Reward Stealing (Staking)** _(exploit-pattern; medium)_: In staking/reward contracts, first depositor front-runs initial reward distribution with minimal (1-wei) deposit, capturing 100% of initial rewards intended for later legitimate stakers.
  - **Specific FP:** Minimum stake amount enforced. Admin-only initial deposit establishes baseline. Time-weighted reward calculation prevents instant claiming. Initial reward distribution delayed until minimum TVL reached.
  - **Provenance:** [SAS-AV-143](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-177

- [ ] **[EVM-STK-043] Reward Dilution via Direct Token Transfer** _(exploit-pattern; medium)_: Attacker transfers staking tokens directly to contract (bypassing `stake()` function), inflating `totalSupply` in balance-based calculations without earning tracked stake. Dilutes rewards for legitimate stakers.
  - **Specific FP:** Separate reward token tracking independent of raw balance. Internal `totalStaked` variable updated only via `stake()`/`unstake()`. Protocol explicitly handles direct transfer surplus.
  - **Provenance:** [SAS-AV-144](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-178

- [ ] **[EVM-STK-044] Balance Caching Issues During Reward Claims** _(exploit-pattern; medium)_: Claiming rewards reads user balance, performs external token transfer, then uses the cached balance for further calculations. Reentrant callback during transfer can manipulate state between read and use.
  - **Specific FP:** `nonReentrant` on all claim functions. Balance read after transfer completes. CEI pattern followed — state updates before external calls.
  - **Provenance:** [SAS-AV-145](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-181

- [ ] **[EVM-STK-045] Restaking Cascading Slashing Risk (EigenLayer-style)** _(exploit-pattern; medium)_: Same stake secures multiple AVSs (Actively Validated Services) via restaking. A slashing event in one AVS can cascade — the same ETH is slashed by AVS-A, then AVS-B detects reduced stake and triggers its own slashing condition. Total slashing across all registered AVSs can exceed 100% of the original stake, creating insolvency.
  - **Specific FP:** Maximum aggregate slash exposure capped across all AVSs. Slashing amounts deducted from future AVS registrations. Insurance or reserve fund for cascading scenarios. Per-AVS stake isolation. Slashing events rate-limited across AVSs.
  - **Provenance:** [SAS-AV-146](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-222

- [ ] **[EVM-STK-046] Queue/List Poisoning via Dust Entries** _(exploit-pattern; medium)_: Attacker fills a withdrawal queue, reward distribution list, or processing queue with thousands of dust-amount entries (1 wei each). Processing the queue requires iterating all entries, and the gas cost grows linearly. Eventually the queue becomes too expensive to process within block gas limits, permanently blocking legitimate withdrawals.
  - **Specific FP:** Minimum entry size enforced (`require(amount >= MIN_AMOUNT)`). Queue implements pagination/batch processing. Economic deterrent per queue entry (fee or deposit). Admin can prune dust entries. Max queue length enforced.
  - **Provenance:** [SAS-AV-147](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-223

- [ ] **[EVM-STK-047] Deprecated Gauge Blocks Claiming Accrued Rewards** _(exploit-pattern; medium)_: Killing/deprecating gauge blocks `claimReward()` for already-accrued, unclaimed rewards — users who earned before deprecation cannot retrieve.
  - **Specific FP:** Kill stops future accrual only — claim remains active for pre-kill balances. Emergency claim bypasses active check.
  - **Provenance:** [SAS-AV-148](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-234

- [ ] **[EVM-STK-048] Withdrawal Queue Bricked by Zero-Amount Entry** _(exploit-pattern; medium)_: FIFO withdrawal queue hits cancelled/zeroed entry that causes `break` or revert instead of skip, permanently blocking all subsequent withdrawals.
  - **Specific FP:** Queue skips zero-amount entries. Cancellation removes or marks entry processed. Linked list allows removal.
  - **Provenance:** [SAS-AV-149](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-258

- [ ] **[EVM-STK-049] Withdrawal Queue Rate Lock-In Front-Run** _(exploit-pattern; medium)_: `requestWithdraw()` locks exchange rate at request time, not claim time. Attacker front-runs pending loss event (slashing, depeg), locks pre-loss rate. Remaining depositors absorb full loss.
  - **Specific FP:** Conversion at claim time using worst of request/claim rate. Same-block deposit+request prevented. Loss realization atomic with share price update.
  - **Provenance:** [SAS-AV-150](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-259

- [ ] **[EVM-STK-050] Reward Accrual During Zero-Depositor Period** _(exploit-pattern; medium)_: Time-based reward distribution starts at vault deployment but no depositors exist yet. First depositor claims all rewards accumulated during the empty period regardless of deposit size or timing.
  - **Specific FP:** Rewards only accrue when `totalSupply > 0`. Reward start time set on first deposit. Unclaimed pre-deposit rewards sent to treasury or burned.
  - **Provenance:** [SAS-AV-151](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-262

- [ ] **[EVM-STK-051] Lazy Epoch Advancement Skips Reward Periods** _(exploit-pattern; medium)_: Epoch advances only on user interaction. No interaction = never advanced — rewards miscalculated or lost when next interaction retroactively applies to wrong epoch.
  - **Specific FP:** Keeper advances epochs independently. Catch-up loop processes skipped epochs. Continuous (non-epoch) reward accrual.
  - **Provenance:** [SAS-AV-152](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-272

- [ ] **[EVM-STK-052] Minimum Lock Period Bypass via Position Modification** _(exploit-pattern; medium)_: Lock enforced on creation/removal but not `increaseLiquidity`/`decreaseLiquidity`. Attacker maintains minimal position, increases massively before profitable swap, decreases after — bypassing lock.
  - **Specific FP:** Lock applies to any increase — `lastModifiedBlock` updated on every change. Fee accrual begins after lock for newly added liquidity.
  - **Provenance:** [SAS-AV-153](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-287

- [ ] **[EVM-STK-053] FIFO Withdrawal Ordering Degrades Yield** _(exploit-pattern; medium)_: Aggregator vault withdraws from sub-vaults in fixed FIFO order, depleting highest-APY vaults first. Remaining capital concentrates in lowest-yield positions, reducing overall returns for all depositors.
  - **Specific FP:** Withdrawal ordering sorted by APY ascending (lowest-yield first). Dynamic rebalancing after withdrawals. Single underlying vault (no ordering issue).
  - **Provenance:** [SAS-AV-154](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-310

- [ ] **[EVM-STK-054] Emission Distribution Before Period Update** _(exploit-pattern; medium)_: `distribute()` reads token balance before `updatePeriod()` mints new emissions. Rewards arrive after distribution — idle until next cycle, underpaying current period.
  - **Specific FP:** `updatePeriod()` called before `distribute()`. Emissions pre-funded before distribution window.
  - **Provenance:** [SAS-AV-155](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-311

- [ ] **[EVM-STK-055] Cached Reward Debt Not Reset After Claim** _(exploit-pattern; medium)_: After `claimRewards()`, `pendingReward`/`rewardDebt` not zeroed. Next claim pays full cached amount again — double payout.
  - **Specific FP:** `pendingReward[user] = 0` after transfer. `rewardDebt` recalculated from current balance and accumulator.
  - **Provenance:** [SAS-AV-156](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-318

- [ ] **[EVM-STK-056] Partial-Claim Timestamp Advance (Unclaimed Reward Forfeiture)** _(exploit-pattern; medium)_: When a claim/harvest function caps the claimed amount (via allowance, balance, or rate limit), the timestamp/checkpoint for future claims advances to `block.timestamp` even when `claimed < owed`. The unclaimed portion is permanently forfeited because the protocol believes it was already distributed. This silently burns user entitlements whenever a rate limit is hit.
  - **Specific FP:** Protocol explicitly documents that unclaimed amounts above the cap are forfeited by design. The checkpoint only advances proportionally to the amount actually claimed.
  - **Provenance:** [SAS-AV-157](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-333

- [ ] **[EVM-STK-057] Keeper Under-Incentivization (Maintenance Function Gas Economics)** _(exploit-pattern; medium)_: Protocol depends on external keepers calling maintenance functions (`accrueInterest()`, `updateRewards()`, `liquidate()`, `performUpkeep()`), but the gas cost of calling these functions exceeds the keeper's reward. When gas prices spike, keepers go offline, causing state to become stale. In lending protocols, this leads to bad debt accumulation from unliquidated positions during high-gas periods.
  - **Specific FP:** Protocol has its own subsidized keeper network. Keeper incentives dynamically scale with gas costs. The maintenance function is not time-critical.
  - **Provenance:** [SAS-AV-158](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-334
