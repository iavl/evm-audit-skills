# Oracle & Pricing Security Checklist

## Chainlink Price Feeds

### Staleness & Liveness
- [ ] **Check `updatedAt` for staleness**: Chainlink returns `(roundId, answer, startedAt, updatedAt, answeredInRound)`. If `block.timestamp - updatedAt > heartbeat`, the price is stale. Different feeds have different heartbeats (ETH/USD: 1h on mainnet, 24h on some L2s). Look for: `latestRoundData()` without staleness check or with wrong heartbeat value. [SigmaPrime oracle, beirao O-01]

- [ ] **Hardcoded staleness threshold across chains**: ETH/USD heartbeat is 3600s on Ethereum, 86400s on Arbitrum. Deploying with a hardcoded 3600s threshold on Arbitrum causes constant "stale price" rejections. Look for: single staleness constant used across multi-chain deployments. [multichain-auditor, beirao O-03]

- [ ] **`answeredInRound < roundId` = stale answer from old round**: The answer wasn't updated in the current round. This is a secondary staleness signal beyond timestamp. Look for: missing `answeredInRound >= roundId` check. [beirao O-02]

- [ ] **`startedAt == 0` means round hasn't started**: A round with `startedAt == 0` is invalid — no price update has occurred for this round. Look for: missing `startedAt > 0` check. [SigmaPrime oracle]

### Answer Bounds
- [ ] **`minAnswer` / `maxAnswer` circuit breakers can mask market prices**: Chainlink feeds have hard-coded min/max bounds. When the real price crosses a bound, the feed may report the floor/ceiling instead of the actual price, enabling over-borrowing or incorrect liquidation. Look for: integrations that do not check the aggregator bounds and reject or safely handle `answer <= minAnswer` or `answer >= maxAnswer`. [SigmaPrime oracle, beirao O-04, beirao CL-14, Arbitrum Checklist, Cyfrin — Chainlink Oracle Security, Venus/Blizz exploit]

- [ ] **Negative prices**: Some feeds CAN return negative prices (oil futures in 2020). `int256 answer` cast to `uint256` becomes a massive number. Look for: `uint256(answer)` without `answer > 0` check. [beirao O-05]

- [ ] **Price = 0 not handled**: If a feed returns zero during initialization or an error condition, multiplication-based valuation can allow free borrows while division by price reverts. Look for: missing `answer > 0` check in oracle integrations. [SigmaPrime oracle, Decurity CDP]

### L2 Sequencer
- [ ] **L2 sequencer downtime leaves stale prices**: On Arbitrum/Optimism, when the sequencer goes down and comes back up, prices from before the outage may remain usable. Check the L2 sequencer uptime feed and enforce a restart grace period before consuming prices. Look for: Chainlink usage on L2s without sequencer status and grace-period checks. [beirao O-06, multichain-auditor, beirao CL-06, Arbitrum Checklist]

- [ ] **Grace period too short after sequencer restart**: After the sequencer comes back, oracles need time to update. A grace period of < 1 hour can still use stale prices. Look for: sequencer grace period < 3600 seconds. [SigmaPrime oracle]

### Feed Configuration
- [ ] **Feed decimal precision varies**: ETH/USD and ETH/BTC commonly use 8 decimals, while other feeds such as LINK/ETH or AMPL/USD can use 18. Downstream lending conversion factors must use the actual feed precision, not a hardcoded assumption. Look for: hardcoded `10**8` or `10**18` adjustments, or deployment parameters that disagree with `feed.decimals()`. [beirao O-07, SigmaPrime oracle, beirao CL-09, Arbitrum Checklist, Cyfrin — Chainlink Oracle Security]

- [ ] **Deprecated or hardcoded feeds can become stale**: Chainlink can deprecate feeds, and a hardcoded address may return stale data indefinitely. Look for: feed addresses without an update/migration path or without monitoring the feed's deprecation status. [SigmaPrime oracle, beirao CL-10]

