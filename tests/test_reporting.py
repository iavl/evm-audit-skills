#!/usr/bin/env python3
"""Tests for deterministic confirmed-only report synthesis."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.audit_artifacts import check_body_hash
from evm_audit_runtime.reporting import derive_issue_candidates
from scripts.render_runtime import domain_context_template, screen_results_template
from scripts.review_ledger import append
from scripts.synthesize_report import ReportSynthesisResult, synthesize
from scripts.validate_audit_run import validate_run

from helpers import ROOT, build_manifest


class ReportingTests(unittest.TestCase):
    def test_issue_candidates_are_exact_projection_of_severity(self) -> None:
        decisions = {
            "INFO": {"severity": "Info"},
            "LOW": {"severity": "Low"},
            "MEDIUM": {"severity": "Medium"},
            "HIGH": {"severity": "High"},
            "CRITICAL": {"severity": "Critical"},
        }
        self.assertEqual(
            derive_issue_candidates(decisions, decisions),
            [
                {"canonical_id": "CRITICAL", "severity": "Critical"},
                {"canonical_id": "HIGH", "severity": "High"},
                {"canonical_id": "MEDIUM", "severity": "Medium"},
            ],
        )

    def artifacts(self, candidate: bool) -> tuple[dict, dict, dict, dict, dict, str]:
        registry, _, _, manifest = build_manifest()
        screen = screen_results_template(manifest)
        candidate_id = screen["results"][0]["canonical_id"]
        evidence = [
            {"kind": "scope", "location": "fixture", "reason": "complete scope"},
            {"kind": "inheritance", "location": "fixture", "reason": "screen disposition"},
        ]
        for result in screen["results"]:
            if result["canonical_id"] == candidate_id and candidate:
                result.update(result="CANDIDATE", scope_complete=False, evidence=[])
            else:
                result.update(result="NOT_APPLICABLE_CONFIRMED", scope_complete=True, evidence=evidence)
        context = {**manifest["audit_context"], "routing_snapshot_id": manifest["routing_snapshot_id"]}
        domain_context = domain_context_template(manifest)
        for requirements in domain_context["domains"].values():
            for item in requirements.values():
                item.update(
                    status="KNOWN",
                    value="fixture",
                    evidence=[{"kind": "scope", "location": "fixture", "reason": "known context"}],
                )
        return registry, manifest, screen, context, domain_context, candidate_id

    def confirmed_record(self, registry: dict, manifest: dict, candidate_id: str) -> dict:
        entry = next(item for item in manifest["selected"] if item["canonical_id"] == candidate_id)
        check = next(item for item in registry["checks"] if item["canonical_id"] == candidate_id)
        record = {
            "record_type": "review",
            "schema_version": 7,
            "revision": 1,
            "canonical_id": candidate_id,
            "owner_domain": entry["owner_domain"],
            "routing_snapshot_id": manifest["routing_snapshot_id"],
            "check_body_hash": check_body_hash(check),
            "review_stage": "PROOF",
            "status": "CONFIRMED",
            "applicability": "APPLICABLE - fixture",
            "code_path": "fixture entry",
            "preconditions": "fixture state",
            "exploitability": "attacker reaches fixture entry",
            "impact": "fixture accounting impact",
            "proof": "deterministic fixture trace",
            "evidence": [{"kind": "trace", "location": "fixture", "reason": "proof trace"}],
        }
        record.update({key: manifest["audit_context"][key] for key in (
            "registry_sha256", "source_digest", "compilation_input_digest",
        )})
        return record

    def append_confirmed_record(
        self, ledger: Path, registry: dict, manifest: dict, candidate_id: str,
        domain_context: dict, screen: dict,
    ) -> None:
        deep = self.confirmed_record(registry, manifest, candidate_id)
        deep.update(
            review_stage="DEEP_REVIEW",
            status="SUSPICIOUS",
            unresolved_reason="proof is pending",
            evidence=[{"kind": "manual", "location": "fixture", "reason": "deep review concern"}],
        )
        append(ledger, manifest, deep, registry, {candidate_id}, domain_context=domain_context, screen_results=screen)
        proof = self.confirmed_record(registry, manifest, candidate_id)
        proof["revision"] = 2
        append(ledger, manifest, proof, registry, {candidate_id}, domain_context=domain_context, screen_results=screen)

    def severity_artifact(
        self, manifest: dict, candidate_id: str, review_state_digest: str, severity: str = "High"
    ) -> dict:
        return {
            "schema_version": 2,
            "routing_snapshot_id": manifest["routing_snapshot_id"],
            "review_state_digest": review_state_digest,
            **{
                key: manifest["audit_context"][key]
                for key in ("registry_sha256", "source_digest", "compilation_input_digest")
            },
            "decisions": {
                candidate_id: {
                    "severity": severity,
                    "rationale": "fixture impact and reachability support the selected level",
                    "dimensions": {
                        "impact": "fund_loss",
                        "exploitability": "permissionless",
                        "privileges": "ordinary_user",
                        "capital_required": "low",
                        "repeatability": "repeatable",
                        "user_interaction": "victim_action",
                        "loss_bound": "affected_users",
                        "protocol_exposure": "affected_users",
                        "recoverability": "admin_remediable",
                    },
                }
            },
        }

    def finding_details(self, manifest: dict, candidate_id: str, review_state_digest: str) -> dict:
        return {
            "schema_version": 2,
            "routing_snapshot_id": manifest["routing_snapshot_id"],
            "review_state_digest": review_state_digest,
            **{
                key: manifest["audit_context"][key]
                for key in ("registry_sha256", "source_digest", "compilation_input_digest")
            },
            "findings": [{
                "canonical_id": candidate_id,
                "location": "Fixture.sol:42",
                "description": "The fixture path demonstrates the confirmed defect.",
                "recommendation": "Add the missing guard before applying the state transition.",
            }],
        }

    def run_synthesis(
        self,
        registry: dict,
        manifest: dict,
        state: dict,
        ledger: list[Path],
        screen: dict,
        context: dict,
        domain_context: dict,
        severity: dict | None = None,
        *,
        finding_details: dict | None = None,
        allow_incomplete: bool = False,
    ) -> ReportSynthesisResult:
        return synthesize(
            ROOT,
            manifest,
            registry,
            state,
            ledger,
            severity,
            finding_details=finding_details,
            allow_incomplete=allow_incomplete,
            screen_results=screen,
            domain_context=domain_context,
            context=context,
        )

    def test_only_confirmed_records_are_reported(self) -> None:
        registry, manifest, screen, context, domain_context, candidate_id = self.artifacts(True)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "review.jsonl"
            self.append_confirmed_record(ledger, registry, manifest, candidate_id, domain_context, screen)
            state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            synthesis = self.run_synthesis(
                registry,
                manifest,
                state,
                [ledger],
                screen,
                context,
                domain_context,
                self.severity_artifact(manifest, candidate_id, state["review_state_digest"]),
                finding_details=self.finding_details(manifest, candidate_id, state["review_state_digest"]),
            )
            report, issues = synthesis.report, synthesis.issue_candidates
        self.assertEqual(state["status"], "COMPLETE_WITH_FINDINGS")
        self.assertIn(f"## Findings\n\n### [{candidate_id}]", report)
        self.assertIn("**Status:** `CONFIRMED`", report)
        self.assertIn("**Checklist reference:**", report)
        self.assertIn("**Location:** Fixture.sol:42", report)
        self.assertIn("**Description:**", report)
        self.assertIn("**Recommendation:**", report)
        self.assertEqual(issues["findings"], [{"canonical_id": candidate_id, "severity": "High"}])
        self.assertEqual(issues["registry_sha256"], manifest["audit_context"]["registry_sha256"])

    def test_incomplete_audit_cannot_claim_clean_report(self) -> None:
        registry, manifest, screen, context, domain_context, _ = self.artifacts(True)
        state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [])
        self.assertEqual(state["status"], "INCOMPLETE_REVIEW")
        with self.assertRaisesRegex(ValueError, "incomplete audit"):
            self.run_synthesis(registry, manifest, state, [], screen, context, domain_context)
        synthesis = self.run_synthesis(
            registry, manifest, state, [], screen, context, domain_context, allow_incomplete=True
        )
        report, issues = synthesis.report, synthesis.issue_candidates
        self.assertIn("# INCOMPLETE AUDIT", report)
        self.assertNotIn("Clean: `true`", report)
        self.assertEqual(issues["findings"], [])

    def test_suspicious_records_cannot_receive_severity(self) -> None:
        registry, manifest, screen, context, domain_context, candidate_id = self.artifacts(True)
        record = self.confirmed_record(registry, manifest, candidate_id)
        record.update(
            review_stage="DEEP_REVIEW",
            status="SUSPICIOUS",
            unresolved_reason="proof is pending",
            evidence=[{"kind": "manual", "location": "fixture", "reason": "deep review concern"}],
        )
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "review.jsonl"
            append(ledger, manifest, record, registry, {candidate_id}, domain_context=domain_context, screen_results=screen)
            state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            with self.assertRaisesRegex(ValueError, "only allowed for CONFIRMED"):
                self.run_synthesis(
                    registry,
                    manifest,
                    state,
                    [ledger],
                    screen,
                    context,
                    domain_context,
                    self.severity_artifact(manifest, candidate_id, state["review_state_digest"]),
                    allow_incomplete=True,
                )

    def test_confirmed_reporting_inputs_are_required_and_strict(self) -> None:
        registry, manifest, screen, context, domain_context, candidate_id = self.artifacts(True)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "review.jsonl"
            self.append_confirmed_record(ledger, registry, manifest, candidate_id, domain_context, screen)
            state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            with self.assertRaisesRegex(ValueError, "INCOMPLETE_SEVERITY"):
                self.run_synthesis(registry, manifest, state, [ledger], screen, context, domain_context)
            with self.assertRaisesRegex(ValueError, "INCOMPLETE_REPORTING"):
                self.run_synthesis(
                    registry,
                    manifest,
                    state,
                    [ledger],
                    screen,
                    context,
                    domain_context,
                    self.severity_artifact(manifest, candidate_id, state["review_state_digest"]),
                )
            synthesis = self.run_synthesis(
                registry,
                manifest,
                state,
                [ledger],
                screen,
                context,
                domain_context,
                self.severity_artifact(manifest, candidate_id, state["review_state_digest"], "Info"),
                finding_details=self.finding_details(manifest, candidate_id, state["review_state_digest"]),
            )
            report, issues = synthesis.report, synthesis.issue_candidates
        self.assertIn("**Severity:** Info", report)
        self.assertEqual(issues["findings"], [])

    def test_legacy_severity_and_missing_dimensions_are_rejected(self) -> None:
        registry, manifest, screen, context, domain_context, candidate_id = self.artifacts(True)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "review.jsonl"
            self.append_confirmed_record(ledger, registry, manifest, candidate_id, domain_context, screen)
            state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            details = self.finding_details(manifest, candidate_id, state["review_state_digest"])
            with self.assertRaisesRegex(ValueError, "INCOMPLETE_SEVERITY"):
                self.run_synthesis(
                    registry,
                    manifest,
                    state,
                    [ledger],
                    screen,
                    context,
                    domain_context,
                    {candidate_id: "High"},
                    finding_details=details,
                )
            invalid = self.severity_artifact(manifest, candidate_id, state["review_state_digest"])
            del invalid["decisions"][candidate_id]["dimensions"]["impact"]
            with self.assertRaisesRegex(ValueError, "INCOMPLETE_SEVERITY"):
                self.run_synthesis(
                    registry,
                    manifest,
                    state,
                    [ledger],
                    screen,
                    context,
                    domain_context,
                    invalid,
                    finding_details=details,
                )
            invalid_enum = self.severity_artifact(manifest, candidate_id, state["review_state_digest"], "Informational")
            with self.assertRaisesRegex(ValueError, "INCOMPLETE_SEVERITY"):
                self.run_synthesis(
                    registry,
                    manifest,
                    state,
                    [ledger],
                    screen,
                    context,
                    domain_context,
                    invalid_enum,
                    finding_details=details,
                )

    def test_finding_details_reject_duplicate_and_extra_ids(self) -> None:
        registry, manifest, screen, context, domain_context, candidate_id = self.artifacts(True)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "review.jsonl"
            self.append_confirmed_record(ledger, registry, manifest, candidate_id, domain_context, screen)
            state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            severity = self.severity_artifact(manifest, candidate_id, state["review_state_digest"])
            duplicate = self.finding_details(manifest, candidate_id, state["review_state_digest"])
            duplicate["findings"].append(dict(duplicate["findings"][0]))
            with self.assertRaisesRegex(ValueError, "INCOMPLETE_REPORTING"):
                self.run_synthesis(registry, manifest, state, [ledger], screen, context, domain_context, severity, finding_details=duplicate)
            extra = self.finding_details(manifest, candidate_id, state["review_state_digest"])
            extra["findings"].append({
                "canonical_id": "EXTRA-001",
                "location": "Extra.sol:1",
                "description": "extra",
                "recommendation": "remove",
            })
            with self.assertRaisesRegex(ValueError, "INCOMPLETE_REPORTING"):
                self.run_synthesis(registry, manifest, state, [ledger], screen, context, domain_context, severity, finding_details=extra)

    def test_synthesis_rejects_stale_deep_review_coverage(self) -> None:
        registry, manifest, screen, context, domain_context, candidate_id = self.artifacts(True)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "review.jsonl"
            self.append_confirmed_record(ledger, registry, manifest, candidate_id, domain_context, screen)
            state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            stale = {**state, "coverage": {**state["coverage"], "deep_reviewed": []}}
            report = self.run_synthesis(
                registry,
                manifest,
                stale,
                [ledger],
                screen,
                context,
                domain_context,
                self.severity_artifact(manifest, candidate_id, state["review_state_digest"]),
                finding_details=self.finding_details(manifest, candidate_id, state["review_state_digest"]),
            ).report
        self.assertIn("# EVM Audit Report", report)


if __name__ == "__main__":
    unittest.main()
