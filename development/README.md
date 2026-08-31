# Development Guide

This directory is not required for normal audits.

- `benchmarks/` contains routing, runtime-cost, and model-knowledge fixtures for quality and regression evaluation. Routing fixtures follow [`schemas/benchmark-routing-fixture.schema.json`](../schemas/benchmark-routing-fixture.schema.json) and live under `benchmarks/routing/automatic/` or `benchmarks/routing/explicit/`. The runner is [`scripts/benchmark_routing.py`](../scripts/benchmark_routing.py).
- [`../tests/`](../tests/) contains automated repository verification and remains at the root because Python, Foundry, claims, and CI use those stable paths.

## Versioning policy

This repository is forward-only while it is under active development.

- `main` defines the only supported schema and runtime contract.
- Old audit artifacts are rejected.
- Old CLI aliases are not preserved.
- Canonical data is updated in place.
- Schema changes update code, data, tests, and docs atomically; unsupported artifacts must be regenerated.
- Unsupported schema versions fail fast and must be regenerated.

Runtime inputs remain outside this directory: [`../skills/`](../skills/),
[`../data/`](../data/), [`../domains/`](../domains/), and
[`../scripts/`](../scripts/).

## Reproducibility and pinned tools

The pinned Python runtime roots are listed in
[`../requirements-runtime.txt`](../requirements-runtime.txt), with the
resolved snapshot in [`../requirements-runtime.lock`](../requirements-runtime.lock).
CI uses Python 3.12 and the pinned compiler in
[`../solc-version.txt`](../solc-version.txt). Model-specific
`known/partial/novel` snapshots are retained only under
`benchmarks/model-knowledge/`; they are not runtime inputs.

Knowledge source history and external integration policy are documented in
[`../docs/knowledge-lineage.md`](../docs/knowledge-lineage.md). Canonical
registry editing rules are in
[`../docs/knowledge-maintenance.md`](../docs/knowledge-maintenance.md).

## Core PR validation

The normal PR workflow runs the fast repository and runtime contracts. It
installs Slither and solc because the Recon and packaging smoke tests use them;
it does not install Foundry.

```bash
python3 scripts/generate_checklists.py --check
python3 scripts/validate_checklists.py --strict
python3 -m unittest discover -s tests -v
git diff --check
```

## Heavy quality validation

The scheduled/manual quality workflow runs the routing quality gate, including
the ordinary benchmark fixtures before the Solidity E2E fixtures:

```bash
python3 scripts/benchmark_routing.py
python3 scripts/benchmark_routing.py --e2e
python3 scripts/knowledge_metrics.py
bash tests/semantics/test_eip6780_differential.sh paris
bash tests/semantics/test_eip6780_differential.sh cancun
```

Benchmark JSONL records include selected/deferred/filtered counts, Screen and
Deep byte sizes, aggregate Domain `SKILL.md` bytes, `routing_recall`, and
`false_negative_cases`. Recall is never traded for prompt reduction: a missing
must-select check fails the fixture before any size result is accepted.

The scheduled `knowledge-health.yml` workflow owns freshness/official-source
checks and the base executable semantic suite:

```bash
python3 scripts/check_knowledge_health.py --check-links
forge test --root tests/semantics -vv
```
