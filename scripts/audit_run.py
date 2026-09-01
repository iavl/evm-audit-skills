#!/usr/bin/env python3
"""Advance an audit run through deterministic artifact stages."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from runtime_log import configure, error, info, stage, success, warning
except ImportError:  # pragma: no cover
    from scripts.runtime_log import configure, error, info, stage, success, warning

try:
    from audit_artifacts import (
        atomic_write_json,
        atomic_write_text,
        derive_review_snapshot_id,
        has_placeholder,
        invalidate_final_outputs,
        load_json,
        validate_domain_context,
        validate_domain_resolution,
        validate_target_snapshot,
    )
    from render_runtime import selected_entries, validate_manifest, validate_screen_results
    from review_ledger import collect_review_records
    from synthesize_report import synthesize
    from validate_audit_run import validate_run
except ImportError:  # pragma: no cover
    from scripts.audit_artifacts import (
        atomic_write_json,
        atomic_write_text,
        derive_review_snapshot_id,
        has_placeholder,
        invalidate_final_outputs,
        load_json,
        validate_domain_context,
        validate_domain_resolution,
        validate_target_snapshot,
    )
    from scripts.render_runtime import selected_entries, validate_manifest, validate_screen_results
    from scripts.review_ledger import collect_review_records
    from scripts.synthesize_report import synthesize
    from scripts.validate_audit_run import validate_run


ROOT = Path(__file__).resolve().parents[1]
TOTAL_STAGES = 7
VERBOSE_CHILD_SCRIPTS = {"select_checks.py", "render_runtime.py"}
REPORTING_DIMENSIONS = (
    "impact", "exploitability", "privileges", "capital_required",
    "repeatability", "user_interaction", "loss_bound", "protocol_exposure",
    "recoverability",
)
REPORTING_IDENTITY_KEYS = (
    "schema_version", "routing_snapshot_id", "review_state_digest",
    "registry_sha256", "source_digest", "compilation_input_digest",
)


def paths(run_dir: Path) -> dict[str, Path]:
    return {
        "feature_map": run_dir / "recon/feature-map.json",
        "manifest": run_dir / "routing/manifest.json",
        "context": run_dir / "context.json",
        "environment": run_dir / "routing/environment-context.json",
        "resolution": run_dir / "reviews/domain-resolution.json",
        "domain_context": run_dir / "reviews/domain-context.json",
        "screen": run_dir / "runtime/screen.md",
        "screen_results": run_dir / "reviews/screen-results.json",
        "audit_state": run_dir / "audit-state.json",
        "report": run_dir / "AUDIT-REPORT.md",
        "issue_candidates": run_dir / "issue-candidates.json",
    }


def _compact_failure(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith("ERROR:"):
            return line.removeprefix("ERROR:").strip()
    return lines[-1] if lines else ""


def _run(root: Path, script: str, arguments: list[str], *, verbose: bool = False) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(root / "scripts" / script), *arguments]
    if verbose and script in VERBOSE_CHILD_SCRIPTS:
        command.append("--verbose")
    result = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
    )
    if verbose and result.stderr:
        sys.stderr.write(result.stderr)
        if not result.stderr.endswith("\n"):
            sys.stderr.write("\n")
    if result.returncode:
        detail = _compact_failure(result.stderr or result.stdout) or f"exit={result.returncode}"
        raise ValueError(f"{script} failed: {detail}")
    return result


def _render_screen(root: Path, values: dict[str, Path], *extra: str, verbose: bool = False) -> None:
    values["screen"].parent.mkdir(parents=True, exist_ok=True)
    _run(
        root,
        "render_runtime.py",
        [
            "--manifest", str(values["manifest"]),
            "--profile", "screen",
            "--output", str(values["screen"]),
            *extra,
        ],
        verbose=verbose,
    )


def _display_stage(name: str) -> str:
    return name.replace("_", " ")


def _log_recon(feature_map: dict[str, Any], target: Path, strict: bool) -> None:
    recon = feature_map["recon_context"]
    complete = recon["compilation_complete"]
    info(f"Audit scope: {target}")
    info(f"Compilation: {'COMPLETE' if complete else 'INCOMPLETE'}")
    if complete:
        success("Recon complete")
    else:
        warning("Recon compilation coverage is incomplete")
        if strict:
            warning("Strict compilation policy rejected this scope")


def _log_routing(manifest: dict[str, Any]) -> None:
    info(f"Selected domains: {len(manifest['selected_domains'])}")
    info(f"Deferred domains: {len(manifest['deferred_domains'])}")
    info(f"Filtered domains: {len(manifest['filtered_domains'])}")
    info(f"Selected checks: {manifest['selected_count']}")
    info(f"Deferred checks: {manifest['deferred_count']}")
    info(f"Filtered checks: {manifest['filtered_count']}")
    success("Routing snapshot created")


def _log_domain_resolution(
    manifest: dict[str, Any], unresolved: set[str] | None = None
) -> None:
    stage("DOMAIN RESOLUTION", step=3, total=TOTAL_STAGES, detail="Resolving Deferred Domains")
    total = len(manifest["deferred_domains"])
    remaining = unresolved if unresolved is not None else {entry["domain"] for entry in manifest["deferred_domains"]}
    info(f"Resolved: {total - len(remaining)} / {total}")
    if remaining:
        warning(f"Deferred Domains remaining: {len(remaining)}")
    else:
        success("Deferred Domains resolved")


def _context_requirement_count(manifest: dict[str, Any]) -> int:
    return sum(
        len(requirements)
        for requirements in manifest.get("required_context_requirements", {}).values()
        if isinstance(requirements, dict)
    )


def _log_domain_context(
    manifest: dict[str, Any], unresolved: set[str] | None = None
) -> None:
    stage("DOMAIN CONTEXT", step=3, total=TOTAL_STAGES, detail="Resolving required Domain context")
    total = _context_requirement_count(manifest)
    if unresolved is None:
        remaining = {
            f"{domain}.{key}"
            for domain, requirements in manifest.get("required_context_requirements", {}).items()
            if isinstance(requirements, dict)
            for key in requirements
        }
    else:
        remaining = unresolved
    info(f"Resolved: {total - len(remaining)} / {total}")
    if remaining:
        warning(f"Required Domain context remaining: {len(remaining)}")
    else:
        success("Domain Context resolved")


def _log_screen(screen: dict[str, Any], candidates: set[str]) -> None:
    results = screen.get("results", [])
    total = len(results) if isinstance(results, list) else 0
    stage("SCREEN", step=4, total=TOTAL_STAGES, detail="Screening routed checks")
    info(f"Screen checks: {total}")
    info(f"Deep candidates: {len(candidates)}")
    info(f"Screen NOT_APPLICABLE: {total - len(candidates)}")
    success("Screen complete")


def _log_deep(candidates: set[str], records: dict[str, dict[str, Any]], pending: set[str]) -> None:
    suspicious = sum(record.get("status") == "SUSPICIOUS" for record in records.values())
    confirmed = sum(record.get("status") == "CONFIRMED" for record in records.values())
    info(f"Reviewed: {len(records)} / {len(candidates)}")
    info(f"Remaining: {len(pending)}")
    info(f"Suspicious: {suspicious}")
    info(f"Confirmed: {confirmed}")


def _log_report(state: dict[str, Any], *, finished: bool) -> None:
    coverage = state.get("coverage", {})
    confirmed = coverage.get("confirmed", []) if isinstance(coverage, dict) else []
    suspicious = coverage.get("suspicious", []) if isinstance(coverage, dict) else []
    stage("REPORT", step=7, total=TOTAL_STAGES, detail="Deriving final audit state")
    info(f"Status: {state.get('status', 'UNKNOWN')}")
    info(f"Complete: {'yes' if state.get('complete') else 'no'}")
    info(f"Confirmed: {len(confirmed) if isinstance(confirmed, list) else 0}")
    info(f"Suspicious: {len(suspicious) if isinstance(suspicious, list) else 0}")
    info(f"Clean: {'yes' if state.get('clean') else 'no'}")
    if finished:
        if state.get("complete"):
            success("Audit complete")
        else:
            warning("Audit remains incomplete")


def _log_current_state(
    state: dict[str, Any],
    manifest: dict[str, Any],
    resolution: dict[str, Any] | None,
    domain_context: dict[str, Any] | None,
) -> None:
    status = state.get("status")
    coverage = state.get("coverage", {})
    if status == "INCOMPLETE_DOMAIN_ROUTING":
        unresolved = None
        if resolution is not None:
            unresolved = {
                domain
                for domain, value in resolution.get("domains", {}).items()
                if isinstance(value, dict) and value.get("status") == "UNKNOWN"
            }
        _log_domain_resolution(manifest, unresolved)
        return
    if status == "INCOMPLETE_CONTEXT":
        unresolved = None
        if domain_context is not None:
            unresolved = {
                f"{domain}.{key}"
                for domain, requirements in domain_context.get("domains", {}).items()
                if isinstance(requirements, dict)
                for key, value in requirements.items()
                if isinstance(value, dict) and value.get("status") == "UNKNOWN"
            }
        _log_domain_context(manifest, unresolved)
        return
    if status == "INCOMPLETE_COVERAGE":
        if manifest["deferred_domains"]:
            unresolved_domains = None
            if resolution is not None:
                unresolved_domains = {
                    domain
                    for domain, value in resolution.get("domains", {}).items()
                    if isinstance(value, dict) and value.get("status") == "UNKNOWN"
                }
            if resolution is None or unresolved_domains:
                _log_domain_resolution(manifest, unresolved_domains)
                return
        if domain_context is None:
            _log_domain_context(manifest)
            return
        unresolved_context = {
            f"{domain}.{key}"
            for domain, requirements in domain_context.get("domains", {}).items()
            if isinstance(requirements, dict)
            for key, value in requirements.items()
            if isinstance(value, dict) and value.get("status") == "UNKNOWN"
        }
        if unresolved_context:
            _log_domain_context(manifest, unresolved_context)
            return
        stage("SCREEN", step=4, total=TOTAL_STAGES, detail="Screening routed checks")
        selected = coverage.get("selected", []) if isinstance(coverage, dict) else []
        candidates = coverage.get("deep_candidates", []) if isinstance(coverage, dict) else []
        not_applicable = coverage.get("screen_not_applicable", []) if isinstance(coverage, dict) else []
        info(f"Screen checks: {len(selected) if isinstance(selected, list) else 0}")
        info(f"Deep candidates: {len(candidates) if isinstance(candidates, list) else 0}")
        info(f"Screen NOT_APPLICABLE: {len(not_applicable) if isinstance(not_applicable, list) else 0}")
        warning("Screen coverage remains incomplete")
        return
    if status == "INCOMPLETE_REVIEW":
        suspicious = coverage.get("suspicious", []) if isinstance(coverage, dict) else []
        candidates = coverage.get("deep_candidates", []) if isinstance(coverage, dict) else []
        reviewed = coverage.get("deep_reviewed", []) if isinstance(coverage, dict) else []
        pending = set(candidates) - set(reviewed) if isinstance(candidates, list) and isinstance(reviewed, list) else set()
        if pending:
            stage("DEEP REVIEW", step=5, total=TOTAL_STAGES, detail="Reviewing Deep candidates")
            info(f"Reviewed: {len(reviewed) if isinstance(reviewed, list) else 0} / {len(candidates) if isinstance(candidates, list) else 0}")
            info(f"Remaining: {len(pending)}")
        elif suspicious:
            stage("PROOF", step=6, total=TOTAL_STAGES, detail="Resolving suspicious findings")
            info(f"Remaining proof items: {len(suspicious)}")
        else:
            stage("DEEP REVIEW", step=5, total=TOTAL_STAGES, detail="Reviewing Deep candidates")
            info(f"Reviewed: {len(reviewed) if isinstance(reviewed, list) else 0} / {len(candidates) if isinstance(candidates, list) else 0}")
            info(f"Remaining: {len(candidates) - len(reviewed) if isinstance(candidates, list) and isinstance(reviewed, list) else 0}")
        warning("Further review is required")
        return
    _log_report(state, finished=True)


def init_run(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    run_dir = args.run_dir.resolve()
    if run_dir.exists() and any(run_dir.iterdir()):
        raise ValueError(f"refusing to initialize non-empty run directory: {run_dir}")
    values = paths(run_dir)
    values["feature_map"].parent.mkdir(parents=True, exist_ok=True)
    values["manifest"].parent.mkdir(parents=True, exist_ok=True)
    target = args.target.resolve()
    audit_root = (args.audit_root or target).resolve()
    recon_args = [str(target), "--root", str(root), "--output", str(values["feature_map"])]
    if args.solc:
        recon_args.extend(["--solc", args.solc])
    if args.audit_root:
        recon_args.extend(["--audit-root", str(audit_root)])
    if args.build_root:
        recon_args.extend(["--build-root", str(args.build_root.resolve())])
    for exclusion in args.exclude:
        recon_args.extend(["--exclude", exclusion])
    for include in args.include:
        recon_args.extend(["--include", include])
    for dependency_root in args.dependency_root or []:
        recon_args.extend(["--dependency-root", dependency_root])
    if args.present_only:
        recon_args.append("--present-only")
    stage("RECON", step=1, total=TOTAL_STAGES, detail="Building scope-bound Feature Map")
    try:
        _run(root, "recon.py", recon_args, verbose=args.verbose)
        feature_map = load_json(values["feature_map"])
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        warning("Recon failed")
        raise
    _log_recon(feature_map, audit_root, args.require_complete_compilation)

    selector_args = [
        "--root", str(root),
        "--feature-map", str(values["feature_map"]),
        "--target-root", str(audit_root),
        "--manifest-out", str(values["manifest"]),
        "--context-out", str(values["context"]),
        "--environment-out", str(values["environment"]),
    ]
    for exclusion in args.exclude:
        selector_args.extend(["--exclude", exclusion])
    if args.build_root:
        selector_args.extend(["--build-root", str(args.build_root.resolve())])
    for include in args.include:
        selector_args.extend(["--include", include])
    for dependency_root in args.dependency_root or []:
        selector_args.extend(["--dependency-root", dependency_root])
    for option in ("domain", "domains", "target_commit", "chain_id", "chain_family", "execution_environment", "fork_block", "compiler_version", "evm_fork", "protocol_version", "audit_timestamp"):
        value = getattr(args, option, None)
        if value is not None:
            selector_args.extend([f"--{option.replace('_', '-')}", str(value)])
    if args.require_complete_compilation:
        selector_args.append("--require-complete-compilation")
    if args.environment_context:
        selector_args.extend(["--environment-context", str(args.environment_context.resolve())])
    stage("ROUTING", step=2, total=TOTAL_STAGES, detail="Building immutable routing snapshot")
    try:
        _run(root, "select_checks.py", selector_args, verbose=args.verbose)
        manifest = load_json(values["manifest"])
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        warning("Routing failed")
        raise
    _log_routing(manifest)
    next_result = next_step(root, run_dir, verbose=args.verbose, emit=False)
    info(f"Next required stage: {_display_stage(next_result['stage'])}")
    return {
        "stage": "INITIALIZED",
        "run_dir": str(run_dir),
        "manifest": str(values["manifest"]),
        "next": next_result,
    }


def _load_run(root: Path, run_dir: Path) -> tuple[dict[str, Path], dict[str, Any], dict[str, Any]]:
    values = paths(run_dir.resolve())
    if not values["manifest"].exists():
        raise ValueError(f"run has no routing manifest: {values['manifest']}")
    manifest = load_json(values["manifest"])
    registry = load_json(root / "data/canonical-checks.json")
    validate_manifest(root, manifest, registry)
    validate_target_snapshot(manifest)
    return values, manifest, registry


def _ledger_paths(run_dir: Path) -> list[Path]:
    return sorted((run_dir / "reviews").glob("review-*.jsonl"))


def _reporting_identity(manifest: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    audit = manifest["audit_context"]
    return {
        "schema_version": 2,
        "routing_snapshot_id": manifest["routing_snapshot_id"],
        "review_state_digest": state["review_state_digest"],
        "registry_sha256": audit["registry_sha256"],
        "source_digest": audit["source_digest"],
        "compilation_input_digest": audit["compilation_input_digest"],
    }


def _reporting_payloads(manifest: dict[str, Any], state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    identity = _reporting_identity(manifest, state)
    confirmed = sorted(state["coverage"]["confirmed"])
    return {
        "severity": {
            **identity,
            "artifact_state": "TEMPLATE",
            "decisions": {
                canonical_id: {
                    "severity": "TODO",
                    "rationale": "TODO: provide proof-bound severity rationale",
                    "dimensions": {dimension: "TODO" for dimension in REPORTING_DIMENSIONS},
                }
                for canonical_id in confirmed
            },
        },
        "finding_details": {
            **identity,
            "artifact_state": "TEMPLATE",
            "findings": [
                {
                    "canonical_id": canonical_id,
                    "location": "TODO",
                    "description": "TODO: describe the confirmed defect",
                    "recommendation": "TODO: provide a concrete remediation",
                }
                for canonical_id in confirmed
            ],
        },
    }


def _reporting_ids(value: dict[str, Any], kind: str) -> tuple[set[str] | None, bool]:
    if kind == "severity":
        decisions = value.get("decisions")
        if not isinstance(decisions, dict) or any(not isinstance(canonical_id, str) for canonical_id in decisions):
            return None, False
        return set(decisions), True
    findings = value.get("findings")
    if not isinstance(findings, list):
        return None, False
    ids = [item.get("canonical_id") for item in findings if isinstance(item, dict)]
    if len(ids) != len(findings) or any(not isinstance(canonical_id, str) for canonical_id in ids):
        return None, False
    return set(ids), len(ids) == len(set(ids))


def _is_generated_reporting_template(value: dict[str, Any], kind: str) -> bool:
    if value.get("artifact_state") == "COMPLETED":
        return False
    content = value.get("decisions" if kind == "severity" else "findings")
    return has_placeholder(content)


def _reporting_matches(
    value: dict[str, Any],
    expected: dict[str, Any],
    confirmed_ids: set[str],
    kind: str,
) -> bool:
    if any(value.get(key) != expected[key] for key in REPORTING_IDENTITY_KEYS):
        return False
    actual_ids, unique = _reporting_ids(value, kind)
    return unique and actual_ids == confirmed_ids


def _archive_stale_reporting(path: Path, value: dict[str, Any], expected: dict[str, Any]) -> Path:
    digest = value.get("review_state_digest")
    prefix = digest[:12] if isinstance(digest, str) and digest else expected["review_state_digest"][:12]
    archived = path.with_name(f"{path.stem}.stale-{prefix}{path.suffix}")
    counter = 1
    while archived.exists():
        archived = path.with_name(f"{path.stem}.stale-{prefix}-{counter}{path.suffix}")
        counter += 1
    path.replace(archived)
    return archived


def _ensure_reporting_template(
    path: Path,
    payload: dict[str, Any],
    kind: str,
) -> tuple[str, Path | None]:
    if not path.exists():
        atomic_write_json(path, payload)
        return "GENERATED_TEMPLATE", None

    try:
        existing = load_json(path)
    except ValueError:
        existing = {}
    expected = {key: payload[key] for key in REPORTING_IDENTITY_KEYS}
    confirmed_ids, _ = _reporting_ids(payload, kind)
    if _reporting_matches(existing, expected, confirmed_ids or set(), kind):
        status = "CURRENT_TEMPLATE" if _is_generated_reporting_template(existing, kind) else "CURRENT_COMPLETED"
        return status, None
    if _is_generated_reporting_template(existing, kind):
        atomic_write_json(path, payload)
        return "REGENERATED_STALE_TEMPLATE", None
    archived = _archive_stale_reporting(path, existing, expected)
    atomic_write_json(path, payload)
    return "ARCHIVED_STALE_ARTIFACT", archived


def _ensure_reporting_templates(manifest: dict[str, Any], state: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    payloads = _reporting_payloads(manifest, state)
    paths_by_kind = {
        "severity": run_dir / "reviews/severity-decisions.json",
        "finding_details": run_dir / "reviews/finding-details.json",
    }
    statuses: dict[str, str] = {}
    archives: dict[str, str] = {}
    for kind, path in paths_by_kind.items():
        status, archived = _ensure_reporting_template(path, payloads[kind], kind)
        statuses[kind] = status
        if archived is not None:
            archives[kind] = str(archived)
    result = {
        "templates": {kind: str(path) for kind, path in paths_by_kind.items()},
        "template_status": statuses,
    }
    if archives:
        result["archived_templates"] = archives
    return result


def status_run(root: Path, run_dir: Path, *, emit: bool = True) -> dict[str, Any]:
    values, manifest, registry = _load_run(root, run_dir)
    screen = load_json(values["screen_results"]) if values["screen_results"].exists() else None
    resolution = load_json(values["resolution"]) if values["resolution"].exists() else None
    domain_context = load_json(values["domain_context"]) if values["domain_context"].exists() else None
    context = load_json(values["context"]) if values["context"].exists() else None
    state = validate_run(
        root,
        manifest,
        registry,
        screen,
        resolution,
        domain_context,
        context,
        _ledger_paths(run_dir),
    )
    atomic_write_json(values["audit_state"], state)
    if emit:
        _log_current_state(state, manifest, resolution, domain_context)
    return state


def next_step(root: Path, run_dir: Path, *, verbose: bool = False, emit: bool = True) -> dict[str, Any]:
    values, manifest, registry = _load_run(root, run_dir)
    resolution: dict[str, Any] | None = None
    if manifest["deferred_domains"]:
        if not values["resolution"].exists():
            if emit:
                _log_domain_resolution(manifest)
            _render_screen(
                root,
                values,
                "--domain-resolution-out",
                str(values["resolution"]),
                verbose=verbose,
            )
            if emit:
                info(f"Resolution template required: {values['resolution']}")
            return {"stage": "DOMAIN_RESOLUTION", "template": str(values["resolution"])}
        resolution = load_json(values["resolution"])
        unresolved = validate_domain_resolution(root, manifest, resolution)
        if emit:
            _log_domain_resolution(manifest, unresolved)
        if unresolved:
            return {"stage": "DOMAIN_RESOLUTION", "unresolved_domains": sorted(unresolved)}

    if not values["domain_context"].exists():
        if emit:
            stage("DOMAIN CONTEXT", step=3, total=TOTAL_STAGES, detail="Resolving required Domain context")
            info(f"Resolved: 0 / {_context_requirement_count(manifest)}")
            warning("Domain Context template required")
        extra = []
        if resolution is not None:
            extra.extend(["--domain-resolution", str(values["resolution"])])
        _render_screen(
            root,
            values,
            *extra,
            "--domain-context-out",
            str(values["domain_context"]),
            verbose=verbose,
        )
        if emit:
            info(f"Domain Context template required: {values['domain_context']}")
        return {"stage": "DOMAIN_CONTEXT", "template": str(values["domain_context"])}
    domain_context = load_json(values["domain_context"])
    unresolved_context = validate_domain_context(root, manifest, domain_context, resolution)
    if emit:
        _log_domain_context(manifest, unresolved_context)
    if unresolved_context:
        return {"stage": "DOMAIN_CONTEXT", "unresolved_context": sorted(unresolved_context)}

    if not values["screen_results"].exists():
        if emit:
            stage("SCREEN", step=4, total=TOTAL_STAGES, detail="Screening routed checks")
            info(f"Screen checks: {len(selected_entries(manifest, domain_resolution=resolution))}")
        extra = ["--domain-context", str(values["domain_context"]), "--screen-results-out", str(values["screen_results"])]
        if resolution is not None:
            extra[0:0] = ["--domain-resolution", str(values["resolution"])]
        _render_screen(root, values, *extra, verbose=verbose)
        if emit:
            info(f"Screen result template required: {values['screen_results']}")
        return {"stage": "SCREEN", "template": str(values["screen_results"])}
    screen = load_json(values["screen_results"])
    candidates = validate_screen_results(root, manifest, screen, resolution)
    if emit:
        _log_screen(screen, candidates)
    review_snapshot = derive_review_snapshot_id(
        root, manifest, resolution, domain_context, screen
    )
    if candidates:
        if emit:
            stage("DEEP REVIEW", step=5, total=TOTAL_STAGES, detail="Reviewing Deep candidates")
        for stale_view in (run_dir / "runtime").glob("deep-*.md"):
            stale_view.unlink()
        for owner in sorted({entry["owner_domain"] for entry in selected_entries(manifest, domain_resolution=resolution) if entry["canonical_id"] in candidates}):
            output = run_dir / "runtime" / f"deep-{owner}.md"
            extra = [
                "--domain-context", str(values["domain_context"]),
                "--screen-results", str(values["screen_results"]),
                "--owner-domain", owner,
                "--output", str(output),
            ]
            if resolution is not None:
                extra[0:0] = ["--domain-resolution", str(values["resolution"])]
            _run(
                root,
                "render_runtime.py",
                ["--manifest", str(values["manifest"]), "--profile", "deep", *extra],
                verbose=verbose,
            )
        records, errors = collect_review_records(
            _ledger_paths(run_dir), manifest, registry, candidates, resolution, review_snapshot
        )
        if errors:
            raise ValueError("; ".join(errors))
        pending = candidates - set(records)
        if emit:
            _log_deep(candidates, records, pending)
        if pending:
            return {"stage": "DEEP_REVIEW", "pending": sorted(pending)}
        suspicious = {
            canonical_id
            for canonical_id, record in records.items()
            if record["status"] == "SUSPICIOUS"
        }
        if suspicious:
            if emit:
                success("Deep review complete")
                stage("PROOF", step=6, total=TOTAL_STAGES, detail="Resolving suspicious findings")
                info(f"Remaining proof items: {len(suspicious)}")
            return {"stage": "PROOF", "pending": sorted(suspicious)}
        if emit:
            success("Deep review complete")

    if not candidates:
        for stale_view in (run_dir / "runtime").glob("deep-*.md"):
            stale_view.unlink()
    state = status_run(root, run_dir, emit=False)
    if emit:
        _log_report(state, finished=True)
    result: dict[str, Any] = {"stage": "REPORT", "status": state["status"], "audit_state": str(values["audit_state"])}
    if state["status"] == "COMPLETE_WITH_FINDINGS":
        result.update(_ensure_reporting_templates(manifest, state, run_dir))
        result.update(
            {
                "required_inputs": ["severity-decisions", "finding-details"],
            }
        )
    return result


def report_run(
    root: Path,
    run_dir: Path,
    severity_path: Path | None = None,
    finding_details_path: Path | None = None,
) -> dict[str, Any]:
    invalidate_final_outputs(run_dir / "AUDIT-REPORT.md", run_dir / "issue-candidates.json")
    values, manifest, registry = _load_run(root, run_dir)
    state = status_run(root, run_dir, emit=False)
    _log_report(state, finished=False)
    severity = load_json(severity_path) if state["complete"] and severity_path else None
    finding_details = load_json(finding_details_path) if state["complete"] and finding_details_path else None
    resolution = load_json(values["resolution"]) if values["resolution"].exists() else None
    screen = load_json(values["screen_results"]) if values["screen_results"].exists() else None
    domain_context = load_json(values["domain_context"]) if values["domain_context"].exists() else None
    context = load_json(values["context"]) if values["context"].exists() else None
    report, issues = synthesize(
        root,
        manifest,
        registry,
        state,
        _ledger_paths(run_dir),
        severity,
        finding_details=finding_details,
        allow_incomplete=not state["complete"],
        domain_resolution=resolution,
        screen_results=screen,
        domain_context=domain_context,
        context=context,
    )
    atomic_write_text(values["report"], report)
    atomic_write_json(values["issue_candidates"], issues)
    if state["complete"]:
        success("Audit complete")
    else:
        warning("Audit remains incomplete")
    return {
        "stage": "REPORT",
        "status": state["status"],
        "complete": state["complete"],
        "report": str(values["report"]),
        "issue_candidates": str(values["issue_candidates"]),
    }


def _add_logging_flags(parser: argparse.ArgumentParser) -> None:
    logging = parser.add_mutually_exclusive_group()
    logging.add_argument("--quiet", action="store_true", help="suppress progress output")
    logging.add_argument("--verbose", action="store_true", help="forward child diagnostics")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("target", type=Path)
    init.add_argument("--run-dir", type=Path, required=True)
    init.add_argument("--audit-root", type=Path)
    init.add_argument("--build-root", type=Path)
    init.add_argument("--root", type=Path, default=ROOT)
    init.add_argument("--solc")
    init.add_argument("--present-only", action="store_true")
    init.add_argument("--exclude", action="append", default=[])
    init.add_argument("--include", action="append", default=[])
    init.add_argument("--dependency-root", action="append", default=None)
    init.add_argument("--domain")
    init.add_argument("--domains")
    init.add_argument("--target-commit")
    init.add_argument("--chain-id", type=int)
    init.add_argument("--chain-family")
    init.add_argument("--execution-environment")
    init.add_argument("--fork-block", type=int)
    init.add_argument("--compiler-version")
    init.add_argument("--evm-fork")
    init.add_argument("--protocol-version")
    init.add_argument("--audit-timestamp")
    init.add_argument("--environment-context", type=Path)
    init.add_argument("--require-complete-compilation", action="store_true")
    _add_logging_flags(init)

    for name in ("next", "status"):
        command = subparsers.add_parser(name)
        command.add_argument("--run-dir", type=Path, required=True)
        command.add_argument("--root", type=Path, default=ROOT)
        _add_logging_flags(command)

    report = subparsers.add_parser("report")
    report.add_argument("--run-dir", type=Path, required=True)
    report.add_argument("--root", type=Path, default=ROOT)
    report.add_argument("--severity-decisions", type=Path)
    report.add_argument("--finding-details", type=Path)
    _add_logging_flags(report)

    args = parser.parse_args(argv)
    configure(quiet=args.quiet, verbose=args.verbose)
    try:
        root = args.root.resolve()
        if args.command == "init":
            result = init_run(root, args)
        elif args.command == "next":
            result = next_step(root, args.run_dir, verbose=args.verbose)
        elif args.command == "status":
            result = status_run(root, args.run_dir)
        else:
            result = report_run(root, args.run_dir, args.severity_decisions, args.finding_details)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.command == "report" and result.get("complete") is False else 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        error(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
