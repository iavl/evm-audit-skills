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

```text
RECON
  ↓
ROUTING
  ↓
DOMAIN CONTEXT
  ↓
SCREEN
  ↓
DEEP REVIEW
  ↓
PROOF
  ↓
REPORT
```

Recon builds evidence about the target. Routing selects the relevant domains
and checks. Screen produces candidates or proven non-applicability; Deep
Review examines candidates; Proof gates the findings that can be reported.

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
