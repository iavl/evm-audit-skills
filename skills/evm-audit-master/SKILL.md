---
name: evm-audit-master
description: Master entry point for EVM smart-contract audits. Route once, enforce evidence-bound review, and synthesize only confirmed findings.
---
# EVM Smart Contract Security Audit — Master

Load this Skill first. Resolve `<suite-root>` as the nearest ancestor containing
`data/`, `domains/`, and `scripts/`; the Skill itself is under
`<suite-root>/skills/`.

## Invariants

- `<suite-root>/data/canonical-checks.json` is the only checklist knowledge source. Generated Markdown is a view; do not load the full registry into model context.
- Run Project Analysis (`RECON`, `ROUTING`) once. Preserve `routing_snapshot_id`, `registry_sha256`, `source_digest`, and `compilation_input_digest` across every artifact.
- Project Analysis may emit `recon/code-index.json` as a navigation hint; inspect it first, load only targeted source ranges, and expand callers/callees whenever reachability is uncertain. Source remains authoritative.
- Query only through the run-bound command (`code_context.py --run-dir <run-dir>`); use `--depth 2 --max-nodes 25 --max-edges 200` when a second hop is needed. Treat node/edge truncation and unresolved edges as reasons to verify more source, never as proof of safety.
- `UNKNOWN` is never absence. Only trusted absence or confirmed environment mismatch may filter; Initial Review (`SCREEN`) may emit only `NOT_APPLICABLE_CONFIRMED` or `CANDIDATE`.
- Deep Audit (`DEEP_REVIEW`) consumes only Initial Review candidates. Every candidate needs one owner-Domain append-only JSONL event stream with valid revisions, typed evidence, and a terminal status.
- `SUSPICIOUS` has no severity and must go through a later Vulnerability Validation (`PROOF`) event. Only `CONFIRMED` records enter the Final Report.
- `CONFIRMED` requires strong proof of reachability, satisfiable preconditions, exploitability, and impact. A runnable PoC is a separate reporting requirement: only confirmed `High` and `Critical` findings require one; confirmed `Info`, `Low`, and `Medium` findings remain reportable without it.
- Solidity POC source is user-owned evidence: archive audit-created or modified tests, helpers, and mocks under `<run-dir>/poc/` before proof, record the durable path in `proof` or `evidence.location`, and never delete or overwrite them after `PROOF` or report generation. Do not add new PoC files to the audited target after routing.
- Keep `<run-dir>` as an external sibling of both the audit and build roots. The controller rejects equal or descendant paths, and pipeline outputs cannot overwrite authoritative source/build inputs.

## Audit lifecycle

```text
Project Analysis
  ├─ Recon
  └─ Routing
        ↓
Context Analysis
  ├─ Domain Resolution
  └─ Domain Context
        ↓
Initial Review
        ↓
Deep Audit
        ↓
Vulnerability Validation
        ↓
Final Report
```

Names such as `RECON`, `SCREEN`, and `PROOF` are stable internal identifiers
used by configuration, persisted artifacts, and runtime control flow. The
public phase names above are presentation labels; they do not rename or
migrate those internal IDs.

## Controller

```bash
python3 <suite-root>/scripts/audit_run.py init <target> --run-dir <run-dir> --domain <domain>
python3 <suite-root>/scripts/audit_run.py next --run-dir <run-dir>
python3 <suite-root>/scripts/audit_run.py status --run-dir <run-dir>
python3 <suite-root>/scripts/audit_run.py report --run-dir <run-dir>
python3 <suite-root>/scripts/audit_run.py verify-poc --run-dir <run-dir>
```

The controller emits compact progress to stderr by default. Use `--verbose` to
forward child diagnostics or `--quiet` to suppress normal progress; the flags
are available on `init`, `next`, `status`, and `report`, and are mutually exclusive.

Repeat `next` until it returns a template or Final Report (`REPORT`). Resolve
only generated evidence-bound templates. Deep Audit (`DEEP_REVIEW`) means
candidate records are missing; Vulnerability Validation (`PROOF`) means the
latest record is `SUSPICIOUS` and the controller exposes a suspicious-only
`runtime/proof-<owner-domain>.md` view. `report` re-derives state from
current artifacts and refuses stale, incomplete, or under-specified reporting
inputs. The `--poc-evidence` input is required only when current severity
decisions contain a confirmed `High` or `Critical` finding. The controller
validates its lineage, exact required-ID projection, source paths, and source
hashes; it discovers the current reporting inputs from the run directory and
never runs the recorded command automatically. The explicit
`--severity-decisions`, `--finding-details`, and `--poc-evidence` flags are
advanced overrides; do not add `--poc-evidence` for an all-`Info`/`Low`/`Medium`
report. A historical generation is `CURRENT` only while its exact reporting
inputs still match the current run-directory artifacts.

