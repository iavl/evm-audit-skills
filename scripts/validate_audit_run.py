#!/usr/bin/env python3
"""Derive audit completion from immutable routing and run artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from audit_artifacts import (
        load_json,
        validate_artifact_identity,
        validate_schema,
    )
    from render_runtime import selected_entries, validate_manifest, validate_screen_results
    from review_ledger import load, validate_records
    from select_checks import load_domains
except ImportError:  # pragma: no cover
    from scripts.audit_artifacts import load_json, validate_artifact_identity, validate_schema
    from scripts.render_runtime import selected_entries, validate_manifest, validate_screen_results
    from scripts.review_ledger import load, validate_records
    from scripts.select_checks import load_domains


ROOT = Path(__file__).resolve().parents[1]
def _identity_error(value: dict[str, Any], manifest: dict[str, Any]) -> str | None:
    try:
        validate_artifact_identity(value, manifest)
    except ValueError as error:
        return str(error)
    return None


def _domain_ids(manifest: dict[str, Any], bucket: str) -> set[str]:
    return {entry["domain"] for entry in manifest.get(bucket, [])}


def validate_domain_resolution(root: Path, manifest: dict[str, Any], value: dict[str, Any], domain_configs: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    try:
        validate_schema(root, "domain-resolution.schema.json", value)
    except ValueError as error:
        errors.append(str(error))
        return errors
    if (identity_error := _identity_error(value, manifest)):
        errors.append(identity_error)
    for key, expected in manifest.get("audit_context", {}).items():
        if value.get(key) != expected:
            errors.append(f"context {key} does not match manifest")
    deferred = _domain_ids(manifest, "deferred_domains")
    actual = set(value["domains"])
    if actual != deferred:
        errors.append(f"domain resolution must contain exactly Deferred Domains: expected={sorted(deferred)} actual={sorted(actual)}")
    for domain, resolution in value["domains"].items():
        if domain not in domain_configs:
            errors.append(f"unknown resolved Domain: {domain}")
            continue
        status = resolution["status"]
        evidence = resolution["evidence"]
        manifest_policy = next((entry.get("trusted_absence_policy") for entry in manifest.get("deferred_domains", []) if entry.get("domain") == domain), None)
        policy = domain_configs[domain].get("trusted_absence_policy", {})
        if manifest_policy != policy:
            errors.append(f"{domain}: trusted_absence_policy changed after routing snapshot")
        allowed = set(policy.get("allowed_evidence", []))
        if status == "ABSENT_CONFIRMED":
            kinds = {item["kind"] for item in evidence}
            if resolution["scope_complete"] is not True:
                errors.append(f"{domain}: ABSENT_CONFIRMED requires scope_complete=true")
            if not kinds or not kinds <= allowed or "scope" not in kinds:
                errors.append(f"{domain}: absence evidence violates trusted_absence_policy")
        elif status == "PRESENT" and not evidence:
            errors.append(f"{domain}: PRESENT requires evidence")
        elif status == "UNKNOWN":
            errors.append(f"{domain}: Deferred Domain remains UNKNOWN")
    return errors


def validate_context(root: Path, manifest: dict[str, Any], value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        validate_schema(root, "audit-context.schema.json", value)
    except ValueError as error:
        errors.append(str(error))
    if (identity_error := _identity_error(value, manifest)):
        errors.append(identity_error)
    unresolved: list[str] = []
    required_context = manifest.get("required_context", {})
    if not isinstance(required_context, dict):
        return errors + ["required_context must be an object"]
    for domain, requirements in required_context.items():
        if not isinstance(requirements, dict):
            errors.append(f"required_context.{domain} must be an object")
            continue
        for key, item in requirements.items():
            if not isinstance(item, dict) or item.get("status") not in {"KNOWN", "NOT_APPLICABLE", "UNKNOWN"}:
                errors.append(f"required_context.{domain}.{key} has an invalid status")
                continue
            if item["status"] == "KNOWN" and ("value" not in item or not item.get("evidence")):
                errors.append(f"required_context.{domain}.{key} KNOWN requires value and evidence")
            if item["status"] == "NOT_APPLICABLE" and not item.get("evidence"):
                errors.append(f"required_context.{domain}.{key} NOT_APPLICABLE requires evidence")
            if item["status"] == "UNKNOWN":
                unresolved.append(f"{domain}.{key}")
    declared = sorted(manifest.get("unresolved_required_context", []))
    if sorted(unresolved) != declared:
        errors.append(f"unresolved_required_context is not independently reproducible: expected={sorted(unresolved)} actual={declared}")
    return errors


def _record_map(paths: list[Path], manifest: dict[str, Any], registry: dict[str, Any], candidates: set[str]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    records: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for path in paths:
        try:
            values = load(path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"{path}: {error}")
            continue
        errors.extend(f"{path}: {error}" for error in validate_records(values, manifest, registry, candidates))
        for record in values:
            if record.get("record_type") != "review":
                continue
            canonical_id = record.get("canonical_id")
            if canonical_id not in candidates:
                continue
            if canonical_id in records:
                errors.append(f"duplicate Deep record across ledgers: {canonical_id}")
            else:
                records[canonical_id] = record
    return records, errors


def validate_run(
    root: Path,
    manifest: dict[str, Any],
    registry: dict[str, Any],
    screen_results: dict[str, Any] | None,
    domain_resolution: dict[str, Any] | None,
    context: dict[str, Any] | None,
    ledger_paths: list[Path],
) -> dict[str, Any]:
    invalid: list[str] = []
    coverage_errors: list[str] = []
    domain_errors: list[str] = []
    context_errors: list[str] = []
    review_errors: list[str] = []

    try:
        validate_manifest(root, manifest, registry)
    except (ValueError, KeyError) as error:
        invalid.append(str(error))

    try:
        selected = {entry["canonical_id"] for entry in selected_entries(manifest, domain_resolution=domain_resolution)}
    except (KeyError, TypeError) as error:
        invalid.append(f"invalid routing manifest selection buckets: {error}")
        selected = set()
    if any(isinstance(entry, dict) and entry.get("route_status") == "SELECTED" for entry in manifest.get("deferred", [])):
        coverage_errors.append("Deferred bucket contains a selected route")

    screen_not_applicable: set[str] = set()
    candidates: set[str] = set()
    if screen_results is None:
        coverage_errors.append("screen-results.json is required")
    else:
        identity = _identity_error(screen_results, manifest)
        if identity:
            invalid.append(identity)
        try:
            candidates = validate_screen_results(root, manifest, screen_results, domain_resolution)
            screen_not_applicable = selected - candidates
        except (ValueError, KeyError) as error:
            coverage_errors.append(str(error))
            raw_results = screen_results.get("results", [])
            if isinstance(raw_results, list):
                candidates = {item["canonical_id"] for item in raw_results if isinstance(item, dict) and isinstance(item.get("canonical_id"), str) and item.get("result") == "CANDIDATE"}
                screen_not_applicable = {item["canonical_id"] for item in raw_results if isinstance(item, dict) and isinstance(item.get("canonical_id"), str) and item.get("result") == "NOT_APPLICABLE_CONFIRMED"}

    if screen_not_applicable & candidates or screen_not_applicable | candidates != selected:
        coverage_errors.append("coverage equation failed: selected_ids != screen_not_applicable_ids union deep_candidate_ids")

    domain_configs = load_domains(root)
    deferred_domains = _domain_ids(manifest, "deferred_domains")
    if deferred_domains and domain_resolution is None:
        domain_errors.append("domain-resolution.json is required for Deferred Domains")
    elif domain_resolution is not None:
        identity = _identity_error(domain_resolution, manifest)
        if identity:
            invalid.append(identity)
        for error in validate_domain_resolution(root, manifest, domain_resolution, domain_configs):
            (invalid if "changed after routing snapshot" in error else domain_errors).append(error)

    if context is not None:
        context_errors.extend(validate_context(root, manifest, context))
    else:
        expected_context = []
        required_context = manifest.get("required_context", {})
        if isinstance(required_context, dict):
            for domain, requirements in required_context.items():
                if isinstance(requirements, dict):
                    for key, item in requirements.items():
                        if isinstance(item, dict) and item.get("status") == "UNKNOWN":
                            expected_context.append(f"{domain}.{key}")
                else:
                    context_errors.append(f"required_context.{domain} must be an object")
        else:
            context_errors.append("required_context must be an object")
        if sorted(expected_context) != sorted(manifest.get("unresolved_required_context", [])):
            context_errors.append("unresolved_required_context is not independently reproducible")
    if manifest.get("unresolved_required_context"):
        context_errors.append("required Domain context remains unresolved")

    records, ledger_errors = _record_map(ledger_paths, manifest, registry, candidates)
    review_errors.extend(ledger_errors)
    reviewed = set(records)
    if candidates - reviewed:
        review_errors.append(f"missing Deep record(s): {sorted(candidates - reviewed)}")

    statuses = {canonical_id: record.get("status") for canonical_id, record in records.items()}
    suspicious = {canonical_id for canonical_id, status in statuses.items() if status == "SUSPICIOUS"}
    confirmed = {canonical_id for canonical_id, status in statuses.items() if status == "CONFIRMED"}
    unresolved = suspicious | (candidates - reviewed)
    if suspicious:
        review_errors.append(f"SUSPICIOUS records block clean completion: {sorted(suspicious)}")

    if invalid:
        status = "INVALID_SNAPSHOT"
    elif coverage_errors:
        status = "INCOMPLETE_COVERAGE"
    elif domain_errors:
        status = "COMPLETE_WITH_UNRESOLVED_DOMAIN_ROUTING"
    elif context_errors:
        status = "COMPLETE_WITH_UNRESOLVED_CONTEXT"
    elif review_errors:
        status = "COMPLETE_WITH_UNRESOLVED_REVIEW"
    else:
        status = "COMPLETE"

    reasons: list[str] = []
    for reason in [*invalid, *coverage_errors, *domain_errors, *context_errors, *review_errors]:
        if reason not in reasons:
            reasons.append(reason)
    state = {
        "schema_version": 1,
        "routing_snapshot_id": manifest.get("routing_snapshot_id"),
        "status": status,
        "clean": status == "COMPLETE" and not confirmed,
        "reasons": reasons,
        "coverage": {
            "selected": sorted(selected),
            "screen_not_applicable": sorted(screen_not_applicable),
            "deep_candidates": sorted(candidates),
            "deep_reviewed": sorted(reviewed),
            "suspicious": sorted(suspicious),
            "confirmed": sorted(confirmed),
            "unresolved": sorted(unresolved),
        },
    }
    try:
        validate_schema(root, "audit-state.schema.json", state)
    except ValueError as error:
        state["reasons"].append(str(error))
        state["status"] = "INVALID_SNAPSHOT"
        state["clean"] = False
    return state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--screen-results", type=Path, required=True)
    parser.add_argument("--domain-resolution", type=Path)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--registry", type=Path, default=ROOT / "data/canonical-checks.json")
    parser.add_argument("--ledger", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = load_json(args.manifest)
        registry = load_json(args.registry)
        screen = load_json(args.screen_results) if args.screen_results.exists() else None
        domain = load_json(args.domain_resolution) if args.domain_resolution else None
        context = load_json(args.context) if args.context else None
        state = validate_run(ROOT, manifest, registry, screen, domain, context, args.ledger)
        rendered = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
        return 0 if state["status"] == "COMPLETE" else 1
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
