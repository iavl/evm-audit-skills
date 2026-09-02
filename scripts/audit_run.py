#!/usr/bin/env python3
"""Advance an audit run through deterministic artifact stages."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evm_audit_runtime.versions import REPORT_CURRENT_VERSION, REPORTING_VERSION
from evm_audit_runtime.controller_state import STAGE_PROGRESS, TOTAL_STAGES, display_stage as _display_stage, progress_metadata

try:
    from runtime_log import configure, error, info, stage, success, warning
except ImportError:  # pragma: no cover
    from scripts.runtime_log import configure, error, info, stage, success, warning

try:
    from codex_model_profile import (
        default_profile,
        global_profile_path,
        init_global_profile,
        load_profile,
        load_global_profile,
        stage_model,
        write_profile,
    )
except ImportError:  # pragma: no cover
    from scripts.codex_model_profile import (
        default_profile,
        global_profile_path,
        init_global_profile,
        load_profile,
        load_global_profile,
        stage_model,
        write_profile,
    )

try:
    from audit_artifacts import (
        atomic_write_bytes,
        atomic_write_json,
        atomic_write_text,
        bound_code_index_status,
        derive_review_snapshot_id,
        json_text,
        load_json,
        load_json_bytes,
        report_bundle_metadata,
        validate_report_generation,
        validate_domain_context,
        validate_domain_resolution,
        validate_issue_candidates,
        validate_reporting_inputs,
        validate_schema,
        validate_target_snapshot,
    )
    from render_runtime import runtime_identity, selected_entries, validate_manifest, validate_screen_results
    from review_ledger import _ledger_lock, collect_review_records
    from synthesize_report import synthesize
    from validate_audit_run import validate_run
except ImportError:  # pragma: no cover
    from scripts.audit_artifacts import (
        atomic_write_bytes,
        atomic_write_json,
        atomic_write_text,
        bound_code_index_status,
        derive_review_snapshot_id,
        json_text,
        load_json,
        load_json_bytes,
        report_bundle_metadata,
        validate_report_generation,
        validate_domain_context,
        validate_domain_resolution,
        validate_issue_candidates,
        validate_reporting_inputs,
        validate_schema,
        validate_target_snapshot,
    )
    from scripts.render_runtime import runtime_identity, selected_entries, validate_manifest, validate_screen_results
    from scripts.review_ledger import _ledger_lock, collect_review_records
    from scripts.synthesize_report import synthesize
    from scripts.validate_audit_run import validate_run


ROOT = Path(__file__).resolve().parents[1]
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


def paths(run_dir: Path) -> dict[str, Any]:
    return {
        "feature_map": run_dir / "recon/feature-map.json",
        "code_index": run_dir / "recon/code-index.json",
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
        "report_bundle": run_dir / "report-bundle.json",
        "report_current": run_dir / "report-current.json",
        "report_generations": run_dir / "report-generations",
        "severity_decisions": run_dir / "reviews/severity-decisions.json",
        "finding_details": run_dir / "reviews/finding-details.json",
        "report_input_severity": run_dir / "report-inputs/severity-decisions.json",
        "report_input_details": run_dir / "report-inputs/finding-details.json",
        "model_profile": run_dir / "config/codex-model-profile.json",
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


def _emit_stage(stage_name: str, detail: str) -> None:
    progress = progress_metadata(stage_name)
    stage(progress["label"], step=progress["step"], total=progress["total"], detail=detail)


def _effective_model_profile(run_dir: Path) -> dict[str, Any]:
    profile_path = paths(run_dir.resolve())["model_profile"]
    return load_profile(profile_path) if profile_path.exists() else default_profile()


def recommended_execution(run_dir: Path, stage_name: str) -> dict[str, str]:
    profile = _effective_model_profile(run_dir)
    return {"provider": profile["provider"], **stage_model(profile, stage_name)}


def _log_model_guidance(run_dir: Path | None, stage_name: str) -> None:
    if run_dir is None:
        return
    execution = recommended_execution(run_dir, stage_name)
    info(f"Codex model: {execution['model']}")
    info(f"Reasoning: {execution['reasoning_effort']}")
    info("Handoff: controller does not switch the active Codex model")


def _stage_result(
    run_dir: Path,
    stage_name: str,
    *,
    summary: str | None = None,
    navigation: dict[str, Any] | None = None,
    **values: Any,
) -> dict[str, Any]:
    result = {
        "stage": stage_name,
        **values,
        "progress": progress_metadata(stage_name, summary=summary),
        "recommended_execution": recommended_execution(run_dir, stage_name),
    }
    if navigation is not None:
        result["navigation"] = navigation
    return result


def _progress_history_entry(
    run_dir: Path,
    stage_name: str,
    state: str,
    *,
    summary: str | None = None,
) -> dict[str, Any]:
    return {
        "stage": stage_name,
        "state": state,
        "progress": progress_metadata(stage_name, summary=summary),
        "recommended_execution": recommended_execution(run_dir, stage_name),
    }


def _recon_progress_summary(feature_map: dict[str, Any]) -> str:
    recon = feature_map["recon_context"]
    files_analyzed = recon.get("files_analyzed", [])
    file_count = len(files_analyzed) if isinstance(files_analyzed, list) else 0
    compilation = "COMPLETE" if recon.get("compilation_complete") else "INCOMPLETE"
    return f"{file_count} Solidity files analyzed; compilation {compilation}"


def _routing_progress_summary(manifest: dict[str, Any]) -> str:
    return (
        f"{len(manifest['selected_domains'])} selected domains; "
        f"{manifest['selected_count']} checks selected; "
        f"{len(manifest['deferred_domains'])} deferred domains; "
        f"{manifest['deferred_count']} checks deferred"
    )


def _unknown_domains(resolution: dict[str, Any] | None) -> set[str] | None:
    if resolution is None:
        return None
    return {
        domain
        for domain, value in resolution.get("domains", {}).items()
        if isinstance(value, dict) and value.get("status") == "UNKNOWN"
    }


def _unknown_context(domain_context: dict[str, Any] | None) -> set[str] | None:
    if domain_context is None:
        return None
    return {
        f"{domain}.{key}"
        for domain, requirements in domain_context.get("domains", {}).items()
        if isinstance(requirements, dict)
        for key, value in requirements.items()
        if isinstance(value, dict) and value.get("status") == "UNKNOWN"
    }


def _state_stage(
    state: dict[str, Any],
    manifest: dict[str, Any],
    resolution: dict[str, Any] | None,
    domain_context: dict[str, Any] | None,
) -> str | None:
    status = state.get("status")
    coverage = state.get("coverage", {})
    if status == "INCOMPLETE_DOMAIN_ROUTING":
        return "DOMAIN_RESOLUTION"
    if status == "INCOMPLETE_CONTEXT":
        return "DOMAIN_CONTEXT"
    if status == "INCOMPLETE_COVERAGE":
        unresolved_domains = _unknown_domains(resolution)
        if manifest.get("deferred_domains") and (unresolved_domains is None or unresolved_domains):
            return "DOMAIN_RESOLUTION"
        if domain_context is None or _unknown_context(domain_context):
            return "DOMAIN_CONTEXT"
        return "SCREEN"
    if status == "INCOMPLETE_REVIEW":
        candidates = coverage.get("deep_candidates", []) if isinstance(coverage, dict) else []
        reviewed = coverage.get("deep_reviewed", []) if isinstance(coverage, dict) else []
        if isinstance(candidates, list) and isinstance(reviewed, list) and set(candidates) - set(reviewed):
            return "DEEP_REVIEW"
        if isinstance(coverage, dict) and coverage.get("suspicious"):
            return "PROOF"
        return "DEEP_REVIEW"
    if status in {"COMPLETE_CLEAN", "COMPLETE_WITH_FINDINGS"}:
        return "REPORT"
    return None


def _log_recon(feature_map: dict[str, Any], target: Path, strict: bool, *, run_dir: Path | None = None) -> None:
    recon = feature_map["recon_context"]
    complete = recon["compilation_complete"]
    info(f"Audit scope: {target}")
    info(f"Compilation: {'COMPLETE' if complete else 'INCOMPLETE'}")
    _log_model_guidance(run_dir, "RECON")
    if complete:
        success("Recon complete")
    else:
        warning("Recon compilation coverage is incomplete")
        if strict:
            warning("Strict compilation policy rejected this scope")


def _log_routing(manifest: dict[str, Any], *, run_dir: Path | None = None) -> None:
    info(f"Selected domains: {len(manifest['selected_domains'])}")
    info(f"Deferred domains: {len(manifest['deferred_domains'])}")
    info(f"Filtered domains: {len(manifest['filtered_domains'])}")
    info(f"Selected checks: {manifest['selected_count']}")
    info(f"Deferred checks: {manifest['deferred_count']}")
    info(f"Filtered checks: {manifest['filtered_count']}")
    _log_model_guidance(run_dir, "ROUTING")
    success("Routing snapshot created")


def _log_domain_resolution(
    manifest: dict[str, Any], unresolved: set[str] | None = None, *, run_dir: Path | None = None
) -> None:
    _emit_stage("DOMAIN_RESOLUTION", "Resolving Deferred Domains")
    _log_model_guidance(run_dir, "DOMAIN_RESOLUTION")
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


def _domain_resolution_summary(
    manifest: dict[str, Any], unresolved: set[str] | None = None
) -> str:
    remaining = (
        unresolved
        if unresolved is not None
        else {entry["domain"] for entry in manifest.get("deferred_domains", [])}
    )
    if remaining:
        suffix = "remain unresolved" if unresolved is not None else "require resolution"
        return f"{len(remaining)} Deferred Domains {suffix}"
    return "All Deferred Domains resolved"


def _domain_context_summary(
    manifest: dict[str, Any], unresolved: set[str] | None = None
) -> str:
    if unresolved is None:
        remaining = {
            f"{domain}.{key}"
            for domain, requirements in manifest.get("required_context_requirements", {}).items()
            if isinstance(requirements, dict)
            for key in requirements
        }
        suffix = "need resolution"
    else:
        remaining = unresolved
        suffix = "remain unresolved"
    if remaining:
        return f"{len(remaining)} required context fields {suffix}"
    return "All required Domain context resolved"


def _screen_summary(
    manifest: dict[str, Any],
    *,
    resolution: dict[str, Any] | None = None,
    coverage: dict[str, Any] | None = None,
) -> str:
    selected = (
        set(coverage.get("selected", []))
        if isinstance(coverage, dict) and isinstance(coverage.get("selected"), list)
        else {entry["canonical_id"] for entry in selected_entries(manifest, domain_resolution=resolution)}
    )
    if isinstance(coverage, dict):
        classified = set(coverage.get("screen_not_applicable", [])) | set(coverage.get("deep_candidates", []))
        remaining = selected - classified
    else:
        remaining = selected
    return f"{len(remaining)} checks require Screen classification"


def _state_progress_summary(
    stage_name: str,
    state: dict[str, Any],
    manifest: dict[str, Any],
    resolution: dict[str, Any] | None,
    domain_context: dict[str, Any] | None,
) -> str:
    coverage = state.get("coverage", {})
    if stage_name == "DOMAIN_RESOLUTION":
        return _domain_resolution_summary(manifest, _unknown_domains(resolution))
    if stage_name == "DOMAIN_CONTEXT":
        return _domain_context_summary(manifest, _unknown_context(domain_context))
    if stage_name == "SCREEN":
        return _screen_summary(manifest, resolution=resolution, coverage=coverage)
    if stage_name == "DEEP_REVIEW":
        candidates = coverage.get("deep_candidates", []) if isinstance(coverage, dict) else []
        reviewed = coverage.get("deep_reviewed", []) if isinstance(coverage, dict) else []
        pending = set(candidates) - set(reviewed) if isinstance(candidates, list) and isinstance(reviewed, list) else set()
        return f"{len(pending)} Deep Review candidates remain"
    if stage_name == "PROOF":
        suspicious = coverage.get("suspicious", []) if isinstance(coverage, dict) else []
        return f"{len(suspicious) if isinstance(suspicious, list) else 0} suspicious findings require Proof"
    if stage_name == "REPORT":
        return f"Audit state: {state.get('status', 'UNKNOWN')}"
    return progress_metadata(stage_name)["summary"]


def _log_domain_context(
    manifest: dict[str, Any], unresolved: set[str] | None = None, *, run_dir: Path | None = None
) -> None:
    _emit_stage("DOMAIN_CONTEXT", "Resolving required Domain context")
    _log_model_guidance(run_dir, "DOMAIN_CONTEXT")
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


def _log_screen(screen: dict[str, Any], candidates: set[str], *, run_dir: Path | None = None) -> None:
    results = screen.get("results", [])
    total = len(results) if isinstance(results, list) else 0
    _emit_stage("SCREEN", "Screening routed checks")
    _log_model_guidance(run_dir, "SCREEN")
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


def _log_report(state: dict[str, Any], *, finished: bool, run_dir: Path | None = None) -> None:
    coverage = state.get("coverage", {})
    confirmed = coverage.get("confirmed", []) if isinstance(coverage, dict) else []
    suspicious = coverage.get("suspicious", []) if isinstance(coverage, dict) else []
    _emit_stage("REPORT", "Deriving final audit state")
    _log_model_guidance(run_dir, "REPORT")
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
    *,
    run_dir: Path | None = None,
) -> None:
    status = state.get("status")
    coverage = state.get("coverage", {})
    if status == "INCOMPLETE_DOMAIN_ROUTING":
        unresolved = None
        if resolution is not None:
            unresolved = _unknown_domains(resolution)
        _log_domain_resolution(manifest, unresolved, run_dir=run_dir)
        return
    if status == "INCOMPLETE_CONTEXT":
        unresolved = None
        if domain_context is not None:
            unresolved = _unknown_context(domain_context)
        _log_domain_context(manifest, unresolved, run_dir=run_dir)
        return
    if status == "INCOMPLETE_COVERAGE":
        if manifest["deferred_domains"]:
            unresolved_domains = None
            if resolution is not None:
                unresolved_domains = _unknown_domains(resolution)
            if resolution is None or unresolved_domains:
                _log_domain_resolution(manifest, unresolved_domains, run_dir=run_dir)
                return
        if domain_context is None:
            _log_domain_context(manifest, run_dir=run_dir)
            return
        unresolved_context = _unknown_context(domain_context) or set()
        if unresolved_context:
            _log_domain_context(manifest, unresolved_context, run_dir=run_dir)
            return
        _emit_stage("SCREEN", "Screening routed checks")
        _log_model_guidance(run_dir, "SCREEN")
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
            _emit_stage("DEEP_REVIEW", "Reviewing Deep candidates")
            _log_model_guidance(run_dir, "DEEP_REVIEW")
            info(f"Reviewed: {len(reviewed) if isinstance(reviewed, list) else 0} / {len(candidates) if isinstance(candidates, list) else 0}")
            info(f"Remaining: {len(pending)}")
        elif suspicious:
            _emit_stage("PROOF", "Resolving suspicious findings")
            _log_model_guidance(run_dir, "PROOF")
            info(f"Remaining proof items: {len(suspicious)}")
        else:
            _emit_stage("DEEP_REVIEW", "Reviewing Deep candidates")
            _log_model_guidance(run_dir, "DEEP_REVIEW")
            info(f"Reviewed: {len(reviewed) if isinstance(reviewed, list) else 0} / {len(candidates) if isinstance(candidates, list) else 0}")
            info(f"Remaining: {len(candidates) - len(reviewed) if isinstance(candidates, list) and isinstance(reviewed, list) else 0}")
        warning("Further review is required")
        return
    _log_report(state, finished=True, run_dir=run_dir)


def _init_model_profile(args: argparse.Namespace, run_dir: Path) -> None:
    if args.model_profile:
        profile = load_profile(args.model_profile.resolve())
    elif args.accept_default_models:
        profile = default_profile()
    else:
        profile = load_global_profile() or default_profile()
    write_profile(paths(run_dir)["model_profile"], profile)


def _relocate_paths(value: Any, source: Path, target: Path) -> Any:
    if isinstance(value, str):
        prefix = str(source)
        return str(target) + value[len(prefix):] if value.startswith(prefix) else value
    if isinstance(value, list):
        return [_relocate_paths(item, source, target) for item in value]
    if isinstance(value, dict):
        return {key: _relocate_paths(item, source, target) for key, item in value.items()}
    return value


def init_run(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    run_dir = args.run_dir.resolve()
    if run_dir.exists():
        if not run_dir.is_dir() or any(run_dir.iterdir()):
            raise ValueError(f"refusing to initialize non-empty run directory: {run_dir}")
    run_dir.parent.mkdir(parents=True, exist_ok=True)
    staging: Path | None = Path(tempfile.mkdtemp(prefix=f".{run_dir.name}.init-", dir=run_dir.parent))
    try:
        assert staging is not None
        _init_model_profile(args, staging)
        values = paths(staging)
        values["feature_map"].parent.mkdir(parents=True, exist_ok=True)
        values["manifest"].parent.mkdir(parents=True, exist_ok=True)
        target = args.target.resolve()
        audit_root = (args.audit_root or target).resolve()
        recon_args = [str(target), "--root", str(root), "--output", str(values["feature_map"])]
        if args.solc:
            recon_args.extend(["--solc", args.solc])
        recon_args.extend(["--code-index-out", str(values["code_index"])])
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
        _emit_stage("RECON", "Building scope-bound Feature Map")
        try:
            _run(root, "recon.py", recon_args, verbose=args.verbose)
            feature_map = load_json(values["feature_map"])
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            warning("Recon failed")
            raise
        _log_recon(feature_map, audit_root, args.require_complete_compilation, run_dir=staging)

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
        _emit_stage("ROUTING", "Building immutable routing snapshot")
        try:
            _run(root, "select_checks.py", selector_args, verbose=args.verbose)
            manifest = load_json(values["manifest"])
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            warning("Routing failed")
            raise
        _log_routing(manifest, run_dir=staging)
        next_result = next_step(root, staging, verbose=args.verbose, emit=False)
        _load_run(root, staging)

        staged_run = staging
        if run_dir.exists():
            if not run_dir.is_dir() or any(run_dir.iterdir()):
                raise ValueError(f"run directory changed during initialization: {run_dir}")
            run_dir.rmdir()
        staged_run.replace(run_dir)
        staging = None
        next_result = _relocate_paths(next_result, staged_run, run_dir)
        info(f"Next required stage: {_display_stage(next_result['stage'])}")
        _log_model_guidance(run_dir, next_result["stage"])
        values = paths(run_dir)
        progress_history = [
            _progress_history_entry(
                run_dir,
                "RECON",
                "COMPLETED",
                summary=_recon_progress_summary(feature_map),
            ),
            _progress_history_entry(
                run_dir,
                "ROUTING",
                "COMPLETED",
                summary=_routing_progress_summary(manifest),
            ),
            {
                "stage": next_result["stage"],
                "state": "CURRENT",
                "progress": next_result["progress"],
                "recommended_execution": next_result["recommended_execution"],
            },
        ]
        return {
            "stage": "INITIALIZED",
            "run_dir": str(run_dir),
            "manifest": str(values["manifest"]),
            "code_index": str(values["code_index"]),
            "progress_history": progress_history,
            "next": next_result,
            "recommended_execution": next_result["recommended_execution"],
        }
    finally:
        if staging is not None and staging.exists():
            shutil.rmtree(staging)


def _optional_code_index_status(
    root: Path,
    values: dict[str, Any],
    manifest: dict[str, Any],
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return bound_code_index_status(root, manifest, values["code_index"], registry=registry)


def _report_generation_paths(base: Path) -> dict[str, Path]:
    return {
        "report": base / "AUDIT-REPORT.md",
        "issue_candidates": base / "issue-candidates.json",
        "report_bundle": base / "report-bundle.json",
        "report_input_severity": base / "severity-decisions.json",
        "report_input_details": base / "finding-details.json",
    }


@contextmanager
def _report_publication_lock(run_dir: Path):
    """Serialize report publication using the ledger's portable lock protocol."""
    with _ledger_lock(run_dir / "report-publication", shared=False):
        yield


