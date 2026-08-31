# EVM Audit Skills

AI-assisted EVM smart-contract audit Skill suite.

## Start Here

### I want to audit a smart-contract project

Read the [Quick Start](QUICKSTART.md), then invoke `evm-audit-master`.
It is the recommended default entry point and handles Recon, routing, Domain
selection, Screen, Deep review, proof, and confirmed-only synthesis.

### I want to use one specific audit Skill

Browse the [Skill Catalog](skills/README.md). Targeted Domain Skills are
advanced entry points for audits with a clearly known scope.

### I want to understand how the audit engine works

Read the [Architecture](docs/architecture.md) and [Audit Runtime](docs/audit-runtime.md).

### I want to develop or improve the Skill suite

Start with the [Development Guide](development/README.md).

## What This Is

Each skill is a structured, sourced checklist of **non-obvious** security vulnerabilities for a specific domain. The canonical JSON registry keeps one stable attack hypothesis per root cause while generated Markdown views remain easy for audit runtimes to consume.

The canonical registry and generated runtime views are validated together; the
registry is authoritative and generated counts are available from the metrics
command.

## Repository Layout

- `skills/` — all directly usable Skill packages; `evm-audit-master` is the default entry point.
- `data/` — canonical security knowledge and runtime feature vocabulary.
- `domains/` — runtime Domain configuration.
- `scripts/` — audit engine and maintenance commands.
- `evm_audit_runtime/` — small pure routing, state, and report decisions shared by the CLIs.
- `schemas/` — runtime artifact schemas.
- `docs/` — architecture and maintenance documentation.
- `development/` — benchmark fixtures; not required for normal audits.
- `tests/` — repository development infrastructure intentionally kept at the root for Python, Foundry, and CI path stability.
- `.github/` — GitHub Actions, which must remain at the repository root.

Domain definitions and relationships live in `domains/*.json`; the generated
[domain catalog](skills/evm-audit-master/references/domains.md) lists every
independently invokable Domain Skill and its current runtime count.

## Knowledge Base

`data/canonical-checks.json` is the single editable source of security-check
knowledge. Generated Skill checklists are derived views and must not be edited
directly.

- [Knowledge architecture](docs/architecture.md)
- [Knowledge maintenance](docs/knowledge-maintenance.md)
- [Knowledge sources and lineage](docs/knowledge-lineage.md)
- [Evidence and verification policy](docs/knowledge-evidence.md)
- [Recon and routing](docs/recon-and-routing.md)
- [Audit runtime](docs/audit-runtime.md)
- [Development and validation](development/README.md)

## Quick Usage

### Run an audit

Just provide the workflow with a contract:

```
audit this contract and file issues: https://github.com/owner/repo/blob/main/contracts/MyContract.sol
```

The workflow will:
1. Load `evm-audit-master` and build a source, dependency, chain, and evidence-backed feature map.
2. Use Slither-backed reconnaissance and the feature-detector registry to emit one immutable routing-v7 manifest; only curated predicates proven false are filtered.
3. Resolve Deferred Domains and required Domain Context from snapshot-bound artifacts before rendering Deep.
4. Render Screen, classify only `NOT_APPLICABLE_CONFIRMED` or `CANDIDATE`, then render Deep from candidates only.
5. Append JSONL Deep/proof events per candidate; revisions retain the full review history and filtered IDs remain only in the machine manifest.
6. Independently derive `audit-state.json`; provide snapshot-bound structured severity/details for confirmed records, then synthesize only `CONFIRMED` records into a final `AUDIT-REPORT.md`.
7. File GitHub issues only for confirmed Medium+ findings when explicitly in scope.

### Runtime-neutral execution

If the runtime supports sub-agents:

- Parallelize independent domain reviews.
- Respect the runtime's concurrency limits.
- Reuse the reconnaissance/source context; do not duplicate source ingestion.
- Use the strongest appropriate available reasoning model.

If sub-agents are unavailable:

- Execute domains sequentially.

## Installation

This repository is a suite, not a collection of independently installable
domain folders. Keep the shared `data/`, `domains/`, `schemas/`, `scripts/`,
and `skills/` together under one installed suite directory. For Codex discovery,
top-level `evm-audit-*` links may point to the matching directory under
`<suite>/skills/`; the packaging smoke test exercises this layout without
modifying the user's installed skills.

See the [Development Guide](development/README.md) for benchmark snapshots,
validation, and reproducibility details.

## Audit Pipeline

```
Contract URL/path
      │
      ▼
  RECON + FEATURE MAP
      │
      ▼
  IMMUTABLE ROUTING (v7 manifest: selected + deferred + filtered IDs)
      │
      ▼
  DEFERRED DOMAIN RESOLUTION → REQUIRED DOMAIN CONTEXT
      │
  SCREEN → CANDIDATE-ONLY DEEP REVIEW (parallel when supported; sequential otherwise)
  ├── candidate domain → review-<skill>.jsonl
  └── filtered IDs remain machine-readable in routing-manifest.json
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

## Audit Output

Each candidate receives one owner-Domain review record, and only `CONFIRMED`
records become findings. See [Audit Runtime](docs/audit-runtime.md) for the
review contract, confirmed finding format, severity rules, and unresolved
review-state requirements.

## License

The repository is licensed under the MIT License in [`LICENSE`](LICENSE). The
root `LICENSE` also preserves the copyright notices for incorporated MIT-licensed
upstream material. Source provenance and pinned upstream revisions are documented
in [`docs/knowledge-lineage.md`](docs/knowledge-lineage.md).
