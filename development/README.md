# Development Guide

This directory is not required for normal audits.

- `benchmarks/` contains routing, runtime-cost, and model-knowledge fixtures for quality and regression evaluation. The runner is [`scripts/benchmark_routing.py`](../scripts/benchmark_routing.py).
- `migrations/` contains historical, one-time canonical-data migrations. Do not run these during a normal audit.
- [`../tests/`](../tests/) contains automated repository verification and remains at the root because Python, Foundry, claims, and CI use those stable paths.

Runtime inputs remain outside this directory: [`../skills/`](../skills/),
[`../data/`](../data/), [`../domains/`](../domains/), and
[`../scripts/`](../scripts/).

Typical checks from the repository root:

```bash
python3 scripts/generate_checklists.py --check
python3 scripts/validate_checklists.py --strict
python3 -m unittest discover -s tests -v
python3 scripts/benchmark_routing.py --e2e
```
