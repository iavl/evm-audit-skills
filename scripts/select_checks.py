#!/usr/bin/env python3
"""Route canonical checks from an evidence-backed reconnaissance feature map.

The selector is deliberately conservative: only a curated predicate can
fast-filter on ``FALSE``. A false keyword-inferred predicate is downgraded to
``UNKNOWN`` and remains selected for inspection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FEATURE_STATES = {"PRESENT", "ABSENT_CONFIRMED", "UNKNOWN"}
PREDICATE_KEYS = ("all_of", "any_of", "none_of")
SELECTOR_VERSION = "2"
ROUTING_MANIFEST_VERSION = 2


class SelectionInputError(ValueError):
    """Raised when the feature map or predicate cannot be evaluated safely."""


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
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def audit_context(
    root: Path,
    registry: dict[str, Any],
    *,
    target_root: Path | None = None,
    target_commit: str | None = None,
    chain_id: int | None = None,
    fork_block: int | None = None,
    compiler_version: str | None = None,
    audit_timestamp: str | None = None,
) -> dict[str, Any]:
    resolved_target = target_root.resolve() if target_root else None
    return {
        "selector_version": SELECTOR_VERSION,
        "registry_sha256": registry_sha256(registry),
        "knowledge_commit": git_value(root, "rev-parse", "HEAD"),
        "knowledge_dirty": bool(git_value(root, "status", "--short")),
        "target_commit": target_commit or (git_value(resolved_target, "rev-parse", "HEAD") if resolved_target else None),
        "chain_id": chain_id,
        "fork_block": fork_block,
        "compiler_version": compiler_version,
        "audit_timestamp": audit_timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def vocabulary(feature_data: dict[str, Any]) -> tuple[set[str], dict[str, str]]:
    values = feature_data.get("features")
    if not isinstance(values, dict):
        raise SelectionInputError("feature registry must contain an object named 'features'")
    names = set(values)
    aliases = feature_data.get("legacy_aliases", {}) or {}
    if not isinstance(aliases, dict) or any(not isinstance(key, str) or not isinstance(value, str) for key, value in aliases.items()):
        raise SelectionInputError("feature registry legacy_aliases must map strings to strings")
    for alias, target in aliases.items():
        if target not in names:
            raise SelectionInputError(f"legacy feature alias {alias!r} points to unknown feature {target!r}")
    return names, aliases


def _evidence(value: Any, feature: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise SelectionInputError(f"feature {feature!r} evidence must be a non-empty string list")
    return [item.strip() for item in value]


def normalize_feature_map(raw: dict[str, Any], names: set[str]) -> dict[str, dict[str, Any]]:
    if raw.get("schema_version") != 1:
        raise SelectionInputError("feature map schema_version must be 1")
    entries = raw.get("features")
    if not isinstance(entries, dict):
        raise SelectionInputError("feature map must contain an object named 'features'")
    unknown = sorted(set(entries) - names)
    if unknown:
        raise SelectionInputError(f"unknown features in feature map: {', '.join(unknown)}")

    normalized: dict[str, dict[str, Any]] = {}
    for feature, entry in entries.items():
        if isinstance(entry, str):
            status = entry
            evidence: list[str] = []
            reason = ""
        elif isinstance(entry, dict):
            status = entry.get("status")
            evidence = _evidence(entry.get("evidence"), feature)
            reason = entry.get("reason", "")
            if not isinstance(reason, str):
                raise SelectionInputError(f"feature {feature!r} reason must be a string")
        else:
            raise SelectionInputError(f"feature {feature!r} must be an object with status/evidence")
        if status not in FEATURE_STATES:
            raise SelectionInputError(f"feature {feature!r} status must be one of {sorted(FEATURE_STATES)}")
        if status != "UNKNOWN" and not evidence:
            raise SelectionInputError(f"feature {feature!r} status {status} requires concrete evidence")
        normalized[feature] = {"status": status, "evidence": evidence}
        if reason.strip():
            normalized[feature]["reason"] = reason.strip()
    return normalized


def legacy_feature_map(raw_features: str, names: set[str], aliases: dict[str, str]) -> dict[str, dict[str, Any]]:
    requested: list[str] = []
    for value in raw_features.split(","):
        value = value.strip()
        if not value:
            continue
        requested.append(aliases.get(value, value))
    unknown = sorted(set(requested) - names)
    if unknown:
        raise SelectionInputError(f"unknown features: {', '.join(unknown)}")
    return {
        feature: {
            "status": "PRESENT" if feature in requested else "UNKNOWN",
            "evidence": ["legacy --features shorthand"] if feature in requested else [],
        }
        for feature in names
    }


def status_for(feature: str, feature_map: dict[str, dict[str, Any]]) -> str:
    return feature_map.get(feature, {"status": "UNKNOWN"})["status"]


def evaluate_group(features: list[str], mode: str, feature_map: dict[str, dict[str, Any]]) -> str:
    """Evaluate one logical predicate group using three-valued logic."""

    if not features:
        return "TRUE"
    states = [status_for(feature, feature_map) for feature in features]
    if mode == "all_of":
        if "ABSENT_CONFIRMED" in states:
            return "FALSE"
        if all(state == "PRESENT" for state in states):
            return "TRUE"
        return "UNKNOWN"
    if mode == "any_of":
        if "PRESENT" in states:
            return "TRUE"
        if all(state == "ABSENT_CONFIRMED" for state in states):
            return "FALSE"
        return "UNKNOWN"
    if mode == "none_of":
        if "PRESENT" in states:
            return "FALSE"
        if all(state == "ABSENT_CONFIRMED" for state in states):
            return "TRUE"
        return "UNKNOWN"
    raise AssertionError(f"unsupported predicate group: {mode}")


def check_predicate(check: dict[str, Any], names: set[str]) -> dict[str, list[str]]:
    predicate = check.get("predicate")
    if predicate is None:
        # Transitional support for schema-v1 registries. Domain names are
        # metadata, not code-surface evidence, and must never route a check.
        legacy = [feature for feature in check.get("features", []) if not feature.startswith("evm-audit-")]
        if legacy:
            return {"all_of": [], "any_of": sorted(set(legacy)), "none_of": []}
        return {"all_of": [], "any_of": [], "none_of": []}
    if not isinstance(predicate, dict):
        raise SelectionInputError(f"{check.get('canonical_id')}: predicate must be an object")
    normalized: dict[str, list[str]] = {}
    for key in PREDICATE_KEYS:
        values = predicate.get(key, [])
        if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
            raise SelectionInputError(f"{check.get('canonical_id')}: predicate.{key} must be a string list")
        normalized[key] = sorted(set(values))
        unknown = sorted(set(normalized[key]) - names)
        if unknown:
            raise SelectionInputError(f"{check.get('canonical_id')}: unknown predicate features: {', '.join(unknown)}")
    return normalized


def evaluate_check(check: dict[str, Any], feature_map: dict[str, dict[str, Any]], names: set[str]) -> dict[str, Any]:
    if check.get("always_screen") is True:
        raw_predicate = check.get("predicate", {}) or {}
        if not isinstance(raw_predicate, dict):
            raise SelectionInputError(f"{check.get('canonical_id')}: predicate must be an object")
        if any(raw_predicate.get(key, []) for key in PREDICATE_KEYS):
            raise SelectionInputError(f"{check.get('canonical_id')}: always_screen cannot accompany a non-empty predicate")
        return {
            "result": "TRUE",
            "predicate_result": "TRUE",
            "predicate_source": check.get("predicate_source", "curated"),
            "predicate": {"all_of": [], "any_of": [], "none_of": []},
            "matched_features": [],
            "unknown_features": [],
            "basis": ["always_screen=true"],
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
        "result": result,
        "predicate_result": predicate_result,
        "predicate_source": predicate_source,
        "predicate": predicate,
        "matched_features": matched,
        "unknown_features": unknown,
        "basis": basis or ["empty predicate"],
    }


def compact_check(check: dict[str, Any], include_provenance: bool = True) -> dict[str, Any]:
    """Return only the fields needed by a domain agent for deep review."""

    result = {
        "canonical_id": check["canonical_id"],
        "title": check["title"],
        "type": check.get("type"),
        "confidence": check.get("confidence"),
        "freshness": check.get("freshness"),
        "verified_at": check.get("verified_at"),
        "predicate": check.get("predicate", {"all_of": [], "any_of": [], "none_of": []}),
        "trigger": check.get("trigger", []),
        "risk": check.get("risk", []),
        "detection": check.get("detection", []),
        "false_positive_gates": check.get("false_positive_gates", []),
        "proof": check.get("proof", []),
    }
    if include_provenance:
        result["provenance"] = [
            {key: value for key, value in entry.items() if key in {"label", "url", "kind", "locator"}}
            for entry in check.get("provenance", [])
        ]
    if check.get("related"):
        result["related"] = check["related"]
    return result


def one_line(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(str(part).strip() for part in value if str(part).strip())
    return str(value).strip()


def selected_markdown(manifest: dict[str, Any], checks: list[dict[str, Any]], profile: str = "full") -> str:
    lines = [
        "<!-- GENERATED ROUTED CHECKS: source is data/canonical-checks.json; do not edit by hand. -->",
        "# Selected EVM Audit Checks",
        "",
        f"Routing result: {manifest['selected_count']} selected, {manifest['filtered_count']} filtered; UNKNOWN remains selected.",
        "",
    ]
    for check in checks:
        entry = compact_check(check, include_provenance=profile == "full")
        selected = next(item for item in manifest["selected"] if item["canonical_id"] == check["canonical_id"])
        lines.append(f"## [{entry['canonical_id']}] {entry['title']}")
        if profile == "full":
            lines.extend([
                f"- **Type / confidence:** {entry['type']} / {entry['confidence']}",
                f"- **Predicate:** all_of={','.join(entry['predicate']['all_of']) or '-'}; any_of={','.join(entry['predicate']['any_of']) or '-'}; none_of={','.join(entry['predicate']['none_of']) or '-'}",
            ])
        lines.extend([
            f"- **Freshness:** {entry['freshness']} / verified_at={entry['verified_at'] or 'unverified'}",
            f"- **Routing basis:** {one_line(selected['basis'])}",
            f"- **Trigger:** {one_line(entry['trigger'])}",
            f"- **Risk:** {one_line(entry['risk'])}",
            f"- **Detection:** {one_line(entry['detection'])}",
            f"- **FP:** {one_line(entry['false_positive_gates'])}",
            f"- **Proof:** {one_line(entry['proof'])}",
        ])
        if entry.get("provenance"):
            source = "; ".join(
                f"[{item.get('label', 'source')}]({item['url']})" if item.get("url") else str(item.get("label", "source"))
                for item in entry["provenance"]
            )
            lines.append(f"- **Provenance:** {source}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def select(
    registry: dict[str, Any],
    feature_map: dict[str, dict[str, Any]],
    names: set[str],
    scope_domains: list[str] | None,
    context: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    selected: list[dict[str, Any]] = []
    filtered: list[dict[str, Any]] = []
    selected_checks: list[dict[str, Any]] = []
    for check in registry.get("checks", []):
        domains = check.get("domains", [])
        if scope_domains and not set(domains) & set(scope_domains):
            continue
        evaluation = evaluate_check(check, feature_map, names)
        owner_domain = check.get("primary_domain")
        if scope_domains and owner_domain not in scope_domains:
            owner_domain = next((domain for domain in scope_domains if domain in domains), owner_domain)
        route_entry = {
            "canonical_id": check["canonical_id"],
            "title": check.get("title", ""),
            "domains": domains,
            "owner_domain": owner_domain,
            "freshness": check.get("freshness"),
            "verified_at": check.get("verified_at"),
            "predicate": evaluation["predicate"],
            "predicate_source": evaluation["predicate_source"],
            "predicate_evaluation": evaluation["predicate_result"],
            "evaluation": evaluation["result"],
            "matched_features": evaluation["matched_features"],
            "unknown_features": evaluation["unknown_features"],
            "basis": evaluation["basis"],
        }
        if evaluation["result"] == "FALSE":
            filtered.append(route_entry)
        else:
            selected.append(route_entry)
            selected_checks.append(check)

    manifest = {
        "schema_version": ROUTING_MANIFEST_VERSION,
        "stage": "FAST_FILTER",
        "audit_context": context or {
            "selector_version": SELECTOR_VERSION,
            "registry_sha256": registry_sha256(registry),
            "knowledge_commit": None,
            "knowledge_dirty": None,
            "target_commit": None,
            "chain_id": None,
            "fork_block": None,
            "compiler_version": None,
            "audit_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
        "scope": {"domains": scope_domains, "candidate_count": len(selected) + len(filtered)},
        "feature_map": {"schema_version": 1, "features": feature_map},
        "features": feature_map,
        "selected_count": len(selected),
        "filtered_count": len(filtered),
        "selected": selected,
        "filtered": filtered,
        "filtered_out": [entry["canonical_id"] for entry in filtered],
    }
    return manifest, selected_checks


def selected_checks(
    registry: dict[str, Any], features: set[str], domain: str | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Compatibility wrapper for callers of the schema-v1 helper.

    Requested features are PRESENT and all other referenced features are
    UNKNOWN, so this wrapper cannot create a false negative. New callers
    should use :func:`select` with an evidence-backed feature map.
    """

    referenced = {
        feature
        for check in registry.get("checks", [])
        for values in (check.get("predicate", {}) or {}).values()
        for feature in values
    }
    names = referenced | set(features)
    feature_map = {
        feature: {
            "status": "PRESENT" if feature in features else "UNKNOWN",
            "evidence": ["legacy selected_checks wrapper"] if feature in features else [],
        }
        for feature in names
    }
    manifest, _ = select(registry, feature_map, names, [domain] if domain else None)
    by_id = {check["canonical_id"]: check for check in registry.get("checks", [])}
    selected = [by_id[entry["canonical_id"]] for entry in manifest["selected"]]
    filtered = [by_id[entry["canonical_id"]] for entry in manifest["filtered"]]
    return selected, filtered


