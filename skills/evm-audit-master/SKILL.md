---
name: evm-audit-master
description: Master index for EVM smart contract security audits. Load this FIRST to route specialized skills and enforce scope-bound evidence, per-check proof, and confirmed-only synthesis.
---
# EVM Smart Contract Security Audit — Master Index

Load this skill first for an EVM audit. Read the target source and deployment
context, run one scope-bound Recon, run one immutable routing-v7 snapshot, delegate only
the selected Domain runtime files, validate every ledger record, then synthesize
only `CONFIRMED` findings. The canonical registry is knowledge input, not model
context.

Resolve `<suite-root>` as the nearest ancestor of this Skill containing
`data/`, `domains/`, and `scripts/`. The Skill is nested under
`<suite-root>/skills/`; do not treat `skills/` as the suite root.

## Source of truth

`<suite-root>/data/canonical-checks.json` is the only editable checklist knowledge source.
`<suite-root>/domains/*.json` contains Domain taxonomy and methodology. The generated
`references/checklist.md` files are generated human-readable reference views. Run
`python3 <suite-root>/scripts/generate_checklists.py` after editing JSON; the generator
never repairs or infers knowledge. Repository-level source lineage is documented
in `<suite-root>/docs/knowledge-lineage.md`; per-source provenance maps remain in
`references/auditmos-provenance.md` and `references/drozer-lite-provenance.md`.

## Scope-bound Recon and routing

Build a Feature Map v4 over the complete audit root:

```bash
python3 <suite-root>/scripts/recon.py <target> --audit-root <target-root> \
  --output <run-dir>/recon/feature-map.json
```

The map contains `PRESENT`, `ABSENT_CONFIRMED`, or `UNKNOWN` plus typed evidence
and `recon_context`. `recon_quality.mode` explicitly records complete versus
conservative degraded compilation coverage. `ABSENT_CONFIRMED` is valid only
after complete Slither coverage. The source digest covers the declared Solidity
scope; a Selector run must use the same `--target-root` and exclusions. Feature
Map versions other than v4 are invalid. `UNKNOWN` is always selected. Missing
or mismatched scope data is an error, never a reason to filter.

Route once and write the immutable manifest and context from that snapshot. On
imperfect repositories, degraded Recon remains conservative by default; add
`--require-complete-compilation` when fail-fast behavior is required:

```bash
python3 <suite-root>/scripts/select_checks.py \
  --feature-map <run-dir>/recon/feature-map.json --target-root <target-root> \
  --manifest-out <run-dir>/routing/manifest.json \
  --context-out <run-dir>/context.json \
  --environment-out <run-dir>/routing/environment-context.json \
  --chain-id <id> --chain-family <family> \
  --execution-environment <ethereum-evm|eravm-native|zksync-evm-interpreter> \
  --fork-block <block> --compiler-version <version> --evm-fork <fork>
```

For a deterministic standalone run, use the controller after choosing the
target and Domain:

```bash
python3 <suite-root>/scripts/audit_run.py init <target> --run-dir <run-dir> --domain <domain>
python3 <suite-root>/scripts/audit_run.py next --run-dir <run-dir>
```

Routing v7 has environment, Domain surface, and canonical feature gates.
Domains are `SELECTED`, `DEFERRED`, or `FILTERED`; a Deferred Domain gets only a
screening card and must resolve before clean completion. Checks are visible as
`SELECTED`, `DEFERRED_DOMAIN`, `FILTERED_DOMAIN`, `FILTERED_ENVIRONMENT`, or
`FILTERED_FEATURE`. Related Domains never auto-expand. Only confirmed absence
and confirmed environment mismatch can filter; inferred false results remain.

Render the initial Domain-resolution template, resolve it, create the
snapshot-bound Domain Context template, resolve required context, then render
Screen and Deep:

