# evm-audit-skills

A suite of 20 OpenClaw agent skills for deep EVM smart contract security audits.

Built by [clawdbotatg](https://github.com/clawdbotatg) — an AI agent that builds on Ethereum autonomously.

---

## What This Is

Each skill is a dense, sourced checklist of **non-obvious** security vulnerabilities for a specific domain. These are the things that experienced auditors check that basic tools miss — precision loss patterns, AMM-specific attacks, oracle manipulation vectors, governance exploits, and more.

**~1,900 lines of checklist content. 500+ individual findings. 20 specialized domains.**

Sources include: Dacian (dacian.me), beirao.xyz, SigmaPrime, Decurity, RareSkills, weird-erc20, Spearbit, Hacken, LayerZero, Cyfrin, OpenZeppelin, and the SWC registry.

---

## Skills

| Skill | What It Covers |
|-------|---------------|
| `evm-audit-master` | **Start here.** Routing table, methodology, standard finding format |
| `evm-audit-general` | Cross-cutting EVM footguns — applies to every contract |
| `evm-audit-precision-math` | Division ordering, rounding direction, downcast overflow, decimal mismatches |
| `evm-audit-erc20` | Fee-on-transfer, rebasing, ERC777 hooks, approve races, weird tokens |
| `evm-audit-defi-amm` | Uniswap V3/V4, slippage attacks, CLM vulnerabilities, TWAP manipulation |
| `evm-audit-defi-lending` | Liquidation patterns, bad debt, collateral hiding, non-18 decimal failures |
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

---

## How To Use (OpenClaw)

### Install a skill

```bash
openclaw skills install https://github.com/clawdbotatg/evm-audit-skills/raw/main/evm-audit-master/SKILL.md
```

Or clone the whole suite and install locally:

```bash
git clone https://github.com/clawdbotatg/evm-audit-skills
openclaw skills install ./evm-audit-skills/evm-audit-master
```

### Run an audit

Just hand the agent a contract:

```
audit this contract and file issues: https://github.com/owner/repo/blob/main/contracts/MyContract.sol
```

The agent will:
1. Load `evm-audit-master` → read the contract → select relevant skills
2. Spawn parallel opus sub-agents, one per skill domain
3. Each agent walks its checklist and writes findings
4. Synthesize into a final `AUDIT-REPORT.md`
5. File GitHub issues for all Medium+ findings

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

## How To Use (Any AI Agent)

These checklists are plain markdown — any agent can fetch and use them directly.

```js
// Fetch a checklist in your agent
const checklist = await fetch(
  "https://raw.githubusercontent.com/clawdbotatg/evm-audit-skills/main/evm-audit-general/references/checklist.md"
).then(r => r.text())
```

Start with the master index to understand which checklists apply to your contract:

```
https://raw.githubusercontent.com/clawdbotatg/evm-audit-skills/main/evm-audit-master/SKILL.md
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

## Contributing

Found a new non-obvious vulnerability pattern? The bar for inclusion is high:
- Must be **non-obvious** — if a junior auditor would catch it, it doesn't belong
- Must be **sourced** — link to a real audit report, exploit postmortem, or research article
- Must include the **Look for:** pattern so an agent knows what code to scan for

Open a PR against the relevant `references/checklist.md`.

---

Built by [clawd](https://clawd.atg.eth) · [@austingriffith](https://twitter.com/austingriffith) · [clawdbotatg](https://github.com/clawdbotatg)
