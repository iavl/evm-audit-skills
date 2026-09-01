#!/usr/bin/env python3
"""Benchmark routing recall, forbidden filters, and runtime context cost."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from audit_artifacts import check_body_hash, validate_domain_context, validate_domain_resolution, validate_schema
    from render_runtime import domain_context_template, render, selected_entries, validate_manifest, validate_screen_results
    from scope_context import DEFAULT_DEPENDENCY_ROOTS, compilation_digests, resolve_build_root, scope_inventory
    from select_checks import audit_context, load_domains, load_json, normalize_feature_map, select, vocabulary
except ImportError:  # pragma: no cover
    from scripts.audit_artifacts import check_body_hash, validate_domain_context, validate_domain_resolution, validate_schema
    from scripts.render_runtime import domain_context_template, render, selected_entries, validate_manifest, validate_screen_results
    from scripts.scope_context import DEFAULT_DEPENDENCY_ROOTS, compilation_digests, resolve_build_root, scope_inventory
    from scripts.select_checks import audit_context, load_domains, load_json, normalize_feature_map, select, vocabulary


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_TARGET = ROOT / "tests/fixtures/recon/Empty.sol"
CONTRACT_PATH = ROOT / "skills/evm-audit-master/references/check-review-contract.runtime.md"


def aggregate_domain_skill_bytes(root: Path) -> int:
    return sum(
        path.stat().st_size
        for path in root.glob("skills/evm-audit-*/SKILL.md")
        if path.parent.name != "evm-audit-master"
    )


def recon_context(target: Path) -> dict[str, object]:
    build_root = resolve_build_root(target)
    files, excluded = scope_inventory(target)
    digests = compilation_digests(
        target,
        files,
        "0.8.24",
        build_root=build_root,
        dependency_roots=DEFAULT_DEPENDENCY_ROOTS,
    )
    return {
        "target_root": str(target.resolve()), "build_root": str(build_root.resolve()), "files_analyzed": files,
        "excluded_paths": excluded, "exclusion_patterns": [], "include_patterns": [],
        "dependency_roots": sorted(DEFAULT_DEPENDENCY_ROOTS), "uncompiled_paths": [],
        "source_digest": digests["audit_source_digest"], **digests, "compilation_complete": True,
        "recon_quality": {
            "compilation_complete": True,
            "absence_filtering_complete": True,
            "mode": "COMPLETE",
            "uncompiled_paths": [],
        },
        "slither_version": "benchmark", "solc_version": "0.8.24",
    }


def feature_map(names: set[str], policies: dict[str, dict[str, object]], present: list[str], absent: list[str]) -> dict[str, object]:
    entries: dict[str, object] = {}
    for name in sorted(names):
        status = "PRESENT" if name in present else "ABSENT_CONFIRMED" if name in absent else "UNKNOWN"
        evidence: list[dict[str, str]] = []
        if status != "UNKNOWN":
            allowed = policies[name]["allowed_absence_evidence"] if status == "ABSENT_CONFIRMED" else ["manual"]
            if allowed:
                evidence = [{"kind": allowed[0], "location": "benchmark", "reason": "declared benchmark scope", "scope_origin": "AUDIT_SCOPE"}]
        entries[name] = {"status": status, "evidence": evidence}
    return {"schema_version": 4, "recon_context": recon_context(SYNTHETIC_TARGET), "features": entries}


def _domains(manifest: dict[str, object], bucket: str) -> list[str]:
    return [entry["domain"] for entry in manifest[bucket]]  # type: ignore[index]


def _total_cost(manifest: dict[str, object], screen: str, deep: str) -> dict[str, int]:
    selected_domains = manifest.get("selected_domains", [])
    deferred_domains = manifest.get("deferred_domains", [])
    domain_screening = len(json.dumps(deferred_domains, ensure_ascii=False, sort_keys=True).encode())
    screen_bytes = len(screen.encode())
    deep_bytes = len(deep.encode())
    shared_contract = len(CONTRACT_PATH.read_bytes())
    methodology = len(json.dumps(selected_domains, ensure_ascii=False, sort_keys=True).encode())
    return {
        "domain_screening_bytes": domain_screening,
        "screen_bytes": screen_bytes,
        "candidate_deep_bytes": deep_bytes,
        "shared_contract_bytes": shared_contract,
        "domain_methodology_bytes": methodology,
        "total_context_bytes": domain_screening + screen_bytes + deep_bytes + shared_contract + methodology,
    }


def validate_fixture(root: Path, fixture: dict[str, object]) -> None:
    validate_schema(root, "benchmark-routing-fixture.schema.json", fixture)
    if set(fixture["present_features"]) & set(fixture["absent_features"]):  # type: ignore[index]
        raise ValueError(f"{fixture['name']}: present_features and absent_features overlap")


def _assert_fixture(fixture: dict[str, object], normalized: dict[str, dict[str, object]], manifest: dict[str, object]) -> None:
    name = fixture["name"]
    selected_domains, deferred_domains, filtered_domains = map(lambda bucket: set(_domains(manifest, bucket)), ("selected_domains", "deferred_domains", "filtered_domains"))
    selected_ids = {entry["canonical_id"] for entry in manifest["selected"]}  # type: ignore[index]
    filtered_ids = {entry["canonical_id"] for entry in manifest["filtered"]}  # type: ignore[index]
    for feature in fixture.get("must_detect_features", []):
        if normalized.get(feature, {}).get("status") != "PRESENT":
            raise ValueError(f"{name}: must-detect feature is not PRESENT: {feature}")
    must_select = set(fixture.get("must_select_checks", []))
    if not must_select <= selected_ids:
        raise ValueError(f"{name}: must-select checks missing: {sorted(must_select - selected_ids)}")
    expected_selected_checks = fixture.get("expected_selected_checks")
    if isinstance(expected_selected_checks, int) and expected_selected_checks != len(selected_ids):
        raise ValueError(f"{name}: selected check count mismatch: expected={expected_selected_checks} actual={len(selected_ids)}")
    expected_filtered_checks = fixture.get("expected_filtered_checks")
    if isinstance(expected_filtered_checks, int) and expected_filtered_checks != len(filtered_ids):
        raise ValueError(f"{name}: filtered check count mismatch: expected={expected_filtered_checks} actual={len(filtered_ids)}")
    must_not_filter = set(fixture.get("must_not_filter_checks", []))
    if must_not_filter & filtered_ids:
        raise ValueError(f"{name}: must-not-filter checks filtered: {sorted(must_not_filter & filtered_ids)}")
    for key, actual in (
        ("expected_selected_domains", selected_domains),
        ("expected_deferred_domains", deferred_domains),
        ("expected_filtered_domains", filtered_domains),
    ):
        expected = fixture.get(key)
        if expected is not None and set(expected) != actual:
            raise ValueError(f"{name}: {key} mismatch: expected={sorted(expected)} actual={sorted(actual)}")
    required = set(fixture.get("must_select_domains", []))
    if not required <= selected_domains:
        raise ValueError(f"{name}: selected Domains missing: {sorted(required - selected_domains)}")
    forbidden = set(fixture.get("must_not_filter_domains", [])) | set(fixture.get("must_not_select_domains", []))
    if forbidden & filtered_domains:
        raise ValueError(f"{name}: forbidden Domains were filtered: {sorted(forbidden & filtered_domains)}")
    if forbidden & selected_domains:
        raise ValueError(f"{name}: forbidden Domains were selected: {sorted(forbidden & selected_domains)}")


def _routing_recall(fixture: dict[str, object], selected_ids: set[str]) -> tuple[float, int]:
    expected = set(fixture.get("must_select_checks", []))
    missing = expected - selected_ids
    return (
        1.0 if not expected else round((len(expected) - len(missing)) / len(expected), 4),
        len(missing),
    )


def run_profile(root: Path, fixture: dict[str, object]) -> dict[str, object]:
    validate_fixture(root, fixture)
    registry = load_json(root / "data/canonical-checks.json")
    names, policies = vocabulary(load_json(root / "data/features.json"))
    domains = load_domains(root)
    present, absent = fixture["present_features"], fixture["absent_features"]
    if not isinstance(present, list) or not isinstance(absent, list) or not set(present + absent) <= names:
        raise ValueError(f"invalid features in {fixture['name']}")
    raw_map = feature_map(names, policies, present, absent)
    normalized = normalize_feature_map(raw_map, names, policies, SYNTHETIC_TARGET)
    scope = fixture.get("domain_scope")
    if scope is not None and (not isinstance(scope, list) or not scope):
        raise ValueError(f"domain_scope must be a non-empty list in {fixture.get('name')}")
    context = audit_context(root, registry, raw_map["recon_context"], target_root=SYNTHETIC_TARGET, audit_timestamp="benchmark")
    environment = {**{key: context[key] for key in ("chain_id", "chain_family", "execution_environment", "compiler_version", "evm_fork", "protocol_version")}, "environment_facts": context["environment_facts"]}
    manifest, _ = select(registry, normalized, names, scope, context, domains, environment, raw_map["recon_context"])
    validate_manifest(root, manifest, registry)
    _assert_fixture(fixture, normalized, manifest)
    domain_resolution = {
        "schema_version": 2,
        "routing_snapshot_id": manifest["routing_snapshot_id"],
        "registry_sha256": manifest["audit_context"]["registry_sha256"],
        "source_digest": manifest["audit_context"]["source_digest"],
        "compilation_input_digest": manifest["audit_context"]["compilation_input_digest"],
        "domains": {
            entry["domain"]: {
                "status": "ABSENT_CONFIRMED",
                "scope_complete": True,
                "evidence": [
                    {"kind": "scope", "location": "benchmark", "reason": "complete synthetic scope"},
                    {"kind": "inheritance", "location": "benchmark", "reason": "no domain surface"},
                ],
            }
            for entry in manifest["deferred_domains"]
        },
    }
    validate_domain_resolution(root, manifest, domain_resolution, require_terminal=True)
    domain_context = domain_context_template(manifest, domain_resolution)
    for values in domain_context["domains"].values():
        for item in values.values():
            item.update(
                status="KNOWN",
                value="benchmark fixture",
                evidence=[{"kind": "scope", "location": "benchmark", "reason": "synthetic context"}],
            )
    validate_domain_context(root, manifest, domain_context, domain_resolution, require_complete=True)
    screen = render(manifest, registry, "screen", set())
    candidates = {entry["canonical_id"] for entry in selected_entries(manifest, domain_resolution=domain_resolution)}
    deep = render(manifest, registry, "deep", candidates)
    cost = _total_cost(manifest, screen, deep)
    proof_ids = set(sorted(candidates)[:3])
    proof_records = {
        canonical_id: {
            "revision": 1,
            "review_stage": "DEEP_REVIEW",
            "status": "SUSPICIOUS",
            "code_path": "benchmark path",
            "unresolved_reason": "benchmark proof pending",
            "evidence": [{"kind": "source", "location": "benchmark", "reason": "sample evidence"}],
        }
        for canonical_id in proof_ids
    }
    proof = render(manifest, registry, "proof", proof_ids, review_snapshot="0" * 64, proof_records=proof_records)
    sample_id = next(iter(proof_ids), manifest["selected"][0]["canonical_id"])
    sample_route = next(entry for entry in manifest["selected"] if entry["canonical_id"] == sample_id)
    sample_identity = {
        "record_type": "review", "schema_version": 7, "canonical_id": sample_id, "revision": 1,
        "owner_domain": sample_route["owner_domain"], "routing_snapshot_id": manifest["routing_snapshot_id"],
        "review_snapshot_id": "0" * 64, "registry_sha256": manifest["audit_context"]["registry_sha256"],
        "source_digest": manifest["audit_context"]["source_digest"], "compilation_input_digest": manifest["audit_context"]["compilation_input_digest"],
        "check_body_hash": check_body_hash(next(check for check in registry["checks"] if check["canonical_id"] == sample_id)),
    }
    cost.update({
        "proof_runtime_bytes": len(proof.encode()),
        "reviewed_safe_record_bytes": len(json.dumps({
            **sample_identity, "review_stage": "DEEP_REVIEW", "status": "REVIEWED_SAFE", "applicability": "APPLICABLE", "code_path": "benchmark", "preserved_invariant": "holds", "evidence": proof_records[sample_id]["evidence"] if proof_ids else [],
        }).encode()),
        "confirmed_record_bytes": len(json.dumps({
            **sample_identity, "review_stage": "PROOF", "status": "CONFIRMED", "applicability": "APPLICABLE", "code_path": "benchmark", "preconditions": "benchmark", "exploitability": "permissionless", "impact": "fund_loss", "proof": "trace", "evidence": proof_records[sample_id]["evidence"] if proof_ids else [],
        }).encode()),
    })
    cost["total_context_bytes"] += cost["proof_runtime_bytes"]
    recall, false_negative_cases = _routing_recall(fixture, candidates)
    if len(screen) >= len(deep):
        raise ValueError(f"{fixture['name']}: screen runtime must be smaller than candidate Deep runtime")
    for key, actual in (("max_selected_checks", len(candidates)), ("max_runtime_bytes", len(screen.encode())), ("max_total_context_bytes", cost["total_context_bytes"])):
        limit = fixture.get(key)
        if isinstance(limit, int) and actual > limit:
            raise ValueError(f"{fixture['name']}: {key}={actual} exceeds hard budget {limit}")
    return {
        "name": fixture["name"], "selected_domains": sorted(_domains(manifest, "selected_domains")),
        "deferred_domains": sorted(_domains(manifest, "deferred_domains")), "filtered_domains": sorted(_domains(manifest, "filtered_domains")),
        "selected_checks": len(candidates), "deferred_checks": manifest["deferred_count"],
        "filtered_checks": manifest["filtered_count"], "screen_runtime_bytes": len(screen.encode()),
        "deep_runtime_bytes": len(deep.encode()), "proof_runtime_bytes": cost["proof_runtime_bytes"],
        "reviewed_safe_record_bytes": cost["reviewed_safe_record_bytes"], "confirmed_record_bytes": cost["confirmed_record_bytes"],
        "aggregate_domain_skill_bytes": aggregate_domain_skill_bytes(root),
        "routing_recall": recall, "false_negative_cases": false_negative_cases, "cost": cost,
    }


def run_e2e(root: Path) -> list[dict[str, object]]:
    cases = {
        "erc20": ({"uses-erc20"}, {"EVM-GEN-001", "EVM-ERC20-001"}),
        "erc4626": ({"uses-erc4626"}, {"EVM-GEN-001", "EVM-ERC4626-001"}),
        "proxy": ({"uses-proxy", "uses-delegatecall", "uses-assembly"}, {"EVM-GEN-001", "EVM-PROXY-001"}),
        "lending-oracle": ({"uses-lending", "uses-oracle"}, {"EVM-GEN-001", "EVM-LEND-001", "EVM-ORACLE-001"}),
        "bridge": ({"uses-bridge"}, {"EVM-GEN-001", "EVM-BRIDGE-001"}),
        "governance": ({"uses-governance"}, {"EVM-GEN-001", "EVM-GOV-001"}),
        "mixed-defi": ({"uses-erc20", "uses-erc4626", "uses-amm", "uses-lending", "uses-oracle", "uses-staking"}, {"EVM-GEN-001", "EVM-ERC20-001", "EVM-ERC4626-001", "EVM-AMM-001", "EVM-LEND-001", "EVM-ORACLE-001", "EVM-STK-001"}),
    }
    registry = load_json(root / "data/canonical-checks.json")
    results: list[dict[str, object]] = []
    for name, (must_detect, expected_checks) in cases.items():
        target_root = root / "tests/fixtures/e2e" / name
        target = target_root / "Main.sol"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            feature_path, manifest_path = output / "feature-map.json", output / "manifest.json"
            screen_path, screen_results_path = output / "screen.md", output / "screen-results.json"
            recon = subprocess.run([sys.executable, str(root / "scripts/recon.py"), str(target), "--audit-root", str(target_root), "--output", str(feature_path)], capture_output=True, text=True)
            if recon.returncode:
                raise ValueError(f"e2e {name} Recon failed: {recon.stderr.strip()}")
            feature_map = load_json(feature_path)
            missing_features = sorted(feature for feature in must_detect if feature_map["features"].get(feature, {}).get("status") != "PRESENT")
            if missing_features:
                raise ValueError(f"e2e {name} Recon missed must-detect features: {missing_features}")
            selector = subprocess.run([sys.executable, str(root / "scripts/select_checks.py"), "--feature-map", str(feature_path), "--target-root", str(target_root), "--manifest-out", str(manifest_path)], capture_output=True, text=True)
            if selector.returncode:
                raise ValueError(f"e2e {name} Selector failed: {selector.stderr.strip()}")
            manifest = load_json(manifest_path)
            render_result = subprocess.run([sys.executable, str(root / "scripts/render_runtime.py"), "--manifest", str(manifest_path), "--profile", "screen", "--output", str(screen_path), "--screen-results-out", str(screen_results_path)], capture_output=True, text=True)
            if render_result.returncode:
                raise ValueError(f"e2e {name} Screen render failed: {render_result.stderr.strip()}")
            screen = screen_path.read_text(encoding="utf-8")
            screen_results = load_json(screen_results_path)
        validate_manifest(root, manifest, registry)
        candidates = validate_screen_results(root, manifest, screen_results)
        missing_checks = sorted(expected_checks - candidates)
        if missing_checks:
            raise ValueError(f"e2e {name} Screen lost must-select checks: {missing_checks}")
        results.append({
            "name": f"e2e-{name}", "selected_domains": sorted(_domains(manifest, "selected_domains")),
            "deferred_domains": sorted(_domains(manifest, "deferred_domains")), "filtered_domains": sorted(_domains(manifest, "filtered_domains")),
            "selected_checks": manifest["selected_count"], "deferred_checks": manifest["deferred_count"],
            "filtered_checks": manifest["filtered_count"], "screen_runtime_bytes": len(screen.encode()),
            "deep_runtime_bytes": None, "aggregate_domain_skill_bytes": aggregate_domain_skill_bytes(root),
            "routing_recall": 1.0, "false_negative_cases": 0,
            "e2e_recall": {"must_detect_features": len(must_detect), "must_select_checks": len(expected_checks), "candidates": len(candidates)}, "e2e_artifacts": ["multi-file feature-map.json", "manifest.json", "screen-results.json"],
        })
    return results


def fixture_paths(root: Path) -> list[Path]:
    benchmark_root = root / "development/benchmarks/routing"
    flat = sorted(benchmark_root.glob("*.json"))
    if flat:
        raise ValueError("routing benchmark fixtures must be under automatic/ or explicit/")
    unexpected = sorted(path.name for path in benchmark_root.iterdir() if path.is_dir() and path.name not in {"automatic", "explicit"}) if benchmark_root.exists() else []
    if unexpected:
        raise ValueError(f"unsupported routing fixture directories: {', '.join(unexpected)}")
    paths = sorted(path for mode in ("automatic", "explicit") for path in (benchmark_root / mode).glob("*.json"))
    if not paths:
        raise ValueError("no routing benchmark fixtures found")
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--e2e", action="store_true", help="also execute Recon -> Selector -> Renderer on Solidity")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        paths = fixture_paths(root)
        results = [run_profile(root, load_json(path)) for path in paths]
        if args.e2e:
            results.extend(run_e2e(root))
        for item in results:
            print(json.dumps(item, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
