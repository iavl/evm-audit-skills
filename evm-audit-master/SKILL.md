---
name: evm-audit-master
description: Master index for EVM smart contract security audits. Load this FIRST to route specialized skills and enforce per-check applicability, evidence review states, and confirmed-only synthesis.
---
# EVM Smart Contract Security Audit — Master Index

## How To Use
1. **Always load this skill first** for any EVM smart contract audit
2. Read the contract(s) under audit
3. Build a reconnaissance feature map and use the selector plus
   `../data/features.json` to select relevant canonical checks
4. Read [the per-check review contract](references/check-review-contract.md)
5. Run the `FAST_FILTER`, `DEEP_REVIEW`, and `PROOF` stages in that contract
6. Put only `CONFIRMED` items into the final audit report and assign severity
   during synthesis

## Domain Index

Domain definitions, routing surfaces, relationships, and current runtime counts
are generated from `../domains/*.json` in [the domain catalog](references/domains.md).

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
knowledge. One-time transformations belong under `../scripts/migrations/` and
the checked-in migrations have already been applied; do not run migrations as
part of ordinary rendering. The registry is machine-only at audit time: domain
agents consume selected check
bodies emitted by the router and must not load the full JSON database. Each
canonical check has an `all_of`/`any_of`/`none_of` predicate over the vocabulary
in `../data/features.json`. The v2 reconnaissance input shape is defined by
`../data/feature-map.schema.json`; evidence uses typed `kind`, `location`, and
`reason` objects. Predicates marked `inferred` came from
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

The v3 routing manifest accounts for every canonical ID in scope. Filtered IDs
remain in the manifest and do not receive per-check Markdown `NOT_APPLICABLE`
records; selected IDs receive exactly one deep/proof ledger record in the file
named for their manifest `owner_domain`. It also records the registry digest,
selector version, knowledge/target repository commits, chain/fork/compiler context, and
audit timestamp for reproducibility.

## Domain Routing

Use the machine selector for global routing. The generated
[domain catalog](references/domains.md) is the human-readable domain index;
`related_domains` is advisory and never expands a direct domain invocation.

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
