#!/usr/bin/env python3
"""Benchmark normalized production routing for explicit and automatic scopes."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from scope_context import compilation_digests, scope_inventory
    from select_checks import audit_context, load_domains, load_json, normalize_feature_map, select, selected_markdown, vocabulary
except ImportError:  # pragma: no cover
    from scripts.scope_context import compilation_digests, scope_inventory
    from scripts.select_checks import audit_context, load_domains, load_json, normalize_feature_map, select, selected_markdown, vocabulary


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_TARGET = ROOT / "tests/fixtures/recon/Empty.sol"


def recon_context(target: Path) -> dict[str, object]:
    files, excluded = scope_inventory(target)
    digests = compilation_digests(target, files, "0.8.24")
    return {
        "target_root": str(target.resolve()), "files_analyzed": files,
        "excluded_paths": excluded, "exclusion_patterns": [], "uncompiled_paths": [],
        "source_digest": digests["audit_source_digest"], **digests, "compilation_complete": True,
        "slither_version": "benchmark", "solc_version": "0.8.24",
    }


def feature_map(names: set[str], policies: dict[str, dict[str, object]], present: list[str], absent: list[str]) -> dict[str, object]:
    entries: dict[str, object] = {}
    for name in sorted(names):
        status = "PRESENT" if name in present else "ABSENT_CONFIRMED" if name in absent else "UNKNOWN"
        evidence = []
        if status != "UNKNOWN":
            allowed = policies[name]["allowed_absence_evidence"] if status == "ABSENT_CONFIRMED" else ["manual"]
            kind = allowed[0] if allowed else "manual"
            evidence = [{"kind": kind, "location": "benchmark", "reason": "declared benchmark scope"}]
        entries[name] = {"status": status, "evidence": evidence}
    return {"schema_version": 3, "recon_context": recon_context(SYNTHETIC_TARGET), "features": entries}


def _domains(manifest: dict[str, object], bucket: str) -> list[str]:
    return [entry["domain"] for entry in manifest[bucket]]  # type: ignore[index]


def run_profile(root: Path, fixture: dict[str, object]) -> dict[str, object]:
    registry = load_json(root / "data/canonical-checks.json")
    names, policies = vocabulary(load_json(root / "data/features.json"))
    domains = load_domains(root)
    present, absent = fixture.get("detected_features", []), fixture.get("absent_features", [])
    if not isinstance(present, list) or not isinstance(absent, list) or not set(present + absent) <= names:
        raise ValueError(f"invalid features in {fixture.get('name')}")
    raw_map = feature_map(names, policies, present, absent)
    normalized = normalize_feature_map(raw_map, names, policies, SYNTHETIC_TARGET)
    scope = fixture.get("domain_scope")
    if scope is not None and (not isinstance(scope, list) or not scope):
        raise ValueError(f"domain_scope must be a non-empty list in {fixture.get('name')}")
    context = audit_context(root, registry, raw_map["recon_context"], target_root=SYNTHETIC_TARGET, audit_timestamp="benchmark")
    environment = {**{key: context[key] for key in ("chain_id", "chain_family", "execution_environment", "compiler_version", "evm_fork", "protocol_version")}, "environment_facts": context["environment_facts"]}
    manifest, checks = select(registry, normalized, names, scope, context, domains, environment, raw_map["recon_context"])

    selected_ids = {entry["canonical_id"] for entry in manifest["selected"]}
    deferred_ids = {entry["canonical_id"] for entry in manifest["deferred"]}
    filtered_ids = {entry["canonical_id"] for entry in manifest["filtered"]}
    must_select = set(fixture.get("must_select_checks", fixture.get("must_select_ids", [])))
    must_not_filter = set(fixture.get("must_not_filter_checks", fixture.get("must_not_filter_ids", [])))
    if not must_select <= selected_ids:
        raise ValueError(f"{fixture.get('name')}: must-select checks missing: {sorted(must_select - selected_ids)}")
    if must_not_filter & filtered_ids:
        raise ValueError(f"{fixture.get('name')}: must-not-filter checks filtered: {sorted(must_not_filter & filtered_ids)}")

    selected_domains = _domains(manifest, "selected_domains")
    deferred_domains = _domains(manifest, "deferred_domains")
    filtered_domains = _domains(manifest, "filtered_domains")
    expected = fixture.get("selected_domains", fixture.get("must_select_domains"))
    if expected is not None and not set(expected) <= set(selected_domains):
        raise ValueError(f"{fixture.get('name')}: selected Domains missing: {sorted(set(expected) - set(selected_domains))}")
    if set(fixture.get("must_not_filter_domains", [])) & set(filtered_domains):
        raise ValueError(f"{fixture.get('name')}: must-not-filter Domains were filtered")

    screen_bytes = len(selected_markdown(manifest, checks, "screen").encode())
    deep_bytes = len(selected_markdown(manifest, checks, "deep").encode())
    if screen_bytes >= deep_bytes:
        raise ValueError(f"{fixture.get('name')}: screen runtime must be smaller than deep runtime")
    for key, actual in (("max_selected_checks", len(selected_ids)), ("max_runtime_bytes", screen_bytes)):
        limit = fixture.get(key)
        if isinstance(limit, int) and actual > limit:
            print(f"WARNING: {fixture.get('name')} {key}={actual} exceeds staged budget {limit}", file=sys.stderr)
    return {
        "name": fixture.get("name"), "selected_domains": selected_domains,
        "deferred_domains": deferred_domains, "filtered_domains": filtered_domains,
        "selected_checks": len(selected_ids), "deferred_checks": len(deferred_ids),
        "filtered_checks": len(filtered_ids), "screen_runtime_bytes": screen_bytes,
        "deep_runtime_bytes": deep_bytes,
    }


def run_e2e(root: Path) -> dict[str, object]:
    target = root / "tests/fixtures/recon/ReconFixture.sol"
    with tempfile.TemporaryDirectory() as directory:
        feature_path, manifest_path = Path(directory) / "feature-map.json", Path(directory) / "manifest.json"
        recon = subprocess.run([sys.executable, str(root / "scripts/recon.py"), str(target), "--output", str(feature_path)], capture_output=True, text=True)
        if recon.returncode:
            raise ValueError(f"e2e Recon failed: {recon.stderr.strip()}")
        selector = subprocess.run([sys.executable, str(root / "scripts/select_checks.py"), "--feature-map", str(feature_path), "--target-root", str(target), "--manifest-out", str(manifest_path), "--profile", "screen"], capture_output=True, text=True)
        if selector.returncode:
            raise ValueError(f"e2e Selector failed: {selector.stderr.strip()}")
        manifest = load_json(manifest_path)
    registry = load_json(root / "data/canonical-checks.json")
    selected_ids = {entry["canonical_id"] for entry in manifest["selected"]}
    checks = [check for check in registry["checks"] if check["canonical_id"] in selected_ids]
    screen_bytes = len(selected_markdown(manifest, checks, "screen").encode())
    deep_bytes = len(selected_markdown(manifest, checks, "deep").encode())
    return {
        "name": "e2e-recon-fixture", "selected_domains": _domains(manifest, "selected_domains"),
        "deferred_domains": _domains(manifest, "deferred_domains"), "filtered_domains": _domains(manifest, "filtered_domains"),
        "selected_checks": manifest["selected_count"], "deferred_checks": manifest["deferred_count"],
        "filtered_checks": manifest["filtered_count"], "screen_runtime_bytes": screen_bytes, "deep_runtime_bytes": deep_bytes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--e2e", action="store_true", help="also execute Recon -> Selector on Solidity")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        paths = sorted((root / "benchmarks/routing").glob("*/*.json")) or sorted((root / "benchmarks/routing").glob("*.json"))
        results = [run_profile(root, load_json(path)) for path in paths]
        if args.e2e:
            results.append(run_e2e(root))
        if not results:
            raise ValueError("no routing benchmark fixtures found")
        for item in results:
            print(json.dumps(item, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
