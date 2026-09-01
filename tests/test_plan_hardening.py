#!/usr/bin/env python3
"""Focused regressions for the hardening and token-efficiency pass."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import EMPTY_TARGET, ROOT, build_manifest, review_inputs, suite_inputs, synthetic_feature_map
from scripts.audit_artifacts import check_body_hash, derive_review_snapshot_id, validate_schema
from scripts.code_context import lookup, validate_code_index
from scripts.recon import actual_compiler_versions
from scripts.render_runtime import domain_resolution_template, render, screen_results_template, validate_screen_results
from scripts.review_ledger import checkpoint, validate_record
from scripts.validate_audit_run import validate_run
from scripts.scope_context import compilation_digests
from scripts.select_checks import audit_context, evaluate_domains, load_domains, normalize_feature_map, select


class PlanHardeningTests(unittest.TestCase):
    def _record(self, registry: dict, manifest: dict, status: str = "NOT_APPLICABLE") -> tuple[dict, str]:
        _, _, snapshot = review_inputs(manifest)
        entry = manifest["selected"][0]
        check = next(item for item in registry["checks"] if item["canonical_id"] == entry["canonical_id"])
        record = {
            "record_type": "review",
            "schema_version": 7,
            "canonical_id": entry["canonical_id"],
            "revision": 1,
            "owner_domain": entry["owner_domain"],
            "routing_snapshot_id": manifest["routing_snapshot_id"],
            "review_snapshot_id": snapshot,
            "registry_sha256": manifest["audit_context"]["registry_sha256"],
            "source_digest": manifest["audit_context"]["source_digest"],
            "compilation_input_digest": manifest["audit_context"]["compilation_input_digest"],
            "check_body_hash": check_body_hash(check),
            "review_stage": "DEEP_REVIEW",
            "status": status,
            "evidence": [{"kind": "scope", "location": "fixture", "reason": "complete scope"}, {"kind": "inheritance", "location": "fixture", "reason": "excluded"}],
        }
        if status == "NOT_APPLICABLE":
            record.update(scope_complete=True, applicability="NOT_APPLICABLE - no reachable surface")
        elif status == "REVIEWED_SAFE":
            record.update(applicability="APPLICABLE - guard", code_path="entry", preserved_invariant="invariant holds")
        return record, snapshot

    def test_deep_not_applicable_is_policy_bound_and_compact(self) -> None:
        registry, _, _, manifest = build_manifest()
        record, snapshot = self._record(registry, manifest)
        self.assertEqual(validate_record(record, manifest, registry, {record["canonical_id"]}, review_snapshot_id=snapshot), [])
        record["evidence"] = [{"kind": "manual", "location": "fixture", "reason": "guess"}]
        self.assertTrue(any("trusted_absence_policy" in error for error in validate_record(record, manifest, registry, {record["canonical_id"]}, review_snapshot_id=snapshot)))
        record["evidence"] = [{"kind": "scope", "location": "fixture", "reason": "complete scope"}, {"kind": "inheritance", "location": "fixture", "reason": "excluded"}]
        record["code_path"] = "TODO"
        self.assertTrue(any("unresolved" in error for error in validate_record(record, manifest, registry, {record["canonical_id"]}, review_snapshot_id=snapshot)))

    def test_invalid_deep_not_applicable_cannot_look_clean(self) -> None:
        registry, _, _, manifest = build_manifest()
        screen, domain_context, _ = review_inputs(manifest)
        candidate_id = screen["results"][0]["canonical_id"]
        for result in screen["results"][1:]:
            result.update(
                result="NOT_APPLICABLE_CONFIRMED",
                scope_complete=True,
                evidence=[
                    {"kind": "scope", "location": "fixture", "reason": "complete scope"},
                    {"kind": "inheritance", "location": "fixture", "reason": "surface absent"},
                ],
            )
        snapshot = derive_review_snapshot_id(ROOT, manifest, None, domain_context, screen)
        record, _ = self._record(registry, manifest)
        record.update(review_snapshot_id=snapshot, evidence=[{"kind": "manual", "location": "fixture", "reason": "guess"}])
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "review.jsonl"
            ledger.write_text("\n".join(json.dumps(value) for value in (checkpoint(manifest, snapshot), record)) + "\n", encoding="utf-8")
            context = {**manifest["audit_context"], "routing_snapshot_id": manifest["routing_snapshot_id"]}
            state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
        self.assertEqual(state["status"], "INCOMPLETE_REVIEW")
        self.assertFalse(state["clean"])
        self.assertIn(candidate_id, state["coverage"]["deep_reviewed"])

    def test_non_applicability_uses_effective_owner_policy(self) -> None:
        registry, names, policies = suite_inputs()
        raw = synthetic_feature_map()
        features = normalize_feature_map(raw, names, policies, EMPTY_TARGET)
        context = audit_context(ROOT, registry, raw["recon_context"], target_root=EMPTY_TARGET, audit_timestamp="test")
        environment = {**{key: context[key] for key in ("chain_id", "chain_family", "execution_environment", "compiler_version", "evm_fork", "protocol_version")}, "environment_facts": context["environment_facts"]}
        configs = load_domains(ROOT)
        configs["evm-audit-general"] = {**configs["evm-audit-general"], "always_screen": False}
        manifest, _ = select(registry, features, names, None, context, configs, environment, raw["recon_context"])
        primary = "evm-audit-precision-math"
        fallback = "evm-audit-general"
        manifest["deferred_domains"] = [
            {
                **entry,
                "trusted_absence_policy": {
                    "requires_complete_scope": True,
                    "allowed_evidence": ["scope", "dependency"],
                },
            }
            if entry["domain"] == primary else entry
            for entry in manifest["deferred_domains"]
        ]
        manifest["selected_domains"] = [
            {
                **entry,
                "trusted_absence_policy": {
                    "requires_complete_scope": True,
                    "allowed_evidence": ["scope", "inheritance"],
                },
            }
            if entry["domain"] == fallback else entry
            for entry in manifest["selected_domains"]
        ]
        from scripts.audit_artifacts import bind_routing_snapshot

        manifest = bind_routing_snapshot(manifest)
        resolution = domain_resolution_template(manifest)
        for domain in resolution["domains"]:
            resolution["domains"][domain] = (
                {
                    "status": "PRESENT",
                    "scope_complete": False,
                    "evidence": [{"kind": "source", "location": "fixture", "reason": "surface present"}],
                }
                if domain == fallback else {
                    "status": "ABSENT_CONFIRMED",
                    "scope_complete": True,
                    "evidence": [{"kind": "scope", "location": "fixture", "reason": "scope"}, {"kind": "inheritance", "location": "fixture", "reason": "absent"}],
                }
            )
        resolution["domains"][primary]["evidence"] = [{"kind": "scope", "location": "fixture", "reason": "scope"}, {"kind": "dependency", "location": "fixture", "reason": "absent"}]
        screen = screen_results_template(manifest, resolution)
        shared = next(item for item in screen["results"] if item["canonical_id"] == "EVM-TIME-001")
        _, context, snapshot = review_inputs(manifest, resolution)
        entry = next(item for item in manifest["deferred"] if item["canonical_id"] == "EVM-TIME-001")
        check = next(item for item in registry["checks"] if item["canonical_id"] == "EVM-TIME-001")
        record = {
            "record_type": "review", "schema_version": 7, "canonical_id": "EVM-TIME-001", "revision": 1,
            "owner_domain": fallback, "routing_snapshot_id": manifest["routing_snapshot_id"], "review_snapshot_id": snapshot,
            "registry_sha256": manifest["audit_context"]["registry_sha256"], "source_digest": manifest["audit_context"]["source_digest"],
            "compilation_input_digest": manifest["audit_context"]["compilation_input_digest"], "check_body_hash": check_body_hash(check),
            "review_stage": "DEEP_REVIEW", "status": "NOT_APPLICABLE", "scope_complete": True,
            "applicability": "NOT_APPLICABLE - effective owner excludes it",
            "evidence": [{"kind": "scope", "location": "fixture", "reason": "scope"}, {"kind": "inheritance", "location": "fixture", "reason": "absent"}],
        }
        self.assertEqual(shared["canonical_id"], "EVM-TIME-001")
        self.assertEqual(validate_record(record, manifest, registry, {record["canonical_id"]}, resolution, snapshot), [])

    def test_proof_runtime_contains_only_suspicious_ids(self) -> None:
        registry, _, _, manifest = build_manifest()
        screen, _, snapshot = review_inputs(manifest)
        first = screen["results"][0]["canonical_id"]
        second = screen["results"][1]["canonical_id"]
        record = {"revision": 1, "review_stage": "DEEP_REVIEW", "status": "SUSPICIOUS", "code_path": "entry", "unresolved_reason": "proof pending", "evidence": [{"kind": "source", "location": "fixture", "reason": "candidate"}]}
        output = render(manifest, registry, "proof", {first}, review_snapshot=snapshot, proof_records={first: record})
        self.assertIn(f"[{first}]", output)
        self.assertNotIn(f"[{second}]", output)
        self.assertIn("proof pending", output)

    def test_code_index_lookup_expands_callers_and_callees(self) -> None:
        digest = "a" * 64
        contract_id = "build://Target.sol::Target"
        entry_id = f"{contract_id}.entry()"
        helper_id = f"{contract_id}.helper()"
        callee_id = f"{contract_id}.callee()"
        contract = {"file": "build://Target.sol", "start_line": 1, "end_line": 6, "bases": [], "scope_origin": "AUDIT_SCOPE"}
        index = {
            "schema_version": 2, "target_root": "fixture", "build_root": "fixture",
            "source_digest": digest, "compilation_input_digest": "b" * 64,
            "contracts": {contract_id: contract}, "inheritance": {contract_id: []}, "external_calls": [], "storage_writes": [], "modifiers": {},
            "source_ranges": {key: {"file": "build://Target.sol", "start_line": 1, "end_line": 2} for key in (entry_id, helper_id, callee_id)},
            "functions": {
                entry_id: {"function_id": entry_id, "contract_id": contract_id, "contract": "Target", "name": "entry", "file": "build://Target.sol", "start_line": 1, "end_line": 2, "visibility": "external", "modifiers": [], "reads": [], "writes": [], "state_reads": [], "state_writes": [], "local_writes": [], "internal_calls": [helper_id], "external_calls": [], "scope_origin": "AUDIT_SCOPE"},
                helper_id: {"function_id": helper_id, "contract_id": contract_id, "contract": "Target", "name": "helper", "file": "build://Target.sol", "start_line": 3, "end_line": 4, "visibility": "internal", "modifiers": [], "reads": [], "writes": [], "state_reads": [], "state_writes": [], "local_writes": [], "internal_calls": [callee_id], "external_calls": [], "scope_origin": "AUDIT_SCOPE"},
                callee_id: {"function_id": callee_id, "contract_id": contract_id, "contract": "Target", "name": "callee", "file": "build://Target.sol", "start_line": 5, "end_line": 6, "visibility": "internal", "modifiers": [], "reads": [], "writes": [], "state_reads": [], "state_writes": [], "local_writes": [], "internal_calls": [], "external_calls": [], "scope_origin": "AUDIT_SCOPE"},
            },
        }
        validate_code_index(ROOT, index)
        result = lookup(index, "Target.helper()", include_callers=True, include_callees=True)
        self.assertEqual(set(result["functions"]), {entry_id, helper_id, callee_id})

    def test_closure_digest_ignores_uncompiled_unrelated_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src"
            source.mkdir()
            target = source / "Target.sol"
            unrelated = source / "Unrelated.sol"
            target.write_text("pragma solidity ^0.8.0; contract Target {}\n", encoding="utf-8")
            unrelated.write_text("pragma solidity ^0.8.0; contract Unrelated {}\n", encoding="utf-8")
            before = compilation_digests(target, ["Target.sol"], "0.8.24", build_root=root, compilation_files=["src/Target.sol"])
            unrelated.write_text("pragma solidity ^0.8.0; contract Unrelated { uint x; }\n", encoding="utf-8")
            after = compilation_digests(target, ["Target.sol"], "0.8.24", build_root=root, compilation_files=["src/Target.sol"])
            self.assertEqual(before["compilation_input_digest"], after["compilation_input_digest"])

    def test_single_file_git_root_and_dependency_only_routing(self) -> None:
        from scripts.select_checks import find_git_root

        self.assertEqual(find_git_root(EMPTY_TARGET), ROOT)
        solc = shutil.which("solc") or "solc"
        result = subprocess.run([sys.executable, "scripts/recon.py", "tests/fixtures/recon/DependencyOnlyTarget.sol", "--solc", solc, "--quiet"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        feature_map = json.loads(result.stdout)
        self.assertEqual({item.get("scope_origin") for item in feature_map["features"]["uses-access-control"]["evidence"]}, {"DEPENDENCY"})
        domains = evaluate_domains(load_domains(ROOT), feature_map["features"], None)
        access = next(item for item in domains[1] if item["domain"] == "evm-audit-access-control")
        self.assertEqual(access["state"], "DEFERRED")

    def test_actual_compiler_versions_prefer_compilation_units(self) -> None:
        class Version:
            version = "0.8.24"

        class Unit:
            compiler_version = Version()

        class Compile:
            compilation_units = {"unit": Unit()}

        class Slither:
            crytic_compile = Compile()

        self.assertEqual(actual_compiler_versions(Slither()), ["0.8.24"])


if __name__ == "__main__":
    unittest.main()