- [ ] **Oracle assumes base=USD when it's actually ETH**: If a protocol needs USD price but uses a `/ETH` denominated feed (or vice versa), all valuations are wrong by the ETH/USD ratio. Look for: feed denomination assumptions without validation. [SigmaPrime oracle]

## TWAP Oracles

- [ ] **TWAP manipulation via low liquidity**: A TWAP oracle averages price over a window, but in low-liquidity pools, even the TWAP can be cheaply manipulated by holding a price position across multiple blocks. Estimate the minimum cost to move and maintain the target price from effective liquidity depth, price impact, trading fees, and the full TWAP window; aggregate TVL is not a substitute for executable depth. For lending uses, pass this result into the `C_manipulation > V_extractable_borrow` check and include the relevant borrow cap, supply cap, and LTV. Look for: TWAP windows shorter than the attacker's affordable holding horizon or price sources with shallow/withdrawable liquidity. [SigmaPrime oracle, beirao O-08]

- [ ] **Uniswap V3 TWAP uses geometric mean**: Unlike V2's arithmetic mean, V3 TWAP is geometric. The geometric mean is ALWAYS ≤ arithmetic mean for non-constant prices. This systematically underprices volatile assets. Look for: protocols using V3 TWAP without understanding it returns geometric mean. [SigmaPrime oracle]

- [ ] **TWAP window too long hides current conditions**: A 24-hour TWAP during a flash crash still shows a near-normal price. This delays liquidations. Look for: TWAP windows > 4 hours used for liquidation triggers. [SigmaPrime oracle]

- [ ] **TWAP on rebasing token**: If a rebasing token's supply doubles, its price halves. TWAP doesn't capture this instantly, creating arbitrage. Look for: TWAP oracles for rebasing token pairs. [SigmaPrime oracle]

- [ ] **Uniswap V3 `observe()` reverts if oracle not initialized**: The oracle must have at least `cardinality` observations. If `cardinality == 1` (default), only the current block is available and any historical query reverts. Look for: `pool.observe()` calls without prior `increaseObservationCardinalityNext()`. [SigmaPrime oracle]

## Spot Price Manipulation

- [ ] **NEVER use spot reserves as a price oracle**: `pool.getReserves()`, `pool.slot0()`, and raw `balanceOf()` values can be manipulated within a single transaction via flash loans. A slippage check around a manipulable spot quote is not an oracle safety proof. Look for: instantaneous AMM state used for pricing, collateral, or execution bounds. [beirao O-09, SigmaPrime oracle]

- [ ] **Read-only reentrancy on Balancer/Curve**: During a Balancer/Curve callback (before state update), calling a view function (like `getRate()`) returns a manipulated rate because the pool state is mid-update. Classic exploit: Sentiment ($1M). Look for: any price query to Balancer/Curve pools within a callback or the same transaction as a pool interaction. [beirao O-10]

## Price Peg Assumptions

- [ ] **LP token valuation via reserves**: `LP_value = 2 * sqrt(reserve0 * reserve1) * price` (Alpha Homora formula) is manipulation-resistant. Using `(reserve0 * price0 + reserve1 * price1) / totalSupply` is manipulable. Look for: LP token pricing formulas that use raw reserves. [SigmaPrime oracle]

## Pyth Network

- [ ] **Pyth prices are pull-based**: Unlike Chainlink (push), Pyth prices must be pushed on-chain by the caller. If nobody pushes, the price is stale. Look for: Pyth integration that assumes prices update automatically. [SigmaPrime oracle]

- [ ] **Pyth confidence interval**: Pyth returns `(price, conf, expo, publishTime)`. During high volatility, `conf` (confidence interval) can be very wide, meaning the price is uncertain. Protocols should check that `conf / price < threshold` (e.g., 5%). Look for: Pyth price usage without confidence interval check. [SigmaPrime oracle]

- [ ] **Pyth `publishTime` staleness**: Must check `publishTime` is recent, similar to Chainlink `updatedAt`. Look for: Pyth prices without publishTime freshness check. [SigmaPrime oracle]

