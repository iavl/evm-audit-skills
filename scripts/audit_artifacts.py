#!/usr/bin/env python3
"""Shared hashing and schema checks for immutable audit-run artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PLACEHOLDER_RE = re.compile(r"\b(?:UNKNOWN|UNRESOLVED|TODO|TBD)\b", re.IGNORECASE)
ABSENCE_EVIDENCE_KINDS = {
    "source",
    "inheritance",
    "interface",
    "dependency",
    "deployment",
    "environment",
    "compiler-ast",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def check_body_hash(check: dict[str, Any]) -> str:
    return canonical_sha256(check)


def registry_sha256(registry: dict[str, Any]) -> str:
    return canonical_sha256(registry)


def routing_snapshot_id(manifest: dict[str, Any]) -> str:
    payload = {key: value for key, value in manifest.items() if key != "routing_snapshot_id"}
    audit_context = payload.get("audit_context")
    if isinstance(audit_context, dict):
        payload["audit_context"] = {
            key: value for key, value in audit_context.items() if key != "audit_timestamp"
        }
    return canonical_sha256(payload)


def bind_routing_snapshot(manifest: dict[str, Any]) -> dict[str, Any]:
    result = dict(manifest)
    result["routing_snapshot_id"] = routing_snapshot_id(result)
    return result


def validate_routing_snapshot(manifest: dict[str, Any]) -> str:
    snapshot = manifest.get("routing_snapshot_id")
    if not isinstance(snapshot, str) or not SHA256_RE.fullmatch(snapshot):
        raise ValueError("routing manifest has no valid routing_snapshot_id")
    expected = routing_snapshot_id(manifest)
    if snapshot != expected:
        raise ValueError("routing manifest snapshot hash is stale or invalid")
    return snapshot


def validate_schema(root: Path, schema_name: str, value: Any) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as error:  # pragma: no cover - dependency failure is operational
        raise ValueError("jsonschema is required; install requirements-runtime.txt") from error
    schema = load_json(root / "schemas" / schema_name)
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda item: list(item.path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise ValueError(f"{schema_name}:{location}: {error.message}")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{number} must contain an object")
        records.append(value)
    return records


def has_placeholder(*values: Any) -> bool:
    return any(PLACEHOLDER_RE.search(str(value or "")) for value in values)


def artifact_identity(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return the hashes every post-routing artifact must carry."""
    audit = manifest["audit_context"]
    return {
        "routing_snapshot_id": manifest["routing_snapshot_id"],
        "registry_sha256": audit["registry_sha256"],
        "source_digest": audit["source_digest"],
        "compilation_input_digest": audit["compilation_input_digest"],
    }


def validate_artifact_identity(value: dict[str, Any], manifest: dict[str, Any]) -> None:
    expected = artifact_identity(manifest)
    for key, wanted in expected.items():
        if value.get(key) != wanted:
            raise ValueError(f"artifact has mismatched {key}")


