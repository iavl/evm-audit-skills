# evm-audit-skills

---

## What This Is

Each skill is a structured, sourced checklist of **non-obvious** security vulnerabilities for a specific domain. The canonical JSON registry keeps one stable attack hypothesis per root cause while generated Markdown views remain easy for audit runtimes to consume.

**868 canonical checks and 871 generated runtime entries across the 19 domain skills plus the master index.**

---

## Skills

| Skill | What It Covers |
|-------|---------------|
| `evm-audit-master` | **Start here.** Routing table, methodology, standard finding format |
| `evm-audit-general` | Cross-cutting EVM footguns — applies to every contract |
| `evm-audit-precision-math` | Division ordering, rounding direction, downcast overflow, decimal mismatches |
| `evm-audit-erc20` | Fee-on-transfer, rebasing, ERC777 hooks, approve races, weird tokens |
| `evm-audit-defi-amm` | Uniswap V3/V4, slippage attacks, CLM vulnerabilities, TWAP manipulation |
| `evm-audit-defi-lending` | Liquidation patterns, bad debt, oracle-manipulation economics, liquidity/cap/LTV stress modeling, collateral hiding, non-18 decimal failures |
| `evm-audit-defi-staking` | Liquid staking, restaking, EigenLayer, cooldown exploitation |
| `evm-audit-erc4626` | Vault share math, inflation attack, rounding direction, 85+ patterns |
| `evm-audit-erc4337` | Account abstraction, paymasters, session keys, bundler trust |
| `evm-audit-bridges` | LayerZero V2, CCIP, Wormhole, Across, message replay, finality |
| `evm-audit-proxies` | UUPS, Transparent, Beacon, Diamond, storage collisions, initializer bugs |
| `evm-audit-signatures` | Replay attacks, ecrecover, EIP-712, permit edge cases, malleability |
| `evm-audit-governance` | Flash loan voting, totalPower manipulation, proposal ordering, CREATE2 fake proposals |
| `evm-audit-oracles` | Chainlink staleness, minAnswer/maxAnswer, L2 sequencer, TWAP limits |
| `evm-audit-assembly` | Memory corruption, FMPA bugs, non-existent contract calls, uint128 overflow |
| `evm-audit-chain-specific` | Arbitrum, Optimism, zkSync, Blast, BSC — L2 quirks and opcode differences |
| `evm-audit-flashloans` | Flash loan attack patterns, oracle manipulation, governance exploits |
| `evm-audit-erc721` | NFT callbacks, enumeration DoS, royalty bypass, wrapped collections |
| `evm-audit-dos` | Unbounded loops, return data bombs, force-send, griefing via revert |
| `evm-audit-access-control` | Centralization risks, 2-step ownership, role escalation, timelock bypass |

## Repository Sources and Lineage

The table distinguishes repositories whose checklist content was merged from repositories used only as references or for coverage comparison.

