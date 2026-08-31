---
name: evm-audit-erc4337
description: Security review for ERC4337 wallets, paymasters, bundlers, and account-abstraction infrastructure. Consume routed selected-check bodies at runtime.
---
# ERC4337 Account Abstraction Security

## Runtime Modes

Resolve `<suite-root>` as the nearest ancestor containing `data/`, `domains/`, and `scripts/`. It is the repository root, not the `skills/` directory.

### Standalone

When invoked directly, create `audits/<repo>-<UTC timestamp>/` with `recon/`, `routing/`, `runtime/`, and `reviews/`, then run the shared pipeline for `evm-audit-erc4337` once:

1. `python3 <suite-root>/scripts/recon.py <target> --audit-root <target-root> --output <run-dir>/recon/feature-map.json`
2. `python3 <suite-root>/scripts/select_checks.py --feature-map <run-dir>/recon/feature-map.json --target-root <target-root> --domain evm-audit-erc4337 --manifest-out <run-dir>/routing/manifest.json --context-out <run-dir>/context.json --environment-out <run-dir>/routing/environment-context.json`
3. `python3 <suite-root>/scripts/render_runtime.py --manifest <run-dir>/routing/manifest.json --profile screen --owner-domain evm-audit-erc4337 --output <run-dir>/runtime/screen-evm-audit-erc4337.md --domain-resolution-out <run-dir>/reviews/domain-resolution.json`
4. Resolve `domain-resolution.json`; then rerun Screen with `--domain-resolution <run-dir>/reviews/domain-resolution.json --screen-results-out <run-dir>/reviews/screen-results.json --output <run-dir>/runtime/screen-evm-audit-erc4337.md`.
5. Classify every Screen card as `NOT_APPLICABLE_CONFIRMED` or `CANDIDATE`; uncertainty is always `CANDIDATE` and Screen never filters.
6. `python3 <suite-root>/scripts/render_runtime.py --manifest <run-dir>/routing/manifest.json --profile deep --domain-resolution <run-dir>/reviews/domain-resolution.json --screen-results <run-dir>/reviews/screen-results.json --owner-domain evm-audit-erc4337 --output <run-dir>/runtime/deep-evm-audit-erc4337.md`
7. Write one JSONL record per candidate with `review_ledger.py`, then derive `audit-state.json` with `validate_audit_run.py`.

### Orchestrated

When Master supplies `context.json`, the immutable routing manifest, Screen results, and `screen-evm-audit-erc4337.md`, consume those artifacts directly. Never rerun Recon or Selector in orchestrated mode.

## Required Context

- `entrypoint_version_account_modules_paymasters_and_bundler_assump`: EntryPoint version, account modules, paymasters, and bundler assumptions

Deferred Domain absence may be marked `ABSENT_CONFIRMED` only with complete
scope evidence accepted by this Domain's trusted-absence policy.

## Domain Review Requirements

- trace validation, replay, prefund, and execution boundaries

Do not load `<suite-root>/data/canonical-checks.json` or the full generated checklist into model context. Apply the tri-state predicate router before deep review. Pattern matches are candidates, not findings. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and runnable PoC or deterministic invariant evidence.
Apply `<suite-root>/skills/evm-audit-master/references/check-review-contract.runtime.md` to every Deep review record.

Related domains (advisory only; never auto-expand direct scope): `evm-audit-signatures`, `evm-audit-access-control`.

## Maintenance View
- `references/checklist.md` is generated for maintenance and compatibility.
