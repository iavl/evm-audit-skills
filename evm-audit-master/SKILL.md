---
name: evm-audit-master
description: Master index for EVM smart contract security audits. Load this FIRST to route specialized skills and enforce per-check applicability, evidence review states, and confirmed-only synthesis.
---
# EVM Smart Contract Security Audit — Master Index

## How To Use
1. **Always load this skill first** for any EVM smart contract audit
2. Read the contract(s) under audit
3. Use the routing table below to load relevant specialized skills
4. Read [the per-check review contract](references/check-review-contract.md)
5. Review every selected checklist item and assign exactly one terminal status
6. Put only `CONFIRMED` items into the final audit report

## All 20 Skills — Definitive Index

| # | Skill | Description | Items |
|---|-------|-------------|-------|
| 1 | **evm-audit-master** | This file. Routing table, methodology, source attribution. Load first. | — |
| 2 | **evm-audit-general** | Cross-cutting issues: storage pointers, struct deletion, mixed accounting, merkle proofs, msg.value in loops, try/catch, delegatecall, upgrades, downcasting, ID/array validation, Unicode source review, inheritance semantics, rebasing tokens, fee-on-transfer, ERC4626 inflation attack | 108 |
| 3 | **evm-audit-precision-math** | Division-before-multiplication, rounding to zero, precision scaling mismatches, downcast overflow, rounding direction (protocol vs user), decimal assumption errors | 36 |
| 4 | **evm-audit-erc20** | Fee-on-transfer, rebasing, ERC777 hooks, approve race conditions, zero-transfer reverts, pausable tokens, deny lists (USDC), deflationary/inflationary tokens, multiple-address tokens | 40 |
| 5 | **evm-audit-defi-amm** | AMM/DEX slippage attacks, wrong slippage bases and token-vs-value bounds, CLM vulnerabilities (TWAP bypass, sandwich via owner functions, stuck tokens, stale approvals, retrospective fees), UniswapV3/V4 hooks, fee tier issues | 66 |
| 6 | **evm-audit-defi-lending** | Auction and liquidation vulnerabilities (self-bidding, incentives, bad debt, partial liquidation, reward ordering), lending/borrowing attacks, oracle-manipulation economics, liquidity/cap/LTV stress modeling, front-run prevention, collateral hiding, insurance fund edge cases, non-18 decimal failures | 88 |
| 7 | **evm-audit-defi-staking** | Liquid staking, restaking, EigenLayer integration, stakedButUnverified accounting, Beacon Chain proof verification (Deneb), validator front-running, cooldown exploitation, reward calculation precision | 57 |
| 8 | **evm-audit-erc4626** | Share/asset conversion, inflation attack, virtual shares, deposit/withdraw rounding, first depositor attack, multi-step operations, 85+ patterns from Dacian's ERC4626 primer | 58 |
| 9 | **evm-audit-erc4337** | Account abstraction, smart wallet security, UserOperation hash integrity, bundler ordering/censorship assumptions, paymaster attacks, session key exploits, gas griefing | 40 |
| 10 | **evm-audit-bridges** | Cross-chain bridge security, LayerZero V2, CCIP, Wormhole, Across, message replay, finality assumptions, relayer trust, adapter pattern issues | 58 |
| 11 | **evm-audit-proxies** | UUPS deep dive (uninitialized implementation, delegatecall to selfdestruct, broken upgrade chain, authorization schema changes), Transparent proxy, Beacon, Diamond, storage collision, immutable variable loss | 32 |
| 12 | **evm-audit-signatures** | Signature replay (missing nonce, cross-chain, missing parameter, no expiration), ecrecover return check, signature malleability, EIP-712 conformance, ECDSA library version requirements | 21 |
| 13 | **evm-audit-governance** | DAO attacks (flash-loan + delegation bypass, voting power destruction, totalPower manipulation, snapshot staleness, quorum impossibility, treasury delegation abuse, restriction bypass, token recycling, proposal deadlines, pre-mint exploitation), proposal execution ordering, fake proposals via CREATE2, multi-sig quorum failure | 54 |
| 14 | **evm-audit-oracles** | Chainlink integration (stale prices, L2 sequencer, per-feed heartbeats, decimal assumptions, wrong addresses, front-running, unhandled reverts, depeg detection, minAnswer/maxAnswer), predictable randomness, Sigma Prime pricing patterns | 48 |
| 15 | **evm-audit-assembly** | Inline assembly memory corruption, user-controlled storage writes, EIP-1153 transient storage isolation, call to non-existent contracts, overflow/underflow without protection, uint128 overflow evading 256-bit detection | 39 |
| 16 | **evm-audit-chain-specific** | L2/alt-chain quirks — Arbitrum, Optimism, zkSync, Blast, BSC, Polygon. Sequencer downtime, different opcodes, gas pricing differences, precompile availability, block time assumptions | 39 |
| 17 | **evm-audit-flashloans** | Flash loan attack patterns, oracle manipulation via flash loans, governance flash loan voting, flash mint issues, composability risks | 14 |
| 18 | **evm-audit-erc721** | NFT-specific issues: onERC721Received callbacks, enumeration DoS, royalty enforcement, metadata manipulation, batch mint edge cases | 39 |
| 19 | **evm-audit-dos** | Denial of service patterns: unbounded loops, block gas limit, self-destruct force-send, storage deletion costs, griefing via revert, return data bombs | 18 |
| 20 | **evm-audit-access-control** | Access control patterns: missing modifiers, `tx.origin` authorization, off-chain signer/frontend trust, 2-step ownership, role-based permissions, emergency pause, time delays, admin overpowers | 21 |

