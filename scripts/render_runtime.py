#!/usr/bin/env python3
"""Render immutable routing output into screen/deep runtime views."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from audit_artifacts import (
        absence_evidence_errors,
        canonical_sha256,
        check_body_hash,
        derive_review_snapshot_id,
        load_json,
        registry_sha256,
        resolved_routes,
        validate_domain_context,
        validate_domain_resolution,
        validate_artifact_identity,
        validate_routing_snapshot,
        validate_schema,
        validate_target_snapshot,
    )
except ImportError:  # pragma: no cover
    from scripts.audit_artifacts import (
        absence_evidence_errors,
        canonical_sha256,
        check_body_hash,
        derive_review_snapshot_id,
        load_json,
        registry_sha256,
        resolved_routes,
        validate_domain_context,
        validate_domain_resolution,
        validate_artifact_identity,
        validate_routing_snapshot,
        validate_schema,
        validate_target_snapshot,
    )

try:
    from runtime_log import configure, error, info, stage, success, verbose as verbose_log, warning
except ImportError:  # pragma: no cover
    from scripts.runtime_log import configure, error, info, stage, success, verbose as verbose_log, warning


ROOT = Path(__file__).resolve().parents[1]
ROUTE_BUCKETS = ("selected", "deferred", "filtered")


def one_line(value: Any) -> str:
    return " ".join(str(item).strip() for item in value if str(item).strip()) if isinstance(value, list) else str(value or "").strip()


def selected_entries(manifest: dict[str, Any], owner_domain: str | None = None, domain_resolution: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    entries = resolved_routes(manifest, domain_resolution)
    return [entry for entry in entries if owner_domain is None or entry["owner_domain"] == owner_domain]


def validate_manifest(root: Path, manifest: dict[str, Any], registry: dict[str, Any]) -> str:
    validate_schema(root, "routing-manifest.schema.json", manifest)
    validate_schema(root, "feature-map.schema.json", manifest["feature_map"])
    snapshot = validate_routing_snapshot(manifest)
    if manifest["audit_context"]["registry_sha256"] != registry_sha256(registry):
        raise ValueError("routing manifest does not match this registry")
    recon_context = manifest["feature_map"]["recon_context"]
    for key in ("source_digest", "audit_source_digest", "dependency_digest", "build_config_digest", "compilation_input_digest"):
        if manifest["audit_context"][key] != recon_context[key]:
            raise ValueError(f"routing manifest {key} does not match Recon")
    checks = {check["canonical_id"]: check for check in registry["checks"]}
    ids_by_bucket: dict[str, list[str]] = {}
    for bucket in ROUTE_BUCKETS:
        ids_by_bucket[bucket] = []
        for entry in manifest[bucket]:
            ids_by_bucket[bucket].append(entry["canonical_id"])
            if entry["owner_domain"] not in entry["domains"]:
                raise ValueError(f"routing manifest owner is outside route domains: {entry['canonical_id']}")
            check = checks.get(entry["canonical_id"])
            if check is None:
                raise ValueError(f"routing manifest references unknown check: {entry['canonical_id']}")
            if entry["check_body_hash"] != check_body_hash(check):
                raise ValueError(f"routing manifest has stale check body: {entry['canonical_id']}")
        if manifest[f"{bucket}_count"] != len(manifest[bucket]):
            raise ValueError(f"routing manifest {bucket}_count is stale")
    all_ids = [canonical_id for bucket in ROUTE_BUCKETS for canonical_id in ids_by_bucket[bucket]]
    if len(all_ids) != len(set(all_ids)):
        raise ValueError("routing manifest contains duplicate canonical IDs")
    if manifest["scope"]["candidate_count"] != len(all_ids):
        raise ValueError("routing manifest scope candidate_count is stale")
    if manifest["filtered_out"] != ids_by_bucket["filtered"]:
        raise ValueError("routing manifest filtered_out is stale")
    domain_buckets = [set(entry["domain"] for entry in manifest[bucket + "_domains"]) for bucket in ("selected", "deferred", "filtered")]
    if any(domain_buckets[left] & domain_buckets[right] for left in range(3) for right in range(left + 1, 3)):
        raise ValueError("routing manifest Domain buckets overlap")
    for bucket, expected_status in (("selected", "SELECTED"), ("deferred", "DEFERRED_DOMAIN")):
        if any(entry["route_status"] != expected_status for entry in manifest[bucket]):
            raise ValueError(f"routing manifest {bucket} route status is inconsistent")
    if any(not entry["route_status"].startswith("FILTERED_") for entry in manifest["filtered"]):
        raise ValueError("routing manifest filtered route status is inconsistent")
    selected_domains = domain_buckets[0]
    deferred_domains = domain_buckets[1]
    filtered_domains = domain_buckets[2]
    required_context_domains = set(manifest["required_context_requirements"])
    if required_context_domains != selected_domains | deferred_domains:
        raise ValueError("required_context_requirements must cover selected and Deferred Domains only")
    if required_context_domains & filtered_domains:
        raise ValueError("filtered Domains must not have required context")
    for entry in manifest["selected"]:
        if not set(entry["domains"]) & selected_domains:
            raise ValueError(f"selected check is not owned by a selected Domain: {entry['canonical_id']}")
    for entry in manifest["deferred"]:
        if not set(entry["domains"]) & deferred_domains:
            raise ValueError(f"deferred check is not owned by a Deferred Domain: {entry['canonical_id']}")
    for entry in manifest["filtered"]:
        if not set(entry["domains"]) & (filtered_domains | selected_domains):
            raise ValueError(f"filtered check is not in the routed Domain scope: {entry['canonical_id']}")
    return snapshot


def _empty_identity(manifest: dict[str, Any]) -> dict[str, Any]:
    audit = manifest["audit_context"]
    return {
        "schema_version": 2,
        "routing_snapshot_id": manifest["routing_snapshot_id"],
        "registry_sha256": audit["registry_sha256"],
        "source_digest": audit["source_digest"],
        "compilation_input_digest": audit["compilation_input_digest"],
    }


def screen_results_template(manifest: dict[str, Any], domain_resolution: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        **_empty_identity(manifest),
        "results": [
            {"canonical_id": entry["canonical_id"], "result": "CANDIDATE", "scope_complete": False, "evidence": []}
            for entry in selected_entries(manifest, domain_resolution=domain_resolution)
        ],
    }


def domain_resolution_template(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        **_empty_identity(manifest),
        "domains": {
            entry["domain"]: {"status": "UNKNOWN", "scope_complete": False, "evidence": []}
            for entry in manifest["deferred_domains"]
        },
    }


def domain_context_template(
    manifest: dict[str, Any],
    domain_resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    eligible = {entry["domain"] for entry in manifest["selected_domains"]}
    if domain_resolution is not None:
        eligible |= {
            domain
            for domain, resolution in domain_resolution["domains"].items()
            if resolution["status"] == "PRESENT"
        }
    return {
        **_empty_identity(manifest),
        "schema_version": 3,
        "domains": {
            domain: {
                key: {"status": "UNKNOWN", "evidence": []}
                for key in manifest["required_context_requirements"].get(domain, {})
            }
            for domain in sorted(eligible)
            if domain in manifest["required_context_requirements"]
        },
    }


def validate_screen_results(root: Path, manifest: dict[str, Any], value: dict[str, Any], domain_resolution: dict[str, Any] | None = None) -> set[str]:
    validate_schema(root, "screen-results.schema.json", value)
    validate_artifact_identity(value, manifest)
    selected = {entry["canonical_id"] for entry in selected_entries(manifest, domain_resolution=domain_resolution)}
    results = value["results"]
    ids = [entry["canonical_id"] for entry in results]
    if len(ids) != len(set(ids)) or set(ids) != selected:
        raise ValueError("screen results must resolve every selected ID exactly once")
    for entry in results:
        if entry["result"] == "NOT_APPLICABLE_CONFIRMED":
            quality = manifest.get("feature_map", {}).get("recon_context", {}).get("recon_quality", {})
            if quality.get("absence_filtering_complete") is not True:
                raise ValueError(
                    f"{entry['canonical_id']}: NOT_APPLICABLE_CONFIRMED requires complete compilation"
                )
            errors = absence_evidence_errors(
                entry["evidence"], entry.get("scope_complete"), entry["canonical_id"]
            )
            if errors:
                raise ValueError("; ".join(errors))
    return {entry["canonical_id"] for entry in results if entry["result"] == "CANDIDATE"}


def render(
    manifest: dict[str, Any],
    registry: dict[str, Any],
    profile: str,
    candidate_ids: set[str],
    owner_domain: str | None = None,
    domain_resolution: dict[str, Any] | None = None,
    review_snapshot: str | None = None,
) -> str:
    entries = {entry["canonical_id"]: entry for entry in selected_entries(manifest, owner_domain, domain_resolution)}
    checks = {
        check["canonical_id"]: check
        for check in registry["checks"]
        if check["canonical_id"] in entries and (profile == "screen" or check["canonical_id"] in candidate_ids)
    }
    ids = sorted(checks)
    audit = manifest["audit_context"]
    lines = [
        "<!-- GENERATED RUNTIME ARTIFACT",
        f"artifact_type: runtime-{profile}",
        f"routing_snapshot_id: {manifest['routing_snapshot_id']}",
        f"review_snapshot_id: {review_snapshot or 'not-yet-defined'}",
        f"registry_sha256: {audit['registry_sha256']}",
        f"source_digest: {audit['source_digest']}",
        f"audit_source_digest: {audit['audit_source_digest']}",
        f"compilation_input_digest: {audit['compilation_input_digest']}",
        f"profile: {profile}",
        f"candidate_set_sha256: {canonical_sha256(ids)}",
        f"candidate_set: {','.join(ids)}",
        "source: data/canonical-checks.json; do not edit by hand. -->",
        "# Routed EVM Audit Checks",
        "",
        f"- **Routing snapshot:** `{manifest['routing_snapshot_id']}`",
        f"- **Review snapshot:** `{review_snapshot or 'not-yet-defined'}`",
        f"- **Candidate set:** `{','.join(ids)}`",
        "",
    ]
    for canonical_id in ids:
        check = checks[canonical_id]
        route = entries[canonical_id]
        lines.extend([f"## [{canonical_id}] {check['title']}"])
        if profile == "deep":
            lines.extend([f"- **Check body hash:** `{route['check_body_hash']}`", f"- **Routing basis:** {one_line(route['basis'])}"])
        lines.extend([f"- **Trigger:** {one_line(check['trigger'])}", f"- **Detection:** {one_line(check['detection'])}"])
        if profile == "deep":
            lines.extend([
                f"- **Risk:** {one_line(check['risk'])}",
                f"- **Applicability:** `{json.dumps(check.get('applicability'), ensure_ascii=False, sort_keys=True)}`",
            ])
            if check.get("fp_policy") == "specific":
                lines.append(f"- **Specific FP:** {one_line(check['false_positive_gates'])}")
            if check.get("proof_policy") == "specific":
                lines.append(f"- **Specific proof:** {one_line(check['proof'])}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_json(path: Path, value: dict[str, Any], *, overwrite: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise ValueError(f"refusing to overwrite existing artifact: {path}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=ROOT / "data/canonical-checks.json")
    parser.add_argument("--profile", choices=("screen", "deep"), required=True)
    parser.add_argument("--screen-results", type=Path, help="validated Screen result artifact for Deep")
    parser.add_argument("--domain-resolution", type=Path, help="resolved Deferred Domain artifact")
    parser.add_argument("--screen-results-out", type=Path, help="write a conservative Screen result template")
    parser.add_argument("--domain-resolution-out", type=Path, help="write an unresolved Deferred Domain template")
    parser.add_argument("--domain-context", type=Path, help="snapshot-bound required Domain context")
    parser.add_argument("--domain-context-out", type=Path, help="write an unresolved Domain Context template")
    parser.add_argument("--owner-domain", help="render only checks owned by this Domain")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--quiet", action="store_true", help="suppress progress output")
    parser.add_argument("--verbose", action="store_true", help="include per-domain render details")
    args = parser.parse_args(argv)
    configure(quiet=args.quiet, verbose=args.verbose)
    try:
        manifest, registry = load_json(args.manifest), load_json(args.registry)
        validate_manifest(ROOT, manifest, registry)
        validate_target_snapshot(manifest)
        domain_resolution = load_json(args.domain_resolution) if args.domain_resolution else None
        unresolved_domains: set[str] = set()
        if args.domain_resolution or args.domain_resolution_out:
            stage("DOMAIN RESOLUTION", step=3, total=7, detail="Resolving deferred audit Domains")
        if domain_resolution is not None:
            unresolved_domains = validate_domain_resolution(
                ROOT, manifest, domain_resolution
            )
            for domain, resolution in sorted(domain_resolution.get("domains", {}).items()):
                info(f"{domain} {resolution['status']}")
            if unresolved_domains:
                warning(f"{len(unresolved_domains)} Deferred Domain(s) remain UNKNOWN")
                if args.profile == "deep":
                    raise ValueError("Deep Review blocked: unresolved Deferred Domains")
            else:
                success("Domain routing resolved")
        elif args.domain_resolution_out and manifest["deferred_domains"]:
            warning(f"{len(manifest['deferred_domains'])} Deferred Domain(s) remain UNKNOWN")
        domain_context = load_json(args.domain_context) if args.domain_context else None
        if domain_context is not None:
            unresolved_context = validate_domain_context(
                ROOT,
                manifest,
                domain_context,
                domain_resolution,
                require_complete=args.profile == "deep",
            )
            if unresolved_context:
                warning(f"{len(unresolved_context)} required Domain context item(s) remain UNKNOWN")
            else:
                success("Domain Context validated")
        review_snapshot: str | None = None
        screen_results: dict[str, Any] | None = None
        if args.profile == "deep":
            stage("DEEP REVIEW", step=5, total=7, detail="Rendering candidate-only Deep Review")
            if not args.screen_results:
                raise ValueError("--profile deep requires --screen-results")
            if manifest["deferred_domains"] and not domain_resolution:
                raise ValueError("Deep Review blocked: --domain-resolution is required for Deferred Domains")
            if not args.domain_context:
                raise ValueError("--profile deep requires --domain-context")
            screen_results = load_json(args.screen_results)
            candidates = validate_screen_results(ROOT, manifest, screen_results, domain_resolution)
            review_snapshot = derive_review_snapshot_id(
                ROOT, manifest, domain_resolution, domain_context, screen_results
            )
        else:
            stage("SCREEN", step=4, total=7, detail="Screening routed checks")
            candidates = set()
            if args.screen_results:
                raise ValueError("--screen-results is only used by --profile deep")
            if args.screen_results_out:
                write_json(args.screen_results_out, screen_results_template(manifest, domain_resolution))
                info(f"Screen result template written to {args.screen_results_out}")
            if args.domain_resolution_out:
                write_json(args.domain_resolution_out, domain_resolution_template(manifest))
                info(f"Domain Resolution template written to {args.domain_resolution_out}")
            if args.domain_context_out:
                write_json(args.domain_context_out, domain_context_template(manifest, domain_resolution))
                info(f"Domain Context template written to {args.domain_context_out}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            render(
                manifest,
                registry,
                args.profile,
                candidates,
                args.owner_domain,
                domain_resolution,
                review_snapshot,
            ),
            encoding="utf-8",
        )
        entries = selected_entries(manifest, args.owner_domain, domain_resolution)
        if args.profile == "screen":
            info(f"Rendered checks: {len(entries)}")
            success("Screen runtime generated")
        else:
            entries = [entry for entry in entries if entry["canonical_id"] in candidates]
            info(f"Candidates admitted: {len(entries)}")
            info(f"Owner Domains: {len({entry['owner_domain'] for entry in entries})}")
            for domain in sorted({entry["owner_domain"] for entry in entries}):
                verbose_log(f"[DOMAIN] {domain} checks={sum(entry['owner_domain'] == domain for entry in entries)} rendered")
            success("Deep runtime generated")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        error(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
