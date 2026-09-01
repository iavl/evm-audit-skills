# EVM Audit Skills

A deterministic, evidence-gated EVM smart-contract audit Skill suite for
Codex.

It combines Slither-backed reconnaissance, immutable checklist routing,
candidate-only Deep Review, proof-gated findings, and deterministic
confirmed-only reporting.

- `evm-audit-master` is the default entry point.
- Evidence-backed routing keeps uncertainty visible.
- Only proven `CONFIRMED` findings reach the final report.

## Quick Start

### 1. Install and make the Skills discoverable

Keep the suite together under your Codex skills directory, then expose its
top-level Skill packages:

```bash
git clone https://github.com/iavl/evm-audit-skills-standalone ~/.codex/skills/evm-audit-skills
for skill in ~/.codex/skills/evm-audit-skills/skills/evm-audit-*; do
  ln -s "$skill" ~/.codex/skills/"$(basename "$skill")"
done
```

If the suite is already checked out, use that directory instead of cloning.
See [QUICKSTART.md](QUICKSTART.md) for the installation and artifact details.

### 2. Open the target repository in Codex

Open the local smart-contract project, or provide its repository URL.

### 3. Ask Codex to run the Master Skill

```text
Audit this smart-contract repository using evm-audit-master:
https://github.com/owner/repo
```

The Master Skill guides the audit through:

```text
RECON → ROUTING → DOMAIN CONTEXT → SCREEN → DEEP REVIEW → PROOF → REPORT
```

GitHub issue creation is opt-in. Add and file confirmed Medium+ findings as
GitHub issues only when you explicitly want issue creation.

## Codex Audit

The default stage profile is:

| Stage | Default Codex model |
| --- | --- |
| Recon / Routing | Luna · Max |
| Domain Resolution / Context | Terra · Medium |
| Screen | Terra · High |
| Deep Review | Sol · High |
| Proof | Sol · xHigh |
| Report | Terra · Medium |

Use the defaults unless you explicitly customize the profile. The model
profile is confirmed once at audit startup and can be customized. See the
[Codex model profile](docs/codex-model-profile.md) for details. Future audits
can use the editable user default at `~/.codex/evm-audit-model-profile.json`.

## How It Works

The audit follows a staged pipeline instead of asking one model to read the
entire codebase and immediately guess vulnerabilities.

The basic idea is:

1. understand what code is actually in scope;
2. determine which security checks are relevant;
3. quickly eliminate checks that are clearly not applicable;
4. deeply investigate the remaining candidates;
5. require proof before calling something a real finding;
6. generate the final report only from confirmed findings.

```text
                         all audit checks
                                │
                                ▼
                          RECON + ROUTING
                                │
                                ▼
                          relevant checks
                                │
                                ▼
                              SCREEN
                            /        \
               proven irrelevant    candidate
                                      │
                                      ▼
                                DEEP REVIEW
                                  /       \
                               safe     suspicious
                                           │
                                           ▼
                                          PROOF
                                       /          \
                                    safe        confirmed
                                                  │
                                                  ▼
                                                REPORT
```

### 1. RECON — Understand the code before auditing it

Reconnaissance builds a machine-readable picture of the target project.

It identifies things such as:

- which Solidity files are actually being audited;
- which project and build configuration is used;
- which dependencies are involved;
- which Solidity compiler version is being used; and
- which important protocol features appear in the code.

For example, Recon may detect upgradeable contracts, ERC-4626 vault logic,
external oracle calls, flash-loan callbacks, or role-based permissions.

Recon is deliberately conservative. If the runtime cannot prove that it has
completely analyzed the relevant code, it does not treat missing evidence as
proof that a feature is absent.

Output:

- Feature Map
- compilation and scope metadata
- source and build fingerprints

### 2. ROUTING — Decide which security checks matter

The repository contains a large security checklist covering many EVM and DeFi
attack classes. Running every check against every contract would waste time
and model context.

Routing uses the Recon result to determine which checks should be examined now,
which need more context first, and which may be excluded only when their
absence or environment mismatch is proven.

For example:

- complete evidence that no proxy architecture is in use → proxy-specific
  checks may be filtered;
- an ERC-4626 vault is detected → vault accounting and share-price checks
  become relevant; and
- oracle usage is unclear → oracle-related checks remain deferred rather than
  being discarded.

Routing produces an immutable snapshot so later audit stages cannot silently
change the set of checks being reviewed.

Output:

- selected checks
- deferred checks
- filtered checks
- routing snapshot

### 3. DOMAIN RESOLUTION & CONTEXT — Understand protocol-specific assumptions

Some security questions cannot be answered from syntax alone. The runtime may
need to understand which oracle is used, how collateral is valued, who can
upgrade the contract, what assets can enter a vault, how liquidation works, or
which external protocols are trusted.

This stage resolves those protocol-specific facts. For example, an audit may
record Chainlink as the oracle, WETH and WBTC as collateral, a 2-of-3 multisig
as the upgrade authority, and a permissionless liquidation path with a 5%
incentive.

If an important fact is still unknown, the audit stays incomplete rather than
guessing. The user-facing stage combines two runtime artifacts: `Domain
Resolution` determines whether deferred domains apply, while `Domain Context`
records the facts required to review the applicable domains.

Output:

- Domain Resolution
- Domain Context

### 4. SCREEN — Quickly separate irrelevant checks from real candidates

