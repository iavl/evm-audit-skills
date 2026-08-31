#!/usr/bin/env python3
"""Tests for runtime artifacts and audit completion safety."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.render_runtime import render, screen_results_template, validate_manifest, validate_screen_results
from scripts.review_ledger import append, check_body_hash, load, validate_record, validate_records
from scripts.scope_context import find_suite_root
from scripts.select_checks import audit_context, load_domains, normalize_feature_map, select
from scripts.validate_audit_run import validate_run

from helpers import EMPTY_TARGET, ROOT, build_manifest, load_json, suite_inputs, synthetic_feature_map


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry, cls.feature_names, cls.feature_policies = suite_inputs()

    def test_suite_runtime_paths_resolve_shared_files(self) -> None:
        master = ROOT / "skills/evm-audit-master/SKILL.md"
        root = find_suite_root(master)
        self.assertEqual(root, ROOT)
        for name in ("data", "domains", "scripts"):
            with self.subTest(name=name):
                self.assertTrue((root / name).is_dir())
        master_text = master.read_text(encoding="utf-8")
        self.assertIn("<suite-root>/scripts/", master_text)
        self.assertNotIn("../scripts/", master_text)

        skill = ROOT / "skills/evm-audit-erc20/SKILL.md"
        self.assertEqual(find_suite_root(skill), ROOT)
        self.assertTrue((ROOT / "data/canonical-checks.json").exists())
        self.assertTrue((ROOT / "domains/erc20.json").exists())
        self.assertTrue((ROOT / "scripts/select_checks.py").exists())
        self.assertIn(
            "<suite-root>/skills/evm-audit-master/references/check-review-contract.runtime.md",
            skill.read_text(encoding="utf-8"),
        )

    def test_selector_single_snapshot_writes_manifest_and_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            feature_path = temp / "feature-map.json"
            feature_path.write_text(json.dumps(synthetic_feature_map()), encoding="utf-8")
            manifest_path, checks_path, context_path = temp / "manifest.json", temp / "screen.md", temp / "context.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/select_checks.py",
                    "--feature-map",
                    str(feature_path),
                    "--target-root",
                    "tests/fixtures/recon/Empty.sol",
                    "--domain",
                    "evm-audit-erc20",
                    "--manifest-out",
                    str(manifest_path),
                    "--context-out",
                    str(context_path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = load_json(manifest_path)
            self.assertTrue(manifest_path.exists() and context_path.exists())
            render_result = subprocess.run(
                [
                    sys.executable,
                    "scripts/render_runtime.py",
                    "--manifest",
                    str(manifest_path),
                    "--profile",
                    "screen",
                    "--output",
                    str(checks_path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(render_result.returncode, 0, render_result.stderr)
            runtime = checks_path.read_text(encoding="utf-8")
            for entry in manifest["selected"]:
                self.assertIn(f"[{entry['canonical_id']}]", runtime)
            self.assertNotIn("LIKELY_SAFE", runtime)

    def test_routing_manifest_covers_scope_and_shared_owner(self) -> None:
        registry, _, _, manifest = build_manifest(
            ("evm-audit-general", "evm-audit-precision-math"),
            all_features=True,
        )
        self.assertEqual(manifest["schema_version"], 6)
        self.assertTrue(manifest["immutable"])
        self.assertIn("target_repo_commit", manifest["audit_context"])
        shared = next(
            entry
            for entry in manifest["selected"] + manifest["filtered"]
            if entry["canonical_id"] == "EVM-TIME-001"
        )
        self.assertEqual(shared["owner_domain"], "evm-audit-precision-math")
        validate_manifest(ROOT, manifest, registry)

    def test_routing_manifest_rejects_invalid_shape(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as manifest_file:
            json.dump(
                {
                    "schema_version": 1,
                    "stage": "FAST_FILTER",
                    "scope": {"domains": ["evm-audit-precision-math"], "candidate_count": 1},
                    "feature_map": {"schema_version": 99, "features": {}},
                    "selected_count": 0,
                    "filtered_count": 0,
                    "selected": [],
                    "filtered": [],
                },
                manifest_file,
            )
            manifest_file.flush()
            with self.assertRaises(ValueError):
                validate_manifest(ROOT, load_json(Path(manifest_file.name)), self.registry)

    def test_screen_deep_uses_only_validated_candidates(self) -> None:
        registry, _, _, manifest = build_manifest(all_features=True)
        screen_results = screen_results_template(manifest)
        self.assertTrue(all(item["result"] == "CANDIDATE" for item in screen_results["results"]))
        candidate = screen_results["results"][0]["canonical_id"]
        not_applicable = screen_results["results"][1]
        for result in screen_results["results"][1:]:
            result["result"] = "NOT_APPLICABLE_CONFIRMED"
            result["evidence"] = [
                {"kind": kind, "location": "fixture", "reason": "complete scope evidence"}
                for kind in ("scope", "inheritance", "interface", "deployment")
            ]
        candidates = validate_screen_results(ROOT, manifest, screen_results)
        self.assertEqual(candidates, {candidate})
        screen = render(manifest, registry, "screen", set())
        deep = render(manifest, registry, "deep", candidates)
        self.assertIn("**Trigger:**", screen)
        self.assertIn("**Detection:**", screen)
        self.assertNotIn("**Risk:**", screen)
        self.assertIn(f"## [{candidate}]", deep)
        self.assertIn("**Risk:**", deep)
        self.assertNotIn(f"## [{not_applicable['canonical_id']}]", deep)
        self.assertNotIn("LIKELY_SAFE", screen + deep)

    def test_global_policies_do_not_enter_deep_cards(self) -> None:
        check = next(
            item
            for item in self.registry["checks"]
            if item["fp_policy"] == "global" and item["proof_policy"] == "global"
        )
        self.assertEqual(check["false_positive_gates"], [])
        self.assertEqual(check["proof"], [])

    def test_audit_state_is_derived_from_screen_coverage(self) -> None:
        _, _, _, manifest = build_manifest()
        screen = screen_results_template(manifest)
        evidence = [
            {"kind": kind, "location": "fixture", "reason": "complete evidence"}
            for kind in ("scope", "inheritance", "interface", "deployment")
        ]
        for result in screen["results"]:
            result["result"] = "NOT_APPLICABLE_CONFIRMED"
            result["evidence"] = evidence
        state = validate_run(ROOT, manifest, self.registry, screen, None, None, [])
        self.assertEqual(state["status"], "COMPLETE")
        self.assertTrue(state["clean"])
        screen["results"][0]["result"] = "CANDIDATE"
        screen["results"][0]["evidence"] = []
        state = validate_run(ROOT, manifest, self.registry, screen, None, None, [])
        self.assertEqual(state["status"], "COMPLETE_WITH_UNRESOLVED_REVIEW")

    def test_unknown_deferred_domain_is_not_complete(self) -> None:
        raw = synthetic_feature_map()
        features = normalize_feature_map(raw, self.feature_names, self.feature_policies, EMPTY_TARGET)
        context = audit_context(
            ROOT,
            self.registry,
            raw["recon_context"],
            target_root=EMPTY_TARGET,
            audit_timestamp="test",
        )
        environment = {
            **{
                key: context[key]
                for key in (
                    "chain_id",
                    "chain_family",
                    "execution_environment",
                    "compiler_version",
                    "evm_fork",
                    "protocol_version",
                )
            },
            "environment_facts": context["environment_facts"],
        }
        configs = load_domains(ROOT)
        required_key = configs["evm-audit-general"]["required_context"][0]["key"]
        domain_context = {
            "domains": {
                "evm-audit-general": {
                    required_key: {"status": "KNOWN", "value": "fixture", "evidence": ["fixture"]}
                }
            }
        }
        manifest, _ = select(
            self.registry,
            features,
            self.feature_names,
            None,
            context,
            configs,
            environment,
            raw["recon_context"],
            domain_context,
        )
        screen = screen_results_template(manifest)
        for result in screen["results"]:
            result["result"] = "NOT_APPLICABLE_CONFIRMED"
            result["evidence"] = [
                {"kind": kind, "location": "fixture", "reason": "complete evidence"}
                for kind in ("scope", "inheritance", "interface", "deployment")
            ]
        resolution = {
            "schema_version": 1,
            "routing_snapshot_id": manifest["routing_snapshot_id"],
            "registry_sha256": manifest["audit_context"]["registry_sha256"],
            "source_digest": manifest["audit_context"]["source_digest"],
            "compilation_input_digest": manifest["audit_context"]["compilation_input_digest"],
            "domains": {
                entry["domain"]: {"status": "UNKNOWN", "scope_complete": False, "evidence": []}
                for entry in manifest["deferred_domains"]
            },
        }
        state = validate_run(ROOT, manifest, self.registry, screen, resolution, None, [])
        self.assertEqual(state["status"], "COMPLETE_WITH_UNRESOLVED_DOMAIN_ROUTING")

    def test_jsonl_resume_requires_same_snapshot_and_appends(self) -> None:
        registry, _, _, manifest = build_manifest()
        entry = manifest["selected"][0]
        check = next(item for item in registry["checks"] if item["canonical_id"] == entry["canonical_id"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review.jsonl"
            record = {
                "record_type": "review",
                "schema_version": 3,
                "canonical_id": check["canonical_id"],
                "owner_domain": entry["owner_domain"],
                "routing_snapshot_id": manifest["routing_snapshot_id"],
                "check_body_hash": check_body_hash(check),
                "review_stage": "DEEP_REVIEW",
                "status": "REVIEWED_SAFE",
                "applicability": "APPLICABLE - fixture",
                "code_path": "fixture entry",
                "preconditions": "fixture state",
                "exploitability": "blocked by fixture guard",
                "impact": "N/A - invariant holds",
                "proof": "fixture invariant holds",
                "preserved_invariant": "fixture invariant",
                "evidence": [{"kind": "test", "location": "fixture", "reason": "test evidence"}],
            }
            append(path, manifest, record)
            self.assertEqual(validate_records(load(path), manifest, registry, {check["canonical_id"]}), [])
            second_entry = manifest["selected"][1]
            second_check = next(item for item in registry["checks"] if item["canonical_id"] == second_entry["canonical_id"])
            second_record = {
                **record,
                "canonical_id": second_check["canonical_id"],
                "owner_domain": second_entry["owner_domain"],
                "check_body_hash": check_body_hash(second_check),
            }
            append(path, manifest, second_record, registry, {check["canonical_id"], second_check["canonical_id"]})
            self.assertEqual(len(load(path)), 3)
            self.assertEqual(
                validate_records(load(path), manifest, registry, {check["canonical_id"], second_check["canonical_id"]}),
                [],
            )
            changed = {**manifest, "audit_context": {**manifest["audit_context"], "source_digest": "0" * 64}}
            self.assertTrue(validate_records(load(path), changed, registry, {check["canonical_id"]}))
            with self.assertRaisesRegex(ValueError, "record_type=review"):
                append(path, manifest, {key: value for key, value in record.items() if key != "record_type"})

    def test_cross_snapshot_resume_cli_is_removed(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/review_ledger.py", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("--" + "resume-from", result.stdout)

    def test_domain_skills_embed_the_evidence_gate(self) -> None:
        for skill_path in sorted((ROOT / "skills").glob("evm-audit-*/SKILL.md")):
            if skill_path.parent.name == "evm-audit-master":
                continue
            text = skill_path.read_text(encoding="utf-8")
            with self.subTest(skill=skill_path.parent.name):
                self.assertIn("## Runtime Modes", text)
                self.assertIn("check-review-contract.runtime.md", text)
                self.assertIn("Never rerun Recon or Selector", text)
                self.assertIn("## Required Context", text)
                self.assertIn("Pattern matches are candidates, not findings", text)
                self.assertIn("reachable path", text)
                self.assertIn("tri-state predicate router", text)
                self.assertIn("Do not load `<suite-root>/data/canonical-checks.json`", text)

    def test_review_contract_keeps_suspicious_out_of_severity(self) -> None:
        text = (ROOT / "skills/evm-audit-master/references/check-review-contract.md").read_text(encoding="utf-8")
        self.assertIn("`SUSPICIOUS`", text)
        self.assertIn("Do not assign severity", text)
        self.assertIn("`CONFIRMED`", text)
        self.assertIn("runnable PoC", text)

    def test_review_ledger_enforces_status_evidence_gate(self) -> None:
        registry, _, _, manifest = build_manifest()
        entry = manifest["selected"][0]
        check = next(item for item in registry["checks"] if item["canonical_id"] == entry["canonical_id"])
        base = {
            "schema_version": 3,
            "record_type": "review",
            "canonical_id": entry["canonical_id"],
            "owner_domain": entry["owner_domain"],
            "routing_snapshot_id": manifest["routing_snapshot_id"],
            "check_body_hash": check_body_hash(check),
            "review_stage": "PROOF",
            "applicability": "APPLICABLE - path exists",
            "code_path": "entry() -> call()",
            "preconditions": "attacker controls target",
            "exploitability": "attacker invokes entry",
            "impact": "accounting accepts false success",
            "proof": "test demonstrates false success",
            "evidence": [{"kind": "test", "location": "fixture", "reason": "executable evidence"}],
        }
        base.update(
            {
                key: manifest["audit_context"][key]
                for key in ("registry_sha256", "source_digest", "compilation_input_digest")
            }
        )
        suspicious = {
            **base,
            "status": "SUSPICIOUS",
            "unresolved_reason": "missing alternate path",
            "code_path": "UNRESOLVED - alternate path pending",
            "severity": "High",
        }
        self.assertTrue(
            any(
                "not valid" in error or "additional" in error
                for error in validate_record(suspicious, manifest, registry, {entry["canonical_id"]})
            )
        )
        confirmed = {**base, "status": "CONFIRMED"}
        self.assertEqual(validate_record(confirmed, manifest, registry, {entry["canonical_id"]}), [])
        old_schema = {**confirmed, "schema_version": 2}
        self.assertTrue(validate_record(old_schema, manifest, registry, {entry["canonical_id"]}))
        incomplete = {key: value for key, value in confirmed.items() if key != "proof"}
        self.assertTrue(
            any(
                "missing review fields" in error or "not valid" in error
                for error in validate_record(incomplete, manifest, registry, {entry["canonical_id"]})
            )
        )


if __name__ == "__main__":
    unittest.main()
