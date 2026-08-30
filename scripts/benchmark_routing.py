#!/usr/bin/env python3
"""Check routing recall and runtime-size baselines for fixed feature profiles."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from select_checks import load_domains, load_json, select, selected_markdown, vocabulary
except ImportError:  # pragma: no cover
    from scripts.select_checks import load_domains, load_json, select, selected_markdown, vocabulary


ROOT = Path(__file__).resolve().parents[1]


def profile_map(names: set[str], present: list[str], machine_absent: set[str]) -> dict[str, dict[str, object]]:
    return {
        name: {
            "status": "PRESENT" if name in present else "ABSENT_CONFIRMED" if name in machine_absent else "UNKNOWN",
            "evidence": [{"kind": "manual", "location": "benchmark", "reason": "declared benchmark scope"}],
        }
        for name in sorted(names)
    }


def run_profile(root: Path, fixture: dict[str, object]) -> dict[str, object]:
    registry = load_json(root / "data/canonical-checks.json")
    feature_data = load_json(root / "data/features.json")
    names, _ = vocabulary(feature_data)
    domains = load_domains(root)
    present = fixture.get("detected_features", [])
    if not isinstance(present, list) or any(feature not in names for feature in present):
        raise ValueError(f"invalid detected_features in {fixture.get('name')}")
    scope = fixture.get("domain_scope")
    if not isinstance(scope, list) or not scope:
        raise ValueError(f"domain_scope is required in {fixture.get('name')}")
    manifest, checks = select(
        registry,
        profile_map(names, present, {"uses-assembly", "uses-create2", "uses-delegatecall", "uses-external-call", "uses-low-level-call", "uses-math", "uses-msg-value", "uses-payable", "uses-signed-conversion", "uses-time"}),
        names,
        scope,
        {"selector_version": "benchmark", "registry_sha256": "benchmark", "knowledge_commit": None, "knowledge_dirty": None, "target_repo_commit": None, "source_digest": "benchmark", "chain_id": None, "chain_family": None, "execution_environment": None, "fork_block": None, "compiler_version": None, "evm_fork": None, "protocol_version": None, "audit_timestamp": "benchmark"},
        domains,
        {},
        None,
    )
    selected_ids = [entry["canonical_id"] for entry in manifest["selected"]]
    must_select = fixture.get("must_select_ids", [])
    if not isinstance(must_select, list) or not set(must_select) <= set(selected_ids):
        missing = sorted(set(must_select if isinstance(must_select, list) else []) - set(selected_ids))
        raise ValueError(f"{fixture.get('name')}: must-select IDs missing: {missing}")
    filtered_ids = set(manifest["filtered_out"])
    expected_selected = fixture.get("selected_checks")
    expected_filtered = fixture.get("filtered_checks")
    if expected_selected != len(selected_ids) or expected_filtered != len(filtered_ids):
        raise ValueError(f"{fixture.get('name')}: check counts changed")
    must_not_filter = fixture.get("must_not_filter_ids", [])
    if not isinstance(must_not_filter, list) or filtered_ids & set(must_not_filter):
        raise ValueError(f"{fixture.get('name')}: must-not-filter IDs were filtered: {sorted(filtered_ids & set(must_not_filter))}")
    runtime = selected_markdown(manifest, checks, "compact")
    runtime_bytes = len(runtime.encode("utf-8"))
    expected_bytes = fixture.get("runtime_bytes")
    if not isinstance(expected_bytes, int) or expected_bytes <= 0:
        raise ValueError(f"{fixture.get('name')}: runtime_bytes baseline is required")
    if runtime_bytes > expected_bytes * 1.2:
        raise ValueError(f"{fixture.get('name')}: runtime bytes {runtime_bytes} exceed 20% baseline {expected_bytes}")
    expected_domains = fixture.get("selected_domains")
    actual_domains = [entry["domain"] for entry in manifest["selected_domains"]]
    if expected_domains != actual_domains:
        raise ValueError(f"{fixture.get('name')}: selected_domains changed: {actual_domains} != {expected_domains}")
    return {"name": fixture.get("name"), "selected_domains": actual_domains, "selected_checks": len(selected_ids), "filtered_checks": len(filtered_ids), "runtime_bytes": runtime_bytes}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        results = [run_profile(args.root.resolve(), load_json(path)) for path in sorted((args.root / "benchmarks/routing").glob("*.json"))]
        if not results:
            raise ValueError("no routing benchmark fixtures found")
        for result in results:
            print(f"{result['name']}: domains={','.join(result['selected_domains'])} selected={result['selected_checks']} filtered={result['filtered_checks']} runtime_bytes={result['runtime_bytes']}")
        return 0
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
