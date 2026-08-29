# evm-audit-skills

A suite of 20 OpenClaw agent skills for deep EVM smart contract security audits.

Built by [clawdbotatg](https://github.com/clawdbotatg) — an AI agent that builds on Ethereum autonomously.

---

## What This Is

Each skill is a dense, sourced checklist of **non-obvious** security vulnerabilities for a specific domain. These are the things that experienced auditors check that basic tools miss — precision loss patterns, AMM-specific attacks, oracle manipulation vectors, governance exploits, and more.

**~3,600 lines of checklist content and 1,004 individual checks across the 19 domain skills plus the master index.**

Sources include Dacian (dacian.me), beirao.xyz, SigmaPrime, Decurity, RareSkills, weird-erc20, Spearbit, Hacken, LayerZero, Cyfrin, OpenZeppelin, the SWC registry, and the GitHub repositories listed in the Repository Sources and Lineage table below.

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
| [sanbir/solidity-auditor-skills](https://github.com/sanbir/solidity-auditor-skills) | Merged and adapted | 166 deduplicated `SAS-AV` checks; commit `b864c2ee3b2f63c4361a5064084ce1e99dcf7444`; MIT |
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

---

## How To Use (OpenClaw)

### Run an audit

Just hand the agent a contract:

```
audit this contract and file issues: https://github.com/owner/repo/blob/main/contracts/MyContract.sol
```

The agent will:
1. Load `evm-audit-master` → read the contract → select relevant skills
2. Each selected domain skill walks its checklist, including the merged SAS-AV, DROZER, and AUDITMOS vectors
3. Spawn parallel opus sub-agents, one per skill domain
4. Each agent walks its checklist and writes findings
5. Synthesize into a final `AUDIT-REPORT.md`
6. File GitHub issues for all Medium+ findings

### The audit pipeline

```
Contract URL/path
      │
      ▼
  RECON (select 5-8 skills from routing table)
      │
      ▼
  PARALLEL AGENTS (one per skill, all run simultaneously)
  ├── agent: evm-audit-general     → findings-general.md
  ├── agent: evm-audit-precision-math → findings-math.md
  ├── agent: evm-audit-defi-amm   → findings-amm.md
  └── ...
      │
      ▼
  SYNTHESIS (deduplicate, rank, cross-cutting analysis)
      │
      ▼
  AUDIT-REPORT.md + GitHub Issues
```

---

## Standard Finding Format

All findings across all skills use this format:

```
## [X-N] Title
**Severity**: Critical / High / Medium / Low / Info
**Category**: [skill name]
**Location**: `functionName()` or file:line
**Description**: What the issue is and why it matters.
**Proof of Concept**: Exact steps to trigger or exploit.
**Recommendation**: Concrete fix with code snippet.
```

**Severity definitions:**
- **Critical** — Direct loss of funds by a third party, no preconditions
- **High** — Loss of funds requiring specific conditions, or permanent DoS
- **Medium** — Degraded behavior, trust model violation, incorrect accounting
- **Low** — Best practice violation, latent bug, no direct fund risk
- **Info** — Informational, no security impact

---

## Example Audit

Full audit of `LiquidityVesting.sol` (Uniswap V3 liquidity vesting contract on Base):
→ [`audits/liquidity-vesting-2026-02-28/`](https://github.com/clawdbotatg/liquidity-vesting/issues)

27 findings across 3 parallel agents. 12 issues filed. Runtime ~10 minutes.

---

## Attribution & Thanks

This skill suite stands entirely on the shoulders of researchers and auditors who published their knowledge openly. Every checklist item is sourced — if you want to go deeper on any topic, these are the primary sources:

### 🙏 People & Teams

**[Dacian](https://dacian.me)** — The single highest-signal source in this entire suite. Eight deep-dive articles covering liquidation vulnerabilities, CLM attacks, slippage, precision loss, signature replay, governance, inline assembly, and lending/borrowing. Essential reading for any serious auditor.
- [DeFi Liquidation Vulnerabilities](https://dacian.me/defi-liquidation-vulnerabilities)
- [Concentrated Liquidity Manager Vulnerabilities](https://dacian.me/concentrated-liquidity-manager-vulnerabilities)
- [DeFi Slippage Attacks](https://dacian.me/defi-slippage-attacks)
- [Precision Loss Errors](https://dacian.me/precision-loss-errors)
- [Signature Replay Attacks](https://dacian.me/signature-replay-attacks)
- [DAO Governance DeFi Attacks](https://dacian.me/dao-governance-defi-attacks)
- [Solidity Inline Assembly Vulnerabilities](https://dacian.me/solidity-inline-assembly-vulnerabilities)
- [Lending/Borrowing DeFi Attacks](https://dacian.me/lending-borrowing-defi-attacks)

**[beirao.xyz](https://beirao.xyz)** — Comprehensive audit checklist covering 200+ non-obvious Solidity footguns, organized by category. The backbone of `evm-audit-general`.

**[Sigma Prime](https://blog.sigmaprime.io)** — Three excellent deep-dives on governance/DAOs, oracles/pricing, and liquid restaking security.
- [Governance & DAOs](https://blog.sigmaprime.io/governance-dao.html)
- [Oracles & Pricing](https://blog.sigmaprime.io/oracles-and-pricing.html)
- [Liquid Restaking](https://blog.sigmaprime.io/liquid-restaking.html)

**[RareSkills](https://www.rareskills.io)** — Detailed articles on smart contract security and UUPS proxy vulnerabilities.
- [Smart Contract Security](https://www.rareskills.io/post/smart-contract-security)
- [UUPS Proxy](https://www.rareskills.io/post/uups-proxy)

**[Cyfrin](https://cyfrin.io)** — Chainlink oracle security deep-dive by Dacian, published via Cyfrin.
- [Chainlink Oracle DeFi Attacks](https://medium.com/cyfrin/chainlink-oracle-defi-attacks-93b6cb6541bf)

### 🔧 Non-repository reference sources

**[Decurity](https://decurity.io)** — Protocol-specific security checklists for AMMs, CDPs, and liquid staking derivatives.

**[Hacken](https://hacken.io)** — Uniswap V4 hooks security guide.

**[OpenZeppelin](https://blog.openzeppelin.com)** — Uniswap V4 hooks audit guide and proxy security research.

**[Spearbit](https://spearbit.com)** — Bridge security checklist.

**[MixBytes](https://mixbytes.io)** — CREATE2 security analysis.

### 📋 Standards

**[EEA EthTrust Security Levels](https://entethalliance.org/specs/ethtrust-sl/)** — The current smart contract security standard (supersedes the SWC registry).

The archived SWC taxonomy is used for legacy weakness identifiers; its repository is listed in the Repository Sources and Lineage table above.

### Protocol Documentation
Uniswap V3/V4 docs, LayerZero V2 security checklist, Chainlink CCIP best practices, Wormhole integration security guide, Across Protocol integration guide, Arbitrum official documentation.

---

## Contributing

Found a new non-obvious vulnerability pattern? The bar for inclusion is high:
- Must be **non-obvious** — if a junior auditor would catch it, it doesn't belong
- Must be **sourced** — link to a real audit report, exploit postmortem, or research article
- Must include the **Look for:** pattern so an agent knows what code to scan for

Open a PR against the relevant `references/checklist.md`.

---

Built by [clawd](https://clawd.atg.eth) · [@austingriffith](https://twitter.com/austingriffith) · [clawdbotatg](https://github.com/clawdbotatg)
