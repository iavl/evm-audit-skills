# Recon and Routing

Run Recon against the complete audit root. Its Feature Map v4 records the
scope digest, compilation-input digest, compilation coverage, analyzed files,
tool versions, and a scope-bound `recon_context`. The map uses
`PRESENT`, `ABSENT_CONFIRMED`, or `UNKNOWN`.

Selector rejects a missing, incomplete, or mismatched scope before filtering.
`UNKNOWN` remains selected. `ABSENT_CONFIRMED` is valid only after complete
Slither coverage and acceptable typed evidence. Evidence for confirmed states
uses `kind`, `location`, and `reason`; absence is accepted only when the
feature's `absence_policy` allows that evidence kind.

## Recon

Build the initial Feature Map from Slither's AST/IR, then supplement remaining
`UNKNOWN` features from deployment evidence:

```bash
python3 scripts/recon.py <target-project-or-solidity-file> --audit-root <target-repo> \
  --output recon-features.json
```

## Routing

Routing v6 applies environment, Domain, and canonical feature gates. Domains
are `SELECTED`, `DEFERRED`, or `FILTERED`; an `UNKNOWN` Domain is Deferred with
a small screening card, and only confirmed absence or confirmed environment
mismatch can filter. Related Domains never auto-expand.

```bash
python3 scripts/select_checks.py --feature-map recon-features.json --target-root <target-repo> \
  --chain-id <id> --chain-family <family> --execution-environment <environment> \
  --fork-block <block> --compiler-version <version> --evm-fork <fork> \
  --manifest-out routing/manifest.json --context-out context.json \
  --environment-out routing/environment-context.json \
  --format json
```

The v6 manifest records selected, Deferred, and filtered Domain/check stages;
registry, source, dependency, build-config, and compilation fingerprints; and
evidence-backed environment facts. `fork_block` is reproducibility metadata,
not hardfork inference.

Canonical predicates use `all_of` / `any_of` / `none_of`. Only a curated
predicate can filter on `FALSE`; an inferred `FALSE` becomes `UNKNOWN` and
remains selected. This allows keyword inference to improve recall without
proving non-applicability.

The manifest is immutable; `render_runtime.py` never re-runs routing. Screen
cards can promote candidates to Deep Review but never filter uncertainty.
Deferred Domain resolution and `screen-results.json` are separately evidenced
artifacts.
