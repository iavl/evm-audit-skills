"""Routing benchmark fixture validation."""

from __future__ import annotations

from pathlib import Path

try:
    from audit_artifacts import validate_schema
    from generate_checklists import load_registry
except ImportError:  # pragma: no cover
    from scripts.audit_artifacts import validate_schema
    from scripts.generate_checklists import load_registry


def validate_benchmark_fixtures(root: Path) -> list[str]:
    errors: list[str] = []
    benchmark_root = root / "development" / "benchmarks" / "routing"
    flat = sorted(benchmark_root.glob("*.json"))
    if flat:
        errors.append("routing benchmark fixtures must be under automatic/ or explicit/")
    for mode in ("automatic", "explicit"):
        for path in sorted((benchmark_root / mode).glob("*.json")):
            try:
                validate_schema(root, "benchmark-routing-fixture.schema.json", load_registry(path))
            except (OSError, ValueError):
                errors.append(f"{path}: invalid benchmark fixture")
    return errors
