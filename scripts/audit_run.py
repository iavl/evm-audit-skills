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
STAGE_PROGRESS: dict[str, dict[str, Any]] = {
    "RECON": {"step": 1, "label": "RECON"},
    "ROUTING": {"step": 2, "label": "ROUTING"},
    "DOMAIN_RESOLUTION": {"step": 3, "label": "DOMAIN RESOLUTION"},
    "DOMAIN_CONTEXT": {"step": 3, "label": "DOMAIN CONTEXT"},
    "SCREEN": {"step": 4, "label": "SCREEN"},
    "DEEP_REVIEW": {"step": 5, "label": "DEEP REVIEW"},
    "PROOF": {"step": 6, "label": "PROOF"},
    "REPORT": {"step": 7, "label": "REPORT"},
}
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


def progress_metadata(stage_name: str, *, summary: str | None = None) -> dict[str, Any]:
    try:
        metadata = STAGE_PROGRESS[stage_name]
    except KeyError as exc:
        raise ValueError(f"unknown audit stage: {stage_name}") from exc
    return {
        "step": metadata["step"],
        "total": TOTAL_STAGES,
        "label": metadata["label"],
        "summary": summary or f"{metadata['label']} stage",
    }


def _emit_stage(stage_name: str, detail: str) -> None:
    progress = progress_metadata(stage_name)
    stage(progress["label"], step=progress["step"], total=progress["total"], detail=detail)


def _display_stage(name: str) -> str:
    return progress_metadata(name)["label"] if name in STAGE_PROGRESS else name.replace("_", " ")


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
    **values: Any,
) -> dict[str, Any]:
    return {
        "stage": stage_name,
        **values,
        "progress": progress_metadata(stage_name, summary=summary),
        "recommended_execution": recommended_execution(run_dir, stage_name),
    }


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


def init_run(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    run_dir = args.run_dir.resolve()
    if run_dir.exists() and any(run_dir.iterdir()):
        raise ValueError(f"refusing to initialize non-empty run directory: {run_dir}")
    _init_model_profile(args, run_dir)
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
    _emit_stage("RECON", "Building scope-bound Feature Map")
    try:
        _run(root, "recon.py", recon_args, verbose=args.verbose)
        feature_map = load_json(values["feature_map"])
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        warning("Recon failed")
        raise
    _log_recon(feature_map, audit_root, args.require_complete_compilation, run_dir=run_dir)

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
    _log_routing(manifest, run_dir=run_dir)
    next_result = next_step(root, run_dir, verbose=args.verbose, emit=False)
    info(f"Next required stage: {_display_stage(next_result['stage'])}")
    _log_model_guidance(run_dir, next_result["stage"])
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
        "progress_history": progress_history,
        "next": next_result,
        "recommended_execution": next_result["recommended_execution"],
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
            return _stage_result(
                run_dir,
                "DEEP_REVIEW",
                summary=f"{len(pending)} Deep Review candidates remain",
                pending=sorted(pending),
            )
        suspicious = {
            canonical_id
            for canonical_id, record in records.items()
            if record["status"] == "SUSPICIOUS"
        }
        if suspicious:
            if emit:
                success("Deep review complete")
                _emit_stage("PROOF", "Resolving suspicious findings")
                _log_model_guidance(run_dir, "PROOF")
                info(f"Remaining proof items: {len(suspicious)}")
            return _stage_result(
                run_dir,
                "PROOF",
                summary=f"{len(suspicious)} suspicious findings require Proof",
                pending=sorted(suspicious),
            )
        if emit:
            success("Deep review complete")

    if not candidates:
        for stale_view in (run_dir / "runtime").glob("deep-*.md"):
            stale_view.unlink()
    state = status_run(root, run_dir, emit=False)
    if emit:
        _log_report(state, finished=True, run_dir=run_dir)
    result: dict[str, Any] = _stage_result(
        run_dir,
        "REPORT",
        summary=f"Audit state: {state['status']}",
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
    invalidate_final_outputs(run_dir / "AUDIT-REPORT.md", run_dir / "issue-candidates.json")
    values, manifest, registry = _load_run(root, run_dir)
    state = status_run(root, run_dir, emit=False)
    _log_report(state, finished=False, run_dir=run_dir)
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
    return _stage_result(
        run_dir,
        "REPORT",
        summary=f"Audit state: {state['status']}",
        status=state["status"],
        complete=state["complete"],
        report=str(values["report"]),
        issue_candidates=str(values["issue_candidates"]),
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