## General Oracle Security

- [ ] **Predictable block-derived randomness**: `block.timestamp`, `blockhash`, and `block.prevrandao` are observable or validator-influenced and must not be the sole entropy for valuable outcomes. Look for: randomness derived directly from block fields without a secure VRF, commit-reveal scheme, or equivalent unpredictability and bias resistance. [SWC-120]

- [ ] **Single oracle dependency**: If the protocol relies on one oracle and it fails/is manipulated, everything breaks. Use multiple oracles with fallback logic (Chainlink primary, TWAP fallback, manual override emergency). Look for: single `priceFeed.latestRoundData()` without fallback. [SigmaPrime oracle]

- [ ] **Oracle update frequency vs protocol tick frequency**: If the oracle updates every hour but the protocol checks prices every minute, 59 out of 60 checks use a "stale" price. This is expected behavior for Chainlink, but the protocol must design around it. Look for: high-frequency price checks on low-frequency oracle feeds. [SigmaPrime oracle]

- [ ] **Multi-hop price derivation accumulates error**: ETH/USD = ETH/BTC × BTC/USD — each feed has its own error range. Multi-hop prices compound errors. Look for: price derivation using 3+ oracle hops. [SigmaPrime oracle]

## Chainlink Deep Dive (Expanded from Beirao/Arbitrum Checklist)

- [ ] **Oracle price update front-running/backrunning**: Oracle update transactions are visible in the mempool, allowing attackers to trade before or after a price change; stablecoin mint/burn and collateral operations are especially sensitive. Look for: user actions and oracle updates that interact without a delay, fee, commit-reveal, or settlement boundary. [beirao CL-11, Cyfrin — Chainlink Oracle Security, Angle Research, Sigma Prime — Oracles & Pricing]

- [ ] **Pricefeed heartbeat too slow for use case**: A 24-hour heartbeat feed is fine for weekly settlements but dangerous for real-time liquidations. If the actual price drops 50% between heartbeats, the protocol uses a 50% stale price. Look for: protocols using feeds with heartbeats longer than their position health check frequency. [beirao CL-08]

## Oracle Price Zero Edge Case

The zero-price check is covered by the canonical Answer Bounds entry above; this section adds no separate runtime row.

---

## Cyfrin — Chainlink Oracle Security Considerations (Phase 3)

- [ ] **Same heartbeat used for multiple feeds with different update frequencies**: If both BTC/USD (1hr heartbeat) and USDC/USD (24hr heartbeat) use the same staleness threshold, one will be too strict (false stale) or too lenient (actually stale). Each feed needs its own heartbeat constant. [Source: Cyfrin — Chainlink Oracle Security, Sherlock JOJO]

- [ ] **Oracle price feed not updated frequently — high deviation threshold**: Similar feeds can have different heartbeat & deviation thresholds. A feed with 1% deviation and 1hr heartbeat will be more accurate than one with 5% deviation and 24hr heartbeat. A deviation threshold only controls when an update is triggered; it is not an economic safety proof. For lending, test both the pre-update stale-price path and the post-threshold updated-price path, include the delay in the manipulation horizon, and compare the resulting manipulation cost with maximum extractable borrow value. [Source: Cyfrin — Chainlink Oracle Security]

- [ ] **Wrong price feed address in constructor vs comments**: Developers copy the correct address in comments but hardcode the wrong address in the constructor (e.g., ETH/USD instead of BTC/USD). Verify all hardcoded addresses against Chainlink's official feed list. [Source: Cyfrin — Chainlink Oracle Security, Sherlock USSD]

- [ ] **Unhandled oracle revert causes complete DoS**: Chainlink multisigs can block price feed access at will. If calls aren't wrapped in try/catch, a disabled feed bricks the entire protocol. Provide functionality to update oracle addresses post-deployment. [Source: Cyfrin — Chainlink Oracle Security, Code4rena Inverse]

