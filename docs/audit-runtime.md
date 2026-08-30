# Audit Runtime

Standalone runs create `audits/<repo>-<UTC timestamp>/` and run Recon/Selector
once. Orchestrated Domain agents consume the shared context, manifest, and
selected runtime file without rerunning either tool. Each selected ID receives
one owner-Domain ledger record and only `CONFIRMED` records enter synthesis.
