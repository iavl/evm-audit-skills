# Audit Workflow

## Overview

An EVM audit is an evidence-gated funnel, not one model reading an entire
repository and guessing vulnerabilities. The runtime starts with a broad
security checklist, narrows it using evidence about the target, investigates
the remaining candidates, and reports only issues that survive proof.

The stages are deliberately ordered: later stages rely on the scope and
decisions established earlier, while uncertainty stays visible until it can
be resolved.

## 1. RECON

Recon builds a trustworthy picture of what is being audited. It establishes:

- the audit scope and build root;
- project configuration and dependencies;
- the Solidity compiler and build environment; and
- important protocol features such as upgradeability, ERC-4626 vaults,
  external oracles, flash-loan callbacks, and role-based permissions.

For example, a target may be a vault in `src/Vault.sol`, while its compilation
context comes from the surrounding Foundry project and its configured
dependencies. Recon keeps those two boundaries distinct so the audit does not
silently omit code needed to understand the target.

Recon is conservative when traversal or compilation is incomplete. Presence
evidence can still identify code that was seen, but missing evidence is not
treated as proof that a feature or dependency is absent.

Main outputs are:

- a Feature Map;
- scope and build metadata; and
- source and build fingerprints.

## 2. ROUTING

The suite contains checks for many EVM and DeFi attack classes. Applying every
check to every contract wastes time and model context, so Routing uses Recon
and trusted environment facts to determine which checks belong in the audit.

Checks can be:

- **selected** for the current review;
- **deferred** until protocol-specific context is available; or
- **filtered** only when trusted evidence proves they do not apply.

Examples:

- verified absence of proxy architecture can filter proxy-specific checks;
- an ERC-4626 vault routes in vault accounting and share-price checks; and
- uncertain oracle usage keeps oracle checks visible for further investigation.

Routing creates an immutable snapshot. Later stages consume that snapshot and
cannot silently change the set of checks under review.

## 3. DOMAIN RESOLUTION & CONTEXT

Some security questions require protocol-specific facts that syntax alone
cannot establish. The audit may need to understand the oracle, accepted
assets, upgrade authority, liquidation mechanism, or trusted external
protocols.

This user-facing stage combines two related runtime activities:

- **Domain Resolution** decides whether a deferred Domain applies to the
  target.
- **Domain Context** records the facts required to review an active Domain.

For example, the audit may resolve Chainlink as the oracle, WETH and WBTC as
collateral, a 2-of-3 multisig as the upgrade authority, and a permissionless
liquidation path with a 5% incentive. If an important fact remains unknown,
the audit cannot claim a clean completion; it must investigate or disclose the
unresolved context.

## 4. SCREEN

Screen is the fast triage stage. Each routed check ends in exactly one of two
user-facing outcomes:

- `NOT_APPLICABLE_CONFIRMED`
- `CANDIDATE`

`NOT_APPLICABLE_CONFIRMED` means evidence proves that the attack class does not
apply. `CANDIDATE` means the check needs deeper analysis, including when the
evidence is incomplete.

For example, an AMM spot-price oracle check can be marked
`NOT_APPLICABLE_CONFIRMED` when the protocol demonstrably never uses an AMM
price. If it does use that price, or the oracle path is unclear, the check
remains a `CANDIDATE`.

The invariant is:

```text
uncertain → CANDIDATE
```

Screen does not emit a “probably safe” result. This keeps uncertain attack
paths in the review rather than filtering them out early.

## 5. DEEP REVIEW

Deep Review examines each candidate against the actual implementation. It
traces state transitions, permissions, external calls, invariants, and
economic assumptions instead of relying on a pattern match.

A small vault example might follow:

```text
deposit()
  ↓
share calculation
  ↓
external token transfer
  ↓
totalAssets()
  ↓
withdraw()
```

The reviewer asks whether the suspected behavior is reachable, which state and
permission checks matter, and whether the claimed impact follows from the
real call path. Deep Review can resolve a candidate as `REVIEWED_SAFE` or leave
it `SUSPICIOUS`; `CONFIRMED` is reserved for Proof.

## 6. PROOF

`SUSPICIOUS` is a hypothesis, not a finding. Proof tests whether the suspected
attack is reachable and exploitable under the target's actual conditions.

Evidence may include:

- strong proof such as a Foundry test, trace, invariant violation, or calculation;
- transaction traces;
- an invariant violation;
- arithmetic or economic calculations; or
- deterministic reproduction of the exploit path.

Proof also considers attacker privileges, required capital, guards, external
dependencies, repeatability, and measurable impact. For a suspected share-price
manipulation issue, it asks whether an attacker can reach the state, whether a
guard blocks it, and whether value can actually be extracted.

Only strong evidence can move a record to `CONFIRMED`. If the invariant or
guard prevents exploitation, the suspicious candidate is resolved as safe
instead. `Proof != PoC`: a runnable exploit PoC is a separate reporting input,
not a prerequisite for confirmation.

## 7. REPORT

Report independently re-validates the current audit state before producing
results. It requires:

- current routing;
- complete required context;
- complete Screen coverage;
- a review for every Deep candidate; and
- no unresolved `SUSPICIOUS` item; and
- reporting artifacts that match the current review and proof state; and
- a validated runnable PoC for each confirmed `High` or `Critical` finding.

Only `CONFIRMED` records enter the final report. The main artifacts are:

- `AUDIT-REPORT.md` for confirmed findings; and
- `issue-candidates.json` for structured issue candidates.

The controller commits these through an immutable content-addressed report
generation and the `report-current.json` pointer; controller output exposes the
generation paths as authoritative, while top-level files are convenience copies.

Incomplete or stale evidence prevents the runtime from presenting a clean,
completed audit. Confirmed `Info`, `Low`, and `Medium` findings do not need a
PoC merely to report, and remain visible in the Markdown report. `Medium` and
above remain issue candidates.

The reporting rule is severity-gated:

```text
CONFIRMED + Medium → report normally; no PoC required
CONFIRMED + High   → INCOMPLETE_POC until a validated PoC is present
PoC admitted       → report after admission and snapshot validation
```

## Example End-to-End Audit

```text
ERC-4626 vault detected
        ↓
vault checks routed in
        ↓
donation attack survives Screen
        ↓
Deep Review finds possible share manipulation
        ↓
Proof runs a Foundry PoC
        ↓
CONFIRMED
        ↓
final report
```

This is a generic illustration of the evidence flow; a real report includes a
finding only when the target-specific proof supports it.

For CLI commands, artifact identity, schemas, and controller behavior, see
[Audit Runtime](audit-runtime.md). For the repository's four-plane design, see
[Architecture](architecture.md).
