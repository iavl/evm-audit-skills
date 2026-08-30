---
name: evm-audit-master
description: Master index for EVM smart contract security audits. Load this FIRST to route specialized skills and enforce scope-bound evidence, per-check proof, and confirmed-only synthesis.
---
# EVM Smart Contract Security Audit — Master Index

Load this skill first for an EVM audit. Read the target source and deployment
context, run one scope-bound Recon, run one routing-v5 snapshot, delegate only
the selected Domain runtime files, validate every ledger record, then synthesize
only `CONFIRMED` findings. The canonical registry is knowledge input, not model
context.

**Total: 869 canonical checks and 872 generated runtime entries across 19 specialized skills + 1 master index**

## Source of truth

`../data/canonical-checks.json` is the only editable checklist knowledge source.
`../domains/*.json` contains Domain taxonomy and methodology. The generated
`references/checklist.md` files are compatibility/maintenance views. Run
`python3 ../scripts/generate_checklists.py` after editing JSON; the generator
never repairs or infers knowledge. Provenance and source lineage are documented
in `references/sources.md`, `references/auditmos-provenance.md`, and
`references/drozer-lite-provenance.md`.

## Scope-bound Recon and routing

Build a Feature Map v3 over the complete audit root:

```bash
python3 ../scripts/recon.py <target> --audit-root <target-root> \
  --output <run-dir>/recon/feature-map.json
```

The map contains `PRESENT`, `ABSENT_CONFIRMED`, or `UNKNOWN` plus typed evidence
and `recon_context`. `ABSENT_CONFIRMED` is valid only after complete Slither
coverage. The source digest covers the declared Solidity scope; a Selector run
must use the same `--target-root` and exclusions. Feature Map versions other
than v3 are invalid. `UNKNOWN` is always selected. Missing or mismatched scope
data is an error, never a reason to filter.

Route once and write all required artifacts from that snapshot:

```bash
python3 ../scripts/select_checks.py \
  --feature-map <run-dir>/recon/feature-map.json --target-root <target-root> \
  --manifest-out <run-dir>/routing/manifest.json \
  --runtime-dir <run-dir>/runtime --context-out <run-dir>/context.json \
  --chain-id <id> --chain-family <family> \
  --execution-environment <ethereum-evm|eravm-native|zksync-evm-interpreter> \
  --fork-block <block> --compiler-version <version> --evm-fork <fork>
```

Routing v5 has environment, Domain surface, and canonical feature gates.
Domains are `SELECTED`, `DEFERRED`, or `FILTERED`; a Deferred Domain gets only a
screening card and must resolve before clean completion. Checks are visible as
`SELECTED`, `DEFERRED_DOMAIN`, `FILTERED_DOMAIN`, `FILTERED_ENVIRONMENT`, or
`FILTERED_FEATURE`. Related Domains never auto-expand. Only confirmed absence
and confirmed environment mismatch can filter; inferred false results remain.

For ZKsync, always identify the deployed runtime. Native EraVM/
ContractDeployer deployments use ZKsync-specific address derivation, while EVM
Bytecode Interpreter contracts use Ethereum-compatible CREATE/CREATE2 derivation.
Gas, opcode, system-contract, and account-abstraction behavior still require
the selected execution environment and chain documentation.

## Execution modes

### Standalone Domain

Create `audits/<repo>-<UTC timestamp>/` with `context.json`, `recon/`,
`routing/`, `runtime/`, and `reviews/`. Run Recon and Selector exactly once,
then consume screen cards and promote only candidates to deep runtime.

### Orchestrated Domains

Master performs Recon and global routing once. Domain agents receive the shared
context, Feature Map v3, routing manifest, and their
`selected-<domain>.md`. They must not rerun Recon or Selector. Parallelize only
when the active runtime supports it; otherwise execute Domains sequentially.

## Review and synthesis

Use `references/check-review-contract.runtime.md` during a run and retain the
full `references/check-review-contract.md` for maintenance. Every selected
canonical ID receives exactly one owner-Domain record with applicability, code
path, preconditions, exploitability, impact, PoC/invariant evidence, and one of:
`NOT_APPLICABLE`, `REVIEWED_SAFE`, `SUSPICIOUS`, `CONFIRMED`. Filtered IDs stay
in the manifest only.

Do not assign severity to `SUSPICIOUS`. If coverage is missing, duplicated, or
malformed, mark the audit incomplete and do not emit a final report. Synthesis
deduplicates only confirmed records and writes `AUDIT-REPORT.md` containing
`CONFIRMED` findings (or a statement that none were established in scope).
File GitHub issues only for confirmed Medium+ findings when explicitly in scope.

The complete audit flow is:

```text
source → Recon/Feature Map v3 → Environment Gate → Domain Gate → Check Gate
       → selected runtime checks → Domain review → proof → confirmed-only synthesis
```