Screen is a fast triage stage. Every routed check ends in one of only two
states:

- `NOT_APPLICABLE_CONFIRMED`
- `CANDIDATE`

`NOT_APPLICABLE_CONFIRMED` means there is enough evidence to prove that the
attack class does not apply to this target. `CANDIDATE` means the check needs
deeper analysis.

For example, a check asking whether an attacker can manipulate an AMM spot
price used as an oracle can be marked `NOT_APPLICABLE_CONFIRMED` when the
protocol never uses an AMM price. If an AMM price is used, or the evidence is
unclear, it remains a `CANDIDATE`.

The important rule is:

```text
uncertain → CANDIDATE
```

Uncertainty is never converted into `NOT_APPLICABLE`; this prevents the audit
from silently filtering out vulnerabilities.

Output:

- Screen results
- Deep-review candidate set

### 5. DEEP REVIEW — Analyze each candidate against the real code path

Deep Review is where most vulnerability reasoning happens. For each candidate,
the auditor examines actual state transitions, permissions, external calls,
invariants, and economic assumptions.

A review may trace a path such as:

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

Or it may trace:

```text
flash loan
  ↓
price manipulation
  ↓
borrow / liquidation
  ↓
accounting update
  ↓
attacker profit
```

Each candidate must produce an evidence-backed review record. Deep Review can
resolve a candidate as `REVIEWED_SAFE` or leave it `SUSPICIOUS`; a safe result
must explain which invariant prevents exploitation. `CONFIRMED` is reserved
for the Proof stage.

Output:

- append-only Deep Review records

### 6. PROOF — Prove or disprove suspicious findings

A suspicious pattern is not automatically a vulnerability. The Proof stage
determines whether the suspected attack is actually reachable and exploitable.

Evidence may include:

- a Foundry proof-of-concept;
- transaction traces;
- invariant violations;
- arithmetic or economic calculations; or
- deterministic reproduction of the exploit path.

For a suspected share-price manipulation issue, Proof asks whether the attacker
can reach the state without privileged access, how much capital is required,
whether a guard stops the attack, and whether measurable value can be
extracted.

A finding becomes `CONFIRMED` only after strong evidence establishes the issue.
If proof shows that an invariant or guard prevents exploitation, the candidate
is resolved as safe instead.

Output:

- proof-backed review revisions
- confirmed findings

### 7. REPORT — Build the report from confirmed evidence only

The final stage independently re-validates the audit state. It checks that:

- routing is current;
- required context is complete;
- Screen coverage is complete;
- every Deep candidate has been reviewed;
- no `SUSPICIOUS` item remains unresolved; and
- reporting artifacts match the latest proof state.

Only `CONFIRMED` records are included as vulnerabilities. The report includes
structured information such as severity, affected location, attack path,
preconditions, exploitability, impact, proof, and recommended remediation.

If the audit is incomplete or an artifact has become stale, the runtime refuses
to present the result as a completed clean audit.

Output:

- `AUDIT-REPORT.md`
- `issue-candidates.json`

## Safety Guarantees

```text
UNKNOWN ≠ ABSENT
incomplete compilation → cannot establish trusted absence
SCREEN → CANDIDATE or NOT_APPLICABLE_CONFIRMED
SUSPICIOUS → PROOF required
CONFIRMED → final report only
stale artifacts → rejected
```

Uncertainty is never silently filtered, incomplete artifacts cannot claim a
clean audit, and stale snapshot-bound review artifacts are not reused.

## Audit Output

Runs are written to `audits/<repo>-<UTC timestamp>/`.

`AUDIT-REPORT.md` contains only `CONFIRMED` findings. Recon, routing, domain
context, Screen, Deep Review, Proof, and machine-readable review artifacts
remain beside it. Unresolved or stale artifacts prevent a clean completion.

## Using Individual Domain Skills

Use an individual Domain Skill when the audit scope is already known. Browse
the [Skill Catalog](skills/README.md) for the available domains; use
`evm-audit-master` when the scope is not known in advance.

## Development & Internals

For maintainers, contributors, and users who want to understand or extend the
runtime.

### Architecture & Documentation

- [Architecture](docs/architecture.md)
- [Audit Runtime](docs/audit-runtime.md)
- [Recon and Routing](docs/recon-and-routing.md)
- [Knowledge Evidence](docs/knowledge-evidence.md)
- [Knowledge Lineage](docs/knowledge-lineage.md)

### Repository Layout

- `skills/` — directly usable Skill packages
- `data/` — canonical security knowledge
- `domains/` — Domain configuration
- `scripts/` — audit runtime and maintenance tooling
- `evm_audit_runtime/` — shared pure runtime logic
- `schemas/` — artifact schemas
- `docs/` — architecture and runtime documentation
- `development/` — benchmarks and maintenance fixtures
- `tests/` — runtime and regression tests

### Knowledge Base

`data/canonical-checks.json` is the authoritative checklist source. Generated
Skill Markdown is derived output and should not be edited directly. See
[Knowledge Maintenance](docs/knowledge-maintenance.md) for editing and
generation rules.

### Development & Validation

See [Development Guide](development/README.md).

## License

The repository is licensed under the MIT License in [`LICENSE`](LICENSE).
Source provenance and pinned upstream revisions are documented in
[`docs/knowledge-lineage.md`](docs/knowledge-lineage.md).