**Total: 876 checklist items across 19 specialized skills + 1 master index**

## Checklist Organization

The 166 attack vectors adapted from sanbir/solidity-auditor-skills, the canonical portions of the 177 EVM-relevant checks adapted from gdroz3r/drozer-lite, and the 116 attack-vector patterns adapted from auditmos/skills retain their source-level provenance. The routed `references/checklist.md` files remain the single runtime source of truth. Repository-level semantic deduplication decisions are recorded in [checklist-semantic-dedup-review.md](references/checklist-semantic-dedup-review.md); the current review has merged unambiguous same-file duplicates while cross-domain candidates remain explicitly pending human adjudication. Covered drozer-lite and Auditmos records remain in their centralized provenance maps without adding runtime checks.

SolidityGuard's 104-pattern index was used only for coverage comparison at commit `35645e8ba76cdacbeec40f347c758de2077e2ecd`; its proprietary content was not copied. New gap checks are independently authored and cite public standards.

## Routing Table — Which Skills To Load

| If the contract involves... | Load skill |
|---|---|
| **Any EVM contract** (always) | `evm-audit-general` |
| **Any math/pricing/fees** (always) | `evm-audit-precision-math` |
| Accepts ERC20 tokens (deposits, swaps, collateral) | `evm-audit-erc20` |
| AMM, DEX, swap router, Uniswap V3/V4 hooks, liquidity pools, CLMs | `evm-audit-defi-amm` |
| Lending, borrowing, CDP, liquidation, AAVE/Compound fork | `evm-audit-defi-lending` |
| Staking, liquid staking (stETH/rETH/cbETH), restaking, EigenLayer | `evm-audit-defi-staking` |
| ERC4626 vaults, share/asset conversion, yield vaults | `evm-audit-erc4626` |
| Account abstraction, smart wallets, paymasters, session keys | `evm-audit-erc4337` |
| Cross-chain bridges, LayerZero, CCIP, Wormhole, Across | `evm-audit-bridges` |
| Upgradeable contracts, proxies (UUPS/Transparent/Beacon/Diamond) | `evm-audit-proxies` |
| Off-chain signatures, EIP-712, permits, meta-transactions | `evm-audit-signatures` |
| DAO governance, voting, timelocks, multi-sig, proposal execution | `evm-audit-governance` |
| Price oracles (Chainlink, TWAP, Pyth), VRF, external data | `evm-audit-oracles` |
| Inline assembly, Yul, CREATE2, low-level calls, precompiles | `evm-audit-assembly` |
| Non-mainnet (Arbitrum, OP, zkSync, Blast, BSC, Polygon) | `evm-audit-chain-specific` |
| Flash loans, composability attacks | `evm-audit-flashloans` |
| NFTs, ERC721, ERC1155, metadata, royalties | `evm-audit-erc721` |
| DoS vectors, gas griefing, unbounded operations | `evm-audit-dos` |
| Access control, roles, ownership, emergency controls | `evm-audit-access-control` |

