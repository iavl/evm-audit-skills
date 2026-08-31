# Development Guide

This directory is not required for normal audits.

- `benchmarks/` contains routing, runtime-cost, and model-knowledge fixtures for quality and regression evaluation. The runner is [`scripts/benchmark_routing.py`](../scripts/benchmark_routing.py).
- `migrations/` contains historical, one-time canonical-data migrations. Do not run these during a normal audit.
- [`../tests/`](../tests/) contains automated repository verification and remains at the root because Python, Foundry, claims, and CI use those stable paths.

Runtime inputs remain outside this directory: [`../skills/`](../skills/),
[`../data/`](../data/), [`../domains/`](../domains/), and
[`../scripts/`](../scripts/).

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

The scheduled `knowledge-health.yml` workflow owns freshness/official-source
checks and the base executable semantic suite:

```bash
python3 scripts/check_knowledge_health.py --check-links
forge test --root tests/semantics -vv
```
