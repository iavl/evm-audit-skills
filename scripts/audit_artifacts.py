#!/usr/bin/env python3
"""Shared hashing and schema checks for immutable audit-run artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

_SUITE_ROOT = str(Path(__file__).resolve().parents[1])
if _SUITE_ROOT not in sys.path:
    sys.path.insert(0, _SUITE_ROOT)
from evm_audit_runtime.routing import effective_owner_domain, resolved_routes
from evm_audit_runtime.versions import REPORT_BUNDLE_VERSION


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
# Only treat a field explicitly marked unresolved as unresolved.  Completed
# prose may legitimately mention words such as "unknown".
UNRESOLVED_MARKERS = ("UNKNOWN", "UNRESOLVED", "TODO", "TBD")
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
    encoded = json.dumps(canonicalize_json(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def report_bundle_metadata(
    manifest: dict[str, Any],
    state: dict[str, Any],
    report: str | bytes,
    issue_candidates: dict[str, Any],
    *,
    issue_candidates_bytes: bytes | None = None,
) -> dict[str, Any]:
    audit = manifest["audit_context"]
    if any(
        issue_candidates.get(key) != state.get(key)
        for key in ("review_snapshot_id", "review_state_digest")
    ):
        raise ValueError("report bundle inputs do not match current audit state")
    return {
        "artifact_type": "report-bundle",
        "schema_version": REPORT_BUNDLE_VERSION,
        "routing_snapshot_id": manifest["routing_snapshot_id"],
        "review_snapshot_id": state.get("review_snapshot_id"),
        "review_state_digest": state.get("review_state_digest"),
        "registry_sha256": audit["registry_sha256"],
        "source_digest": audit["source_digest"],
        "compilation_input_digest": audit["compilation_input_digest"],
        "report_sha256": sha256_bytes(report if isinstance(report, bytes) else report.encode("utf-8")),
        "issue_candidates_sha256": sha256_bytes(
            issue_candidates_bytes
            if issue_candidates_bytes is not None
            else json_text(issue_candidates).encode("utf-8")
        ),
    }


def canonicalize_json(value: Any) -> Any:
    """Canonicalize object keys while preserving the order of every array."""
    if isinstance(value, dict):
        return {key: canonicalize_json(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [canonicalize_json(item) for item in value]
    return value


def _sorted_json_items(value: Any) -> Any:
    """Sort only schema-defined set-like collections such as evidence."""
    if not isinstance(value, list):
        return value
    normalized = [canonicalize_json(item) for item in value]
    return sorted(
        normalized,
        key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
    )


def _canonical_domain_resolution(value: Any) -> Any:
    normalized = canonicalize_json(value)
    if isinstance(normalized, dict) and isinstance(normalized.get("domains"), dict):
        for resolution in normalized["domains"].values():
            if isinstance(resolution, dict) and "evidence" in resolution:
                resolution["evidence"] = _sorted_json_items(resolution["evidence"])
    return normalized


def _canonical_domain_context(value: Any) -> Any:
    normalized = canonicalize_json(value)
    if isinstance(normalized, dict) and isinstance(normalized.get("domains"), dict):
        for requirements in normalized["domains"].values():
            if isinstance(requirements, dict):
                for context_entry in requirements.values():
                    if isinstance(context_entry, dict) and "evidence" in context_entry:
                        context_entry["evidence"] = _sorted_json_items(context_entry["evidence"])
    return normalized


def _canonical_screen_results(value: Any) -> Any:
    normalized = canonicalize_json(value)
    if isinstance(normalized, dict) and isinstance(normalized.get("results"), list):
        for result in normalized["results"]:
            if isinstance(result, dict) and "evidence" in result:
                result["evidence"] = _sorted_json_items(result["evidence"])
        normalized["results"] = sorted(
            normalized["results"],
            key=lambda result: result.get("canonical_id", "") if isinstance(result, dict) else json.dumps(result, ensure_ascii=False, sort_keys=True),
        )
    return normalized


def _canonical_review_record(value: Any) -> Any:
    normalized = canonicalize_json(value)
    if isinstance(normalized, dict) and "evidence" in normalized:
        normalized["evidence"] = _sorted_json_items(normalized["evidence"])
    return normalized


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


def review_snapshot_id(
    manifest: dict[str, Any],
    domain_resolution: dict[str, Any] | None,
    domain_context: dict[str, Any],
    screen_results: dict[str, Any],
) -> str:
    """Hash the exact post-routing inputs consumed by Deep Review."""
    snapshot = manifest.get("routing_snapshot_id")
    if not isinstance(snapshot, str) or not SHA256_RE.fullmatch(snapshot):
        raise ValueError("review snapshot requires a valid routing_snapshot_id")
    # A no-op empty resolution artifact is semantically identical to no Deferred Domains.
    normalized_resolution = None if not manifest.get("deferred_domains") else domain_resolution
    return canonical_sha256(
        {
            "routing_snapshot_id": snapshot,
            "domain_resolution": _canonical_domain_resolution(normalized_resolution),
            "domain_context": _canonical_domain_context(domain_context),
            "screen_results": _canonical_screen_results(screen_results),
        }
    )


def review_state_digest(records: dict[str, dict[str, Any]], candidate_ids: set[str]) -> str:
    """Hash the current latest review record for every Deep candidate."""
    missing = sorted(candidate_ids - set(records))
    if missing:
        raise ValueError(f"cannot derive review_state_digest; missing review records: {missing}")
    return canonical_sha256(
        {
            "candidates": [
                {"canonical_id": canonical_id, "record": _canonical_review_record(records[canonical_id])}
                for canonical_id in sorted(candidate_ids)
            ]
        }
    )


def validate_review_state_binding(value: dict[str, Any], digest: str | None) -> None:
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        raise ValueError("current review_state_digest is unavailable")
    if value.get("review_state_digest") != digest:
        raise ValueError("artifact has mismatched review_state_digest")


def atomic_write_text(path: Path, content: str) -> None:
    """Replace a file atomically, leaving no stale partial output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        temporary = None
        try:
            descriptor = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except OSError:
            pass
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json_text(value))


