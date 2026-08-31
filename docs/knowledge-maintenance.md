# Knowledge Maintenance

This document describes how contributors maintain the canonical security
knowledge base. It is for repository maintenance; normal audits should start
with [`QUICKSTART.md`](../QUICKSTART.md).

## Canonical inputs

[`data/canonical-checks.json`](../data/canonical-checks.json) is the only
editable checklist knowledge source. It is a machine database and should not be
loaded wholesale into model context. Each canonical check keeps one stable
attack hypothesis per root cause and records its Domain, trigger, detection,
false-positive gates, proof obligation, predicate, provenance, verification,
and freshness metadata.

[`domains/*.json`](../domains/) contains Domain taxonomy and methodology.
Feature definitions live in [`data/features.json`](../data/features.json), and
the feature-map input shape is documented by
[`data/feature-map.schema.json`](../data/feature-map.schema.json).

## Generated views and migrations

The generated `references/checklist.md` files, Skill wrappers, and Domain
catalog are derived views. Edit the JSON inputs and run the generator; do not
hand-edit generated runtime views.

The generator is a pure renderer and never repairs or overrides registry
knowledge. One-time schema or knowledge transformations live in
[`development/migrations/`](../development/migrations/); checked-in migrations
have already been applied and are not part of ordinary maintenance.

For the field-level workflow, use [`Adding a Check`](adding-a-check.md). For
source history and external integration policy, use
[`Knowledge Sources and Lineage`](knowledge-lineage.md).

## Predicate maintenance

Each canonical check stores an explicit `all_of` / `any_of` / `none_of`
predicate. Historically keyword-derived predicates are marked `inferred`, and
hand-reviewed combinations are marked `curated`. Predicate filtering semantics
are described in [`Recon and Routing`](recon-and-routing.md). Evidence classes
and freshness requirements are described in [`Knowledge Evidence`](knowledge-evidence.md).

## Validation and reproducibility

The commands, CI split, pinned Python and solc versions, and reproducibility
guidance live in the [`Development Guide`](../development/README.md).
