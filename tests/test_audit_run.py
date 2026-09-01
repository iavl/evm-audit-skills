#!/usr/bin/env python3
"""Tests for the deterministic audit-run controller."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import EMPTY_TARGET, ROOT
from scripts.review_ledger import append


class AuditRunTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *arguments],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    @staticmethod
    def read(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_controller_advances_templates_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            result = self.run_cli(
                "scripts/audit_run.py",
                "init",
                str(EMPTY_TARGET),
                "--run-dir",
                str(run_dir),
                "--audit-root",
                str(EMPTY_TARGET),
                "--domain",
                "evm-audit-general",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("DOMAIN_CONTEXT", result.stdout)
            self.assertEqual(
                json.loads(result.stdout)["next"]["recommended_execution"],
                {"provider": "codex", "model": "gpt-5.6-terra", "reasoning_effort": "medium"},
            )
            result = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("DOMAIN_CONTEXT", result.stdout)
            self.assertEqual(json.loads(result.stdout)["progress"]["label"], "DOMAIN CONTEXT")
            context_path = run_dir / "reviews/domain-context.json"
            context = self.read(context_path)
            for requirements in context["domains"].values():
                for item in requirements.values():
                    item.update(
                        status="KNOWN",
                        value="fixture",
                        evidence=[{"kind": "scope", "location": "fixture", "reason": "known context"}],
                    )
            context_path.write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")

            result = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            screen_payload = json.loads(result.stdout)
            self.assertEqual(screen_payload["progress"]["step"], 4)
            self.assertEqual(screen_payload["progress"]["label"], "SCREEN")
            screen_path = run_dir / "reviews/screen-results.json"
            screen = self.read(screen_path)
            for item in screen["results"]:
                item.update(
                    result="NOT_APPLICABLE_CONFIRMED",
                    scope_complete=True,
                    evidence=[
                        {"kind": "scope", "location": "fixture", "reason": "complete scope"},
                        {"kind": "source", "location": "fixture", "reason": "trigger absent"},
                    ],
                )
            screen_path.write_text(json.dumps(screen, indent=2) + "\n", encoding="utf-8")

            result = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("COMPLETE_CLEAN", result.stdout)
            report_payload = json.loads(result.stdout)
            self.assertEqual(report_payload["progress"]["step"], 7)
            self.assertEqual(report_payload["progress"]["label"], "REPORT")
            self.assertEqual(
                report_payload["recommended_execution"],
                {"provider": "codex", "model": "gpt-5.6-terra", "reasoning_effort": "medium"},
            )
            manifest = self.read(run_dir / "routing/manifest.json")
            state = self.read(run_dir / "audit-state.json")
            identity = {
                "schema_version": 2,
                "routing_snapshot_id": manifest["routing_snapshot_id"],
                "review_state_digest": state["review_state_digest"],
                **{
                    key: manifest["audit_context"][key]
                    for key in ("registry_sha256", "source_digest", "compilation_input_digest")
                },
            }
            severity_path = run_dir / "severity-decisions.json"
            severity_path.write_text(json.dumps({**identity, "decisions": {}}) + "\n", encoding="utf-8")
            details_path = run_dir / "finding-details.json"
            details_path.write_text(json.dumps({**identity, "findings": []}) + "\n", encoding="utf-8")
            result = self.run_cli(
                "scripts/audit_run.py",
                "report",
                "--run-dir",
                str(run_dir),
                "--severity-decisions",
                str(severity_path),
                "--finding-details",
                str(details_path),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report_command = json.loads(result.stdout)
            self.assertEqual(report_command["progress"]["step"], 7)
            self.assertEqual(report_command["progress"]["label"], "REPORT")
            report = (run_dir / "AUDIT-REPORT.md").read_text(encoding="utf-8")
            self.assertIn("COMPLETE_CLEAN", report)
            self.assertTrue((run_dir / "issue-candidates.json").exists())

    def test_report_rederives_state_after_current_ledger_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            result = self.run_cli(
                "scripts/audit_run.py",
                "init",
                str(EMPTY_TARGET),
                "--run-dir",
                str(run_dir),
                "--audit-root",
                str(EMPTY_TARGET),
                "--domain",
                "evm-audit-general",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            context_path = run_dir / "reviews/domain-context.json"
            context = self.read(context_path)
            for requirements in context["domains"].values():
                for item in requirements.values():
                    item.update(
                        status="KNOWN",
                        value="fixture",
                        evidence=[{"kind": "scope", "location": "fixture", "reason": "known context"}],
                    )
            context_path.write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")

            result = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            screen_path = run_dir / "reviews/screen-results.json"
            screen = self.read(screen_path)
            candidate = screen["results"][0]
            candidate.update(result="CANDIDATE", scope_complete=False, evidence=[])
            evidence = [
                {"kind": "scope", "location": "fixture", "reason": "complete scope"},
                {"kind": "source", "location": "fixture", "reason": "screen disposition"},
            ]
            for item in screen["results"][1:]:
                item.update(result="NOT_APPLICABLE_CONFIRMED", scope_complete=True, evidence=evidence)
            screen_path.write_text(json.dumps(screen, indent=2) + "\n", encoding="utf-8")

            result = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            self.assertIn("DEEP_REVIEW", result.stdout)
            deep_payload = json.loads(result.stdout)
            self.assertEqual(deep_payload["progress"]["step"], 5)
            self.assertEqual(deep_payload["progress"]["label"], "DEEP REVIEW")
            self.assertIn("Deep Review candidates remain", deep_payload["progress"]["summary"])
            self.assertEqual(
                deep_payload["recommended_execution"],
                {"provider": "codex", "model": "gpt-5.6-sol", "reasoning_effort": "high"},
            )
            manifest = self.read(run_dir / "routing/manifest.json")
            route = next(item for item in manifest["selected"] if item["canonical_id"] == candidate["canonical_id"])
            record = {
                "record_type": "review",
                "schema_version": 6,
                "canonical_id": candidate["canonical_id"],
                "owner_domain": route["owner_domain"],
                "check_body_hash": route["check_body_hash"],
                "review_stage": "DEEP_REVIEW",
                "status": "REVIEWED_SAFE",
                "applicability": "APPLICABLE - fixture",
                "code_path": "fixture entry",
                "preconditions": "fixture state",
                "exploitability": "guard holds",
                "impact": "none",
                "proof": "fixture invariant",
                "preserved_invariant": "fixture invariant",
                "evidence": [{"kind": "test", "location": "fixture", "reason": "test evidence"}],
            }
            ledger = run_dir / "reviews/review-evm-audit-general.jsonl"
            append(
                ledger,
                manifest,
                record,
                self.read(ROOT / "data/canonical-checks.json"),
                {candidate["canonical_id"]},
                domain_context=context,
                screen_results=screen,
            )

            result = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("COMPLETE_CLEAN", result.stdout)
            result = self.run_cli("scripts/audit_run.py", "report", "--run-dir", str(run_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            ledger.unlink()

            result = self.run_cli("scripts/audit_run.py", "report", "--run-dir", str(run_dir))
            self.assertNotEqual(result.returncode, 0)
            state = self.read(run_dir / "audit-state.json")
            self.assertEqual(state["status"], "INCOMPLETE_REVIEW")
            self.assertFalse(state["complete"])
            report = (run_dir / "AUDIT-REPORT.md").read_text(encoding="utf-8")
            self.assertIn("# INCOMPLETE AUDIT", report)
            self.assertNotIn("COMPLETE_CLEAN", report)

    def test_controller_routes_suspicious_records_to_proof(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            result = self.run_cli(
                "scripts/audit_run.py",
                "init",
                str(EMPTY_TARGET),
                "--run-dir",
                str(run_dir),
                "--audit-root",
                str(EMPTY_TARGET),
                "--domain",
                "evm-audit-general",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            poc_path = run_dir / "poc/RetainedPoC.t.sol"
            poc_source = """// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.26;