def _publication_identity(manifest: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    return {
        "routing_snapshot_id": manifest["routing_snapshot_id"],
        "review_snapshot_id": state.get("review_snapshot_id"),
        "review_state_digest": state.get("review_state_digest"),
        "status": state.get("status"),
    }


def _pointer_references_generation(path: Path, generation: str) -> bool:
    try:
        return load_json(path).get("generation") == generation
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def _report_generation_inventory(
    values: dict[str, Any],
    current_generation: str | None = None,
) -> dict[str, list[str]]:
    staging_artifacts: list[str] = []
    orphaned_generations: list[str] = []
    generations = values["report_generations"]
    if generations.exists() and not generations.is_dir():
        raise ValueError(f"report-generations is not a directory: {generations}")
    if not generations.exists():
        return {"orphaned_generations": orphaned_generations, "staging_artifacts": staging_artifacts}
    for path in sorted(generations.iterdir(), key=lambda item: item.name):
        if path.is_symlink() or not path.is_dir():
            continue
        if path.name.startswith(".tmp-"):
            staging_artifacts.append(path.name)
        elif path.name.startswith("generation-") and path.name != current_generation:
            orphaned_generations.append(path.name)
    return {
        "orphaned_generations": orphaned_generations,
        "staging_artifacts": staging_artifacts,
    }


def _current_report_generation(
    root: Path,
    values: dict[str, Any],
) -> tuple[dict[str, Path], dict[str, Any]] | None:
    pointer_path = values["report_current"]
    if not pointer_path.exists():
        return None
    pointer = load_json(pointer_path)
    validate_schema(root, "report-current.schema.json", pointer)
    generation = pointer["generation"]
    generation_root = values["report_generations"] / generation
    if generation_root.parent.resolve() != values["report_generations"].resolve() or not generation_root.is_dir():
        raise ValueError("report-current.json points outside report-generations")
    artifacts = _report_generation_paths(generation_root)
    bundle_bytes = artifacts["report_bundle"].read_bytes()
    if hashlib.sha256(bundle_bytes).hexdigest() != pointer["report_bundle_sha256"]:
        raise ValueError("report-current.json does not match its report bundle")
    return artifacts, pointer


def _sync_report_convenience_copies(
    values: dict[str, Any],
    artifacts: dict[str, Path],
    *,
    finding_report: bool,
) -> dict[str, Any]:
    # ponytail: convenience copies are best-effort; report-current.json is the commit boundary.
    copies = (
        (values["report"], artifacts["report"]),
        (values["issue_candidates"], artifacts["issue_candidates"]),
        (values["report_bundle"], artifacts["report_bundle"]),
    )
    if finding_report:
        copies += (
            (values["report_input_severity"], artifacts["report_input_severity"]),
            (values["report_input_details"], artifacts["report_input_details"]),
        )
    failed_paths: list[str] = []
    warnings: list[str] = []
    for destination, source in copies:
        try:
            atomic_write_bytes(destination, source.read_bytes())
        except OSError as exc:
            message = f"could not refresh convenience report copy {destination}: {exc}"
            failed_paths.append(str(destination))
            warnings.append(message)
            warning(message)
    return {"synced": not failed_paths, "failed_paths": failed_paths, "warnings": warnings}


def _convenience_copies_current(
    values: dict[str, Any],
    artifacts: dict[str, Path],
    *,
    finding_report: bool,
) -> bool:
    copies = (
        (values["report"], artifacts["report"]),
        (values["issue_candidates"], artifacts["issue_candidates"]),
        (values["report_bundle"], artifacts["report_bundle"]),
    )
    if finding_report:
        copies += (
            (values["report_input_severity"], artifacts["report_input_severity"]),
            (values["report_input_details"], artifacts["report_input_details"]),
        )
    try:
        return all(destination.exists() and destination.read_bytes() == source.read_bytes() for destination, source in copies)
    except OSError:
        return False


def _report_bundle_status(
    root: Path,
    values: dict[str, Any],
    manifest: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    try:
        current = _current_report_generation(root, values)
        artifacts, pointer = current if current is not None else (values, None)
        inventory = _report_generation_inventory(values, pointer["generation"] if pointer else None)
        if pointer is None and values["report_bundle"].exists():
            return {
                "status": "ABSENT",
                "current": False,
                "message": "legacy report outputs are uncommitted; rerun report to republish",
                **inventory,
            }
        marker = artifacts["report_bundle"]
        if not marker.exists():
            if pointer is not None:
                raise ValueError("current report generation has no report bundle")
            return {
                "status": "ABSENT",
                "current": False,
                "message": "report bundle has not been committed",
                **inventory,
            }
        metadata = load_json(marker)
        validate_schema(root, "report-bundle.schema.json", metadata)
        issue_candidates, issue_candidates_bytes = load_json_bytes(artifacts["issue_candidates"])
        severity_decisions_bytes = finding_details_bytes = None
        severity_decisions = finding_details = None
        if state.get("status") == "COMPLETE_WITH_FINDINGS":
            severity_decisions, severity_decisions_bytes = load_json_bytes(artifacts["report_input_severity"])
            finding_details, finding_details_bytes = load_json_bytes(artifacts["report_input_details"])
            validate_reporting_inputs(
                root,
                manifest,
                state,
                severity_decisions,
                finding_details,
            )
        validate_issue_candidates(
            root,
            manifest,
            state,
            issue_candidates,
            severity_decisions,
        )
        if pointer is not None:
            run_dir = values["manifest"].parent.parent
            resolution = load_json(values["resolution"]) if values["resolution"].exists() else None
            screen = load_json(values["screen_results"]) if values["screen_results"].exists() else None
            domain_context = load_json(values["domain_context"]) if values["domain_context"].exists() else None
            context = load_json(values["context"]) if values["context"].exists() else None
            synthesis = synthesize(
                root,
                manifest,
                load_json(root / "data/canonical-checks.json"),
                state,
                _ledger_paths(run_dir),
                severity_decisions,
                finding_details=finding_details,
                severity_decisions_bytes=severity_decisions_bytes,
                finding_details_bytes=finding_details_bytes,
                allow_incomplete=not state["complete"],
                domain_resolution=resolution,
                screen_results=screen,
                domain_context=domain_context,
                context=context,
            )
            if synthesis.state != state:
                raise ValueError("report generation state differs from current audit state")
            validate_report_generation(
                synthesis.report,
                synthesis.issue_candidates,
                artifacts["report"].read_bytes(),
                issue_candidates,
                issue_candidates_bytes,
            )
        expected = report_bundle_metadata(
            manifest,
            state,
            artifacts["report"].read_bytes(),
            issue_candidates,
            issue_candidates_bytes=issue_candidates_bytes,
            severity_decisions_bytes=severity_decisions_bytes,
            finding_details_bytes=finding_details_bytes,
        )
        if metadata != expected:
            raise ValueError("report bundle marker or body hashes do not match current audit state")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        return {"status": "STALE", "current": False, "message": f"report bundle is not current: {error}"}
    finding_report = state.get("status") == "COMPLETE_WITH_FINDINGS"
    convenience_synced = _convenience_copies_current(values, artifacts, finding_report=finding_report)
    result = {
        "status": "CURRENT",
        "current": True,
        "message": "report bundle matches current audit state",
        "convenience_synced": convenience_synced,
        **inventory,
    }
    if pointer is not None:
        result.update(
            {
                "generation": pointer["generation"],
                "report": str(artifacts["report"]),
                "issue_candidates": str(artifacts["issue_candidates"]),
                "bundle": str(artifacts["report_bundle"]),
            }
        )
    return result


def _report_generation_status(values: dict[str, Any], bundle_status: dict[str, Any]) -> dict[str, Any]:
    result = {
        "status": bundle_status["status"],
        "current": bundle_status["current"],
        "current_pointer": str(values["report_current"]),
        "convenience_synced": bundle_status.get("convenience_synced", False),
    }
    for key in ("generation", "report", "issue_candidates", "bundle"):
        if key in bundle_status:
            result[key] = bundle_status[key]
    return result


def _load_run(root: Path, run_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    values = paths(run_dir.resolve())
    if not values["manifest"].exists():
        raise ValueError(f"run has no routing manifest: {values['manifest']}")
    manifest = load_json(values["manifest"])
    registry = load_json(root / "data/canonical-checks.json")
    validate_manifest(root, manifest, registry)
    validate_target_snapshot(manifest)
    values["code_index_status"] = _optional_code_index_status(root, values, manifest, registry)
    if values["code_index_status"]["status"] not in {"ABSENT", "CURRENT"}:
        warning(values["code_index_status"]["message"])
    return values, manifest, registry


def _ledger_paths(run_dir: Path) -> list[Path]:
    return sorted((run_dir / "reviews").glob("review-*.jsonl"))


def _runtime_view_current(output: Path, expected: dict[str, Any]) -> bool:
    metadata = output.with_suffix(".meta.json")
    if not output.exists() or not metadata.exists():
        return False
    try:
        value = load_json(metadata)
        validate_schema(ROOT, "runtime-metadata.schema.json", value)
        identity = {key: item for key, item in value.items() if key != "runtime_sha256"}
        return identity == expected and value["runtime_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def _prune_runtime_views(run_dir: Path, profile: str, keep: set[Path]) -> None:
    for output in (run_dir / "runtime").glob(f"{profile}-*.md"):
        if output.resolve() in keep:
            continue
        output.unlink()
        metadata = output.with_suffix(".meta.json")
        if metadata.exists():
            metadata.unlink()


def _render_owner_view(
    root: Path,
    values: dict[str, Path],
    *,
    profile: str,
    owner: str,
    ids: set[str],
    review_snapshot: str,
    resolution: Path | None = None,
    ledger_paths: list[Path] | None = None,
    verbose: bool = False,
) -> tuple[Path, bool]:
    output = values["manifest"].parent.parent / "runtime" / f"{profile}-{owner}.md"
    expected = runtime_identity(
        load_json(values["manifest"]), profile, sorted(ids), owner, review_snapshot
    )
    if _runtime_view_current(output, expected):
        return output, True
    extra = [
        "--domain-context", str(values["domain_context"]),
        "--screen-results", str(values["screen_results"]),
        "--owner-domain", owner,
        "--output", str(output),
    ]
    if resolution is not None:
        extra[0:0] = ["--domain-resolution", str(resolution)]
    if profile == "proof":
        for ledger in ledger_paths or []:
            extra.extend(["--ledger", str(ledger)])
    _run(
        root,
        "render_runtime.py",
        ["--manifest", str(values["manifest"]), "--profile", profile, *extra],
        verbose=verbose,
    )
    if not _runtime_view_current(output, expected):
        raise ValueError(f"renderer produced an invalid runtime view: {output}")
    return output, False


def _reporting_identity(manifest: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    audit = manifest["audit_context"]
    return {
        "schema_version": REPORTING_VERSION,
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
    return value.get("artifact_state") == "TEMPLATE"


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


def status_run(
    root: Path,
    run_dir: Path,
    *,
    emit: bool = True,
    include_execution: bool = False,
) -> dict[str, Any]:
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
        _log_current_state(state, manifest, resolution, domain_context, run_dir=run_dir)
    if not include_execution:
        return state
    bundle_status = _report_bundle_status(root, values, manifest, state)
    stage_name = _state_stage(state, manifest, resolution, domain_context)
    if stage_name is None:
        return state
    return {
        **state,
        "stage": stage_name,
        "progress": progress_metadata(
            stage_name,
            summary=_state_progress_summary(
                stage_name, state, manifest, resolution, domain_context
            ),
        ),
        "recommended_execution": recommended_execution(run_dir, stage_name),
        "navigation": values["code_index_status"],
        "report_bundle": bundle_status,
        "report_generation": _report_generation_status(values, bundle_status),
    }


def next_step(root: Path, run_dir: Path, *, verbose: bool = False, emit: bool = True) -> dict[str, Any]:
    values, manifest, registry = _load_run(root, run_dir)
    resolution: dict[str, Any] | None = None
    if manifest["deferred_domains"]:
        if not values["resolution"].exists():
            if emit:
                _log_domain_resolution(manifest, run_dir=run_dir)
            _render_screen(
                root,
                values,
                "--domain-resolution-out",
                str(values["resolution"]),
                verbose=verbose,
            )
            if emit:
                info(f"Resolution template required: {values['resolution']}")
            return _stage_result(
                run_dir,
                "DOMAIN_RESOLUTION",
                summary=_domain_resolution_summary(manifest),
                navigation=values["code_index_status"],
                template=str(values["resolution"]),
            )
        resolution = load_json(values["resolution"])
        unresolved = validate_domain_resolution(root, manifest, resolution)
        if emit:
            _log_domain_resolution(manifest, unresolved, run_dir=run_dir)
        if unresolved:
            return _stage_result(
                run_dir,
                "DOMAIN_RESOLUTION",
                summary=_domain_resolution_summary(manifest, unresolved),
                navigation=values["code_index_status"],
                unresolved_domains=sorted(unresolved),
            )

    if not values["domain_context"].exists():
        if emit:
            _emit_stage("DOMAIN_CONTEXT", "Resolving required Domain context")
            _log_model_guidance(run_dir, "DOMAIN_CONTEXT")
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
        return _stage_result(
            run_dir,
            "DOMAIN_CONTEXT",
            summary=_domain_context_summary(manifest),
            navigation=values["code_index_status"],
            template=str(values["domain_context"]),
        )
    domain_context = load_json(values["domain_context"])
    unresolved_context = validate_domain_context(root, manifest, domain_context, resolution)
    if emit:
        _log_domain_context(manifest, unresolved_context, run_dir=run_dir)
    if unresolved_context:
        return _stage_result(
            run_dir,
            "DOMAIN_CONTEXT",
            summary=_domain_context_summary(manifest, unresolved_context),
            navigation=values["code_index_status"],
            unresolved_context=sorted(unresolved_context),
        )

    if not values["screen_results"].exists():
        if emit:
            _emit_stage("SCREEN", "Screening routed checks")
            _log_model_guidance(run_dir, "SCREEN")
            info(f"Screen checks: {len(selected_entries(manifest, domain_resolution=resolution))}")
        extra = ["--domain-context", str(values["domain_context"]), "--screen-results-out", str(values["screen_results"])]
        if resolution is not None:
            extra[0:0] = ["--domain-resolution", str(values["resolution"])]
        _render_screen(root, values, *extra, verbose=verbose)
        if emit:
            info(f"Screen result template required: {values['screen_results']}")
        return _stage_result(
            run_dir,
            "SCREEN",
            summary=_screen_summary(manifest, resolution=resolution),
            navigation=values["code_index_status"],
            template=str(values["screen_results"]),
        )
    screen = load_json(values["screen_results"])
    candidates = validate_screen_results(root, manifest, screen, resolution)
    if emit:
        _log_screen(screen, candidates, run_dir=run_dir)
    review_snapshot = derive_review_snapshot_id(
        root, manifest, resolution, domain_context, screen
    )
    if candidates:
        if emit:
            _emit_stage("DEEP_REVIEW", "Reviewing Deep candidates")
            _log_model_guidance(run_dir, "DEEP_REVIEW")
        deep_views: set[Path] = set()
        for owner in sorted({entry["owner_domain"] for entry in selected_entries(manifest, domain_resolution=resolution) if entry["canonical_id"] in candidates}):
            output, _ = _render_owner_view(
                root,
                values,
                profile="deep",
                owner=owner,
                ids={entry["canonical_id"] for entry in selected_entries(manifest, owner, resolution) if entry["canonical_id"] in candidates},
                review_snapshot=review_snapshot,
                resolution=values["resolution"] if resolution is not None else None,
                verbose=verbose,
            )
            deep_views.add(output.resolve())
        _prune_runtime_views(run_dir, "deep", deep_views)
        records, errors = collect_review_records(
            _ledger_paths(run_dir), manifest, registry, candidates, resolution, review_snapshot
        )
        if errors:
            raise ValueError("; ".join(errors))
        pending = candidates - set(records)
        if emit:
            _log_deep(candidates, records, pending)
        if pending:
            return _stage_result(
                run_dir,
                "DEEP_REVIEW",
                summary=f"{len(pending)} Deep Review candidates remain",
                navigation=values["code_index_status"],
                pending=sorted(pending),
            )
        suspicious = {
            canonical_id
            for canonical_id, record in records.items()
            if record["status"] == "SUSPICIOUS"
        }
        if suspicious:
            proof_views: set[Path] = set()
            ledgers = _ledger_paths(run_dir)
            for owner in sorted({record["owner_domain"] for record in records.values() if record.get("status") == "SUSPICIOUS"}):
                output, _ = _render_owner_view(
                    root,
                    values,
                    profile="proof",
                    owner=owner,
                    ids={canonical_id for canonical_id, record in records.items() if record.get("status") == "SUSPICIOUS" and record.get("owner_domain") == owner},
                    review_snapshot=review_snapshot,
                    resolution=values["resolution"] if resolution is not None else None,
                    ledger_paths=ledgers,
                    verbose=verbose,
                )
                proof_views.add(output.resolve())
            _prune_runtime_views(run_dir, "proof", proof_views)
            if emit:
                success("Deep review complete")
                _emit_stage("PROOF", "Resolving suspicious findings")
                _log_model_guidance(run_dir, "PROOF")
                info(f"Remaining proof items: {len(suspicious)}")
            return _stage_result(
                run_dir,
                "PROOF",
                summary=f"{len(suspicious)} suspicious findings require Proof",
                navigation=values["code_index_status"],
                pending=sorted(suspicious),
                runtime_views=[str(path) for path in sorted(proof_views)],
            )
        if emit:
            success("Deep review complete")

    if not candidates:
        _prune_runtime_views(run_dir, "deep", set())
    _prune_runtime_views(run_dir, "proof", set())
    state = status_run(root, run_dir, emit=False)
    if emit:
        _log_report(state, finished=True, run_dir=run_dir)
    result: dict[str, Any] = _stage_result(
        run_dir,
        "REPORT",
        summary=f"Audit state: {state['status']}",
        navigation=values["code_index_status"],
        status=state["status"],
        audit_state=str(values["audit_state"]),
    )
    if state["status"] == "COMPLETE_WITH_FINDINGS":
        result.update(_ensure_reporting_templates(manifest, state, run_dir))
        result.update(
            {
                "required_inputs": ["severity-decisions", "finding-details"],
            }
        )
    return result


def models_run(
    root: Path,
    run_dir: Path | None,
    *,
    model_profile_path: Path | None = None,
    reset_defaults: bool = False,
    init_global: bool = False,
) -> dict[str, Any]:
    if init_global:
        if run_dir is not None or model_profile_path is not None or reset_defaults:
            raise ValueError("--init-global cannot be combined with run-scoped model options")
        profile = init_global_profile()
        return {
            "stage": "MODELS",
            "scope": "global",
            "profile_path": str(global_profile_path()),
            "persisted": True,
            "profile": profile,
        }
    if model_profile_path is not None and reset_defaults:
        raise ValueError("--model-profile and --reset-defaults are mutually exclusive")
    if run_dir is None:
        raise ValueError("--run-dir is required unless --init-global is used")
    run_dir = run_dir.resolve()
    values, _, _ = _load_run(root, run_dir)
    if model_profile_path is not None:
        profile = load_profile(model_profile_path.resolve())
        write_profile(values["model_profile"], profile)
    elif reset_defaults:
        profile = default_profile()
        write_profile(values["model_profile"], profile)
    elif values["model_profile"].exists():
        profile = load_profile(values["model_profile"])
    else:
        profile = default_profile()
    return {
        "stage": "MODELS",
        "profile_path": str(values["model_profile"]),
        "persisted": values["model_profile"].exists(),
        "profile": profile,
    }


def report_run(
    root: Path,
    run_dir: Path,
    severity_path: Path | None = None,
    finding_details_path: Path | None = None,
) -> dict[str, Any]:
    values, manifest, registry = _load_run(root, run_dir)
    state = status_run(root, run_dir, emit=False)
    _log_report(state, finished=False, run_dir=run_dir)
    severity = severity_bytes = None
    finding_details = finding_details_bytes = None
    if state["complete"]:
        if state["status"] == "COMPLETE_WITH_FINDINGS":
            severity_path = severity_path or values["severity_decisions"]
            finding_details_path = finding_details_path or values["finding_details"]
        if severity_path is not None:
            severity, severity_bytes = load_json_bytes(severity_path)
        if finding_details_path is not None:
            finding_details, finding_details_bytes = load_json_bytes(finding_details_path)
    resolution = load_json(values["resolution"]) if values["resolution"].exists() else None
    screen = load_json(values["screen_results"]) if values["screen_results"].exists() else None
    domain_context = load_json(values["domain_context"]) if values["domain_context"].exists() else None
    context = load_json(values["context"]) if values["context"].exists() else None
    synthesis = synthesize(
        root,
        manifest,
        registry,
        state,
        _ledger_paths(run_dir),
        severity,
        finding_details=finding_details,
        severity_decisions_bytes=severity_bytes,
        finding_details_bytes=finding_details_bytes,
        allow_incomplete=not state["complete"],
        domain_resolution=resolution,
        screen_results=screen,
        domain_context=domain_context,
        context=context,
    )
    current_state = synthesis.state
    report = synthesis.report
    issues = synthesis.issue_candidates
    severity_bytes = synthesis.severity_decisions_bytes
    finding_details_bytes = synthesis.finding_details_bytes
    if current_state["status"] == "COMPLETE_WITH_FINDINGS":
        if severity_bytes is None or finding_details_bytes is None:
            raise ValueError("finding report is missing exact reporting input bytes")
    bundle = report_bundle_metadata(
        manifest,
        current_state,
        report,
        issues,
        issue_candidates_bytes=json_text(issues).encode("utf-8"),
        severity_decisions_bytes=severity_bytes,
        finding_details_bytes=finding_details_bytes,
    )
    validate_schema(root, "report-bundle.schema.json", bundle)
    report_generations = values["report_generations"]
    report_generations.mkdir(parents=True, exist_ok=True)
    generation_id = uuid.uuid4().hex
    generation = report_generations / f"generation-{generation_id}"
    staging: Path | None = None
    generation_created = False
    pointer_committed = False
    convenience: dict[str, Any] = {"synced": False, "failed_paths": [], "warnings": []}
    bundle_status: dict[str, Any]
    with _report_publication_lock(values["manifest"].parent.parent):
        try:
            try:
                _current_report_generation(root, values)
            except ValueError as exc:
                warning(f"replacing stale or legacy report pointer: {exc}")
            staging = Path(tempfile.mkdtemp(prefix=f".tmp-{generation_id}-", dir=report_generations))
            artifacts = _report_generation_paths(staging)
            if current_state["status"] == "COMPLETE_WITH_FINDINGS":
                atomic_write_bytes(artifacts["report_input_severity"], severity_bytes)
                atomic_write_bytes(artifacts["report_input_details"], finding_details_bytes)
            atomic_write_text(artifacts["report"], report)
            atomic_write_json(artifacts["issue_candidates"], issues)
            atomic_write_json(artifacts["report_bundle"], bundle)
            bundle_bytes = artifacts["report_bundle"].read_bytes()
            candidate_issues, _ = load_json_bytes(artifacts["issue_candidates"])
            candidate_severity = None
            if current_state["status"] == "COMPLETE_WITH_FINDINGS":
                candidate_severity = load_json(artifacts["report_input_severity"])
            validate_issue_candidates(root, manifest, current_state, candidate_issues, candidate_severity)
            validate_report_generation(
                report,
                issues,
                artifacts["report"].read_bytes(),
                candidate_issues,
                artifacts["issue_candidates"].read_bytes(),
            )
            validate_schema(root, "report-bundle.schema.json", load_json(artifacts["report_bundle"]))
            fresh_state = status_run(root, values["manifest"].parent.parent, emit=False)
            if _publication_identity(manifest, fresh_state) != _publication_identity(manifest, current_state):
                raise ValueError("audit state changed during report publication; retry the report")
            staging.replace(generation)
            staging = generation
            generation_created = True
            pointer = {
                "artifact_type": "report-current",
                "schema_version": REPORT_CURRENT_VERSION,
                "generation": generation.name,
                "report_bundle_sha256": hashlib.sha256(bundle_bytes).hexdigest(),
            }
            validate_schema(root, "report-current.schema.json", pointer)
            atomic_write_json(values["report_current"], pointer)
            pointer_committed = True
            convenience = _sync_report_convenience_copies(
                values,
                _report_generation_paths(generation),
                finding_report=current_state["status"] == "COMPLETE_WITH_FINDINGS",
            )
            bundle_status = _report_bundle_status(root, values, manifest, current_state)
            if not bundle_status["current"]:
                raise ValueError(f"report publication is stale: {bundle_status.get('message', 'validation failed')}")
        finally:
            if staging is not None and staging.exists():
                if staging == generation and pointer_committed:
                    # The renamed generation is intentionally retained for history.
                    pass
                else:
                    shutil.rmtree(staging)
            if generation_created and not pointer_committed and generation.exists() and not _pointer_references_generation(values["report_current"], generation.name):
                shutil.rmtree(generation)
    if current_state["complete"]:
        success("Audit complete")
    else:
        warning("Audit remains incomplete")
    generation_artifacts = _report_generation_paths(generation)
    bundle_status = _report_bundle_status(root, values, manifest, current_state)
    return _stage_result(
        run_dir,
        "REPORT",
        summary=f"Audit state: {current_state['status']}",
        navigation=values["code_index_status"],
        status=current_state["status"],
        complete=current_state["complete"],
        generation=generation.name,
        report=str(generation_artifacts["report"]),
        issue_candidates=str(generation_artifacts["issue_candidates"]),
        report_bundle_path=str(generation_artifacts["report_bundle"]),
        report_current=str(values["report_current"]),
        convenience={
            **convenience,
            "report": str(values["report"]),
            "issue_candidates": str(values["issue_candidates"]),
            "report_bundle": str(values["report_bundle"]),
        },
        report_bundle=bundle_status,
        report_generation=_report_generation_status(values, bundle_status),
    )


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
    model_options = init.add_mutually_exclusive_group()
    model_options.add_argument(
        "--accept-default-models",
        action="store_true",
        help="persist the canonical Codex stage-model profile",
    )
    model_options.add_argument(
        "--model-profile",
        type=Path,
        help="validate and persist a Codex stage-model profile",
    )
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

    models = subparsers.add_parser("models")
    models.add_argument("--run-dir", type=Path)
    models.add_argument("--root", type=Path, default=ROOT)
    models.add_argument(
        "--init-global",
        action="store_true",
        help="create the user-level Codex profile if it does not exist",
    )
    model_options = models.add_mutually_exclusive_group()
    model_options.add_argument(
        "--reset-defaults",
        action="store_true",
        help="replace the run-scoped Codex profile with canonical defaults",
    )
    model_options.add_argument(
        "--model-profile",
        type=Path,
        help="validate and replace the run-scoped Codex profile",
    )
    _add_logging_flags(models)

    args = parser.parse_args(argv)
    configure(quiet=args.quiet, verbose=args.verbose)
    try:
        root = args.root.resolve()
        if args.command == "init":
            result = init_run(root, args)
        elif args.command == "next":
            result = next_step(root, args.run_dir, verbose=args.verbose)
        elif args.command == "status":
            result = status_run(root, args.run_dir, include_execution=True)
        elif args.command == "models":
            result = models_run(
                root,
                args.run_dir,
                model_profile_path=args.model_profile,
                reset_defaults=args.reset_defaults,
                init_global=args.init_global,
            )
        else:
            result = report_run(root, args.run_dir, args.severity_decisions, args.finding_details)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.command == "report" and result.get("complete") is False else 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        error(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
