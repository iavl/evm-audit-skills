---
name: evm-audit-governance
description: Security review for governance, voting, proposals, timelocks, and treasury control. Consume routed selected-check bodies at runtime.
---
# Governance and DAO Security

## Runtime Modes

Resolve `<suite-root>` as the nearest ancestor containing `data/`, `domains/`, and `scripts/`. It is the repository root, not the `skills/` directory.

### Standalone

When invoked directly, create `audits/<repo>-<UTC timestamp>/` with `recon/`, `routing/`, `runtime/`, and `reviews/`, then run the shared pipeline for `evm-audit-governance` once:

1. `python3 <suite-root>/scripts/recon.py <target> --audit-root <target-root> --output <run-dir>/recon/feature-map.json`
2. `python3 <suite-root>/scripts/select_checks.py --feature-map <run-dir>/recon/feature-map.json --target-root <target-root> --domain evm-audit-governance --manifest-out <run-dir>/routing/manifest.json --context-out <run-dir>/context.json --environment-out <run-dir>/routing/environment-context.json`
3. `python3 <suite-root>/scripts/render_runtime.py --manifest <run-dir>/routing/manifest.json --profile screen --owner-domain evm-audit-governance --output <run-dir>/runtime/screen-evm-audit-governance.md --domain-resolution-out <run-dir>/reviews/domain-resolution.json`
4. Resolve `domain-resolution.json`; then rerun Screen with `--domain-resolution <run-dir>/reviews/domain-resolution.json --screen-results-out <run-dir>/reviews/screen-results.json --output <run-dir>/runtime/screen-evm-audit-governance.md`.
5. Classify every Screen card as `NOT_APPLICABLE_CONFIRMED` or `CANDIDATE`; uncertainty is always `CANDIDATE` and Screen never filters.
6. `python3 <suite-root>/scripts/render_runtime.py --manifest <run-dir>/routing/manifest.json --profile deep --domain-resolution <run-dir>/reviews/domain-resolution.json --screen-results <run-dir>/reviews/screen-results.json --owner-domain evm-audit-governance --output <run-dir>/runtime/deep-evm-audit-governance.md`
7. Write one JSONL record per candidate with `review_ledger.py`, then derive `audit-state.json` with `validate_audit_run.py`.

### Orchestrated

When Master supplies `context.json`, the immutable routing manifest, Screen results, and `screen-evm-audit-governance.md`, consume those artifacts directly. Never rerun Recon or Selector in orchestrated mode.

## Required Context

- `voting_power_quorum_timelock_proposal_and_execution_model`: voting power, quorum, timelock, proposal, and execution model

Deferred Domain absence may be marked `ABSENT_CONFIRMED` only with complete
scope evidence accepted by this Domain's trusted-absence policy.

## Domain Review Requirements

- trace proposal creation through execution and cancellation

Do not load `<suite-root>/data/canonical-checks.json` or the full generated checklist into model context. Apply the tri-state predicate router before deep review. Pattern matches are candidates, not findings. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and runnable PoC or deterministic invariant evidence.
Apply `<suite-root>/skills/evm-audit-master/references/check-review-contract.runtime.md` to every Deep review record.

Related domains (advisory only; never auto-expand direct scope): `evm-audit-access-control`, `evm-audit-flashloans`.

## Maintenance View
- `references/checklist.md` is a generated human-readable reference view.