## Audit Methodology

### Phase 1: Reconnaissance
**Entry:** Contract source is available from the supplied URL or local path.

**Actions:**
1. Fetch or read all contract files in scope.
2. Identify contract files, state-changing entry points, and external dependencies.
3. Map inheritance, proxy, delegatecall, and implementation relationships.
4. Identify external calls, token interactions, and relevant deployment chain(s).

**Exit:** The audit scope, source inventory, entry points, dependencies, and target chain(s) are recorded.

### Phase 2: Skill Selection
**Entry:** Phase 1 scope and protocol surfaces are recorded.

**Actions:**
1. Load `evm-audit-general` and `evm-audit-precision-math` for every audit.
2. Add skills from the routing table. For oracle-backed lending, also load `evm-audit-oracles`; load `evm-audit-defi-amm` when the price source depends on AMM liquidity.
3. Use each selected skill's `references/checklist.md` as the runtime checklist. The merged SAS-AV, DROZER, and AUDITMOS vectors remain in those domain checklists.

**Exit:** The selected skill set and the exact checklist source for each skill are recorded.

### Phase 3: Execute Selected Domain Reviews
**Entry:** Phase 2 has produced the selected skill set and checklist sources.

**Actions:**
1. If the runtime supports sub-agents, create one review task per selected skill and parallelize independent domain reviews.
2. Respect the runtime's concurrency limits. Reuse the source inventory and shared contract context captured in Phase 1; do not duplicate source ingestion. Use the strongest appropriate available reasoning model.
3. If sub-agents are unavailable, execute one domain review at a time sequentially.
4. Give each review access to the full contract source captured in Phase 1, its one checklist, this master skill, and `references/check-review-contract.md`; do not refetch or re-ingest the same source unless a missing-file or verification gap requires it.
5. Require each domain review to write `audits/<repo>-<date>/review-<skill>.md` with exactly one review record for every checklist item. Reviews must not emit unqualified findings outside the review contract.
6. Wait for every selected review to finish before synthesis.

**Exit:** Every expected checklist item has one valid record with one of the four terminal statuses. Missing, duplicate, unknown, or malformed records make the audit incomplete.

### Phase 4: Synthesis
**Entry:** All selected review ledgers exist and pass the coverage and format gate.

**Actions:**
1. Validate that every expected item appears exactly once and that every status is one of `NOT_APPLICABLE`, `REVIEWED_SAFE`, `SUSPICIOUS`, or `CONFIRMED`.
2. If coverage or record validation fails, mark the audit `INCOMPLETE` and do not write a final `AUDIT-REPORT.md`.
3. Review only `CONFIRMED` records for duplicate root causes and cross-cutting interactions. Check oracle-backed lending economics, state-machine consistency, and combined attack paths.
4. If synthesis discovers a new cross-cutting candidate, map it to existing checklist item(s), or record it in `review-integration.md` and apply the same review contract before admission.
5. Write `AUDIT-REPORT.md` using only `CONFIRMED` findings ranked by severity. Do not include N/A, safe, or suspicious records as findings.
6. If all records are terminal but any item is `SUSPICIOUS`, mark the report `COMPLETE_WITH_UNRESOLVED_REVIEW`; do not claim the audit is clean or vulnerability-free. If there are no confirmed findings, say only that no confirmed findings were established within the reviewed scope.

**Exit:** The final report contains only confirmed findings, or no final report exists because coverage is incomplete.

### Phase 5: File Issues (if repo provided)
**Entry:** `AUDIT-REPORT.md` passed Phase 4 and contains only confirmed findings.

**Actions:**
1. Run `gh issue create --repo <owner/repo>` only for confirmed findings with Medium severity or above.
2. Skip Info and Low unless explicitly asked.
3. Prefix issue titles with `[Critical]`, `[High]`, or `[Medium]`.

**Exit:** Every created issue maps to a confirmed finding in `AUDIT-REPORT.md`; no issue is created for a suspicious or unreviewed item.

---

## Standard Finding Format

Only final `CONFIRMED` findings and the synthesis output use this format. Per-check records use the linked [review contract](references/check-review-contract.md).

