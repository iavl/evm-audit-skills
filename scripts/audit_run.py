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
    from audit_artifacts import (
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


def paths(run_dir: Path) -> dict[str, Path]:
    return {
        "feature_map": run_dir / "recon/feature-map.json",
        "manifest": run_dir / "routing/manifest.json",
        "context": run_dir / "context.json",
        "environment": run_dir / "environment.json",
        "resolution": run_dir / "reviews/domain-resolution.json",
        "domain_context": run_dir / "reviews/domain-context.json",
        "screen": run_dir / "runtime/screen.md",
        "screen_results": run_dir / "reviews/screen-results.json",
        "audit_state": run_dir / "audit-state.json",
        "report": run_dir / "AUDIT-REPORT.md",
        "issue_candidates": run_dir / "issue-candidates.json",
    }


def _run(root: Path, script: str, arguments: list[str]) -> None:
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / script), *arguments],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit={result.returncode}"
        raise ValueError(f"{script} failed: {detail}")


def _render_screen(root: Path, values: dict[str, Path], *extra: str) -> None:
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
    )


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
    for exclusion in args.exclude:
        recon_args.extend(["--exclude", exclusion])
    if args.present_only:
        recon_args.append("--present-only")
    _run(root, "recon.py", recon_args)

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
    for option in ("domain", "domains", "target_commit", "chain_id", "chain_family", "execution_environment", "fork_block", "compiler_version", "evm_fork", "protocol_version", "audit_timestamp"):
        value = getattr(args, option, None)
        if value is not None:
            selector_args.extend([f"--{option.replace('_', '-')}", str(value)])
    if args.require_complete_compilation:
        selector_args.append("--require-complete-compilation")
    if args.environment_context:
        selector_args.extend(["--environment-context", str(args.environment_context.resolve())])
    _run(root, "select_checks.py", selector_args)
    return {
        "stage": "INITIALIZED",
        "run_dir": str(run_dir),
        "manifest": str(values["manifest"]),
        "next": next_step(root, run_dir),
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


def status_run(root: Path, run_dir: Path) -> dict[str, Any]:
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
    values["audit_state"].write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return state


def next_step(root: Path, run_dir: Path) -> dict[str, Any]:
    values, manifest, registry = _load_run(root, run_dir)
    resolution: dict[str, Any] | None = None
    if manifest["deferred_domains"]:
        if not values["resolution"].exists():
            _render_screen(root, values, "--domain-resolution-out", str(values["resolution"]))
            return {"stage": "DOMAIN_RESOLUTION", "template": str(values["resolution"])}
        resolution = load_json(values["resolution"])
        unresolved = validate_domain_resolution(root, manifest, resolution)
        if unresolved:
            return {"stage": "DOMAIN_RESOLUTION", "unresolved_domains": sorted(unresolved)}

    if not values["domain_context"].exists():
        extra = []
        if resolution is not None:
            extra.extend(["--domain-resolution", str(values["resolution"])])
        _render_screen(root, values, *extra, "--domain-context-out", str(values["domain_context"]))
        return {"stage": "DOMAIN_CONTEXT", "template": str(values["domain_context"])}
    domain_context = load_json(values["domain_context"])
    unresolved_context = validate_domain_context(root, manifest, domain_context, resolution)
    if unresolved_context:
        return {"stage": "DOMAIN_CONTEXT", "unresolved_context": sorted(unresolved_context)}

    if not values["screen_results"].exists():
        extra = ["--domain-context", str(values["domain_context"]), "--screen-results-out", str(values["screen_results"])]
        if resolution is not None:
            extra[0:0] = ["--domain-resolution", str(values["resolution"])]
        _render_screen(root, values, *extra)
        return {"stage": "SCREEN", "template": str(values["screen_results"])}
    screen = load_json(values["screen_results"])
    candidates = validate_screen_results(root, manifest, screen, resolution)
    if candidates:
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
            _run(root, "render_runtime.py", ["--manifest", str(values["manifest"]), "--profile", "deep", *extra])
        records, errors = collect_review_records(_ledger_paths(run_dir), manifest, registry, candidates, resolution)
        if errors:
            raise ValueError("; ".join(errors))
        if candidates - set(records):
            return {"stage": "DEEP_REVIEW", "pending": sorted(candidates - set(records))}

    state = status_run(root, run_dir)
    return {"stage": "REPORT", "status": state["status"], "audit_state": str(values["audit_state"])}


def report_run(root: Path, run_dir: Path, severity_path: Path | None = None) -> dict[str, Any]:
    values, manifest, registry = _load_run(root, run_dir)
    if not values["audit_state"].exists():
        status_run(root, run_dir)
    state = load_json(values["audit_state"])
    severity = load_json(severity_path) if severity_path else None
    resolution = load_json(values["resolution"]) if values["resolution"].exists() else None
    report, issues = synthesize(
        root,
        manifest,
        registry,
        state,
        _ledger_paths(run_dir),
        severity,
        domain_resolution=resolution,
    )
    values["report"].write_text(report, encoding="utf-8")
    values["issue_candidates"].write_text(json.dumps(issues, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"stage": "REPORT", "report": str(values["report"]), "issue_candidates": str(values["issue_candidates"])}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("target", type=Path)
    init.add_argument("--run-dir", type=Path, required=True)
    init.add_argument("--audit-root", type=Path)
    init.add_argument("--root", type=Path, default=ROOT)
    init.add_argument("--solc")
    init.add_argument("--present-only", action="store_true")
    init.add_argument("--exclude", action="append", default=[])
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

    for name in ("next", "status"):
        command = subparsers.add_parser(name)
        command.add_argument("--run-dir", type=Path, required=True)
        command.add_argument("--root", type=Path, default=ROOT)

    report = subparsers.add_parser("report")
    report.add_argument("--run-dir", type=Path, required=True)
    report.add_argument("--root", type=Path, default=ROOT)
    report.add_argument("--severity-decisions", type=Path)

    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        if args.command == "init":
            result = init_run(root, args)
        elif args.command == "next":
            result = next_step(root, args.run_dir)
        elif args.command == "status":
            result = status_run(root, args.run_dir)
        else:
            result = report_run(root, args.run_dir, args.severity_decisions)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
