---
name: evm-audit-master
description: Master index for EVM smart contract security audits. Load this FIRST to route specialized skills and enforce per-check applicability, evidence review states, and confirmed-only synthesis.
---
# EVM Smart Contract Security Audit — Master Index

## How To Use
1. **Always load this skill first** for any EVM smart contract audit
2. Read the contract(s) under audit
3. Build a reconnaissance feature map and use the routing table plus
   `../data/features.json` to select relevant canonical checks
4. Read [the per-check review contract](references/check-review-contract.md)
5. Run the `FAST_FILTER`, `DEEP_REVIEW`, and `PROOF` stages in that contract
6. Put only `CONFIRMED` items into the final audit report and assign severity
   during synthesis

## All 20 Skills — Definitive Index

| # | Skill | Description | Runtime entries |
|---|-------|-------------|-------|
| 1 | **evm-audit-master** | This file. Routing table, methodology, source attribution. Load first. | — |
| 2 | **evm-audit-general** | Cross-cutting issues: storage pointers, struct deletion, mixed accounting, merkle proofs, msg.value in loops, try/catch, delegatecall, upgrades, downcasting, ID/array validation, Unicode source review, inheritance semantics, rebasing tokens, fee-on-transfer, ERC4626 inflation attack | 109 |
| 3 | **evm-audit-precision-math** | Division-before-multiplication, rounding to zero, precision scaling mismatches, downcast overflow, rounding direction (protocol vs user), decimal assumption errors | 36 |
| 4 | **evm-audit-erc20** | Fee-on-transfer, rebasing, ERC777 hooks, approve race conditions, zero-transfer reverts, pausable tokens, deny lists (USDC), deflationary/inflationary tokens, multiple-address tokens | 40 |
| 5 | **evm-audit-defi-amm** | AMM/DEX slippage attacks, wrong slippage bases and token-vs-value bounds, CLM vulnerabilities (TWAP bypass, sandwich via owner functions, stuck tokens, stale approvals, retrospective fees), UniswapV3/V4 hooks, fee tier issues | 66 |
| 6 | **evm-audit-defi-lending** | Auction and liquidation vulnerabilities (self-bidding, incentives, bad debt, partial liquidation, reward ordering), lending/borrowing attacks, oracle-manipulation economics, liquidity/cap/LTV stress modeling, front-run prevention, collateral hiding, insurance fund edge cases, non-18 decimal failures | 88 |
| 7 | **evm-audit-defi-staking** | Liquid staking, restaking, EigenLayer integration, stakedButUnverified accounting, Beacon Chain proof verification (Deneb), validator front-running, cooldown exploitation, reward calculation precision | 57 |
| 8 | **evm-audit-erc4626** | Share/asset conversion, inflation attack, virtual shares, deposit/withdraw rounding, first depositor attack, multi-step operations, 85+ patterns from Dacian's ERC4626 primer | 53 |
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

**Total: 869 canonical checks and 872 generated runtime entries across 19 specialized skills + 1 master index**

## Checklist Organization

The JSON registry at `data/canonical-checks.json` is the single editable source
of truth. The 19 `references/checklist.md` files are deterministic generated
runtime views. Every check has a stable canonical ID, structured
trigger/detection/false-positive/proof fields, a `type` (`normative`,
`semantic`, `exploit-pattern`, or `heuristic`), and a `confidence` label. The
166 attack vectors adapted from sanbir/solidity-auditor-skills, the
EVM-relevant drozer-lite records, and the Auditmos patterns remain traceable as
provenance and aliases.

Semantic deduplication is evidence-based: merge only when root cause, trigger,
proof obligation, and impact are the same. Otherwise retain the contextual
checks and link them with `related` IDs. Decisions are recorded in
[checklist-semantic-dedup-review.md](references/checklist-semantic-dedup-review.md);
a lower check count is not a goal by itself.

SolidityGuard's 104-pattern index was used only for coverage comparison at commit `35645e8ba76cdacbeec40f347c758de2077e2ecd`; its proprietary content was not copied. New gap checks are independently authored and cite public standards.

## Canonical Registry and Feature Routing

The editable registry is `../data/canonical-checks.json`; run
`python3 ../scripts/generate_checklists.py` to regenerate the domain views. The
generator is a pure renderer: it must not infer, repair, or override canonical
knowledge. One-time transformations belong under `../scripts/migrations/`. The
current checkout can be migrated with
`python3 ../scripts/migrations/001_registry_v3.py`; do not run migrations as
part of ordinary rendering. The registry is machine-only at audit time: domain
agents consume selected check
bodies emitted by the router and must not load the full JSON database. Each
canonical check has an `all_of`/`any_of`/`none_of` predicate over the vocabulary
in `../data/features.json`. The reconnaissance input shape is defined by
`../data/feature-map.schema.json`. Predicates marked `inferred` came from
keyword inference; `curated` predicates are hand-reviewed. A false inferred
predicate is not exclusion evidence and is downgraded to `UNKNOWN`; only a
curated `FALSE` may fast-filter. The legacy `features` list is retained only as
a derived union for compatibility.