contract RetainedPoC {
    function proof() external pure returns (uint256) {
        return 1;
    }
}
"""
            poc_path.parent.mkdir(parents=True)
            poc_path.write_text(poc_source, encoding="utf-8")
            poc_location = poc_path.relative_to(run_dir).as_posix()
            context_path = run_dir / "reviews/domain-context.json"
            context = self.read(context_path)
            for requirements in context["domains"].values():
                for item in requirements.values():
                    item.update(
                        status="KNOWN",
                        value="fixture",
                        evidence=[{"kind": "scope", "location": "fixture", "reason": "known context"}],
                    )
            context_path.write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")
            self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            screen_path = run_dir / "reviews/screen-results.json"
            screen = self.read(screen_path)
            candidate = screen["results"][0]
            candidate.update(result="CANDIDATE", scope_complete=False, evidence=[])
            evidence = [
                {"kind": "scope", "location": "fixture", "reason": "complete scope"},
                {"kind": "source", "location": "fixture", "reason": "screen disposition"},
            ]
            for item in screen["results"][1:]:
                item.update(result="NOT_APPLICABLE_CONFIRMED", scope_complete=True, evidence=evidence)
            screen_path.write_text(json.dumps(screen, indent=2) + "\n", encoding="utf-8")
            result = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            self.assertIn("DEEP_REVIEW", result.stdout)
            self.assertEqual(
                json.loads(result.stdout)["recommended_execution"],
                {"provider": "codex", "model": "gpt-5.6-sol", "reasoning_effort": "high"},
            )

            manifest = self.read(run_dir / "routing/manifest.json")
            route = next(item for item in manifest["selected"] if item["canonical_id"] == candidate["canonical_id"])
            suspicious = {
                "record_type": "review",
                "schema_version": 6,
                "canonical_id": candidate["canonical_id"],
                "owner_domain": route["owner_domain"],
                "check_body_hash": route["check_body_hash"],
                "review_stage": "DEEP_REVIEW",
                "status": "SUSPICIOUS",
                "applicability": "APPLICABLE - fixture",
                "code_path": "fixture entry",
                "preconditions": "fixture state",
                "exploitability": "alternate path unresolved",
                "impact": "potential issue",
                "proof": "proof pending",
                "unresolved_reason": "proof pending",
                "evidence": [{"kind": "manual", "location": "fixture", "reason": "deep review"}],
            }
            ledger = run_dir / "reviews/review-evm-audit-general.jsonl"
            append(
                ledger,
                manifest,
                suspicious,
                self.read(ROOT / "data/canonical-checks.json"),
                {candidate["canonical_id"]},
                domain_context=context,
                screen_results=screen,
            )
            result = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PROOF", result.stdout)
            self.assertIn(candidate["canonical_id"], result.stdout)
            proof_payload = json.loads(result.stdout)
            self.assertEqual(proof_payload["progress"]["step"], 6)
            self.assertEqual(proof_payload["progress"]["label"], "PROOF")
            self.assertIn("suspicious findings require Proof", proof_payload["progress"]["summary"])
            self.assertEqual(
                proof_payload["recommended_execution"],
                {"provider": "codex", "model": "gpt-5.6-sol", "reasoning_effort": "max"},
            )
            resolved = {
                **{key: value for key, value in suspicious.items() if key != "unresolved_reason"},
                "review_stage": "PROOF",
                "status": "REVIEWED_SAFE",
                "exploitability": "guard holds",
                "impact": "none",
                "proof": f"POC source retained at {poc_location}; fixture invariant holds",
                "preserved_invariant": "fixture invariant",
                "evidence": [{"kind": "test", "location": poc_location, "reason": "proof source and test result"}],
            }
            append(
                ledger,
                manifest,
                resolved,
                self.read(ROOT / "data/canonical-checks.json"),
                {candidate["canonical_id"]},
                domain_context=context,
                screen_results=screen,
            )
            result = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("REPORT", result.stdout)
            self.assertIn("COMPLETE_CLEAN", result.stdout)
            report_payload = json.loads(result.stdout)
            self.assertEqual(report_payload["progress"]["step"], 7)
            self.assertEqual(report_payload["progress"]["label"], "REPORT")
            for _ in range(2):
                result = self.run_cli("scripts/audit_run.py", "report", "--run-dir", str(run_dir))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(poc_path.read_text(encoding="utf-8"), poc_source)
                self.assertIn(poc_location, (run_dir / "reviews/review-evm-audit-general.jsonl").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
