# Codex Model Profile

This is the default execution profile for Codex-driven EVM audits. Confirm one
profile at audit startup; explicit stage overrides may customize that profile
for the audit.

| Public phase | Default Codex model |
| --- | --- |
| Project Analysis | Luna · Max |
| Context Analysis | Terra · Medium |
| Initial Review | Terra · High |
| Deep Audit | Sol · High |
| Vulnerability Validation | Sol · Max |
| Final Report | Terra · Medium |

Use the defaults unless a stage needs a deliberate model or reasoning
override. The selected profile is stored as
`config/codex-model-profile.json` inside the audit run and must contain every
internal stage ID exactly once. The public phase names group those stable
machine keys for human-readable presentation.

To set defaults for future audits, create and edit
`~/.codex/evm-audit-model-profile.json`:

```bash
python3 scripts/audit_run.py models --init-global
```

`init` copies the validated user-level profile into the run. Later global edits
apply only to new runs; edit the run-scoped copy to change an existing run.
If the user-level file is absent, `init` snapshots the built-in defaults.

The model profile controls model selection only. It does not relax immutable
routing, evidence gates, proof requirements, stale-artifact rejection, or
confirmed-only reporting.

The controller exposes the recommended model and reasoning pair to the
executor; it does not switch the active Codex model.

The machine-readable contract is the
[Codex model profile schema](../schemas/codex-model-profile.schema.json); the
profile validation and default values live in
[`scripts/codex_model_profile.py`](../scripts/codex_model_profile.py).