Start reconnaissance with
`python3 ../scripts/recon.py <target> --output <recon-features.json>` so supported
presence and absence decisions come from Slither AST/IR evidence. Supplement
remaining `UNKNOWN` features from deployment and source evidence; never turn an
unresolved detector into `ABSENT_CONFIRMED`. Then run
`python3 ../scripts/select_checks.py --feature-map <recon-features.json> --format json`
to produce a routing manifest. Use
`--emit-checks --profile compact --format markdown` to emit token-efficient
selected check bodies. Record `--target-root`, `--chain-id`, `--fork-block`, and
`--compiler-version` when available. `PRESENT`, `ABSENT_CONFIRMED`, and
`UNKNOWN` are distinct: unknown evidence is conservatively selected. The legacy
`--features` shorthand remains safe but treats omitted features as unknown.

The routing manifest accounts for every canonical ID in scope. Filtered IDs
remain in the manifest and do not receive per-check Markdown `NOT_APPLICABLE`
records; selected IDs receive exactly one deep/proof ledger record in the file
named for their manifest `owner_domain`. It also records the registry digest,
selector version, knowledge/target commits, chain/fork/compiler context, and
audit timestamp for reproducibility.

## Routing Table — Which Skills and Features To Load

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
1. Build the feature map from Slither AST/IR, the source inventory, entry points, dependencies, and target chain; use manual/LLM review only to supplement `UNKNOWN`.
2. Evaluate the tri-state evidence map with the selector. Only curated predicates proven false may be filtered; inferred false and unknown high-risk surfaces remain selected.
3. For oracle-backed lending, select `evm-audit-oracles`; select `evm-audit-defi-amm` when the price source depends on AMM liquidity.
4. Use the selected-check output emitted by the selector. The generated `references/checklist.md` files are maintenance compatibility views, not the default model input. Canonical IDs, not repeated source labels, define review identity.

**Exit:** The selected skill set and the exact checklist source for each skill are recorded.

### Phase 3: Execute Selected Domain Reviews
**Entry:** Phase 2 has produced the selected skill set and checklist sources.

**Actions:**
1. If the runtime supports sub-agents, parallelize independent selected-domain reviews and respect the runtime's concurrency limits.
2. Reuse the reconnaissance source inventory and shared contract context; do not duplicate source ingestion or assume a particular model/runtime.
3. If sub-agents are unavailable, execute selected domains sequentially.
4. Preserve filtered-out IDs only in the routing manifest. For selected IDs, run deep review and proof stages under `references/check-review-contract.md`.
5. Require each domain review to write `audits/<repo>-<date>/review-<skill>.md` with exactly one canonical review record per selected ID assigned to that owner domain. Filtered IDs stay only in the manifest, and shared IDs must not produce duplicate findings.
6. Wait for every selected review to finish before synthesis.

**Exit:** Every expected checklist item has one valid record with one of the four terminal statuses. Missing, duplicate, unknown, or malformed records make the audit incomplete.

### Phase 4: Synthesis
**Entry:** All selected review ledgers exist and pass the coverage and format gate.

**Actions:**
1. Validate the routing manifest so every in-scope canonical ID appears exactly once in `selected` or `filtered`. Then require every selected ID to appear exactly once across the domain ledgers; filtered IDs remain manifest-only. Every ledger status must be one of `NOT_APPLICABLE`, `REVIEWED_SAFE`, `SUSPICIOUS`, or `CONFIRMED`.
2. If coverage or record validation fails, mark the audit `INCOMPLETE` and do not write a final `AUDIT-REPORT.md`.
3. Review only `CONFIRMED` records for duplicate root causes and cross-cutting interactions. Check oracle-backed lending economics, state-machine consistency, and combined attack paths.
4. If synthesis discovers a new cross-cutting candidate, map it to existing checklist item(s), or record it in `review-integration.md` and apply the same review contract before admission.
5. Write `AUDIT-REPORT.md` using only `CONFIRMED` findings ranked by the [severity model](references/severity-scoring.md). Do not include N/A, safe, or suspicious records as findings.
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
**Checklist reference**: `<canonical-id>`
**Legacy/source references**: `<source IDs or aliases from canonical registry>`
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

Use the dimensions and mapping in
[`references/severity-scoring.md`](references/severity-scoring.md). Assign
severity only after the `CONFIRMED` evidence gate passes; never assign a
finding severity to `SUSPICIOUS`.

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
