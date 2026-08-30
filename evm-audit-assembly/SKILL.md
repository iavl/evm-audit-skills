---
name: evm-audit-assembly
description: Security review for inline assembly, Yul, CREATE2, low-level calls, and EVM opcodes. Consume routed selected-check bodies at runtime.
---
# Assembly and Opcode Security

## Audit Contract
When invoked directly, run the shared pipeline for `evm-audit-assembly` only:

Resolve `<suite-root>` as the parent directory containing this Skill, `data/`, and `scripts/`.

1. Run `python3 <suite-root>/scripts/recon.py <target> --output recon-features.json`.
2. Run `python3 <suite-root>/scripts/select_checks.py --feature-map recon-features.json --domain evm-audit-assembly --format json > routing-manifest.json`.
3. Run `python3 <suite-root>/scripts/select_checks.py --feature-map recon-features.json --domain evm-audit-assembly --emit-checks --profile compact --format markdown > selected-checks.runtime.md`.
4. Read `<suite-root>/evm-audit-master/references/check-review-contract.md`, review only the routed checks, and write `review-evm-audit-assembly.md`.

Do not load `<suite-root>/data/canonical-checks.json` or the full generated checklist into model context. Apply the tri-state predicate router before deep review. Pattern matches are candidates, not findings. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and runnable PoC or deterministic invariant evidence.

Related domains (advisory only; never auto-expand direct scope): `evm-audit-general`, `evm-audit-chain-specific`.

## Maintenance View
- `references/checklist.md` is generated for maintenance and compatibility.