def invalidate_final_outputs(*paths: Path) -> None:
    for path in paths:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


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


def is_unresolved_value(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().upper()
    return any(
        normalized == marker or normalized.startswith(f"{marker} ") or normalized.startswith(f"{marker}:")
        or normalized.startswith(f"{marker}-") or normalized.startswith(f"{marker}—")
        for marker in UNRESOLVED_MARKERS
    )


def has_unresolved_marker(*values: Any) -> bool:
    return any(is_unresolved_value(value) for value in values)


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
    if not kinds & (ABSENCE_EVIDENCE_KINDS - {"scope"}):
        errors.append(f"{label}: non-applicability requires evidence for an exclusion dimension")
    return errors


def validate_non_applicability(
    *,
    evidence: Any,
    scope_complete: Any,
    trusted_absence_policy: dict[str, Any] | None,
    recon_quality: dict[str, Any] | None,
    label: str,
    values: tuple[Any, ...] = (),
) -> list[str]:
    """Apply the same fail-closed absence policy to every review stage."""
    errors = absence_evidence_errors(evidence, scope_complete, label)
    if (recon_quality or {}).get("absence_filtering_complete") is not True:
        errors.append(f"{label}: NOT_APPLICABLE requires complete compilation")
    if not isinstance(trusted_absence_policy, dict):
        errors.append(f"{label}: trusted_absence_policy is unavailable")
    else:
        allowed = set(trusted_absence_policy.get("allowed_evidence", []))
        kinds = {item.get("kind") for item in evidence if isinstance(item, dict)} if isinstance(evidence, list) else set()
        if not kinds or not kinds <= allowed:
            errors.append(f"{label}: non-applicability evidence violates trusted_absence_policy")
        if trusted_absence_policy.get("requires_complete_scope") is True and "scope" not in kinds:
            errors.append(f"{label}: complete-scope absence requires scope evidence")
    if has_unresolved_marker(*values):
        errors.append(f"{label}: non-applicability cannot contain unresolved field markers")
    return errors


def _domain_route(manifest: dict[str, Any], domain: str) -> dict[str, Any] | None:
    return next(
        (
            entry
            for entry in [*manifest.get("selected_domains", []), *manifest.get("deferred_domains", [])]
            if entry.get("domain") == domain
        ),
        None,
    )


def trusted_absence_policy(manifest: dict[str, Any], domain: str) -> dict[str, Any] | None:
    route = _domain_route(manifest, domain)
    policy = route.get("trusted_absence_policy") if route else None
    return policy if isinstance(policy, dict) else None


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
            quality = manifest.get("feature_map", {}).get("recon_context", {}).get("recon_quality", {})
            if quality.get("absence_filtering_complete") is not True:
                raise ValueError(f"{domain}: ABSENT_CONFIRMED is unavailable with incomplete compilation")
            errors = validate_non_applicability(
                evidence=evidence,
                scope_complete=resolution["scope_complete"],
                trusted_absence_policy=route.get("trusted_absence_policy"),
                recon_quality=manifest.get("feature_map", {}).get("recon_context", {}).get("recon_quality"),
                label=domain,
            )
            if errors:
                raise ValueError("; ".join(errors))
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
            elif status == "NOT_APPLICABLE":
                route = _domain_route(manifest, domain)
                errors = validate_non_applicability(
                    evidence=item.get("evidence"),
                    scope_complete=item.get("scope_complete"),
                    trusted_absence_policy=route.get("trusted_absence_policy") if route else None,
                    recon_quality=manifest.get("feature_map", {}).get("recon_context", {}).get("recon_quality"),
                    label=f"{domain}.{key}",
                )
                if errors:
                    raise ValueError("; ".join(errors))
            if requirements[domain][key]["required"] and status == "UNKNOWN":
                unresolved.add(f"{domain}.{key}")
                if require_complete:
                    raise ValueError(f"required Domain context remains UNKNOWN: {domain}.{key}")
    return unresolved


def derive_review_snapshot_id(
    root: Path,
    manifest: dict[str, Any],
    domain_resolution: dict[str, Any] | None,
    domain_context: dict[str, Any],
    screen_results: dict[str, Any],
) -> str:
    """Validate all current Deep inputs, then derive their deterministic identity."""
    validate_routing_snapshot(manifest)
    if manifest.get("deferred_domains"):
        if domain_resolution is None:
            raise ValueError("review snapshot requires domain-resolution.json")
        validate_domain_resolution(root, manifest, domain_resolution, require_terminal=True)
    elif domain_resolution is not None:
        validate_domain_resolution(root, manifest, domain_resolution, require_terminal=True)
    validate_domain_context(root, manifest, domain_context, domain_resolution, require_complete=True)
    try:
        from render_runtime import validate_screen_results
    except ImportError:  # pragma: no cover - package-style import
        from scripts.render_runtime import validate_screen_results

    validate_screen_results(root, manifest, screen_results, domain_resolution)
    return review_snapshot_id(manifest, domain_resolution, domain_context, screen_results)


def validate_target_snapshot(manifest: dict[str, Any]) -> None:
    """Reject consumption of a manifest after the audited target changed."""
    try:
        from scope_context import compilation_digests, resolve_build_root, resolve_scope_root, scope_inventory
    except ImportError:  # pragma: no cover - supports package-style imports
        from scripts.scope_context import compilation_digests, resolve_build_root, resolve_scope_root, scope_inventory

    recon = manifest["feature_map"]["recon_context"]
    target_root = resolve_scope_root(Path(recon["target_root"]))
    build_root = resolve_build_root(target_root, Path(recon["build_root"]))
    exclusions = tuple(recon["exclusion_patterns"])
    includes = tuple(recon.get("include_patterns", ()))
    dependency_roots = tuple(recon.get("dependency_roots", ()))
    files, excluded = scope_inventory(target_root, exclusions, includes, dependency_roots)
    current = compilation_digests(
        target_root,
        files,
        recon["solc_version"],
        build_root=build_root,
        dependency_roots=dependency_roots,
        compilation_files=recon.get("compilation_files"),
        compiler_versions=recon.get("compiler_versions"),
    )
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
    if (
        str(build_root) != recon["build_root"]
        or excluded != recon["excluded_paths"]
        or any(actual[key] != expected[key] for key in expected)
    ):
        raise ValueError("Target source/build inputs changed after routing. Rerun Recon and Selector.")
