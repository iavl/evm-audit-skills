#!/usr/bin/env python3
"""Tests for deterministic confirmed-only report synthesis."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.audit_artifacts import check_body_hash
from scripts.render_runtime import domain_context_template, screen_results_template
from scripts.review_ledger import append
from scripts.synthesize_report import synthesize
from scripts.validate_audit_run import validate_run

from helpers import ROOT, build_manifest


class ReportingTests(unittest.TestCase):
    def artifacts(self, candidate: bool) -> tuple[dict, dict, dict, dict, dict, str]:
        registry, _, _, manifest = build_manifest()
        screen = screen_results_template(manifest)
        candidate_id = screen["results"][0]["canonical_id"]
        evidence = [
            {"kind": "scope", "location": "fixture", "reason": "complete scope"},
            {"kind": "source", "location": "fixture", "reason": "screen disposition"},
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
            "schema_version": 5,
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

    def test_only_confirmed_records_are_reported(self) -> None:
        registry, manifest, screen, context, domain_context, candidate_id = self.artifacts(True)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "review.jsonl"
            append(ledger, manifest, self.confirmed_record(registry, manifest, candidate_id), registry, {candidate_id})
            state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            report, issues = synthesize(
                ROOT,
                manifest,
                registry,
                state,
                [ledger],
                {candidate_id: "High"},
            )
        self.assertEqual(state["status"], "COMPLETE_WITH_FINDINGS")
        self.assertIn(f"## Findings\n\n### [{candidate_id}]", report)
        self.assertEqual(issues["findings"], [{"canonical_id": candidate_id, "severity": "High"}])
        self.assertEqual(issues["registry_sha256"], manifest["audit_context"]["registry_sha256"])

    def test_incomplete_audit_cannot_claim_clean_report(self) -> None:
        registry, manifest, screen, context, domain_context, _ = self.artifacts(True)
        state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [])
        self.assertEqual(state["status"], "INCOMPLETE_REVIEW")
        with self.assertRaisesRegex(ValueError, "incomplete audit"):
            synthesize(ROOT, manifest, registry, state, [])
        report, issues = synthesize(ROOT, manifest, registry, state, [], allow_incomplete=True)
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
            append(ledger, manifest, record, registry, {candidate_id})
            state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            with self.assertRaisesRegex(ValueError, "only allowed for CONFIRMED"):
                synthesize(
                    ROOT,
                    manifest,
                    registry,
                    state,
                    [ledger],
                    {candidate_id: "High"},
                    allow_incomplete=True,
                )


if __name__ == "__main__":
    unittest.main()
