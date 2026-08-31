# Audit Runtime

Standalone runs create `audits/<repo>-<UTC timestamp>/` and run Recon/Selector
once. Orchestrated Domain agents consume the shared context, immutable manifest,
Screen results, and rendered runtime file without rerunning routing. Each
candidate ID receives one owner-Domain JSONL record and only `CONFIRMED` records
enter synthesis. Runtime Markdown is a generated view with snapshot, registry,
source, compilation-input, profile, and candidate-set hashes; the renderer
validates those identities before reading check bodies. Completion comes from
`validate_audit_run.py`.
