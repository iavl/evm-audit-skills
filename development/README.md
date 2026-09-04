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
- `poc-evidence` is v1; report bundles are v3 with optional `poc_evidence_sha256`. Review records remain v7.
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

The normal PR workflow runs independent test layers in parallel. The layer
boundaries are explicit in [`scripts/run_test_suite.py`](../scripts/run_test_suite.py):

- `fast-unit` covers pure routing, state, schema, reporting, generation, and knowledge checks.
- `controller-reporting-publication` covers E2E report publication/rollback; `controller-reporting-authoring` covers report-input and PoC policy behavior; `controller-lifecycle` covers lifecycle, observation, PoC, ledger, and trust boundaries.
- `slither-integration` covers real Slither/compiler, Recon, code-index, closure, and packaging compatibility.
- `platform-concurrency` covers cross-process locking and publication; Windows runs only this focused layer.

Run one layer locally with:

```bash
python3 scripts/run_fast_tests.py
python3 scripts/run_controller_tests.py
python3 scripts/run_controller_tests.py --shard reporting
python3 scripts/run_controller_tests.py --shard reporting-publication
python3 scripts/run_controller_tests.py --shard reporting-authoring
python3 scripts/run_controller_tests.py --shard lifecycle
python3 scripts/run_slither_tests.py
python3 scripts/run_platform_tests.py
```

The complete local command remains available and discovers the full suite:

```bash
python3 scripts/generate_checklists.py --check
python3 scripts/validate_checklists.py --strict
python3 scripts/run_all_tests.py
git diff --check
```

Each layer reports its test count, elapsed time, and slowest ten tests. The
timing-only baseline tool is [`scripts/test_timing.py`](../scripts/test_timing.py)
and can emit JSON with `--json`.

## Heavy quality validation

The scheduled/manual quality workflow runs the routing quality gate, including
the ordinary benchmark fixtures before the Solidity E2E fixtures:

```bash
python3 scripts/benchmark_routing.py
python3 scripts/benchmark_routing.py --e2e
python3 scripts/benchmark_code_context.py
python3 scripts/knowledge_metrics.py
bash tests/semantics/test_eip6780_differential.sh paris
bash tests/semantics/test_eip6780_differential.sh cancun
```

Benchmark JSONL records include selected/deferred/filtered counts, Screen and
Deep byte sizes, aggregate Domain `SKILL.md` bytes, `routing_recall`, and
`false_negative_cases`. Recall is never traded for prompt reduction: a missing
must-select check fails the fixture before any size result is accepted.

The separate code-context benchmark records exact index/query bytes, selected
nodes, unique and serialized edge counts, unresolved edges, and explicit
truncation flags. The lightweight benchmark also runs in normal Python CI.

The scheduled `knowledge-health.yml` workflow owns freshness/official-source
checks and the base executable semantic suite:

```bash
python3 scripts/check_knowledge_health.py --check-links
forge test --root tests/semantics -vv
```
