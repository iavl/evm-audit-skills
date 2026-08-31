---
name: evm-audit-defi-lending
description: Security review for lending, borrowing, collateral, liquidation, and CDP protocols. Consume routed selected-check bodies at runtime.
---
# Lending and Liquidation Security

## Runtime Modes

Resolve `<suite-root>` as the nearest ancestor containing `data/`, `domains/`, and `scripts/`. It is the repository root, not the `skills/` directory.

### Standalone

When invoked directly, create `audits/<repo>-<UTC timestamp>/` with `recon/`, `routing/`, `runtime/`, and `reviews/`, then run the shared pipeline for `evm-audit-defi-lending` once:

1. `python3 <suite-root>/scripts/recon.py <target> --audit-root <target-root> --output <run-dir>/recon/feature-map.json`
2. `python3 <suite-root>/scripts/select_checks.py --feature-map <run-dir>/recon/feature-map.json --target-root <target-root> --domain evm-audit-defi-lending --manifest-out <run-dir>/routing/manifest.json --context-out <run-dir>/context.json --environment-out <run-dir>/routing/environment-context.json`
3. `python3 <suite-root>/scripts/render_runtime.py --manifest <run-dir>/routing/manifest.json --profile screen --owner-domain evm-audit-defi-lending --output <run-dir>/runtime/screen-evm-audit-defi-lending.md --domain-resolution-out <run-dir>/reviews/domain-resolution.json`
4. Resolve `domain-resolution.json`; rerun Screen with `--domain-resolution <run-dir>/reviews/domain-resolution.json --domain-context-out <run-dir>/reviews/domain-context.json --output <run-dir>/runtime/screen-evm-audit-defi-lending.md`.
5. Resolve `domain-context.json`; rerun Screen with `--domain-resolution <run-dir>/reviews/domain-resolution.json --domain-context <run-dir>/reviews/domain-context.json --screen-results-out <run-dir>/reviews/screen-results.json --output <run-dir>/runtime/screen-evm-audit-defi-lending.md`.
6. Classify every Screen card as `NOT_APPLICABLE_CONFIRMED` or `CANDIDATE`; uncertainty is always `CANDIDATE` and Screen never filters.
7. `python3 <suite-root>/scripts/render_runtime.py --manifest <run-dir>/routing/manifest.json --profile deep --domain-resolution <run-dir>/reviews/domain-resolution.json --domain-context <run-dir>/reviews/domain-context.json --screen-results <run-dir>/reviews/screen-results.json --owner-domain evm-audit-defi-lending --output <run-dir>/runtime/deep-evm-audit-defi-lending.md`
8. Write one JSONL record per candidate with `review_ledger.py`, then derive `audit-state.json` with `validate_audit_run.py --manifest <run-dir>/routing/manifest.json --context <run-dir>/context.json --domain-resolution <run-dir>/reviews/domain-resolution.json --domain-context <run-dir>/reviews/domain-context.json --screen-results <run-dir>/reviews/screen-results.json --ledger <run-dir>/reviews/review-evm-audit-defi-lending.jsonl --output <run-dir>/audit-state.json`.

### Orchestrated

When Master supplies `context.json`, the immutable routing manifest, Screen results, and `screen-evm-audit-defi-lending.md`, consume those artifacts directly. Never rerun Recon or Selector in orchestrated mode.

## Required Context

- `oracle_configuration_collateral_parameters_caps_liquidations_and`: oracle configuration, collateral parameters, caps, liquidations, and interest model

Deferred Domain absence may be marked `ABSENT_CONFIRMED` only with complete
scope evidence accepted by this Domain's trusted-absence policy. Required
Domain Context is a separate snapshot-bound artifact; required `UNKNOWN`
context blocks Deep and completion.

## Domain Review Requirements

- model solvency, bad debt, and liquidation economics

Do not load `<suite-root>/data/canonical-checks.json` or the full generated checklist into model context. Apply the tri-state predicate router before deep review. Pattern matches are candidates, not findings. A Screen or Deep `NOT_APPLICABLE` disposition requires complete scope evidence plus evidence for the relevant exclusion dimension; uncertainty remains a candidate or `SUSPICIOUS`. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and runnable PoC or deterministic invariant evidence.
Apply `<suite-root>/skills/evm-audit-master/references/check-review-contract.runtime.md` to every Deep review record.

Related domains (advisory only; never auto-expand direct scope): `evm-audit-precision-math`, `evm-audit-erc20`, `evm-audit-oracles`.

## Maintenance View
- `references/checklist.md` is a generated human-readable reference view.
