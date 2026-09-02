#!/usr/bin/env python3
"""Tests for deterministic confirmed-only report synthesis."""

from __future__ import annotations

import hashlib
import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_artifacts import check_body_hash, json_text, sha256_bytes, validate_poc_evidence, validate_target_snapshot
from evm_audit_runtime.reporting import derive_issue_candidates, derive_poc_required_ids, poc_required
from scripts.render_runtime import domain_context_template, screen_results_template
from scripts.review_ledger import append
from scripts.scope_context import compilation_digests, scope_inventory
from scripts.synthesize_report import ReportSynthesisResult, main as synthesize_main, synthesize
from scripts.validate_audit_run import validate_run

from helpers import ROOT, build_manifest


class ReportingTests(unittest.TestCase):
    def test_poc_required_policy_threshold(self) -> None:
        self.assertEqual([poc_required(level) for level in ("Info", "Low", "Medium", "High", "Critical")], [False, False, False, True, True])

    def test_poc_required_ids_are_deterministic(self) -> None:
        decisions = {
            "C": {"severity": "Critical"},
            "A": {"severity": "Medium"},
            "B": {"severity": "High"},
        }
        self.assertEqual(derive_poc_required_ids(["C", "A", "B"], decisions), ["B", "C"])

    def test_medium_does_not_require_poc(self) -> None:
        self.assertFalse(poc_required("Medium"))

    def test_low_does_not_require_poc(self) -> None:
        self.assertFalse(poc_required("Low"))

    def test_info_does_not_require_poc(self) -> None:
        self.assertFalse(poc_required("Info"))

    def test_high_requires_poc(self) -> None:
        self.assertTrue(poc_required("High"))

    def test_critical_requires_poc(self) -> None:
        self.assertTrue(poc_required("Critical"))

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

    def poc_evidence(
        self,
        manifest: dict,
        state: dict,
        candidate_id: str,
        severity: dict,
        source_path: str,
        source_sha256: str,
    ) -> dict:
        return {
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
            "severity_decisions_sha256": sha256_bytes(json_text(severity).encode("utf-8")),
            "findings": [{
                "canonical_id": candidate_id,
                "severity": severity["decisions"][candidate_id]["severity"],
                "runner": "foundry",
                "command": "forge test --match-test testExploit -vvv",
                "sources": [{"path": source_path, "sha256": source_sha256}],
                "entrypoint": "testExploit",
                "expected_result": "The exploit reproduces the confirmed defect.",
                "result_summary": "The fixture reproduced the confirmed defect.",
            }],
        }

    def poc_case(self, directory: Path) -> tuple[dict, dict, dict, bytes, dict, Path]:
        registry, manifest, screen, context, domain_context, candidate_id = self.artifacts(True)
        ledger = directory / "review.jsonl"
        self.append_confirmed_record(ledger, registry, manifest, candidate_id, domain_context, screen)
        state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
        severity = self.severity_artifact(manifest, candidate_id, state["review_state_digest"])
        severity_bytes = json_text(severity).encode("utf-8")
        source = directory / "poc/Exploit.t.sol"
        source.parent.mkdir()
        source.write_text("contract Exploit {}\n", encoding="utf-8")
        poc = self.poc_evidence(
            manifest,
            state,
            candidate_id,
            severity,
            source.relative_to(directory).as_posix(),
            hashlib.sha256(source.read_bytes()).hexdigest(),
        )
        return manifest, state, severity, severity_bytes, poc, source

    def low_level_poc_case(self, root: Path) -> tuple[list[str], Path, Path]:
        registry, manifest, screen, context, domain_context, candidate_id = self.artifacts(True)
        ledger = root / "review.jsonl"
        self.append_confirmed_record(ledger, registry, manifest, candidate_id, domain_context, screen)
        state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
        severity = self.severity_artifact(manifest, candidate_id, state["review_state_digest"])
        severity_bytes = json_text(severity).encode("utf-8")
        details = self.finding_details(manifest, candidate_id, state["review_state_digest"])
        source = root / "poc/Exploit.t.sol"
        source.parent.mkdir()
        source.write_text("contract Exploit {}\n", encoding="utf-8")
        poc = self.poc_evidence(
            manifest,
            state,
            candidate_id,
            severity,
            source.relative_to(root).as_posix(),
            sha256_bytes(source.read_bytes()),
        )
        manifest_path = root / "manifest.json"
        state_path = root / "audit-state.json"
        screen_path = root / "screen-results.json"
        domain_context_path = root / "domain-context.json"
        context_path = root / "context.json"
        severity_path = root / "severity.json"
        details_path = root / "details.json"
        poc_path = root / "external/deep/nested/poc-evidence.json"
        poc_path.parent.mkdir(parents=True)
        for path, value in (
            (manifest_path, manifest),
            (state_path, state),
            (screen_path, screen),
            (domain_context_path, domain_context),
            (context_path, context),
            (severity_path, severity),
            (details_path, details),
            (poc_path, poc),
        ):
            path.write_text(json_text(value), encoding="utf-8")
        output = root / "out/AUDIT-REPORT.md"
        issues = root / "out/issue-candidates.json"
        bundle = root / "out/report-bundle.json"
        command = [
            "--manifest", str(manifest_path), "--audit-state", str(state_path),
            "--context", str(context_path), "--domain-context", str(domain_context_path),
            "--screen-results", str(screen_path), "--ledger", str(ledger),
            "--severity-decisions", str(severity_path), "--finding-details", str(details_path),
            "--poc-evidence", str(poc_path), "--output", str(output),
            "--issue-candidates-out", str(issues), "--bundle-metadata-out", str(bundle),
        ]
        return command, root, output

    def test_synthesize_report_poc_validation_uses_explicit_run_dir(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            command, run_dir, output = self.low_level_poc_case(Path(directory))
            result = synthesize_main([*command, "--run-dir", str(run_dir)])
            self.assertEqual(result, 0)
            self.assertIn("**Severity:** High", output.read_text(encoding="utf-8"))

    def test_synthesize_report_poc_metadata_location_does_not_change_source_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            command, run_dir, output = self.low_level_poc_case(Path(directory))
            self.assertEqual(synthesize_main(command), 1)
            self.assertFalse(output.exists())
            self.assertEqual(synthesize_main([*command, "--run-dir", str(run_dir)]), 0)
            self.assertTrue(output.exists())

    def test_poc_evidence_validates_lineage_and_source_hash(self) -> None:
        registry, manifest, screen, context, domain_context, candidate_id = self.artifacts(True)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "review.jsonl"
            self.append_confirmed_record(ledger, registry, manifest, candidate_id, domain_context, screen)
            state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            severity = self.severity_artifact(manifest, candidate_id, state["review_state_digest"])
            severity_bytes = json_text(severity).encode("utf-8")
            source = Path(directory) / "poc/Exploit.t.sol"
            source.parent.mkdir()
            source.write_text("contract Exploit {}\n", encoding="utf-8")
            poc = self.poc_evidence(
                manifest, state, candidate_id, severity, "poc/Exploit.t.sol",
                hashlib.sha256(source.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                validate_poc_evidence(
                    ROOT, manifest, state, severity, severity_bytes, poc, run_dir=Path(directory)
                ),
                [candidate_id],
            )

    def test_poc_source_hash_tamper_is_rejected(self) -> None:
        registry, manifest, screen, context, domain_context, candidate_id = self.artifacts(True)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "review.jsonl"
            self.append_confirmed_record(ledger, registry, manifest, candidate_id, domain_context, screen)
            state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            severity = self.severity_artifact(manifest, candidate_id, state["review_state_digest"])
            severity_bytes = json_text(severity).encode("utf-8")
            source = Path(directory) / "poc/Exploit.t.sol"
            source.parent.mkdir()
            source.write_text("contract Exploit {}\n", encoding="utf-8")
            poc = self.poc_evidence(
                manifest, state, candidate_id, severity, "poc/Exploit.t.sol",
                hashlib.sha256(source.read_bytes()).hexdigest(),
            )
            source.write_text("contract Exploit { uint256 changed; }\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source hash does not match"):
                validate_poc_evidence(ROOT, manifest, state, severity, severity_bytes, poc, run_dir=Path(directory))

    def test_deleted_poc_source_is_rejected(self) -> None:
        registry, manifest, screen, context, domain_context, candidate_id = self.artifacts(True)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "review.jsonl"
            self.append_confirmed_record(ledger, registry, manifest, candidate_id, domain_context, screen)
            state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            severity = self.severity_artifact(manifest, candidate_id, state["review_state_digest"])
            severity_bytes = json_text(severity).encode("utf-8")
            source = Path(directory) / "poc/Exploit.t.sol"
            source.parent.mkdir()
            source.write_text("contract Exploit {}\n", encoding="utf-8")
            poc = self.poc_evidence(
                manifest, state, candidate_id, severity, "poc/Exploit.t.sol",
                hashlib.sha256(source.read_bytes()).hexdigest(),
            )
            source.unlink()
            with self.assertRaisesRegex(ValueError, "source is missing"):
                validate_poc_evidence(ROOT, manifest, state, severity, severity_bytes, poc, run_dir=Path(directory))

    def test_poc_evidence_binds_review_and_severity_bytes(self) -> None:
        registry, manifest, screen, context, domain_context, candidate_id = self.artifacts(True)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "review.jsonl"
            self.append_confirmed_record(ledger, registry, manifest, candidate_id, domain_context, screen)
            state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            severity = self.severity_artifact(manifest, candidate_id, state["review_state_digest"])
            severity_bytes = json_text(severity).encode("utf-8")
            source = Path(directory) / "poc/Exploit.t.sol"
            source.parent.mkdir()
            source.write_text("contract Exploit {}\n", encoding="utf-8")
            poc = self.poc_evidence(
                manifest, state, candidate_id, severity, "poc/Exploit.t.sol",
                hashlib.sha256(source.read_bytes()).hexdigest(),
            )
            for field, expected in (("review_state_digest", "0" * 64), ("severity_decisions_sha256", "0" * 64)):
                changed = {**poc, field: expected}
                with self.subTest(field=field):
                    with self.assertRaisesRegex(ValueError, "mismatched"):
                        validate_poc_evidence(ROOT, manifest, state, severity, severity_bytes, changed, run_dir=Path(directory))

    def test_poc_source_cannot_escape_allowed_roots(self) -> None:
        registry, manifest, screen, context, domain_context, candidate_id = self.artifacts(True)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "review.jsonl"
            self.append_confirmed_record(ledger, registry, manifest, candidate_id, domain_context, screen)
            state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            severity = self.severity_artifact(manifest, candidate_id, state["review_state_digest"])
            severity_bytes = json_text(severity).encode("utf-8")
            outside = Path(directory).parent / "outside-poc.t.sol"
            outside.write_text("contract Outside {}\n", encoding="utf-8")
            poc = self.poc_evidence(
                manifest, state, candidate_id, severity, "../outside-poc.t.sol",
                hashlib.sha256(outside.read_bytes()).hexdigest(),
            )
            with self.assertRaisesRegex(ValueError, "path traversal"):
                validate_poc_evidence(ROOT, manifest, state, severity, severity_bytes, poc, run_dir=Path(directory))

    def test_poc_source_symlink_escape_is_rejected(self) -> None:
        registry, manifest, screen, context, domain_context, candidate_id = self.artifacts(True)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "review.jsonl"
            self.append_confirmed_record(ledger, registry, manifest, candidate_id, domain_context, screen)
            state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            severity = self.severity_artifact(manifest, candidate_id, state["review_state_digest"])
            severity_bytes = json_text(severity).encode("utf-8")
            outside = Path(directory).parent / "outside-poc-link.t.sol"
            outside.write_text("contract Outside {}\n", encoding="utf-8")
            link = Path(directory) / "poc/Exploit.t.sol"
            link.parent.mkdir()
            link.symlink_to(outside)
            poc = self.poc_evidence(
                manifest, state, candidate_id, severity, "poc/Exploit.t.sol",
                hashlib.sha256(outside.read_bytes()).hexdigest(),
            )
            with self.assertRaisesRegex(ValueError, "escapes allowed roots"):
                validate_poc_evidence(ROOT, manifest, state, severity, severity_bytes, poc, run_dir=Path(directory))

    def test_high_poc_durable_source_must_be_under_run_poc(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            manifest, state, severity, severity_bytes, poc, source = self.poc_case(run_dir)
            target_source = run_dir / "TargetPoC.t.sol"
            target_source.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            poc["findings"][0]["sources"][0] = {
                "path": target_source.name,
                "sha256": sha256_bytes(target_source.read_bytes()),
            }
            with self.assertRaisesRegex(ValueError, "run-dir/poc"):
                validate_poc_evidence(ROOT, manifest, state, severity, severity_bytes, poc, run_dir=run_dir)

    def test_absolute_poc_source_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            manifest, state, severity, severity_bytes, poc, source = self.poc_case(run_dir)
            poc["findings"][0]["sources"][0]["path"] = str(source)
            with self.assertRaisesRegex(ValueError, "relative to run-dir/poc"):
                validate_poc_evidence(ROOT, manifest, state, severity, severity_bytes, poc, run_dir=run_dir)

    def test_target_tree_source_cannot_satisfy_final_poc_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            manifest, state, severity, severity_bytes, poc, source = self.poc_case(run_dir)
            target_root = run_dir / "target"
            target_root.mkdir()
            target_source = target_root / "TargetPoC.t.sol"
            target_source.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            manifest = copy.deepcopy(manifest)
            manifest["feature_map"]["recon_context"]["target_root"] = str(target_root)
            poc["findings"][0]["sources"] = [{
                "path": target_source.name,
                "sha256": sha256_bytes(target_source.read_bytes()),
            }]
            with self.assertRaisesRegex(ValueError, "run-dir/poc"):
                validate_poc_evidence(ROOT, manifest, state, severity, severity_bytes, poc, run_dir=run_dir)

    def test_build_root_source_cannot_satisfy_final_poc_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            manifest, state, severity, severity_bytes, poc, source = self.poc_case(run_dir)
            build_root = run_dir / "build"
            build_root.mkdir()
            build_source = build_root / "BuildPoC.t.sol"
            build_source.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            manifest = copy.deepcopy(manifest)
            manifest["feature_map"]["recon_context"]["build_root"] = str(build_root)
            poc["findings"][0]["sources"] = [{
                "path": build_source.name,
                "sha256": sha256_bytes(build_source.read_bytes()),
            }]
            with self.assertRaisesRegex(ValueError, "run-dir/poc"):
                validate_poc_evidence(ROOT, manifest, state, severity, severity_bytes, poc, run_dir=run_dir)

    def test_run_poc_source_survives_target_snapshot_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            manifest, state, severity, severity_bytes, poc, _ = self.poc_case(run_dir)
            foundry_root = run_dir / "foundry-repository"
            target = foundry_root / "src/Target.sol"
            target.parent.mkdir(parents=True)
            target.write_text("pragma solidity ^0.8.24; contract Target {}\n", encoding="utf-8")
            (foundry_root / "foundry.toml").write_text(
                '[profile.default]\nsrc = "src"\n', encoding="utf-8"
            )
            files, excluded = scope_inventory(foundry_root, dependency_roots=())
            digests = compilation_digests(
                foundry_root,
                files,
                "0.8.24",
                build_root=foundry_root,
                dependency_roots=(),
            )
            manifest = copy.deepcopy(manifest)
            recon = manifest["feature_map"]["recon_context"]
            recon.update(
                target_root=str(foundry_root.resolve()),
                build_root=str(foundry_root.resolve()),
                files_analyzed=files,
                excluded_paths=excluded,
                dependency_roots=[],
                source_digest=digests["audit_source_digest"],
                audit_source_digest=digests["audit_source_digest"],
                dependency_digest=digests["dependency_digest"],
                build_config_digest=digests["build_config_digest"],
                compilation_input_digest=digests["compilation_input_digest"],
            )
            validate_target_snapshot(manifest)
            self.assertEqual(
                validate_poc_evidence(ROOT, manifest, state, severity, severity_bytes, poc, run_dir=run_dir),
                [state["coverage"]["confirmed"][0]],
            )
            validate_target_snapshot(manifest)

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
        poc_evidence: dict | None = None,
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
            poc_evidence=poc_evidence,
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
                self.severity_artifact(manifest, candidate_id, state["review_state_digest"], "Medium"),
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
        self.assertEqual(issues["findings"], [{"canonical_id": candidate_id, "severity": "Medium"}])
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

    def test_high_synthesis_rejects_missing_poc(self) -> None:
        registry, manifest, screen, context, domain_context, candidate_id = self.artifacts(True)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "review.jsonl"
            self.append_confirmed_record(ledger, registry, manifest, candidate_id, domain_context, screen)
            state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            with self.assertRaisesRegex(ValueError, "INCOMPLETE_POC"):
                self.run_synthesis(
                    registry, manifest, state, [ledger], screen, context, domain_context,
                    self.severity_artifact(manifest, candidate_id, state["review_state_digest"], "High"),
                    finding_details=self.finding_details(manifest, candidate_id, state["review_state_digest"]),
                )

    def test_low_confirmed_finding_reports_without_poc(self) -> None:
        registry, manifest, screen, context, domain_context, candidate_id = self.artifacts(True)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "review.jsonl"
            self.append_confirmed_record(ledger, registry, manifest, candidate_id, domain_context, screen)
            state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            synthesis = self.run_synthesis(
                registry, manifest, state, [ledger], screen, context, domain_context,
                self.severity_artifact(manifest, candidate_id, state["review_state_digest"], "Low"),
                finding_details=self.finding_details(manifest, candidate_id, state["review_state_digest"]),
            )
        self.assertIn("**Severity:** Low", synthesis.report)
        self.assertIn("**PoC:** Not required by policy", synthesis.report)
        self.assertEqual(synthesis.issue_candidates["findings"], [])

    def test_info_confirmed_finding_reports_without_poc(self) -> None:
        registry, manifest, screen, context, domain_context, candidate_id = self.artifacts(True)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "review.jsonl"
            self.append_confirmed_record(ledger, registry, manifest, candidate_id, domain_context, screen)
            state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            synthesis = self.run_synthesis(
                registry, manifest, state, [ledger], screen, context, domain_context,
                self.severity_artifact(manifest, candidate_id, state["review_state_digest"], "Info"),
                finding_details=self.finding_details(manifest, candidate_id, state["review_state_digest"]),
            )
        self.assertIn("**Severity:** Info", synthesis.report)
        self.assertIn("**PoC:** Not required by policy", synthesis.report)
        self.assertEqual(synthesis.issue_candidates["findings"], [])

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
                self.severity_artifact(manifest, candidate_id, state["review_state_digest"], "Medium"),
                finding_details=self.finding_details(manifest, candidate_id, state["review_state_digest"]),
            ).report
        self.assertIn("# EVM Audit Report", report)


if __name__ == "__main__":
    unittest.main()