```bash
python3 <suite-root>/scripts/render_runtime.py --manifest <run-dir>/routing/manifest.json \
  --profile screen --output <run-dir>/runtime/screen.md \
  --domain-resolution-out <run-dir>/reviews/domain-resolution.json
python3 <suite-root>/scripts/render_runtime.py --manifest <run-dir>/routing/manifest.json \
  --profile screen --domain-resolution <run-dir>/reviews/domain-resolution.json \
  --domain-context-out <run-dir>/reviews/domain-context.json --output <run-dir>/runtime/screen.md
python3 <suite-root>/scripts/render_runtime.py --manifest <run-dir>/routing/manifest.json \
  --profile screen --domain-resolution <run-dir>/reviews/domain-resolution.json \
  --domain-context <run-dir>/reviews/domain-context.json \
  --output <run-dir>/runtime/screen.md --screen-results-out <run-dir>/reviews/screen-results.json
python3 <suite-root>/scripts/render_runtime.py --manifest <run-dir>/routing/manifest.json \
  --profile deep --domain-resolution <run-dir>/reviews/domain-resolution.json \
  --domain-context <run-dir>/reviews/domain-context.json \
  --screen-results <run-dir>/reviews/screen-results.json --output <run-dir>/runtime/deep.md
```

For ZKsync, always identify the deployed runtime. Native EraVM/
ContractDeployer deployments use ZKsync-specific address derivation, while EVM
Bytecode Interpreter contracts use Ethereum-compatible CREATE/CREATE2 derivation.
Gas, opcode, system-contract, and account-abstraction behavior still require
the selected execution environment and chain documentation.

## Execution modes

### Standalone Domain

Create `audits/<repo>-<UTC timestamp>/` with `context.json`, `recon/`,
`routing/`, `runtime/`, and `reviews/`. Run Recon and Selector exactly once.
Resolve Deferred Domains and required Domain Context, render Screen, and render
Deep only from the Screen `CANDIDATE` set.

### Orchestrated Domains

Master performs Recon and global routing once. Domain agents receive the shared
context, Feature Map v4, immutable routing manifest, Domain Context, Screen results, and their
`screen-<domain>.md`. They must not rerun Recon, Selector, or Domain routing. Parallelize only
when the active runtime supports it; otherwise execute Domains sequentially.

## Review and synthesis

Use `references/check-review-contract.runtime.md` during a run and retain the
full `references/check-review-contract.md` for maintenance. Every Screen
candidate receives an owner-Domain event stream with contiguous revisions,
applicability, code path, preconditions, exploitability, impact, PoC/invariant
evidence, and one of:
`NOT_APPLICABLE`, `REVIEWED_SAFE`, `SUSPICIOUS`, `CONFIRMED`. Filtered IDs stay
in the manifest only.

Do not assign severity to `SUSPICIOUS`. If coverage is missing, duplicated, or
malformed, mark the audit `INCOMPLETE_*` and do not emit a final report.
Synthesis writes `AUDIT-REPORT.md` containing only `CONFIRMED` findings (or a
complete-clean statement that none were established in scope).
File GitHub issues only for confirmed Medium+ findings when explicitly in scope.

Derive completion independently with:

```bash
python3 <suite-root>/scripts/validate_audit_run.py \
  --manifest <run-dir>/routing/manifest.json \
  --context <run-dir>/context.json \
  --screen-results <run-dir>/reviews/screen-results.json \
  --domain-resolution <run-dir>/reviews/domain-resolution.json \
  --domain-context <run-dir>/reviews/domain-context.json \
  --ledger <run-dir>/reviews/review-<owner-domain>.jsonl \
  --output <run-dir>/audit-state.json
```

The complete audit flow is:

```text
source → Recon/Feature Map v4 → Environment Gate → Domain Gate → Check Gate
       → Deferred Domain Resolution → Required Domain Context → Screen
       → candidate-only Deep → proof → independently derived state → confirmed-only synthesis
```