def parse_domains(args: argparse.Namespace, registry: dict[str, Any]) -> list[str] | None:
    if args.domain and args.domains:
        raise SelectionInputError("use only one of --domain and --domains")
    raw = args.domain or args.domains
    if not raw:
        return None
    values = sorted({value.strip() for value in raw.split(",") if value.strip()})
    if not values:
        raise SelectionInputError("domain scope must contain at least one domain")
    known = {domain for check in registry.get("checks", []) for domain in check.get("domains", [])}
    unknown = sorted(set(values) - known)
    if unknown:
        raise SelectionInputError(f"unknown domains: {', '.join(unknown)}")
    return values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--feature-map", type=Path, help="JSON feature map with PRESENT/ABSENT_CONFIRMED/UNKNOWN evidence")
    source.add_argument("--features", help="legacy comma-separated PRESENT feature shorthand; omitted features remain UNKNOWN")
    parser.add_argument("--domain", help="limit selection to one domain skill")
    parser.add_argument("--domains", help="comma-separated in-scope domains for a global manifest")
    parser.add_argument("--emit-checks", action="store_true", help="include selected check bodies in JSON or render them in Markdown")
    parser.add_argument("--profile", choices=("full", "compact"), default="full", help="selected-check body profile; compact omits provenance and repeated metadata")
    parser.add_argument("--target-root", type=Path, help="target repository used to resolve target_commit")
    parser.add_argument("--target-commit", help="explicit target repository commit")
    parser.add_argument("--chain-id", type=int, help="deployment chain ID")
    parser.add_argument("--fork-block", type=int, help="fork or state snapshot block")
    parser.add_argument("--compiler-version", help="compiler version used by the audited artifact")
    parser.add_argument("--audit-timestamp", help="explicit ISO-8601 audit timestamp; defaults to current UTC")
    parser.add_argument("--format", choices=("text", "json", "markdown"), default="text")
    args = parser.parse_args(argv)
    root = args.root.resolve()

    try:
        registry = load_json(root / "data" / "canonical-checks.json")
        feature_data = load_json(root / "data" / "features.json")
        names, aliases = vocabulary(feature_data)
        if args.feature_map:
            feature_map = normalize_feature_map(load_json(args.feature_map.resolve()), names)
        else:
            feature_map = legacy_feature_map(args.features or "", names, aliases)
        feature_map = {
            feature: feature_map.get(feature, {"status": "UNKNOWN", "evidence": []})
            for feature in sorted(names)
        }
        scope_domains = parse_domains(args, registry)
        context = audit_context(
            root,
            registry,
            target_root=args.target_root,
            target_commit=args.target_commit,
            chain_id=args.chain_id,
            fork_block=args.fork_block,
            compiler_version=args.compiler_version,
            audit_timestamp=args.audit_timestamp,
        )
        manifest, selected_checks = select(registry, feature_map, names, scope_domains, context)
        if args.emit_checks:
            manifest["selected_checks"] = [
                compact_check(check, include_provenance=args.profile == "full") for check in selected_checks
            ]

        if args.format == "json":
            print(json.dumps(manifest, ensure_ascii=False, indent=2))
        elif args.format == "markdown":
            print(selected_markdown(manifest, selected_checks, args.profile), end="")
        else:
            print(f"stage={manifest['stage']} selected={manifest['selected_count']} filtered={manifest['filtered_count']}")
            for entry in manifest["selected"]:
                print(f"{entry['canonical_id']}\t{','.join(entry['matched_features']) or 'UNKNOWN/always_screen'}\t{entry['title']}")
            if manifest["filtered"]:
                print("filtered_out=" + ",".join(entry["canonical_id"] for entry in manifest["filtered"]))
        return 0
    except (OSError, KeyError, SelectionInputError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
