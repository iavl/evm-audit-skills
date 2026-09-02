"""Fast, isolated audit-run fixtures for controller tests."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from helpers import ROOT, build_manifest
from scripts.audit_artifacts import bind_routing_snapshot, check_body_hash, json_text
from scripts.audit_run import paths, status_run
from scripts.render_runtime import domain_context_template, screen_results_template
from scripts.review_ledger import append


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json_text(value), encoding="utf-8")


def _base_run(
    run_dir: Path,
    *,
    selected_count: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    registry, raw, _, manifest = build_manifest()
    if selected_count < len(manifest["selected"]):
        # ponytail: narrow synthetic fixture; full routes remain covered by routing and E2E tests.
        manifest = {
            **manifest,
            "selected": manifest["selected"][:selected_count],
            "selected_count": selected_count,
            "scope": {**manifest["scope"], "candidate_count": selected_count},
        }
        manifest = bind_routing_snapshot(manifest)
    context = {**manifest["audit_context"], "routing_snapshot_id": manifest["routing_snapshot_id"]}
    domain_context = domain_context_template(manifest)
    for requirements in domain_context["domains"].values():
        for item in requirements.values():
            item.update(
                status="KNOWN",
                value="fixture",
                evidence=[{"kind": "scope", "location": "fixture", "reason": "known context"}],
            )
    screen = screen_results_template(manifest)
    evidence = [
        {"kind": "scope", "location": "fixture", "reason": "complete scope"},
        {"kind": "inheritance", "location": "fixture", "reason": "trigger absent"},
    ]
    for item in screen["results"]:
        item.update(result="NOT_APPLICABLE_CONFIRMED", scope_complete=True, evidence=evidence)
    _write(paths(run_dir)["feature_map"], raw)
    _write(paths(run_dir)["manifest"], manifest)
    _write(paths(run_dir)["context"], context)
    _write(paths(run_dir)["domain_context"], domain_context)
    _write(paths(run_dir)["screen_results"], screen)
    return registry, manifest, context, screen, domain_context


def make_clean_review_state(run_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create a complete clean run without invoking CLI subprocesses."""
    _, manifest, _, _, _ = _base_run(run_dir, selected_count=1)
    state = status_run(ROOT, run_dir, emit=False)
    return manifest, state


