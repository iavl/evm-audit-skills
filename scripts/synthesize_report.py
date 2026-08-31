#!/usr/bin/env python3
"""Synthesize a deterministic confirmed-only audit report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SUITE_ROOT = str(Path(__file__).resolve().parents[1])
if _SUITE_ROOT not in sys.path:
    sys.path.insert(0, _SUITE_ROOT)
from evm_audit_runtime.reporting import SEVERITY_ORDER, issue_candidate
from evm_audit_runtime.routing import resolved_routes

try:
    from audit_artifacts import (
        load_json,
        validate_artifact_identity,
        validate_domain_resolution,
        validate_schema,
        validate_target_snapshot,
    )
    from render_runtime import validate_manifest
    from review_ledger import collect_review_records
except ImportError:  # pragma: no cover
    from scripts.audit_artifacts import (
        load_json,
        validate_artifact_identity,
        validate_domain_resolution,
        validate_schema,
        validate_target_snapshot,
    )
    from scripts.render_runtime import validate_manifest
    from scripts.review_ledger import collect_review_records

try:
    from runtime_log import configure, error, success
except ImportError:  # pragma: no cover
    from scripts.runtime_log import configure, error, success


ROOT = Path(__file__).resolve().parents[1]
def _provenance(check: dict[str, Any]) -> str:
    values: list[str] = []
    for item in check.get("provenance", []):
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("locator") or "").strip()
        url = str(item.get("url") or "").strip()
        if label and url:
            values.append(f"[{label}]({url})")
        elif label:
            values.append(label)
    return "; ".join(values) or "None recorded"


def _severity_decisions(value: dict[str, Any] | None) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("severity decisions must be an object")
    decisions: dict[str, str] = {}
    for canonical_id, raw in value.items():
        severity = raw.get("severity") if isinstance(raw, dict) else raw
        if severity not in SEVERITY_ORDER:
            raise ValueError(f"invalid severity for {canonical_id}: {severity}")
        decisions[canonical_id] = severity
    return decisions


def _coverage_sets(state: dict[str, Any]) -> tuple[set[str], set[str], set[str]]:
    coverage = state["coverage"]
    selected = set(coverage["selected"])
    screen_not_applicable = set(coverage["screen_not_applicable"])
    candidates = set(coverage["deep_candidates"])
    if screen_not_applicable & candidates or screen_not_applicable | candidates != selected:
        raise ValueError("audit-state coverage equation failed")
    return selected, screen_not_applicable, candidates


def _issue_artifact(root: Path, manifest: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    identity = manifest["audit_context"]
    value = {
        "schema_version": 1,
        "routing_snapshot_id": manifest["routing_snapshot_id"],
        "registry_sha256": identity["registry_sha256"],
        "source_digest": identity["source_digest"],
        "compilation_input_digest": identity["compilation_input_digest"],
        "findings": findings,
    }
    validate_schema(root, "issue-candidates.schema.json", value)
    return value


def synthesize(
    root: Path,
    manifest: dict[str, Any],
    registry: dict[str, Any],
    state: dict[str, Any],
    ledger_paths: list[Path],
    severity_decisions: dict[str, Any] | None = None,
    *,
    allow_incomplete: bool = False,
    domain_resolution: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    validate_manifest(root, manifest, registry)
    validate_target_snapshot(manifest)
    validate_schema(root, "audit-state.schema.json", state)
    validate_artifact_identity(state, manifest)
    if domain_resolution is not None:
        validate_domain_resolution(root, manifest, domain_resolution)
    if state["recon_quality"] != manifest["feature_map"]["recon_context"]["recon_quality"]:
        raise ValueError("audit-state Recon quality does not match the routing manifest")
    selected, _, candidates = _coverage_sets(state)
    active_ids = {entry["canonical_id"] for entry in resolved_routes(manifest, domain_resolution)}
    if selected != active_ids:
        raise ValueError("audit-state selected coverage does not match the resolved routing manifest")
    latest, errors = collect_review_records(
        ledger_paths, manifest, registry, candidates, domain_resolution
    )
    if errors:
        raise ValueError("; ".join(errors))
    confirmed = {canonical_id for canonical_id, record in latest.items() if record["status"] == "CONFIRMED"}
    suspicious = {canonical_id for canonical_id, record in latest.items() if record["status"] == "SUSPICIOUS"}
    declared_confirmed = set(state["coverage"]["confirmed"])
    if confirmed != declared_confirmed:
        raise ValueError("audit-state confirmed coverage does not match latest ledger state")
    if suspicious != set(state["coverage"]["suspicious"]):
        raise ValueError("audit-state suspicious coverage does not match latest ledger state")
    if state["complete"] and state["status"] not in {"COMPLETE_CLEAN", "COMPLETE_WITH_FINDINGS"}:
        raise ValueError("audit-state marks an invalid complete status")
    if state["complete"] and state["coverage"]["unresolved"]:
        raise ValueError("complete audit-state cannot contain unresolved review IDs")
    if state["status"] == "COMPLETE_CLEAN" and not state["clean"]:
        raise ValueError("COMPLETE_CLEAN must set clean=true")
    if state["status"] == "COMPLETE_WITH_FINDINGS" and state["clean"]:
        raise ValueError("COMPLETE_WITH_FINDINGS must set clean=false")
    if not state["complete"] and not allow_incomplete:
        raise ValueError("refusing to synthesize a final report from an incomplete audit")

    decisions = _severity_decisions(severity_decisions)
    for canonical_id in decisions:
        if canonical_id not in latest:
            raise ValueError(f"severity decision has no latest review record: {canonical_id}")
        if latest[canonical_id]["status"] != "CONFIRMED":
            raise ValueError(f"severity is only allowed for CONFIRMED records: {canonical_id}")

    if not state["complete"]:
        report = "\n".join([
            "# INCOMPLETE AUDIT",
            "",
            f"- **Status:** `{state['status']}`",
            "- **Complete:** `false`",
            "- **Clean:** `false`",
            f"- **Recon quality:** `{state['recon_quality']['mode']}`",
            f"- **Routing snapshot:** `{manifest['routing_snapshot_id']}`",
            f"- **Registry:** `{manifest['audit_context']['registry_sha256']}`",
            f"- **Source digest:** `{manifest['audit_context']['source_digest']}`",
            f"- **Compilation input digest:** `{manifest['audit_context']['compilation_input_digest']}`",
            "",
            "This artifact is not a final vulnerability report. Resolve the listed audit-state reasons before reporting findings.",
            "",
            "## Reasons",
            *[f"- {reason}" for reason in state["reasons"]],
            "",
        ])
        return report, _issue_artifact(root, manifest, [])

    if state["status"] == "COMPLETE_CLEAN" and confirmed:
        raise ValueError("COMPLETE_CLEAN cannot contain confirmed findings")
    if state["status"] == "COMPLETE_WITH_FINDINGS" and not confirmed:
        raise ValueError("COMPLETE_WITH_FINDINGS requires confirmed findings")

    checks = {check["canonical_id"]: check for check in registry.get("checks", [])}
    report_lines = [
        "# EVM Audit Report",
        "",
        f"- **Status:** `{state['status']}`",
        f"- **Complete:** `{str(state['complete']).lower()}`",
        f"- **Clean:** `{str(state['clean']).lower()}`",
        f"- **Routing snapshot:** `{manifest['routing_snapshot_id']}`",
        f"- **Registry:** `{manifest['audit_context']['registry_sha256']}`",
        f"- **Source digest:** `{manifest['audit_context']['source_digest']}`",
        f"- **Compilation input digest:** `{manifest['audit_context']['compilation_input_digest']}`",
        f"- **Recon quality:** `{state['recon_quality']['mode']}`",
        "",
        "## Findings",
    ]
    if not confirmed:
        report_lines.extend(["", "No confirmed findings were established within the reviewed scope."])
    issue_findings: list[dict[str, Any]] = []
    for canonical_id in sorted(confirmed):
        record = latest[canonical_id]
        check = checks.get(canonical_id)
        if check is None:
            raise ValueError(f"confirmed record is absent from registry: {canonical_id}")
        severity = decisions.get(canonical_id)
        report_lines.extend([
            "",
            f"### [{canonical_id}] {check['title']}",
            f"- **Severity:** {severity or 'Unassigned'}",
            f"- **Owner Domain:** {record['owner_domain']}",
            f"- **Applicability:** {record['applicability']}",
            f"- **Code path:** {record['code_path']}",
            f"- **Preconditions:** {record['preconditions']}",
            f"- **Exploitability:** {record['exploitability']}",
            f"- **Impact:** {record['impact']}",
            f"- **Proof:** {record['proof']}",
            f"- **Provenance:** {_provenance(check)}",
        ])
        if issue_candidate(severity):
            issue_findings.append({"canonical_id": canonical_id, "severity": severity})
    report_lines.append("")
    return "\n".join(report_lines), _issue_artifact(root, manifest, issue_findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--audit-state", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=ROOT / "data/canonical-checks.json")
    parser.add_argument("--ledger", type=Path, action="append", default=[])
    parser.add_argument("--domain-resolution", type=Path)
    parser.add_argument("--severity-decisions", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--issue-candidates-out", type=Path)
    parser.add_argument("--allow-incomplete", action="store_true", help="write an explicitly incomplete artifact")
    parser.add_argument("--quiet", action="store_true", help="suppress progress output")
    args = parser.parse_args(argv)
    configure(quiet=args.quiet)
    try:
        manifest = load_json(args.manifest)
        registry = load_json(args.registry)
        state = load_json(args.audit_state)
        severity = load_json(args.severity_decisions) if args.severity_decisions else None
        domain_resolution = load_json(args.domain_resolution) if args.domain_resolution else None
        report, issues = synthesize(
            ROOT,
            manifest,
            registry,
            state,
            args.ledger,
            severity,
            allow_incomplete=args.allow_incomplete,
            domain_resolution=domain_resolution,
        )
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(report, encoding="utf-8")
        else:
            print(report, end="")
        if args.issue_candidates_out:
            args.issue_candidates_out.parent.mkdir(parents=True, exist_ok=True)
            args.issue_candidates_out.write_text(json.dumps(issues, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        success("Confirmed-only report synthesized")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        error(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