| Repository | Relationship to this suite | Scope / revision |
|---|---|---|
| [austintgriffith/evm-audit-skills](https://github.com/austintgriffith/evm-audit-skills) | Base repository / current fork parent | Original 20-skill structure and initial checklists |
| [sanbir/solidity-auditor-skills](https://github.com/sanbir/solidity-auditor-skills) | Merged and adapted | 166 source-level deduplicated `SAS-AV` checks; commit `b864c2ee3b2f63c4361a5064084ce1e99dcf7444`; MIT |
| [gdroz3r/drozer-lite](https://github.com/gdroz3r/drozer-lite) | Merged and adapted | 177 EVM checks; commit `fcc489d7eb14208bedcb6290b7b8ca5af6058539`; MIT |
| [auditmos/skills](https://github.com/auditmos/skills) | Merged and adapted | 116 attack-vector patterns; commit `c9583babb0ce189d9f39a05caf94b5a5da655010`; MIT |
| [devdacian/ai-auditor-primers](https://github.com/devdacian/ai-auditor-primers) | Reference only | Primer patterns cross-referenced and integrated selectively; no full repository copied |
| [d-xo/weird-erc20](https://github.com/d-xo/weird-erc20) | Reference only | Non-standard ERC20 behavior catalog |
| [juancito-dev/multichain-auditor](https://github.com/juancito-dev/multichain-auditor) | Reference only | Cross-chain deployment and EVM-chain pitfalls; formerly recorded as `0xJuancito/multichain-auditor` |
| [tamjidahmed0/smart-contract-audit-checklist](https://github.com/tamjidahmed0/smart-contract-audit-checklist) | Reference only (historical) | Practical Solidity footguns from the recorded source checklist; the original repository was unavailable when rechecked |
| [nascentxyz/simple-security-toolkit](https://github.com/nascentxyz/simple-security-toolkit) | Reference only | DeFi security and audit-readiness guidance |
| [SmartContractSecurity/SWC-registry](https://github.com/SmartContractSecurity/SWC-registry) | Reference only | Archived weakness taxonomy used for legacy `SWC-*` provenance |
| [alt-research2/SolidityGuard](https://github.com/alt-research2/SolidityGuard) | Coverage comparison only | No text, code, identifiers, or directory structure imported |

The three rows marked “Merged and adapted” represent external repository content incorporated into the runtime checklists; the base row records the original lineage. The SolidityGuard comparison used commit `35645e8ba76cdacbeec40f347c758de2077e2ecd`; resulting gap checks were independently written from public EIP, SWC, and ERC-4337 references.

External source integration is preserved as provenance, not counted as separate attack vectors. Edit [`data/canonical-checks.json`](data/canonical-checks.json), then run `python3 scripts/generate_checklists.py` to update the 19 generated runtime views. Semantic merges require the same root cause, trigger, proof obligation, and impact; otherwise related contextual checks remain distinct.

---

## How To Use

### Run an audit

Just provide the workflow with a contract:

```
audit this contract and file issues: https://github.com/owner/repo/blob/main/contracts/MyContract.sol
```

The workflow will:
1. Load `evm-audit-master` and build a source, dependency, chain, and feature map.
2. Use the domain routing table and `data/features.json` to run the fast filter.
3. Deep-review only selected canonical IDs, then prove candidates with a PoC or deterministic invariant.
4. Write lightweight filtered records and full records for deep/proof stages under the review contract.
5. Synthesize only `CONFIRMED` records into a final `AUDIT-REPORT.md` and assign severity there.
6. File GitHub issues only for confirmed Medium+ findings when explicitly in scope.

### Runtime-neutral execution

If the runtime supports sub-agents:

- Parallelize independent domain reviews.
- Respect the runtime's concurrency limits.
- Reuse the reconnaissance/source context; do not duplicate source ingestion.
- Use the strongest appropriate available reasoning model.

If sub-agents are unavailable:

- Execute domains sequentially.

### Canonical source and validation

The editable source is [`data/canonical-checks.json`](data/canonical-checks.json).
Feature definitions live in [`data/features.json`](data/features.json), and a
reconnaissance feature map can be evaluated with:

```bash
python3 scripts/select_checks.py --features uses-erc20,uses-oracle --format json
```

Regenerate and validate the runtime views with:

```bash
python3 scripts/generate_checklists.py --check
python3 scripts/validate_checklists.py --strict
python3 -m unittest discover -s tests -v
```

Model-specific `known/partial/novel` snapshots are retained only under
`benchmarks/model-knowledge/`; they are not runtime inputs.

### The audit pipeline

```
Contract URL/path
      │
      ▼
  RECON + FEATURE MAP
      │
      ▼
  FAST FILTER (route canonical IDs)
      │
      ▼
  DEEP REVIEW (parallel when supported; sequential otherwise)
  ├── selected domain → review-<skill>.md
  └── ...
      │
      ▼
  PROOF (PoC / invariant) → CONFIRMED candidates
      │
      ▼
  SYNTHESIS (validate coverage, deduplicate, score severity)
      │
      ▼
  AUDIT-REPORT.md + GitHub Issues
```

---

## Review Ledger and Confirmed Finding Format

Each routed canonical ID receives one review record. Fast-filtered items use the lightweight format; deep/proof candidates include applicability, code path, preconditions, exploitability, impact, PoC/invariant evidence, and exactly one of `NOT_APPLICABLE`, `REVIEWED_SAFE`, `SUSPICIOUS`, or `CONFIRMED`. See [`evm-audit-master/references/check-review-contract.md`](evm-audit-master/references/check-review-contract.md).

Only `CONFIRMED` records may become findings. Confirmed findings use this format:

```
## [X-N] Title
**Status**: CONFIRMED
**Checklist reference**: `<canonical-id>`
**Legacy/source references**: `<source IDs or aliases from canonical registry>`
**Severity**: Critical / High / Medium / Low / Info
**Category**: [skill name]
**Location**: `functionName()` or file:line
**Applicability**: APPLICABLE — why the checklist item applies
**Code path**: Exact reachable path
**Preconditions**: Concrete conditions
**Exploitability**: How the conditions are satisfied
**Impact**: Concrete consequence
**Proof of Concept / Invariant Violation**: Runnable proof or deterministic invariant violation
**Description**: What the issue is and why it matters.
**Recommendation**: Concrete fix with code snippet.
```

Severity is assigned only after confirmation using the dimensions and mapping in [`evm-audit-master/references/severity-scoring.md`](evm-audit-master/references/severity-scoring.md). Checklist type and confidence never determine severity.

`NOT_APPLICABLE`, `REVIEWED_SAFE`, and `SUSPICIOUS` records never appear as findings in `AUDIT-REPORT.md`. If all records have terminal statuses but suspicious items remain, the report must disclose unresolved review status and must not claim the audit is clean.

---
