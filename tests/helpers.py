"""Small shared inputs for Python tests; no test framework or runner lives here."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.scope_context import compilation_digests, scope_inventory
from scripts.select_checks import audit_context, load_domains, normalize_feature_map, select, vocabulary


ROOT = Path(__file__).resolve().parents[1]
EMPTY_TARGET = ROOT / "tests/fixtures/recon/Empty.sol"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def suite_inputs() -> tuple[dict[str, Any], set[str], dict[str, dict[str, Any]]]:
    registry = load_json(ROOT / "data/canonical-checks.json")
    feature_names, policies = vocabulary(load_json(ROOT / "data/features.json"))
    return registry, feature_names, policies


def synthetic_feature_map(
    statuses: Mapping[str, str] | None = None,
    target: Path = EMPTY_TARGET,
) -> dict[str, Any]:
    _, feature_names, policies = suite_inputs()
    files, excluded = scope_inventory(target)
    digests = compilation_digests(target, files, "0.8.24")
    requested = dict(statuses or {})
    features: dict[str, dict[str, Any]] = {}
    for feature in sorted(feature_names):
        status = requested.get(feature, "UNKNOWN")
        if status == "UNKNOWN":
            evidence: list[dict[str, str]] = []
        elif status == "ABSENT_CONFIRMED":
            kind = (policies[feature].get("allowed_absence_evidence") or ["manual"])[0]
            evidence = [{"kind": kind, "location": "fixture", "reason": "explicit fixture evidence"}]
        else:
            evidence = [{"kind": "manual", "location": "fixture", "reason": "explicit fixture evidence"}]
        features[feature] = {"status": status, "evidence": evidence}
    return {
        "schema_version": 4,
        "recon_context": {
            "target_root": str(target.resolve()),
            "files_analyzed": files,
            "excluded_paths": excluded,
            "exclusion_patterns": [],
            "uncompiled_paths": [],
            "source_digest": digests["audit_source_digest"],
            **digests,
            "compilation_complete": True,
            "slither_version": "synthetic",
            "solc_version": "0.8.24",
        },
        "features": features,
    }


def build_manifest(
    domains: Sequence[str] = ("evm-audit-general",),
    statuses: Mapping[str, str] | None = None,
    *,
    all_features: bool = False,
    domain_context: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    registry, feature_names, policies = suite_inputs()
    requested = {name: "PRESENT" for name in feature_names} if all_features else {}
    requested.update(statuses or {})
    raw = synthetic_feature_map(requested)
    normalized = normalize_feature_map(raw, feature_names, policies, EMPTY_TARGET)
    context = audit_context(
        ROOT,
        registry,
        raw["recon_context"],
        target_root=EMPTY_TARGET,
        audit_timestamp="test",
    )
    environment = {
        **{
            key: context[key]
            for key in (
                "chain_id",
                "chain_family",
                "execution_environment",
                "compiler_version",
                "evm_fork",
                "protocol_version",
            )
        },
        "environment_facts": context["environment_facts"],
    }
    configs = load_domains(ROOT)
    if domain_context is None:
        domain_context = {
            "domains": {
                domain: {
                    requirement["key"]: {
                        "status": "KNOWN",
                        "value": "fixture",
                        "evidence": ["fixture"],
                    }
                    for requirement in configs[domain]["required_context"]
                }
                for domain in domains
            }
        }
    manifest, _ = select(
        registry,
        normalized,
        feature_names,
        list(domains),
        context,
        configs,
        environment,
        raw["recon_context"],
        domain_context,
    )
    return registry, raw, normalized, manifest