- [ ] **VRF REQUEST_CONFIRMATIONS too low for target chain reorg depth**: Default value of 3 from Chainlink tutorial is insufficient for Polygon (frequent 30+ block reorgs). Chain-specific values needed per deployment. [Source: Cyfrin — Chainlink Oracle Security]

- [ ] **Bets/inputs accepted after randomness request**: If users can place bets or modify inputs after the VRF randomness request but before fulfillment, they can front-run the oracle response to game the outcome. [Source: Cyfrin — Chainlink Oracle Security]

- [ ] **Randomness callback selects against MUTABLE shared state (word-informed steering)**: The VRF word is *unbiasable* but *public in the mempool* for `requestConfirmations` blocks before the callback mines. If `fulfillRandomWords` computes the outcome from live state that anyone can change in that gap — `word % totalWeight`, an array length/order, a live balance/supply, a cumulative-weight tree/index — then whoever reads the pending word can move the result onto a chosen target. The mutating actor need NOT be the purchaser and need NOT touch "their own" input: a *third party's* deposit/mint/list that changes the *shared selection pool* every pending request resolves against is enough. Fix: snapshot all outcome-inputs at request time, or reject any callback that could have observed a post-request mutation (e.g. stage deposits so they can't enter the pool until after the last honorable callback block: `requestConfirmations + activationDelay > maxCallbackDelay`). Note: even when the Chainlink VRF wrapper itself is trusted/out-of-scope, the contract's *use* of the word (selection against mutable state) is in scope. Look for: `fulfillRandomWords`/reveal callbacks that read storage which any external function mutates; deposit/mint/list/withdraw/reprice functions with no lock while a request is pending. [Source: FWA / TokenWorks CryptoPunk #5450 incident, 2026]

