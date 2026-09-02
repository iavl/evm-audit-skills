# EVM Audit Skills

A deterministic, evidence-gated EVM smart-contract audit Skill suite for
Codex.

It combines Slither-backed reconnaissance, immutable checklist routing,
candidate-only Deep Review, proof-gated findings, and confirmed-only reporting.

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
See [QUICKSTART.md](QUICKSTART.md) for the focused start guide.

### 2. Open the target repository in Codex

Open the local smart-contract project, or provide its repository URL.

### 3. Ask Codex to run the Master Skill

```text
Audit this smart-contract repository using evm-audit-master:
https://github.com/owner/repo
```

GitHub issue creation is opt-in. Ask Codex to file confirmed Medium+ findings
only when you explicitly want issue creation.

## Codex Audit

The default Codex profile assigns different models to different audit stages:

| Stage | Default Codex model |
| --- | --- |
| Recon / Routing | Luna · Max |
| Domain Resolution / Context | Terra · Medium |
| Screen | Terra · High |
| Deep Review | Sol · High |
| Proof | Sol · Max |
| Report | Terra · Medium |

Use the defaults unless you explicitly customize the profile. It is confirmed
once at audit startup. See the [Codex model profile](docs/codex-model-profile.md)
for details.

## How It Works

Instead of asking one model to read the entire codebase and guess
vulnerabilities, the audit progressively narrows a large security checklist
into a small set of evidence-backed findings.

```text
                      all security checks
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
              proven irrelevant   candidate
                                     │
                                     ▼
                               DEEP REVIEW
                                 /       \
                              safe     suspicious
                                          │
                                          ▼
                                         PROOF
                                      /        \
                                   safe      confirmed
                                               │
                                               ▼
                                             REPORT
```

| Stage | What it does |
| --- | --- |
| **Recon** | Understands the audit scope, build environment, dependencies, and important protocol features. |
| **Routing** | Selects relevant security checks while keeping uncertain checks visible. |
| **Domain Resolution & Context** | Resolves protocol-specific facts such as oracle usage, permissions, assets, and liquidation assumptions. |
| **Screen** | Separates checks that are provably irrelevant from checks that require deeper investigation. |
| **Deep Review** | Analyzes candidate vulnerabilities against real code paths, state transitions, invariants, and economic assumptions. |
| **Proof** | Uses PoCs, traces, invariants, or calculations to prove or disprove suspicious issues. |
| **Report** | Re-validates the audit state and reports only confirmed findings. |

The key rule throughout the pipeline is:

```text
uncertain → investigate further
uncertain ≠ safe
```

This prevents incomplete analysis from silently becoming a clean audit. For a
detailed walkthrough of every stage, see [Audit Workflow](docs/audit-workflow.md).

## Safety Guarantees

```text
UNKNOWN ≠ ABSENT

incomplete compilation
→ cannot establish trusted absence

SCREEN
→ CANDIDATE or NOT_APPLICABLE_CONFIRMED

SUSPICIOUS
→ PROOF required

CONFIRMED
→ final report only

stale artifacts
→ rejected
```

Uncertainty is never silently filtered, incomplete artifacts cannot claim a
clean audit, and stale review artifacts are not reused. See
[Audit Runtime](docs/audit-runtime.md) for implementation-level details.

## Audit Output

Runs are written to an external sibling such as `../<repo>-audit-run/`, never
inside the target or build root. `AUDIT-REPORT.md`
contains only `CONFIRMED` findings; supporting Recon, routing, context, review,
and proof artifacts remain beside it.

## Using Individual Domain Skills

Use `evm-audit-master` by default. When the audit scope is already known, use
an individual Domain Skill from the [Skill Catalog](skills/README.md).

## Development & Internals

For maintainers, contributors, and advanced users who want to understand or
extend the repository.

### Architecture & Documentation

- [Audit Workflow](docs/audit-workflow.md)
- [Architecture](docs/architecture.md)
- [Audit Runtime](docs/audit-runtime.md)
- [Recon and Routing](docs/recon-and-routing.md)
- [Codex Model Profile](docs/codex-model-profile.md)
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

See the [Development Guide](development/README.md).

## License

The repository is licensed under the MIT License in [`LICENSE`](LICENSE).
Source provenance and pinned upstream revisions are documented in
[`docs/knowledge-lineage.md`](docs/knowledge-lineage.md).
