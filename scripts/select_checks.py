#!/usr/bin/env python3
"""Route canonical checks from a scope-bound Feature Map v3."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scope_context import compilation_digests, resolve_scope_root, scope_inventory, source_digest
except ImportError:  # pragma: no cover
    from scripts.scope_context import compilation_digests, resolve_scope_root, scope_inventory, source_digest


ROOT = Path(__file__).resolve().parents[1]
FEATURE_STATES = {"PRESENT", "ABSENT_CONFIRMED", "UNKNOWN"}
PREDICATE_KEYS = ("all_of", "any_of", "none_of")
SELECTOR_VERSION = "5"
ROUTING_MANIFEST_VERSION = 5
FEATURE_MAP_VERSION = 3
EVIDENCE_KINDS = {"slither-ast", "slither-ir", "compiler-ast", "source", "deployment", "manual"}
HARD_FORKS = ("frontier", "homestead", "byzantium", "constantinople", "istanbul", "berlin", "london", "paris", "shanghai", "cancun", "prague")
CHAIN_FAMILY_BY_ID = {
    1: "ethereum", 10: "op-stack", 56: "bnb-smart-chain", 137: "polygon-pos",
    324: "zksync-era", 8453: "op-stack", 42161: "arbitrum", 81457: "blast",
}
EXECUTION_ENVIRONMENTS_BY_CHAIN_ID = {
    **{chain_id: {"ethereum-evm"} for chain_id in CHAIN_FAMILY_BY_ID if chain_id != 324},
    324: {"eravm-native", "zksync-evm-interpreter"},
}


class SelectionInputError(ValueError):
    """Raised when routing input cannot safely support selection."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SelectionInputError(f"cannot read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise SelectionInputError(f"JSON root must be an object: {path}")
    return value