~~~
## [X-N] Title
**Status**: CONFIRMED
**Checklist reference**: `<skill>/<check-ref>`
**Severity**: Critical / High / Medium / Low / Info
**Category**: [skill name that caught this]
**Location**: `functionName()` or file:line
**Applicability**: APPLICABLE — why the checklist item applies
**Code path**: Exact reachable path from entry point to affected operation
**Preconditions**: Concrete state, caller, timing, balance, role, or deployment conditions
**Exploitability**: How an attacker or permitted actor satisfies the preconditions
**Impact**: Concrete security, accounting, availability, or trust-model consequence
**Proof of Concept / Invariant Violation**: Runnable test/transaction trace, or deterministic invariant violation with evidence
**Description**: What the issue is and why it matters. Be specific — name the variable, line, or pattern.
**Recommendation**: Concrete fix with code snippet where possible.
~~~

**Severity definitions** (use these, not your own judgment):
- **Critical**: Direct loss of funds by a third party, no preconditions
- **High**: Loss of funds requiring specific conditions, or permanent DoS
- **Medium**: Degraded behavior, trust model violation, incorrect accounting, or owner-only fund loss
- **Low**: Best practice violation, latent bug, or confusing behavior without direct fund risk
- **Info**: Informational, no security impact

Assign severity only after the `CONFIRMED` evidence gate passes. Never assign a finding severity to `SUSPICIOUS`.

## Source Attribution Key
- `[beirao]` — beirao.xyz audit checklist
- `[Dacian]` — dacian.me security articles (8 deep-dive articles covering liquidation, CLM, slippage, precision, signatures, governance, assembly, lending)
- `[Devdacian Primer]` — devdacian/ai-auditor-primers GitHub (base.primer.md — comprehensive 33KB primer)
- `[Decurity AMM/CDP/LSD]` — Decurity protocol-specific checklists
- `[weird-erc20]` — d-xo/weird-erc20 repository
- `[multichain-auditor]` — 0xJuancito multichain auditor
- `[SigmaPrime]` — Sigma Prime security blog (governance, oracles, liquid restaking articles)
- `[RareSkills]` — RareSkills security articles (smart contract security, UUPS proxy)
- `[Cyfrin]` — Cyfrin/Dacian Chainlink oracle security article
- `[ERC4626 checklist]` — ERC4626 security checklist
- `[ERC4626 primer]` — ERC4626 vulnerability primer (85+ patterns)
- `[ERC4337 checklist]` — Account abstraction security checklist
- `[Hacken UniV4]` — Hacken Uniswap V4 hooks audit guide
- `[LayerZeroV2 checklist]` — LayerZero V2 security checklist
- `[CCIP checklist]` — Chainlink CCIP best practices
- `[Wormhole checklist]` — Wormhole integration security
- `[Across checklist]` — Across Protocol integration guide
- `[Spearbit bridge]` — Spearbit bridge security checklist
- `[mixbytes CREATE2]` — MixBytes CREATE2 security analysis
- `[SWC-XXX]` — Smart Contract Weakness Classification registry (superseded by EEA EthTrust)
- `[Arbitrum docs]` — Arbitrum official documentation
- `[Blast docs]` — Blast L2 documentation
- `[SAS-AV]` — source-level deduplicated attack vectors adapted from [sanbir/solidity-auditor-skills](https://github.com/sanbir/solidity-auditor-skills), retaining the source vector number for provenance
- `[DROZER]` — EVM-relevant source-level deduplicated attack vectors adapted from [gdroz3r/drozer-lite](https://github.com/gdroz3r/drozer-lite) at pinned commit `fcc489d7eb14208bedcb6290b7b8ca5af6058539`
- `[AUDITMOS]` — source-level attack-vector patterns adapted from [auditmos/skills](https://github.com/auditmos/skills) at pinned commit `c9583babb0ce189d9f39a05caf94b5a5da655010`; covered patterns are tracked in the [Auditmos provenance map](references/auditmos-provenance.md)
- `[EIP-1153]` — Ethereum transient storage specification used for independently authored transient-storage checks
- `[ERC-4337]` — Account abstraction specification used for independently authored UserOperation and bundler checks
- `[OWASP]` — OWASP Smart Contract Top 10 used for independently authored operational-boundary checks
