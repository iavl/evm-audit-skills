---
name: evm-audit-assembly
description: Security review for inline assembly, Yul, CREATE2, low-level calls, and EVM opcodes. Consume routed selected-check bodies at runtime.
---
# Assembly and Opcode Security

## Runtime Modes

Resolve `<suite-root>` as the parent directory containing this Skill, `data/`, and `scripts/`.

### Standalone

When invoked directly, create `audits/<repo>-<UTC timestamp>/` with `recon/`, `routing/`, `runtime/`, and `reviews/`, then run the shared pipeline for `evm-audit-assembly` once:

1. `python3 <suite-root>/scripts/recon.py <target> --audit-root <target-root> --output <run-dir>/recon/feature-map.json`
2. `python3 <suite-root>/scripts/select_checks.py --feature-map <run-dir>/recon/feature-map.json --target-root <target-root> --domain evm-audit-assembly --profile screen --manifest-out <run-dir>/routing/manifest.json --checks-out <run-dir>/runtime/screen-evm-audit-assembly.md --context-out <run-dir>/context.json`
3. Classify screen cards as `NOT_APPLICABLE`, `LIKELY_SAFE`, or `CANDIDATE`. Uncertain cards are `CANDIDATE`; Screen never filters.
4. Load only candidates with `--profile deep --candidate-ids <ids>` and apply `<suite-root>/evm-audit-master/references/check-review-contract.runtime.md`.

### Orchestrated

When Master supplies `context.json`, the Feature Map v3, routing manifest, and `selected-evm-audit-assembly.md`, consume those artifacts directly. Never rerun Recon or Selector in orchestrated mode.

## Required Context

- `compiler_target_and_assembly_call_sites`: compiler target and assembly call sites

## Domain Review Requirements

- compare Yul/EVM behavior with the selected runtime

Do not load `<suite-root>/data/canonical-checks.json` or the full generated checklist into model context. Apply the tri-state predicate router before deep review. Pattern matches are candidates, not findings. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and runnable PoC or deterministic invariant evidence.

Related domains (advisory only; never auto-expand direct scope): `evm-audit-general`, `evm-audit-chain-specific`.

## Maintenance View
- `references/checklist.md` is generated for maintenance and compatibility.