def registry_sha256(registry: dict[str, Any]) -> str:
    encoded = json.dumps(registry, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def git_value(root: Path, *args: str) -> str | None:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def build_info(root: Path) -> dict[str, Any]:
    path = root / "build-info.json"
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def knowledge_state(root: Path) -> tuple[str | None, bool | None]:
    commit = git_value(root, "rev-parse", "HEAD")
    status = git_value(root, "status", "--short")
    if commit is not None and status is not None:
        return commit, bool(status)
    info = build_info(root)
    fallback = info.get("source_commit")
    return (fallback if isinstance(fallback, str) and fallback else None), None


def audit_context(
    root: Path,
    registry: dict[str, Any],
    recon_context: dict[str, Any],
    *,
    target_root: Path,
    target_commit: str | None = None,
    chain_id: int | None = None,
    chain_family: str | None = None,
    execution_environment: str | None = None,
    fork_block: int | None = None,
    compiler_version: str | None = None,
    evm_fork: str | None = None,
    protocol_version: str | None = None,
    audit_timestamp: str | None = None,
) -> dict[str, Any]:
    knowledge_commit, knowledge_dirty = knowledge_state(root)
    environment = validate_environment_context(
        recon_context, chain_id=chain_id, chain_family=chain_family,
        execution_environment=execution_environment, compiler_version=compiler_version,
        evm_fork=evm_fork, protocol_version=protocol_version,
    )
    return {
        "selector_version": SELECTOR_VERSION,
        "registry_sha256": registry_sha256(registry),
        "knowledge_commit": knowledge_commit,
        "knowledge_dirty": knowledge_dirty,
        "target_repo_commit": target_commit or git_value(target_root.resolve(), "rev-parse", "HEAD"),
        "source_digest": recon_context["source_digest"],
        "audit_source_digest": recon_context["audit_source_digest"],
        "dependency_digest": recon_context["dependency_digest"],
        "build_config_digest": recon_context["build_config_digest"],
        "compilation_digest": recon_context["compilation_digest"],
        **environment,
        "fork_block": fork_block,
        "fork_block_semantics": "reproducibility metadata only; does not derive evm_fork",
        "audit_timestamp": audit_timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def validate_environment_context(
    recon_context: dict[str, Any], *, chain_id: int | None = None,
    chain_family: str | None = None, execution_environment: str | None = None,
    compiler_version: str | None = None, evm_fork: str | None = None,
    protocol_version: str | None = None,
) -> dict[str, Any]:
    mapped_family = CHAIN_FAMILY_BY_ID.get(chain_id)
    if mapped_family and chain_family and chain_family != mapped_family:
        raise SelectionInputError(
            f"chain_id {chain_id} maps to {mapped_family}, not {chain_family}"
        )
    if chain_id in EXECUTION_ENVIRONMENTS_BY_CHAIN_ID and execution_environment:
        allowed = EXECUTION_ENVIRONMENTS_BY_CHAIN_ID[chain_id]
        if execution_environment not in allowed:
            raise SelectionInputError(
                f"chain_id {chain_id} is incompatible with execution_environment {execution_environment}"
            )
    recon_compiler = recon_context.get("solc_version")
    if compiler_version and recon_compiler:
        cli_version, detected_version = _version(compiler_version), _version(recon_compiler)
        if cli_version is None or detected_version is None or cli_version != detected_version:
            raise SelectionInputError(
                f"compiler_version {compiler_version} conflicts with Recon solc_version {recon_compiler}"
            )
    resolved_family = mapped_family or chain_family
    resolved_compiler = compiler_version or recon_compiler

    def fact(value: Any, evidence: str) -> dict[str, Any]:
        return {"value": value, "status": "CONFIRMED" if value is not None else "UNKNOWN", "evidence": evidence if value is not None else None}

    return {
        "chain_id": chain_id,
        "chain_family": resolved_family,
        "execution_environment": execution_environment,
        "compiler_version": resolved_compiler,
        "evm_fork": evm_fork,
        "protocol_version": protocol_version,
        "environment_facts": {
            "chain_id": fact(chain_id, "cli"),
            "chain_family": fact(resolved_family, "chain-id mapping" if mapped_family else "cli"),
            "execution_environment": fact(execution_environment, "cli validated against chain_id" if chain_id else "cli"),
            "compiler_version": fact(resolved_compiler, "Recon compiler evidence" if recon_compiler else "cli"),
            "evm_fork": fact(evm_fork, "explicit cli; fork_block does not derive this value"),
            "protocol_version": fact(protocol_version, "cli"),
        },
    }


def vocabulary(feature_data: dict[str, Any]) -> tuple[set[str], dict[str, dict[str, Any]]]:
    if feature_data.get("schema_version") != 2:
        raise SelectionInputError("feature registry schema_version must be 2")
    values = feature_data.get("features")
    if not isinstance(values, dict) or not values:
        raise SelectionInputError("feature registry must contain a non-empty object named 'features'")
    policies: dict[str, dict[str, Any]] = {}
    for feature, entry in values.items():
        if not isinstance(entry, dict):
            raise SelectionInputError(f"feature {feature!r} configuration must be an object")
        if entry.get("absence_policy") not in {"machine-only", "machine-or-deployment", "manual-allowed", "never-confirm-absence"}:
            raise SelectionInputError(f"feature {feature!r} has invalid absence_policy")
        allowed = entry.get("allowed_absence_evidence")
        if not isinstance(allowed, list) or any(kind not in EVIDENCE_KINDS for kind in allowed):
            raise SelectionInputError(f"feature {feature!r} has invalid allowed_absence_evidence")
        policies[feature] = entry
    return set(values), policies


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise SelectionInputError(f"{label} must be a string list")
    if len(value) != len(set(value)):
        raise SelectionInputError(f"{label} must not contain duplicates")
    return value


def validate_recon_context(raw: Any, target_root: Path | None, exclusions: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise SelectionInputError("Feature Map v3 requires recon_context")
    required = {
        "target_root", "files_analyzed", "excluded_paths", "exclusion_patterns", "uncompiled_paths", "source_digest",
        "audit_source_digest", "dependency_digest", "build_config_digest", "compilation_digest",
        "compilation_complete", "slither_version", "solc_version",
    }
    if set(raw) != required:
        raise SelectionInputError(f"recon_context fields must be {sorted(required)}")
    _string_list(raw["files_analyzed"], "recon_context.files_analyzed")
    _string_list(raw["excluded_paths"], "recon_context.excluded_paths")
    exclusion_patterns = _string_list(raw["exclusion_patterns"], "recon_context.exclusion_patterns")
    if exclusion_patterns != sorted(set(exclusions)):
        raise SelectionInputError("Recon exclusion_patterns do not match the current audit scope")
    uncompiled = _string_list(raw["uncompiled_paths"], "recon_context.uncompiled_paths")
    if not isinstance(raw["target_root"], str) or not raw["target_root"]:
        raise SelectionInputError("recon_context.target_root must be a path")
    for key in ("source_digest", "audit_source_digest", "dependency_digest", "build_config_digest", "compilation_digest"):
        if not isinstance(raw[key], str) or not re.fullmatch(r"[0-9a-f]{64}", raw[key]):
            raise SelectionInputError(f"recon_context.{key} must be a SHA-256 digest")
    if raw["source_digest"] != raw["audit_source_digest"]:
        raise SelectionInputError("recon_context.source_digest must equal audit_source_digest")
    if raw["compilation_complete"] is not True or uncompiled:
        raise SelectionInputError("FAST_FILTER requires compilation_complete=true and no uncompiled paths")
    if not isinstance(raw["slither_version"], str) or not raw["slither_version"]:
        raise SelectionInputError("recon_context.slither_version is required")
    if raw["solc_version"] is not None and not isinstance(raw["solc_version"], str):
        raise SelectionInputError("recon_context.solc_version must be a string or null")
    if target_root is None:
        raise SelectionInputError("Feature Map v3 selection requires --target-root")
    resolved = resolve_scope_root(target_root)
    files, excluded = scope_inventory(resolved, exclusions)
    actual_digest = source_digest(resolved, files)
    if actual_digest != raw["source_digest"]:
        raise SelectionInputError("Recon source_digest does not match the current audit scope")
    actual_digests = compilation_digests(resolved, files, raw["solc_version"])
    for key, value in actual_digests.items():
        if raw[key] != value:
            raise SelectionInputError(f"Recon {key} does not match the current audit scope")
    if Path(raw["target_root"]).resolve() != resolved:
        raise SelectionInputError("Recon target_root does not match --target-root")
    if raw["excluded_paths"] != excluded:
        raise SelectionInputError("Recon excluded_paths do not match the current audit scope")
    return dict(raw)


def _evidence(value: Any, feature: str) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SelectionInputError(f"feature {feature!r} evidence must be a list")
    normalized: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict) or set(item) != {"kind", "location", "reason"}:
            raise SelectionInputError(f"feature {feature!r} evidence entries need kind/location/reason")
        if item.get("kind") not in EVIDENCE_KINDS or any(not isinstance(item.get(key), str) or not item[key].strip() for key in ("location", "reason")):
            raise SelectionInputError(f"feature {feature!r} has invalid typed evidence")
        normalized.append({key: item[key].strip() for key in ("kind", "location", "reason")})
    return normalized


def normalize_feature_map(
    raw: dict[str, Any],
    names: set[str],
    policies: dict[str, dict[str, Any]],
    target_root: Path | None,
    exclusions: tuple[str, ...] = (),
) -> dict[str, dict[str, Any]]:
    if raw.get("schema_version") != FEATURE_MAP_VERSION:
        raise SelectionInputError(f"feature map schema_version must be {FEATURE_MAP_VERSION}")
    validate_recon_context(raw.get("recon_context"), target_root, exclusions)
    entries = raw.get("features")
    if not isinstance(entries, dict):
        raise SelectionInputError("feature map must contain an object named 'features'")
    unknown = sorted(set(entries) - names)
    if unknown:
        raise SelectionInputError(f"unknown features in feature map: {', '.join(unknown)}")

    normalized: dict[str, dict[str, Any]] = {}
    for feature, entry in entries.items():
        if not isinstance(entry, dict) or not set(entry) <= {"status", "evidence", "reason"}:
            raise SelectionInputError(f"feature {feature!r} must contain status/evidence and optional reason")
        status = entry.get("status")
        evidence = _evidence(entry.get("evidence"), feature)
        reason = entry.get("reason", "")
        if status not in FEATURE_STATES:
            raise SelectionInputError(f"feature {feature!r} status must be one of {sorted(FEATURE_STATES)}")
        if not isinstance(reason, str):
            raise SelectionInputError(f"feature {feature!r} reason must be a string")
        if status != "UNKNOWN" and not evidence:
            raise SelectionInputError(f"feature {feature!r} status {status} requires concrete evidence")
        if status == "ABSENT_CONFIRMED":
            allowed = set(policies[feature]["allowed_absence_evidence"])
            kinds = {item["kind"] for item in evidence}
            if policies[feature]["absence_policy"] == "never-confirm-absence" or not kinds or not kinds <= allowed:
                status = "UNKNOWN"
                reason = f"absence rejected by policy {policies[feature]['absence_policy']}"
        normalized[feature] = {"status": status, "evidence": evidence}
        if reason.strip():
            normalized[feature]["reason"] = reason.strip()
    return {
        feature: normalized.get(feature, {"status": "UNKNOWN", "evidence": []})
        for feature in sorted(names)
    }


def status_for(feature: str, feature_map: dict[str, dict[str, Any]]) -> str:
    return feature_map.get(feature, {"status": "UNKNOWN"})["status"]


def evaluate_group(features: list[str], mode: str, feature_map: dict[str, dict[str, Any]]) -> str:
    if not features:
        return "TRUE"
    states = [status_for(feature, feature_map) for feature in features]
    if mode == "all_of":
        return "FALSE" if "ABSENT_CONFIRMED" in states else "TRUE" if all(state == "PRESENT" for state in states) else "UNKNOWN"
    if mode == "any_of":
        return "TRUE" if "PRESENT" in states else "FALSE" if all(state == "ABSENT_CONFIRMED" for state in states) else "UNKNOWN"
    if mode == "none_of":
        return "FALSE" if "PRESENT" in states else "TRUE" if all(state == "ABSENT_CONFIRMED" for state in states) else "UNKNOWN"
    raise AssertionError(f"unsupported predicate group: {mode}")


def check_predicate(check: dict[str, Any], names: set[str]) -> dict[str, list[str]]:
    predicate = check.get("predicate")
    if not isinstance(predicate, dict) or set(predicate) != set(PREDICATE_KEYS):
        raise SelectionInputError(f"{check.get('canonical_id')}: predicate must contain all_of/any_of/none_of")
    normalized: dict[str, list[str]] = {}
    for key in PREDICATE_KEYS:
        values = predicate[key]
        if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
            raise SelectionInputError(f"{check.get('canonical_id')}: predicate.{key} must be a string list")
        normalized[key] = sorted(set(values))
        unknown = sorted(set(normalized[key]) - names)
        if unknown:
            raise SelectionInputError(f"{check.get('canonical_id')}: unknown predicate features: {', '.join(unknown)}")
    return normalized


def evaluate_check(check: dict[str, Any], feature_map: dict[str, dict[str, Any]], names: set[str]) -> dict[str, Any]:
    if check.get("always_screen") is True:
        return {
            "result": "TRUE", "predicate_result": "TRUE", "predicate_source": check.get("predicate_source", "curated"),
            "predicate": {key: [] for key in PREDICATE_KEYS}, "matched_features": [], "unknown_features": [], "basis": ["always_screen=true"],
        }
    predicate = check_predicate(check, names)
    groups = {key: evaluate_group(predicate[key], key, feature_map) for key in PREDICATE_KEYS}
    predicate_result = "FALSE" if "FALSE" in groups.values() else "TRUE" if all(value == "TRUE" for value in groups.values()) else "UNKNOWN"
    predicate_source = check.get("predicate_source", "inferred")
    result = "UNKNOWN" if predicate_result == "FALSE" and predicate_source != "curated" else predicate_result
    referenced = {feature for values in predicate.values() for feature in values}
    matched = sorted(feature for feature in referenced if status_for(feature, feature_map) == "PRESENT")
    unknown = sorted(feature for feature in referenced if status_for(feature, feature_map) == "UNKNOWN")
    basis = [f"{key}={value}" for key, value in groups.items() if predicate[key]]
    if matched:
        basis.append("present=" + ",".join(matched))
    if unknown:
        basis.append("unknown=" + ",".join(unknown))
    if predicate_result == "FALSE":
        basis.append("failed=" + ",".join(key for key, value in groups.items() if value == "FALSE"))
    if predicate_result == "FALSE" and result == "UNKNOWN":
        basis.append("inferred-false-downgraded=UNKNOWN")
    return {
        "result": result, "predicate_result": predicate_result, "predicate_source": predicate_source,
        "predicate": predicate, "matched_features": matched, "unknown_features": unknown, "basis": basis or ["empty predicate"],
    }


def _version(value: str) -> tuple[int, int, int] | None:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", value)
    return tuple(map(int, match.groups())) if match else None


def compiler_matches(constraint: str, actual: str) -> bool | None:
    version = _version(actual)
    if version is None:
        return None
    for clause in constraint.split(","):
        match = re.fullmatch(r"\s*(>=|<=|==|>|<)\s*(\d+\.\d+\.\d+)\s*", clause)
        if not match:
            raise SelectionInputError(f"invalid compiler applicability constraint: {constraint}")
        expected = _version(match.group(2))
        operator = match.group(1)
        if expected is None or not {">=": version >= expected, "<=": version <= expected, "==": version == expected, ">": version > expected, "<": version < expected}[operator]:
            return False
    return True


def evaluate_environment(check: dict[str, Any], environment: dict[str, Any]) -> tuple[str, list[str]]:
    applicability = check.get("applicability")
    if not applicability:
        return "TRUE", ["no environment constraints"]
    results: list[str] = []
    basis: list[str] = []
    dimensions = (
        ("chain_ids", "chain_id"),
        ("chain_families", "chain_family"),
        ("execution_environments", "execution_environment"),
        ("protocol_versions", "protocol_version"),
    )
    for allowed_key, actual_key in dimensions:
        allowed = applicability.get(allowed_key, []) or []
        if not allowed:
            continue
        fact = environment.get("environment_facts", {}).get(actual_key, {})
        actual = fact.get("value") if fact.get("status") == "CONFIRMED" else None
        result = "UNKNOWN" if actual is None else "TRUE" if actual in allowed else "FALSE"
        results.append(result)
        basis.append(f"{actual_key}={result}")
    constraint = applicability.get("compiler")
    if constraint:
        fact = environment.get("environment_facts", {}).get("compiler_version", {})
        actual = fact.get("value") if fact.get("status") == "CONFIRMED" else None
        match = None if actual is None else compiler_matches(constraint, actual)
        result = "UNKNOWN" if match is None else "TRUE" if match else "FALSE"
        results.append(result)
        basis.append(f"compiler={result}")
    fork_fact = environment.get("environment_facts", {}).get("evm_fork", {})
    actual_fork = fork_fact.get("value") if fork_fact.get("status") == "CONFIRMED" else None
    for bound_key, comparison in (("evm_fork_from", "from"), ("evm_fork_until", "until")):
        bound = applicability.get(bound_key)
        if not bound:
            continue
        if bound not in HARD_FORKS:
            raise SelectionInputError(f"{check.get('canonical_id')}: unknown EVM fork {bound!r}")
        if actual_fork is None:
            result = "UNKNOWN"
        elif actual_fork not in HARD_FORKS:
            raise SelectionInputError(f"unknown target EVM fork {actual_fork!r}")
        else:
            ok = HARD_FORKS.index(actual_fork) >= HARD_FORKS.index(bound) if comparison == "from" else HARD_FORKS.index(actual_fork) <= HARD_FORKS.index(bound)
            result = "TRUE" if ok else "FALSE"
        results.append(result)
        basis.append(f"{bound_key}={result}")
    return ("FALSE" if "FALSE" in results else "TRUE" if all(result == "TRUE" for result in results) else "UNKNOWN"), basis


def evaluate_domains(
    domain_configs: dict[str, dict[str, Any]],
    feature_map: dict[str, dict[str, Any]],
    explicit_domains: list[str] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    selected: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    filtered: list[dict[str, Any]] = []
    considered = explicit_domains or sorted(domain_configs)
    for domain in considered:
        config = domain_configs[domain]
        if explicit_domains:
            result, basis = "TRUE", ["explicit domain scope"]
        elif config.get("always_screen"):
            result, basis = "TRUE", ["always_screen=true"]
        else:
            result = evaluate_group(config["surface_features"], "any_of", feature_map)
            basis = [f"surface_features.any_of={result}"]
        state = "SELECTED" if result == "TRUE" else "FILTERED" if result == "FALSE" else "DEFERRED"
        entry = {
            "domain": domain, "state": state, "evaluation": result,
            "surface_features": config["surface_features"], "basis": basis,
        }
        {"SELECTED": selected, "DEFERRED": deferred, "FILTERED": filtered}[state].append(entry)
    return selected, deferred, filtered


def compact_check(check: dict[str, Any], profile: str = "screen") -> dict[str, Any]:
    profile = {"compact": "screen", "full": "deep"}.get(profile, profile)
    result = {
        "canonical_id": check["canonical_id"], "title": check["title"],
        "trigger": check.get("trigger", []), "detection": check.get("detection", []),
    }
    if profile == "deep":
        result.update({key: check.get(key) for key in (
            "description", "risk", "type", "confidence", "fp_policy", "proof_policy",
            "verification", "applicability",
        )})
        result["false_positive_gates"] = check.get("false_positive_gates", []) if check.get("fp_policy") == "specific" else []
        result["proof"] = check.get("proof", []) if check.get("proof_policy") == "specific" else []
        result["provenance"] = [
            {key: value for key, value in entry.items() if key in {"label", "url", "kind", "locator"}}
            for entry in check.get("provenance", []) if entry.get("kind") == "official"
        ]
        if check.get("related"):
            result["related"] = check["related"]
    return result


def one_line(value: Any) -> str:
    return " ".join(str(part).strip() for part in value if str(part).strip()) if isinstance(value, list) else str(value).strip()


def selected_markdown(
    manifest: dict[str, Any], checks: list[dict[str, Any]], profile: str = "deep",
    candidate_ids: set[str] | None = None,
) -> str:
    profile = {"compact": "screen", "full": "deep"}.get(profile, profile)
    selected_by_id = {item["canonical_id"]: item for item in manifest["selected"]}
    checks = [check for check in checks if candidate_ids is None or check["canonical_id"] in candidate_ids]
    lines = [
        "<!-- GENERATED ROUTED CHECKS: source is data/canonical-checks.json; do not edit by hand. -->",
        "# Selected EVM Audit Checks", "",
        f"Routing result: {manifest['selected_count']} selected, {manifest['deferred_count']} deferred, {manifest['filtered_count']} filtered.",
        "Screen uncertainty escalates to Deep Review; it never filters a check.", "",
    ]
    if profile == "deep":
        lines.extend([
            "Global review contract: verify every reachable path before REVIEWED_SAFE; confirm only with reachable preconditions, concrete impact, and a runnable PoC/trace or deterministic invariant violation.", "",
        ])
    for check in checks:
        entry = compact_check(check, profile)
        selected = selected_by_id[check["canonical_id"]]
        lines.append(f"## [{entry['canonical_id']}] {entry['title']}")
        if profile == "deep":
            lines.extend([
                f"- **Type / confidence:** {entry['type']} / {entry['confidence']}",
                f"- **Risk:** {one_line(entry['risk'])}",
            ])
            if entry.get("applicability"):
                lines.append(f"- **Environment applicability:** `{json.dumps(entry['applicability'], ensure_ascii=False, sort_keys=True)}`")
        if profile == "deep":
            lines.append(f"- **Routing basis:** {one_line(selected['basis'])}")
        lines.extend([f"- **Trigger:** {one_line(entry['trigger'])}", f"- **Detection:** {one_line(entry['detection'])}"])
        if profile == "deep" and entry["false_positive_gates"]:
            lines.append(f"- **Specific FP:** {one_line(entry['false_positive_gates'])}")
        if profile == "deep" and entry["proof"]:
            lines.append(f"- **Specific proof:** {one_line(entry['proof'])}")
        if entry.get("provenance"):
            lines.append("- **Provenance:** " + "; ".join(
                f"[{item.get('label', 'source')}]({item['url']})" if item.get("url") else str(item.get("label", "source"))
                for item in entry["provenance"]
            ))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def domain_screening_markdown(deferred_domains: list[dict[str, Any]], domain_configs: dict[str, dict[str, Any]]) -> str:
    lines = ["# Deferred Domain Screening Cards", "", "A Deferred Domain must become Selected or Filtered before a clean/complete audit.", ""]
    for entry in deferred_domains:
        domain = entry["domain"]
        lines.extend([f"## {domain}", "", "Look for:"])
        lines.extend(f"- {term}" for term in domain_configs[domain]["screening_terms"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def evaluate_required_context(
    selected_domains: list[dict[str, Any]], domain_configs: dict[str, dict[str, Any]],
    supplied: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    supplied_domains = (supplied or {}).get("domains", {})
    if not isinstance(supplied_domains, dict):
        raise SelectionInputError("domain context must contain an object named domains")
    result: dict[str, Any] = {}
    unresolved: list[str] = []
    for domain_entry in selected_domains:
        domain = domain_entry["domain"]
        values = supplied_domains.get(domain, {})
        if not isinstance(values, dict):
            raise SelectionInputError(f"domain context for {domain} must be an object")
        result[domain] = {}
        for requirement in domain_configs[domain]["required_context"]:
            key = requirement["key"]
            value = values.get(key, {"status": "UNKNOWN"})
            if not isinstance(value, dict) or value.get("status") not in {"KNOWN", "NOT_APPLICABLE", "UNKNOWN"}:
                raise SelectionInputError(f"{domain}.{key} must have status KNOWN, NOT_APPLICABLE, or UNKNOWN")
            if value["status"] == "KNOWN" and ("value" not in value or not value.get("evidence")):
                raise SelectionInputError(f"{domain}.{key} KNOWN requires value and evidence")
            if value["status"] == "NOT_APPLICABLE" and not value.get("evidence"):
                raise SelectionInputError(f"{domain}.{key} NOT_APPLICABLE requires evidence")
            result[domain][key] = {"description": requirement["description"], **value}
            if requirement["required"] and value["status"] == "UNKNOWN":
                unresolved.append(f"{domain}.{key}")
    return result, unresolved


def select(
    registry: dict[str, Any],
    feature_map: dict[str, dict[str, Any]],
    names: set[str],
    scope_domains: list[str] | None,
    context: dict[str, Any] | None = None,
    domain_configs: dict[str, dict[str, Any]] | None = None,
    environment: dict[str, Any] | None = None,
    recon_context: dict[str, Any] | None = None,
    domain_context: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    environment = environment or {}
    if domain_configs is None:
        selected_domains = [{"domain": domain, "evaluation": "TRUE", "surface_features": [], "basis": ["explicit domain scope"]} for domain in (scope_domains or [])]
        if not selected_domains:
            selected_domains = [{"domain": domain, "evaluation": "TRUE", "surface_features": [], "basis": ["implicit scope"]} for domain in sorted({d for c in registry.get("checks", []) for d in c.get("domains", [])})]
        deferred_domains: list[dict[str, Any]] = []
        filtered_domains: list[dict[str, Any]] = []
    else:
        selected_domains, deferred_domains, filtered_domains = evaluate_domains(domain_configs, feature_map, scope_domains)
    selected_domain_ids = {entry["domain"] for entry in selected_domains}
    deferred_domain_ids = {entry["domain"] for entry in deferred_domains}
    filtered_domain_ids = {entry["domain"] for entry in filtered_domains}
    considered_domain_ids = selected_domain_ids | deferred_domain_ids | filtered_domain_ids

    selected: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    filtered: list[dict[str, Any]] = []
    selected_checks: list[dict[str, Any]] = []
    for check in registry.get("checks", []):
        domains = check.get("domains", [])
        scoped_domains = sorted(set(domains) & considered_domain_ids)
        if not scoped_domains:
            continue
        active_domains = sorted(set(domains) & selected_domain_ids)
        deferred_for_check = sorted(set(domains) & deferred_domain_ids)
        filtered_for_check = sorted(set(domains) & filtered_domain_ids)
        owner_domain = check.get("primary_domain")
        if not active_domains:
            bucket_domains = deferred_for_check or filtered_for_check
            if owner_domain not in bucket_domains:
                owner_domain = bucket_domains[0]
            route_entry = {
                "canonical_id": check["canonical_id"], "title": check.get("title", ""), "domains": domains,
                "owner_domain": owner_domain, "freshness": check.get("freshness"), "verified_at": check.get("verified_at"),
                "route_status": "DEFERRED_DOMAIN" if deferred_for_check else "FILTERED_DOMAIN",
                "environment_evaluation": "NOT_EVALUATED", "environment_basis": [],
                "predicate": check.get("predicate"), "predicate_source": check.get("predicate_source"),
                "predicate_evaluation": "NOT_EVALUATED", "feature_evaluation": "NOT_EVALUATED",
                "matched_features": [], "unknown_features": [],
                "basis": [f"domain={bucket_domains[0]}:{'DEFERRED' if deferred_for_check else 'FILTERED'}"],
            }
            (deferred if deferred_for_check else filtered).append(route_entry)
            continue
        environment_result, environment_basis = evaluate_environment(check, environment)
        feature = evaluate_check(check, feature_map, names)
        if owner_domain not in active_domains:
            owner_domain = active_domains[0]
        if environment_result == "FALSE":
            route_status = "FILTERED_ENVIRONMENT"
        elif feature["result"] == "FALSE":
            route_status = "FILTERED_FEATURE"
        else:
            route_status = "SELECTED"
        route_entry = {
            "canonical_id": check["canonical_id"], "title": check.get("title", ""), "domains": domains,
            "owner_domain": owner_domain, "freshness": check.get("freshness"), "verified_at": check.get("verified_at"),
            "route_status": route_status, "environment_evaluation": environment_result, "environment_basis": environment_basis,
            "predicate": feature["predicate"], "predicate_source": feature["predicate_source"],
            "predicate_evaluation": feature["predicate_result"], "feature_evaluation": feature["result"],
            "matched_features": feature["matched_features"], "unknown_features": feature["unknown_features"],
            "basis": [*environment_basis, *feature["basis"]],
        }
        if route_status == "SELECTED":
            selected.append(route_entry)
            selected_checks.append(check)
        else:
            filtered.append(route_entry)

    required_context, unresolved_context = evaluate_required_context(
        selected_domains, domain_configs or {}, domain_context,
    ) if domain_configs else ({}, [])
    if deferred_domains:
        completion_status = "COMPLETE_WITH_UNRESOLVED_DOMAIN_ROUTING"
    elif unresolved_context:
        completion_status = "COMPLETE_WITH_UNRESOLVED_CONTEXT"
    else:
        completion_status = "READY_FOR_REVIEW"
    manifest = {
        "schema_version": ROUTING_MANIFEST_VERSION,
        "stage": "ENVIRONMENT_DOMAIN_CHECK_ROUTING",
        "audit_context": context or {
            "selector_version": SELECTOR_VERSION, "registry_sha256": registry_sha256(registry),
            "knowledge_commit": None, "knowledge_dirty": None, "target_repo_commit": None,
            "source_digest": (recon_context or {}).get("source_digest"),
            "audit_source_digest": (recon_context or {}).get("audit_source_digest"),
            "dependency_digest": (recon_context or {}).get("dependency_digest"),
            "build_config_digest": (recon_context or {}).get("build_config_digest"),
            "compilation_digest": (recon_context or {}).get("compilation_digest"),
            "chain_id": None, "chain_family": None,
            "execution_environment": None, "fork_block": None, "fork_block_semantics": "reproducibility metadata only; does not derive evm_fork",
            "compiler_version": None, "evm_fork": None, "protocol_version": None, "environment_facts": {},
            "audit_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
        "scope": {"domains": scope_domains, "candidate_count": len(selected) + len(deferred) + len(filtered)},
        "feature_map": {"schema_version": FEATURE_MAP_VERSION, "recon_context": recon_context, "features": feature_map},
        "selected_domains": selected_domains, "deferred_domains": deferred_domains, "filtered_domains": filtered_domains,
        "required_context": required_context,
        "completion_gate": {
            "status": completion_status,
            "unresolved_deferred_domains": sorted(deferred_domain_ids),
            "unresolved_required_context": unresolved_context,
        },
        "selected_count": len(selected), "deferred_count": len(deferred), "filtered_count": len(filtered),
        "selected": selected, "deferred": deferred, "filtered": filtered,
        "filtered_out": [entry["canonical_id"] for entry in filtered],
    }
    return manifest, selected_checks


def load_domains(root: Path) -> dict[str, dict[str, Any]]:
    configs = {}
    for path in sorted((root / "domains").glob("*.json")):
        if path.name == "domain.schema.json":
            continue
        value = load_json(path)
        configs[value["id"]] = value
    return configs


def parse_domains(args: argparse.Namespace, known: set[str]) -> list[str] | None:
    if args.domain and args.domains:
        raise SelectionInputError("use only one of --domain and --domains")
    raw = args.domain or args.domains
    if not raw:
        return None
    values = sorted({value.strip() for value in raw.split(",") if value.strip()})
    unknown = sorted(set(values) - known)
    if not values or unknown:
        raise SelectionInputError(f"unknown or empty domain scope: {', '.join(unknown)}")
    return values


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--feature-map", type=Path, required=True, help="scope-bound Feature Map v3")
    parser.add_argument("--target-root", type=Path, required=True, help="current audit scope used to verify recon source_digest")
    parser.add_argument("--exclude", action="append", default=[], help="additional audit-scope glob; must match Recon")
    parser.add_argument("--domain", help="explicit single-domain scope")
    parser.add_argument("--domains", help="explicit comma-separated domain scope")
    parser.add_argument("--emit-checks", action="store_true", help="include/render selected check bodies on stdout")
    parser.add_argument("--profile", choices=("screen", "deep", "full", "compact"), default="screen")
    parser.add_argument("--candidate-ids", help="comma-separated selected IDs to promote from screen to deep")
    parser.add_argument("--target-commit")
    parser.add_argument("--chain-id", type=int)
    parser.add_argument("--chain-family")
    parser.add_argument("--execution-environment", choices=("ethereum-evm", "eravm-native", "zksync-evm-interpreter"))
    parser.add_argument("--fork-block", type=int, help="reproducibility metadata only; does not derive --evm-fork")
    parser.add_argument("--compiler-version")
    parser.add_argument("--evm-fork", choices=HARD_FORKS)
    parser.add_argument("--protocol-version")
    parser.add_argument("--audit-timestamp")
    parser.add_argument("--manifest-out", type=Path)
    parser.add_argument("--checks-out", type=Path, help="single-domain selected Markdown")
    parser.add_argument("--runtime-dir", type=Path, help="write selected-<owner-domain>.md files")
    parser.add_argument("--context-out", type=Path)
    parser.add_argument("--screening-out", type=Path, help="write tiny screening cards for Deferred Domains")
    parser.add_argument("--domain-context", type=Path, help="evidence-backed required Domain context JSON")
    parser.add_argument("--format", choices=("text", "json", "markdown"), default="text")
    args = parser.parse_args(argv)
    root = args.root.resolve()

    try:
        registry = load_json(root / "data" / "canonical-checks.json")
        feature_data = load_json(root / "data" / "features.json")
        names, policies = vocabulary(feature_data)
        raw_feature_map = load_json(args.feature_map.resolve())
        exclusions = tuple(args.exclude)
        feature_map = normalize_feature_map(raw_feature_map, names, policies, args.target_root, exclusions)
        recon_context = validate_recon_context(raw_feature_map["recon_context"], args.target_root, exclusions)
        domain_configs = load_domains(root)
        scope_domains = parse_domains(args, set(domain_configs))
        if args.checks_out and (not scope_domains or len(scope_domains) != 1):
            raise SelectionInputError("--checks-out requires exactly one --domain")
        context = audit_context(
            root, registry, recon_context, target_root=args.target_root, target_commit=args.target_commit,
            chain_id=args.chain_id, chain_family=args.chain_family, execution_environment=args.execution_environment,
            fork_block=args.fork_block, compiler_version=args.compiler_version, evm_fork=args.evm_fork,
            protocol_version=args.protocol_version, audit_timestamp=args.audit_timestamp,
        )
        environment = {key: context[key] for key in ("chain_id", "chain_family", "execution_environment", "compiler_version", "evm_fork", "protocol_version")}
        environment["environment_facts"] = context["environment_facts"]
        domain_context = load_json(args.domain_context.resolve()) if args.domain_context else None
        manifest, checks = select(registry, feature_map, names, scope_domains, context, domain_configs, environment, recon_context, domain_context)
        candidate_ids = {value.strip() for value in (args.candidate_ids or "").split(",") if value.strip()} or None
        selected_ids = {entry["canonical_id"] for entry in manifest["selected"]}
        if candidate_ids and not candidate_ids <= selected_ids:
            raise SelectionInputError(f"candidate IDs are not selected: {', '.join(sorted(candidate_ids - selected_ids))}")
        if candidate_ids and {"compact": "screen", "full": "deep"}.get(args.profile, args.profile) != "deep":
            raise SelectionInputError("--candidate-ids requires --profile deep")

        if args.manifest_out:
            write_text(args.manifest_out, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        if args.context_out:
            write_text(args.context_out, json.dumps(context, ensure_ascii=False, indent=2) + "\n")
        if args.checks_out:
            write_text(args.checks_out, selected_markdown(manifest, checks, args.profile, candidate_ids))
        if args.screening_out:
            write_text(args.screening_out, domain_screening_markdown(manifest["deferred_domains"], domain_configs))
        if args.runtime_dir:
            by_owner: dict[str, list[dict[str, Any]]] = {}
            owner_by_id = {entry["canonical_id"]: entry["owner_domain"] for entry in manifest["selected"]}
            for check in checks:
                by_owner.setdefault(owner_by_id[check["canonical_id"]], []).append(check)
            for owner, owner_checks in sorted(by_owner.items()):
                write_text(args.runtime_dir / f"selected-{owner}.md", selected_markdown(manifest, owner_checks, args.profile, candidate_ids))

        output_manifest = dict(manifest)
        if args.emit_checks:
            output_manifest["selected_checks"] = [compact_check(check, args.profile) for check in checks if candidate_ids is None or check["canonical_id"] in candidate_ids]
        if args.format == "json":
            print(json.dumps(output_manifest, ensure_ascii=False, indent=2))
        elif args.format == "markdown":
            print(selected_markdown(manifest, checks, args.profile, candidate_ids), end="")
        else:
            print(f"stage={manifest['stage']} selected_domains={len(manifest['selected_domains'])} deferred_domains={len(manifest['deferred_domains'])} selected={manifest['selected_count']} deferred={manifest['deferred_count']} filtered={manifest['filtered_count']}")
            for entry in manifest["selected"]:
                print(f"{entry['canonical_id']}\t{','.join(entry['matched_features']) or 'UNKNOWN/always_screen'}\t{entry['title']}")
        return 0
    except (OSError, KeyError, SelectionInputError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