def validate_context(root: Path, manifest: dict[str, Any], value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        validate_schema(root, "audit-context.schema.json", value)
    except ValueError as error:
        errors.append(str(error))
        return errors
    expected = {**manifest["audit_context"], "routing_snapshot_id": manifest["routing_snapshot_id"]}
    for key in sorted(set(expected) | set(value)):
        if value.get(key) != expected.get(key):
            errors.append(f"context.{key} differs from routing snapshot")
    return errors


def absence_evidence_errors(
    evidence: Any,
    scope_complete: Any,
    label: str,
) -> list[str]:
    errors: list[str] = []
    if scope_complete is not True:
        errors.append(f"{label}: NOT_APPLICABLE_CONFIRMED requires scope_complete=true")
    if not isinstance(evidence, list) or not evidence:
        return errors + [f"{label}: non-applicability requires typed evidence"]
    kinds = {item.get("kind") for item in evidence if isinstance(item, dict)}
    if "scope" not in kinds:
        errors.append(f"{label}: non-applicability requires scope evidence")
    if not kinds & ABSENCE_EVIDENCE_KINDS:
        errors.append(f"{label}: non-applicability requires evidence for an exclusion dimension")
    return errors


def _domain_route(manifest: dict[str, Any], domain: str) -> dict[str, Any] | None:
    return next(
        (entry for entry in manifest.get("deferred_domains", []) if entry.get("domain") == domain),
        None,
    )


def validate_domain_resolution(
    root: Path,
    manifest: dict[str, Any],
    value: dict[str, Any],
    *,
    require_terminal: bool = False,
) -> set[str]:
    validate_schema(root, "domain-resolution.schema.json", value)
    validate_artifact_identity(value, manifest)
    expected = {entry["domain"] for entry in manifest["deferred_domains"]}
    actual = set(value["domains"])
    if actual != expected:
        raise ValueError(
            "domain resolution must contain exactly Deferred Domains: "
            f"expected={sorted(expected)} actual={sorted(actual)}"
        )

    unresolved: set[str] = set()
    for domain, resolution in value["domains"].items():
        route = _domain_route(manifest, domain)
        if route is None:
            raise ValueError(f"unknown resolved Domain: {domain}")
        status = resolution["status"]
        evidence = resolution["evidence"]
        if status == "PRESENT" and not evidence:
            raise ValueError(f"{domain}: PRESENT requires evidence")
        if status == "ABSENT_CONFIRMED":
            policy = route.get("trusted_absence_policy") or {}
            kinds = {item["kind"] for item in evidence}
            allowed = set(policy.get("allowed_evidence", []))
            if resolution["scope_complete"] is not True:
                raise ValueError(f"{domain}: ABSENT_CONFIRMED requires scope_complete=true")
            if not kinds or not kinds <= allowed:
                raise ValueError(f"{domain}: absence evidence violates trusted_absence_policy")
            if policy.get("requires_complete_scope") is True and "scope" not in kinds:
                raise ValueError(f"{domain}: complete-scope absence requires scope evidence")
        if status == "UNKNOWN":
            unresolved.add(domain)
            if require_terminal:
                raise ValueError(
                    f"Deferred Domain {domain} is unresolved; resolve Domain screening before Deep."
                )
    return unresolved


def _non_empty_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _eligible_context_domains(
    manifest: dict[str, Any],
    domain_resolution: dict[str, Any] | None,
) -> set[str]:
    domains = {entry["domain"] for entry in manifest.get("selected_domains", [])}
    if domain_resolution is not None:
        domains |= {
            domain
            for domain, resolution in domain_resolution.get("domains", {}).items()
            if resolution.get("status") == "PRESENT"
        }
    return domains


def validate_domain_context(
    root: Path,
    manifest: dict[str, Any],
    value: dict[str, Any],
    domain_resolution: dict[str, Any] | None = None,
    *,
    require_complete: bool = False,
) -> set[str]:
    validate_schema(root, "domain-context.schema.json", value)
    validate_artifact_identity(value, manifest)
    if domain_resolution is not None:
        validate_domain_resolution(root, manifest, domain_resolution)
    requirements = manifest.get("required_context_requirements")
    if not isinstance(requirements, dict):
        raise ValueError("routing manifest has no required_context_requirements")
    expected_domains = _eligible_context_domains(manifest, domain_resolution)
    expected_domains &= set(requirements)
    actual_domains = set(value["domains"])
    if actual_domains != expected_domains:
        raise ValueError(
            "domain context must contain exactly eligible Domains: "
            f"expected={sorted(expected_domains)} actual={sorted(actual_domains)}"
        )

    unresolved: set[str] = set()
    for domain in sorted(expected_domains):
        expected_keys = set(requirements[domain])
        actual_keys = set(value["domains"][domain])
        if actual_keys != expected_keys:
            raise ValueError(
                f"domain context requirements mismatch for {domain}: "
                f"expected={sorted(expected_keys)} actual={sorted(actual_keys)}"
            )
        for key, item in value["domains"][domain].items():
            status = item["status"]
            if status == "KNOWN":
                if not _non_empty_value(item.get("value")) or not item.get("evidence"):
                    raise ValueError(f"{domain}.{key} KNOWN requires value and evidence")
            elif status == "NOT_APPLICABLE" and not item.get("evidence"):
                raise ValueError(f"{domain}.{key} NOT_APPLICABLE requires evidence")
            if requirements[domain][key]["required"] and status == "UNKNOWN":
                unresolved.add(f"{domain}.{key}")
                if require_complete:
                    raise ValueError(f"required Domain context remains UNKNOWN: {domain}.{key}")
    return unresolved


def validate_target_snapshot(manifest: dict[str, Any]) -> None:
    """Reject consumption of a manifest after the audited target changed."""
    try:
        from scope_context import compilation_digests, resolve_scope_root, scope_inventory
    except ImportError:  # pragma: no cover - supports package-style imports
        from scripts.scope_context import compilation_digests, resolve_scope_root, scope_inventory

    recon = manifest["feature_map"]["recon_context"]
    target_root = resolve_scope_root(Path(recon["target_root"]))
    exclusions = tuple(recon["exclusion_patterns"])
    files, excluded = scope_inventory(target_root, exclusions)
    current = compilation_digests(target_root, files, recon["solc_version"])
    expected = {
        "source_digest": recon["source_digest"],
        "audit_source_digest": recon["audit_source_digest"],
        "dependency_digest": recon["dependency_digest"],
        "build_config_digest": recon["build_config_digest"],
        "compilation_input_digest": recon["compilation_input_digest"],
    }
    actual = {
        "source_digest": current["audit_source_digest"],
        "audit_source_digest": current["audit_source_digest"],
        **current,
    }
    if excluded != recon["excluded_paths"] or any(actual[key] != expected[key] for key in expected):
        raise ValueError("Target source/build inputs changed after routing. Rerun Recon and Selector.")
