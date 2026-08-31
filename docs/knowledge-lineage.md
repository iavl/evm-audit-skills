# Knowledge Sources and Lineage

This document records the repository lineage, integrated external knowledge,
source acquisition status, pinned revisions, provenance maps, and license
handling. It is repository-level documentation, not runtime checklist input.

## Repository lineage

| Source | Relationship to this suite | Scope / revision |
|---|---|---|
| [austintgriffith/evm-audit-skills](https://github.com/austintgriffith/evm-audit-skills) | Base repository / current fork parent | Original 20-skill structure and initial checklists |
| [sanbir/solidity-auditor-skills](https://github.com/sanbir/solidity-auditor-skills) | Merged and adapted | 166 source-level deduplicated `SAS-AV` checks; commit `b864c2ee3b2f63c4361a5064084ce1e99dcf7444`; MIT |
| [gdroz3r/drozer-lite](https://github.com/gdroz3r/drozer-lite) | Merged and adapted | 177 EVM checks; commit `fcc489d7eb14208bedcb6290b7b8ca5af6058539`; MIT |
| [auditmos/skills](https://github.com/auditmos/skills) | Merged and adapted | 116 attack-vector patterns; commit `c9583babb0ce189d9f39a05caf94b5a5da655010`; MIT |

The four rows above record the repository lineage and the external repository
content incorporated into the runtime checklists. The base row records the
original lineage; the other three rows identify adapted integrations.

## External references and comparisons

| Source | Relationship to this suite | Scope / revision |
|---|---|---|
| [OpenZeppelin Contracts ERC4626 guide](https://docs.openzeppelin.com/contracts/5.x/erc4626) | Official implementation reference | Fee-aware asset/share conversion context |
| [devdacian/ai-auditor-primers](https://github.com/devdacian/ai-auditor-primers) | Reference only | Primer patterns cross-referenced and integrated selectively; no full repository copied |
| [d-xo/weird-erc20](https://github.com/d-xo/weird-erc20) | Reference only | Non-standard ERC20 behavior catalog |
| [juancito-dev/multichain-auditor](https://github.com/juancito-dev/multichain-auditor) | Reference only | Cross-chain deployment and EVM-chain pitfalls; formerly recorded as `0xJuancito/multichain-auditor` |
| [tamjidahmed0/smart-contract-audit-checklist](https://github.com/tamjidahmed0/smart-contract-audit-checklist) | Reference only (historical) | Practical Solidity footguns from the recorded source checklist; the original repository was unavailable when rechecked |
| [nascentxyz/simple-security-toolkit](https://github.com/nascentxyz/simple-security-toolkit) | Reference only | DeFi security and audit-readiness guidance |
| [SmartContractSecurity/SWC-registry](https://github.com/SmartContractSecurity/SWC-registry) | Reference only | Archived weakness taxonomy used for legacy `SWC-*` provenance |
| [alt-research2/SolidityGuard](https://github.com/alt-research2/SolidityGuard) | Coverage comparison only | No text, code, identifiers, or directory structure imported |

The SolidityGuard comparison used commit
`35645e8ba76cdacbeec40f347c758de2077e2ecd`; resulting gap checks were
independently written from public EIP, SWC, and ERC-4337 references.

External source integration is preserved as provenance, not counted as
separate attack vectors. Semantic merges require the same root cause, trigger,
proof obligation, and impact; otherwise related contextual checks remain
distinct.

## Source acquisition log

Date fetched: 2026-02-27

### Successfully fetched sources

#### Dacian Articles (via archive.org — all 8 articles)

| Source | URL | Status |
|---|---|---|
| DeFi Liquidation Vulnerabilities | https://dacian.me/defi-liquidation-vulnerabilities | ✅ via archive.org (50KB, truncated — very dense) |
| CLM Vulnerabilities | https://dacian.me/concentrated-liquidity-manager-vulnerabilities | ✅ via archive.org (20KB, complete) |
| DeFi Slippage Attacks | https://dacian.me/defi-slippage-attacks | ✅ via archive.org (27KB, complete) |
| Precision Loss Errors | https://dacian.me/precision-loss-errors | ✅ via archive.org (30KB, complete) |
| Signature Replay Attacks | https://dacian.me/signature-replay-attacks | ✅ via archive.org (15KB, complete) |
| DAO Governance DeFi Attacks | https://dacian.me/dao-governance-defi-attacks | ✅ via archive.org (50KB, truncated) |
| Inline Assembly Vulnerabilities | https://dacian.me/solidity-inline-assembly-vulnerabilities | ✅ via archive.org (35KB, complete) |
| Lending/Borrowing DeFi Attacks | https://dacian.me/lending-borrowing-defi-attacks | ✅ via archive.org (29KB, complete) |

#### Devdacian GitHub

| Source | URL | Status |
|---|---|---|
| AI Auditor Primers — base.primer.md | https://raw.githubusercontent.com/devdacian/ai-auditor-primers/main/primers/base.primer.md | ✅ (33KB) |
| AI Auditor Primers — amy.vault.erc4626.primer.md | https://raw.githubusercontent.com/devdacian/ai-auditor-primers/main/primers/amy.vault.erc4626.primer.md | ✅ listed (299KB — too large to process fully) |
| Primers repo tree | https://api.github.com/repos/devdacian/ai-auditor-primers/git/trees/main?recursive=1 | ✅ (2 primers found) |

#### RareSkills

| Source | URL | Status |
|---|---|---|
| Smart Contract Security | https://www.rareskills.io/post/smart-contract-security | ✅ via archive.org (50KB, truncated) |
| UUPS Proxy | https://www.rareskills.io/post/uups-proxy | ✅ via archive.org (21KB, complete) |

#### Sigma Prime

| Source | URL | Status |
|---|---|---|
| Governance & DAOs | https://blog.sigmaprime.io/governance-dao.html | ✅ direct (17KB) |
| Oracles & Pricing | https://blog.sigmaprime.io/oracles-and-pricing.html | ✅ direct (20KB) |
| Liquid Restaking | https://blog.sigmaprime.io/liquid-restaking.html | ✅ direct (26KB) |

#### Cyfrin / Dacian

| Source | URL | Status |
|---|---|---|
| Chainlink Oracle Security | https://medium.com/cyfrin/chainlink-oracle-defi-attacks-93b6cb6541bf | ✅ direct (22KB) |

#### SWC Registry

| Source | URL | Status |
|---|---|---|
| README | https://raw.githubusercontent.com/SmartContractSecurity/SWC-registry/master/README.md | ✅ (registry no longer maintained since 2020, superseded by EEA EthTrust Security Levels) |

#### gdroz3r/drozer-lite

| Source | URL | Status |
|---|---|---|
| EVM profile checklists (177 checks) | https://github.com/gdroz3r/drozer-lite/tree/fcc489d7eb14208bedcb6290b7b8ca5af6058539/checklists | ✅ pinned to commit `fcc489d7eb14208bedcb6290b7b8ca5af6058539`; Solana and ICP profiles excluded |
| MIT license | https://github.com/gdroz3r/drozer-lite/blob/fcc489d7eb14208bedcb6290b7b8ca5af6058539/LICENSE | ✅ included in `THIRD_PARTY_NOTICES.md` |

The per-check deduplication map is maintained in
[`drozer-lite-provenance.md`](../skills/evm-audit-master/references/drozer-lite-provenance.md).
It is audit metadata and is not a runtime checklist.

#### auditmos/skills (fetched 2026-08-29)

| Source | URL | Status |
|---|---|---|
| Attack-vector reference patterns and slippage skill extras | https://github.com/auditmos/skills/tree/c9583babb0ce189d9f39a05caf94b5a5da655010/skills | ✅ pinned to commit `c9583babb0ce189d9f39a05caf94b5a5da655010`; 112 `reference.md` patterns plus 4 slippage patterns listed in `SKILL.md` |
| MIT license | https://github.com/auditmos/skills/blob/c9583babb0ce189d9f39a05caf94b5a5da655010/LICENSE | ✅ included in `THIRD_PARTY_NOTICES.md` |

The per-pattern deduplication map is maintained in
[`auditmos-provenance.md`](../skills/evm-audit-master/references/auditmos-provenance.md).
It is audit metadata and is not a runtime checklist.

The two provenance maps document source-level coverage only; they do not
certify semantic uniqueness across the 19 runtime checklists. Repository-level
runtime decisions are recorded in
[`checklist-semantic-dedup-review.md`](../skills/evm-audit-master/references/checklist-semantic-dedup-review.md),
and deterministic maintenance checks are implemented in
`scripts/validate_checklists.py`.

#### alt-research2/SolidityGuard (coverage comparison only; reviewed 2026-08-29)

| Source | URL | Status |
|---|---|---|
| 104-pattern index | https://github.com/alt-research2/SolidityGuard/tree/35645e8ba76cdacbeec40f347c758de2077e2ecd/.claude/skills/solidity-guard/skills/vulnerability-scanner/resources | ✅ used only to identify coverage gaps; no source text, code, identifiers, or directory structure imported |
| License | https://github.com/alt-research2/SolidityGuard/blob/35645e8ba76cdacbeec40f347c758de2077e2ecd/LICENSE | ⚠️ proprietary, non-commercial license reviewed; not incorporated because all resulting checks are independently authored |

#### Public references for independently authored gap checks

| Source | URL | Status |
|---|---|---|
| EIP-1153: Transient Storage Opcodes | https://eips.ethereum.org/EIPS/eip-1153 | ✅ used for transient-storage isolation checks |
| ERC-4337: Account Abstraction Using Alt Mempool | https://eips.ethereum.org/EIPS/eip-4337 | ✅ used for UserOperation hash and bundler trust checks |
| SWC Registry | https://swcregistry.io/ | ✅ used for SWC-109, SWC-115, SWC-120, SWC-124, SWC-125, SWC-130, and SWC-136 checks |
| OWASP Smart Contract Top 10 | https://scs.owasp.org/sctop10/ | ✅ used for the off-chain signer/frontend operational-boundary check |
| OpenZeppelin Contracts ERC4626 guide | https://docs.openzeppelin.com/contracts/5.x/erc4626 | ✅ used for fee-aware asset/share conversion context |

### Failed sources

| Source | URL | Reason |
|---|---|---|
| Dacian direct (all URLs) | https://dacian.me/* | 429 — Vercel Security Checkpoint (bot protection). Resolved via archive.org. |
| ConsenSys Best Practices | https://consensys.github.io/smart-contract-best-practices/attacks/ | 404 — GitHub Pages site no longer at this path |
| MixBytes — Liquid Staking | https://mixbytes.io/blog/liquid | Fetch failed (connection error) |
| MixBytes — Account Abstraction | https://mixbytes.io/blog/account-abstraction | Not attempted (similar expected failure) |
| Solodit Checklist | https://solodit.cyfrin.io/checklist | JS-rendered, requires browser. Archive.org not attempted. |
| Blast Integration Bugs | https://nirlin-blast-bugs.notion.site/... | Notion pages require JS rendering |
| DeFi Llama Hacks | https://defillama.com/hacks | JS-rendered dashboard |
| Rekt News | https://rekt.news | Referenced in articles but not independently fetched |
| OpenZeppelin CHANGELOG | https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/CHANGELOG.md | Not fetched (very large, low signal-to-noise ratio) |

## Notes

- **SWC Registry** has not been updated since 2020 and has been superseded by the [EEA EthTrust Security Levels Specification](https://entethalliance.org/specs/ethtrust-sl/). All SWC weaknesses were incorporated into that spec. Existing checklist items already cover the most critical SWC entries.
- **Devdacian's base.primer.md** (33KB) is an extremely high-quality comprehensive primer covering lending, liquidation, signatures, precision, slippage, oracle, CLM, staking, auction, and reentrancy vulnerability patterns with detailed invariants and checklists. Content from this primer has been cross-referenced and integrated.
- All Dacian articles were successfully fetched via Wayback Machine (archive.org) after direct access was blocked by Vercel bot protection.
- Total extracted content: ~450KB of high-quality audit security content processed into checklist items across 8+ skill files.

## Licensing

Third-party license text lives in [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).
It does not declare a license for independently authored repository content;
that content is licensed by [`LICENSE`](../LICENSE).