def make_confirmed_state(
    run_dir: Path,
    severities: list[str],
    *,
    include_poc: bool = True,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    """Create a complete run with confirmed findings and optional PoC evidence."""
    registry, manifest, context, screen, domain_context = _base_run(
        run_dir, selected_count=max(1, len(severities))
    )
    candidate_ids = [item["canonical_id"] for item in screen["results"][: len(severities)]]
    evidence = [
        {"kind": "scope", "location": "fixture", "reason": "complete scope"},
        {"kind": "inheritance", "location": "fixture", "reason": "screen disposition"},
    ]
    for item in screen["results"]:
        if item["canonical_id"] in candidate_ids:
            item.update(result="CANDIDATE", scope_complete=False, evidence=[])
        else:
            item.update(result="NOT_APPLICABLE_CONFIRMED", scope_complete=True, evidence=evidence)
    _write(paths(run_dir)["screen_results"], screen)
    for candidate_id in candidate_ids:
        route = next(item for item in manifest["selected"] if item["canonical_id"] == candidate_id)
        ledger = run_dir / f"reviews/review-{route['owner_domain']}.jsonl"
        suspicious = {
            "record_type": "review",
            "schema_version": 7,
            "canonical_id": candidate_id,
            "owner_domain": route["owner_domain"],
            "check_body_hash": check_body_hash(
                next(item for item in registry["checks"] if item["canonical_id"] == candidate_id)
            ),
            "review_stage": "DEEP_REVIEW",
            "status": "SUSPICIOUS",
            "code_path": "fixture entry",
            "unresolved_reason": "proof pending",
            "evidence": [{"kind": "manual", "location": "fixture", "reason": "deep review"}],
        }
        append(
            ledger,
            manifest,
            suspicious,
            registry,
            set(candidate_ids),
            domain_context=domain_context,
            screen_results=screen,
        )
        confirmed = {key: value for key, value in suspicious.items() if key != "unresolved_reason"}
        confirmed.update(
            review_stage="PROOF",
            status="CONFIRMED",
            applicability="APPLICABLE - fixture",
            preconditions="fixture state",
            exploitability="fixture path is reachable",
            impact="fixture impact",
            proof="deterministic fixture trace",
            evidence=[{"kind": "trace", "location": "fixture", "reason": "proof trace"}],
        )
        append(
            ledger,
            manifest,
            confirmed,
            registry,
            set(candidate_ids),
            domain_context=domain_context,
            screen_results=screen,
        )
    state = status_run(ROOT, run_dir, emit=False)
    identity = {
        "schema_version": 2,
        "artifact_state": "COMPLETED",
        "routing_snapshot_id": manifest["routing_snapshot_id"],
        "review_state_digest": state["review_state_digest"],
        **{
            key: manifest["audit_context"][key]
            for key in ("registry_sha256", "source_digest", "compilation_input_digest")
        },
    }
    severity = {
        **identity,
        "decisions": {
            candidate_id: {
                "severity": level,
                "rationale": "fixture proof",
                "dimensions": {
                    "impact": "fund_loss",
                    "exploitability": "permissionless",
                    "privileges": "none",
                    "capital_required": "none",
                    "repeatability": "one_shot",
                    "user_interaction": "none",
                    "loss_bound": "single_user",
                    "protocol_exposure": "single_position",
                    "recoverability": "irreversible",
                },
            }
            for candidate_id, level in zip(candidate_ids, severities)
        },
    }
    details = {
        **identity,
        "findings": [
            {
                "canonical_id": candidate_id,
                "location": "Fixture.sol:1",
                "description": "fixture finding",
                "recommendation": "fix fixture",
            }
            for candidate_id in candidate_ids
        ],
    }
    severity_bytes = json_text(severity).encode("utf-8")
    _write(paths(run_dir)["severity_decisions"], severity)
    _write(paths(run_dir)["finding_details"], details)
    required = [
        candidate_id
        for candidate_id, level in zip(candidate_ids, severities)
        if level in {"High", "Critical"}
    ]
    poc = None
    if required and include_poc:
        poc_findings = []
        for candidate_id in required:
            source = run_dir / "poc" / candidate_id / "Exploit.t.sol"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(
                f"contract Exploit_{candidate_id.replace('-', '_')} {{}}\n",
                encoding="utf-8",
            )
            poc_findings.append(
                {
                    "canonical_id": candidate_id,
                    "severity": severity["decisions"][candidate_id]["severity"],
                    "runner": "foundry",
                    "command": "forge test --match-test testExploit -vvv",
                    "sources": [
                        {
                            "path": source.relative_to(run_dir).as_posix(),
                            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        }
                    ],
                    "entrypoint": "testExploit",
                    "expected_result": "The exploit reproduces the confirmed defect.",
                    "result_summary": "The fixture reproduced the confirmed defect.",
                }
            )
        poc = {
            "artifact_type": "poc-evidence",
            "schema_version": 1,
            "artifact_state": "COMPLETED",
            "routing_snapshot_id": manifest["routing_snapshot_id"],
            "review_snapshot_id": state["review_snapshot_id"],
            "review_state_digest": state["review_state_digest"],
            **{
                key: manifest["audit_context"][key]
                for key in ("registry_sha256", "source_digest", "compilation_input_digest")
            },
            "severity_decisions_sha256": hashlib.sha256(severity_bytes).hexdigest(),
            "findings": poc_findings,
        }
        _write(paths(run_dir)["poc_evidence"], poc)
    return manifest, state, severity, details, poc


def make_high_state_with_poc(run_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    return make_confirmed_state(run_dir, ["High"])


def make_high_state_without_poc(run_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    return make_confirmed_state(run_dir, ["High"], include_poc=False)