- [ ] **One-directional lock on the selection window**: A window-lock that blocks *withdrawals* (pool shrink) but not *deposits* (pool growth) — or the reverse — still lets an attacker steer a pending randomness callback from the unguarded direction. Additive steering is as strong as subtractive. Look for: a `block.number < lastRequestBlock + lock` (or `withdrawLockBlocks`) guard on the withdraw path but no equivalent on deposit/mint/list, often with a comment like "pool growth never invalidates a pending request." [Source: FWA / TokenWorks CryptoPunk #5450 incident, 2026]

- [ ] **Fee/price slippage guard mistaken for a selection guard**: A callback that re-checks `fee`/`price` drift within a tolerance does NOT protect *which* item is selected. Selection via `word % N` is discontinuous in `N`, so a mutation far too small to push a smooth fee past its slippage tolerance can still relocate the selection target arbitrarily — the guard and the exploit have different sensitivities. Also: "selection always lands on a valid active item" is an invariant that stays true *during* the exploit; it is not proof that the item cannot be chosen by an adversary. Look for: a slippage/tolerance check inside the fulfillment that guards an amount/price, while the winning item is chosen from mutable weight/index/length. [Source: FWA / TokenWorks CryptoPunk #5450 incident, 2026]

## Sigma Prime — Oracles & Pricing (Phase 3)

- [ ] **Homegrown oracle — multiple feeds dominated by single source**: Synthetix's multiple price feeds were all heavily influenced by the UniswapV1 MKR/ETH pool. Verify feed independence; median of correlated feeds provides false security. [Source: Sigma Prime — Oracles & Pricing]

- [ ] **Oracle front-running/backrunning via timing delays**: Users can observe pending oracle updates and trade just before/after to profit from the price delta. Use pull-style oracles, faster L2s, or settlement periods. [Source: Sigma Prime — Oracles & Pricing, Synthetix]

- [ ] **Gas congestion delays oracle updates — cascading liquidations**: On Black Thursday 2020, high gas caused Maker oracle lag, then a sudden 20% price drop caused mass liquidations. Bidding software couldn't handle gas spikes, allowing $0 bids to win $8.3M of ETH. Audit off-chain software too. [Source: Sigma Prime — Oracles & Pricing, MakerDAO]

- [ ] **Hardcoded price peg assumptions**: USDC/DAI can depeg, and tokens pegged to ETH or BTC such as stETH, rETH, cbETH, WBTC, and wstETH can trade away from 1:1. Never hardcode token == $1 or token == underlying; use an appropriate price feed and depeg tolerance. Look for: collateral or settlement values derived from a hardcoded peg instead of the token's actual market value. [SigmaPrime oracle, beirao O-11, beirao O-12, beirao CL-13, Cyfrin — Chainlink Oracle Security, Sigma Prime — Oracles & Pricing]

- [ ] **Manual multi-sig oracle update acts as hardcoded during delays**: If token price bounds require multi-sig to update, delayed signatures effectively hardcode the stale price, enabling exploitation. USDR/TNGBL was exploited this way. [Source: Sigma Prime — Oracles & Pricing, Tangible USDR]

- [ ] **TWAP mean can be skewed by single extreme reading**: With readings [10, 9999, 12, 11], mean TWAP = 2508 despite 75% of prices being ~10-12. Especially dangerous for illiquid pools. Consider median or trimmed mean. [Source: Sigma Prime — Oracles & Pricing]

## Supplemental Attack Vectors (SAS-AV)

These vectors are merged from sanbir/solidity-auditor-skills; each item retains a detection condition (D), false-positive gate (FP), and source provenance.

- [ ] **[SAS-AV-114] Funding Rate Derived from Single Trade Price**
  - **D:** Perp funding rate uses last trade price as mark. Single self-trade at extreme price skews funding — attacker profits on opposing position.
  - **FP:** Mark from TWAP or external oracle. Funding rate capped per period. VWAP used.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-246

- [ ] **[SAS-AV-115] LST Redemption-Rate vs Market-Price Divergence**
  - **D:** LST collateral valued at protocol redemption rate (`stETH.getPooledEthByShares()`) while market trades at discount. Borrower posts overvalued collateral, borrows against inflated value. During stress, redemption rate stays high while market drops — bad debt.
  - **FP:** Market price feed (Chainlink stETH/ETH) used. `min(redemptionRate, marketPrice)` for valuation. LTV haircut for historical deviation. Circuit breaker on divergence.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-248

- [ ] **[SAS-AV-124] Oracle Extractable Value (OEV) Liquidation Leakage**
  - **D:** Liquidation callable by anyone with full `liquidationBonus` going to `msg.sender`. Oracle price update → MEV race to liquidate → value leaks from protocol to searchers with no recapture.
  - **FP:** OEV-aware oracle (API3 OEV Network, Chainlink SVR). Liquidation bonus auctioned with proceeds to protocol. Dutch auction liquidation. Keeper priority window.
  - **Origin:** `sanbir/solidity-auditor-skills` AV-300

## drozer-lite Additions

The checks below are the canonical runtime additions from the EVM-relevant drozer-lite profiles. Each item retains the source profile and pinned commit.

- [ ] **[DROZER-GAME-3] Time-Gated Actions with Observable Default Outcomes / Selective Callback Revert**
  - **D:** A time-gated action has a default outcome if the user does not act within the window; the attacker observes the would-be outcome and acts only if unfavorable (letting the default apply otherwise). Or: a callback (RNG consumer, settlement callback) can selectively revert on unfavorable outcomes, forcing a re-roll.
  - **FP:** No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.
  - **Methodology:** For every time-gated mechanism, identify the default outcome and whether attackers can observe the alternative before acting. For every callback that consumes a random result, verify the callback cannot revert on unfavorable outcomes (use try/catch to absorb reverts, or require the callback to be made by the protocol not the user).
  - **Look for:** `if (block.timestamp > deadline) { applyDefault(); } else { requireUserAction(); }` where the user knows both outcomes RNG consumer contract that reverts in `fulfillRandomWords` when result is unfavorable Settlement callback callable by the winning party who can choose to revert
  - **Origin:** [gdroz3r/drozer-lite — checklists/gaming.md](https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists/gaming.md) @ fcc489d7eb14208bedcb6290b7b8ca5af6058539