`verify-poc` is the only command that executes recorded Foundry or Hardhat
commands. It uses a controlled build workspace, structured argv, and
`shell=False`, and writes a non-gating `poc-verification` receipt containing
only execution status and output hashes. `status`, `next`, and `report` never
execute PoC commands.

For `report` and `status` results, consume the paths under
`report_generation` (and the report result's `report`, `issue_candidates`, and
`report_bundle_path`) as authoritative. Top-level `AUDIT-REPORT.md`,
`issue-candidates.json`, and `report-bundle.json` are convenience copies only;
their synchronization status is explicit and a failed copy must not change the
authoritative generation.

## Codex-visible phase progress

Controller stderr is terminal-oriented and may be collapsed by the Codex UI.
After `init`, `next`, `status`, or `report` returns a user-relevant phase,
render compact chat banners from its `progress` and `recommended_execution`
fields before continuing model-owned work. For `init`, render exactly one
banner for each entry in `progress_history`, in order; the first entries are
completed stages and the final entry is the current `next` stage. Do not render
`next` a second time. For the other commands, render one banner from the
returned stage fields.

```text
+----------------------------------------------+
|         EVM AUDIT :: <PHASE NAME>             |
+----------------------------------------------+
  Phase: <step>/<total>
  <summary>
  Model: <model>
  Reasoning: <reasoning_effort>
```

Use only controller-provided phase and counts; never infer them from stderr.
Keep UI-only last-phase state to avoid repeating a banner when no phase
transition occurred, and never persist that state into audit artifacts. Do not
show these banners for internal helper calls such as `recon.py`,
`select_checks.py`, `render_runtime.py`, or `validate_audit_run.py`. The model
recommendation is a handoff, not an automatic active-model switch.

## Codex model policy

For a new Codex audit with no confirmed profile, ask once before starting:

```text
EVM AUDIT :: CODEX MODEL PROFILE
Project Analysis: gpt-5.6-luna max
Context Analysis: gpt-5.6-terra medium
Initial Review: gpt-5.6-terra high
Deep Audit: gpt-5.6-sol high
Vulnerability Validation: gpt-5.6-sol max
Final Report: gpt-5.6-terra medium

Use this default profile?
1. Use defaults
2. Customize
```

If `~/.codex/evm-audit-model-profile.json` exists, display that validated
user-level profile in this prompt instead of the built-in table. On confirmation
the controller snapshots the selected values into the run.
Use the user-level default at `~/.codex/evm-audit-model-profile.json` when it
exists; `python3 <suite-root>/scripts/audit_run.py models --init-global`
creates it once with canonical defaults. For confirmation, use
`--accept-default-models`, or build one validated profile with selective stage
edits and pass it with `--model-profile`. Persist the resolved choice in
`<run-dir>/config/codex-model-profile.json`; once present, do not ask again.
For customization, show the full current profile once and accept only changed
lines such as `SCREEN = gpt-5.6-sol/high`, preserving omitted internal stages.
At each transition, follow `recommended_execution`. This is a handoff only:
do not claim an active Codex model switch unless a documented runtime mechanism
actually provides one. The profile is execution metadata and never security
lineage or artifact identity.

## Model decisions

The model may choose the audit scope, provide evidence-backed environment and
Domain resolutions, complete required context, classify Initial Review cards,
write Deep Audit/Vulnerability Validation records, and assign structured
severity plus reporting details after confirmation. It may parallelize independent Domain work only when the active
runtime supports it; otherwise use sequential execution.

The model must not treat pattern matches as findings, turn `UNKNOWN` into
absence, rerun routing in a Domain Skill, assign severity to `SUSPICIOUS`, or
emit a Final Report from missing/malformed coverage. Do not proactively build
Foundry or Hardhat exploit tests for `Info`, `Low`, or `Medium` findings after
strong proof is otherwise sufficient. Build the smallest deterministic
runnable PoC after severity for `High` and `Critical`; if a reproduction is
needed to establish correctness, keep the finding `SUSPICIOUS` until it is
available. Filing GitHub issues is separate and requires explicit scope; only
confirmed Medium+ findings qualify.

Apply the compact review contract at
`<suite-root>/skills/evm-audit-master/references/check-review-contract.runtime.md`.
Use [`docs/audit-runtime.md`](../../docs/audit-runtime.md) for low-level CLI,
artifact schema, and report-format details.
