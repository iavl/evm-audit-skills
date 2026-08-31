#!/usr/bin/env python3
"""Regression tests for the canonical checklist and routing workflow."""

from __future__ import annotations

import hashlib
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.check_knowledge_health import knowledge_health, source_status
from scripts.generate_checklists import load_domains, write_outputs
from scripts.render_runtime import render, screen_results_template, validate_manifest
from scripts.scope_context import find_suite_root
from scripts.select_checks import audit_context, evaluate_check, evaluate_environment, evaluate_group, knowledge_state, normalize_feature_map, select, validate_environment_context, vocabulary
from scripts.review_ledger import append, check_body_hash, merge, resumable, validate_record
from scripts.validate_audit_run import validate_run
from scripts.validate_checklists import validate_knowledge_claims


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ChecklistTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_json(ROOT / "data" / "canonical-checks.json")
        cls.by_id = {check["canonical_id"]: check for check in cls.registry["checks"]}
        cls.feature_data = load_json(ROOT / "data/features.json")
        cls.feature_names, cls.feature_policies = vocabulary(cls.feature_data)
        result = subprocess.run(
            [sys.executable, "scripts/recon.py", "tests/fixtures/recon/Empty.sol", "--solc", str(Path("/usr/local/bin/solc")) if Path("/usr/local/bin/solc").exists() else "solc"],
            cwd=ROOT, capture_output=True, text=True,
        )
        if result.returncode:
            raise RuntimeError(result.stderr)
        cls.empty_feature_map = json.loads(result.stdout)

    def v4_map(self, statuses: dict[str, str]) -> dict:
        feature_map = copy.deepcopy(self.empty_feature_map)
        for feature, status in statuses.items():
            feature_map["features"][feature] = {
                "status": status,
                "evidence": [] if status == "UNKNOWN" else [{"kind": "manual", "location": "fixture", "reason": "explicit fixture evidence"}],
            }
        return feature_map

    def explicit_manifest(self, domain: str = "evm-audit-general") -> dict:
        raw = self.v4_map({})
        features = normalize_feature_map(raw, self.feature_names, self.feature_policies, ROOT / "tests/fixtures/recon/Empty.sol")
        context = audit_context(ROOT, self.registry, raw["recon_context"], target_root=ROOT / "tests/fixtures/recon/Empty.sol", audit_timestamp="test")
        environment = {**{key: context[key] for key in ("chain_id", "chain_family", "execution_environment", "compiler_version", "evm_fork", "protocol_version")}, "environment_facts": context["environment_facts"]}
        config = load_domains(ROOT)
        key = config[domain]["required_context"][0]["key"]
        domain_context = {"domains": {domain: {key: {"status": "KNOWN", "value": "fixture", "evidence": ["fixture"]}}}}
        manifest, _ = select(self.registry, features, self.feature_names, [domain], context, config, environment, raw["recon_context"], domain_context)
        return manifest

    def test_generated_markdown_is_current(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/generate_checklists.py", "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_generator_is_a_pure_renderer(self) -> None:
        registry_path = ROOT / "data/canonical-checks.json"
        before = hashlib.sha256(registry_path.read_bytes()).hexdigest()
        result = subprocess.run(
            [sys.executable, "scripts/generate_checklists.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        after = hashlib.sha256(registry_path.read_bytes()).hexdigest()
        self.assertEqual(before, after)

    def test_domain_configuration_drives_generated_skills(self) -> None:
        domains = load_domains(ROOT)
        self.assertEqual(set(domains), {path.parent.name for path in (ROOT / "skills").glob("evm-audit-*/SKILL.md") if path.parent.name != "evm-audit-master"})
        source = (ROOT / "scripts/generate_checklists.py").read_text(encoding="utf-8")
        self.assertNotIn("DOMAIN_CODES", source)
        self.assertNotIn("DOMAIN_TITLES", source)
        for domain in domains:
            skill = (ROOT / "skills" / domain / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn(f"--domain {domain}", skill)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "domains").mkdir()
            (root / "domains/example.json").write_text(json.dumps({
                "id": "evm-audit-example",
                "name": "Example",
                "checklist_title": "Example Checklist",
                "description": "Example domain.",
                "surface_features": ["uses-example"],
                "related_domains": [],
                "always_screen": False,
                "screening_terms": ["example"],
                "required_context": [{"key": "example_context", "required": True, "description": "example context"}],
                "review_requirements": ["example review"],
                "trusted_absence_policy": {"requires_complete_scope": True, "allowed_evidence": ["scope"]},
            }), encoding="utf-8")
            write_outputs({"checks": []}, root)
            self.assertTrue((root / "skills/evm-audit-example/SKILL.md").exists())
            self.assertTrue((root / "skills/evm-audit-example/references/checklist.md").exists())

    def test_all_skills_live_under_skills_directory(self) -> None:
        skill_paths = sorted((ROOT / "skills").glob("evm-audit-*/SKILL.md"))
        self.assertEqual(len(skill_paths), 20)
        self.assertFalse(list(ROOT.glob("evm-audit-*")))
        for path in skill_paths:
            name = next(line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("name: "))
            self.assertEqual(path.parent.name, name.removeprefix("name: "))

    def test_no_evm_audit_skill_directories_remain_at_repository_root(self) -> None:
        self.assertEqual([], [path.name for path in ROOT.glob("evm-audit-*") if path.is_dir()])

    def test_generated_skill_paths_use_skills_directory(self) -> None:
        self.assertTrue((ROOT / "skills/evm-audit-master/SKILL.md").exists())
        self.assertEqual(19, len(list((ROOT / "skills").glob("evm-audit-*/references/checklist.md"))))
        self.assertFalse((ROOT / "evm-audit-master").exists())

    def test_suite_root_resolution_from_nested_skill(self) -> None:
        self.assertEqual(ROOT, find_suite_root(ROOT / "skills/evm-audit-master/SKILL.md"))

    def test_master_skill_can_resolve_data_domains_scripts(self) -> None:
        root = find_suite_root(ROOT / "skills/evm-audit-master/SKILL.md")
        for name in ("data", "domains", "scripts"):
            with self.subTest(name=name):
                self.assertTrue((root / name).is_dir())
        text = (ROOT / "skills/evm-audit-master/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("<suite-root>/scripts/", text)
        self.assertNotIn("../scripts/", text)

    def test_domain_skill_can_resolve_shared_runtime(self) -> None:
        skill = ROOT / "skills/evm-audit-erc20/SKILL.md"
        root = find_suite_root(skill)
        self.assertTrue((root / "data/canonical-checks.json").exists())
        self.assertTrue((root / "domains/erc20.json").exists())
        self.assertTrue((root / "scripts/select_checks.py").exists())
        text = skill.read_text(encoding="utf-8")
        self.assertIn("<suite-root>/skills/evm-audit-master/references/check-review-contract.runtime.md", text)

    def test_benchmark_path_is_development_benchmarks(self) -> None:
        source = (ROOT / "scripts/benchmark_routing.py").read_text(encoding="utf-8")
        self.assertIn('"development/benchmarks/routing"', source)
        self.assertTrue((ROOT / "development/benchmarks/routing").is_dir())
        self.assertFalse((ROOT / "benchmarks").exists())

    def test_readme_links_do_not_reference_old_skill_paths(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("skills/evm-audit-master", text)
        self.assertNotRegex(text, r"\]\(evm-audit-[^)]+\)")
        self.assertNotIn("](benchmarks/", text)
        self.assertNotIn("](scripts/migrations/", text)

    def test_knowledge_claims_and_forbidden_regressions(self) -> None:
        claims = load_json(ROOT / "tests/knowledge/claims.json")["claims"]
        for claim in claims:
            with self.subTest(claim=claim["id"]):
                check = self.by_id[claim["canonical_id"]]
                self.assertTrue(claim["evidence"])
                self.assertTrue(any(item["kind"] in {"official", "executable"} for item in claim["evidence"]))
                text = json.dumps(
                    {key: value for key, value in check.items() if key != "aliases"},
                    ensure_ascii=False,
                ).lower()
                runtime_text = "\n".join(
                    path.read_text(encoding="utf-8")
                    for path in (ROOT / "skills").glob("evm-audit-*/references/checklist.md")
                ).lower()
                for term in claim["required_terms"]:
                    self.assertIn(term.lower(), text)
                for term in claim["forbidden_terms"]:
                    self.assertNotIn(term.lower(), text)
                    self.assertNotIn(term.lower(), runtime_text)

    def test_erc4626_rounding_is_one_canonical_check(self) -> None:
        matches = [check for check in self.registry["checks"] if check["canonical_id"] == "ERC4626-ROUND-001"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["domains"], ["evm-audit-erc4626"])
        self.assertEqual(len(matches[0]["aliases"]), 6)

    def test_predicates_are_explicit_and_domain_independent(self) -> None:
        for check in self.registry["checks"]:
            with self.subTest(canonical_id=check["canonical_id"]):
                self.assertEqual(set(check["predicate"]), {"all_of", "any_of", "none_of"})
                routed = {feature for group in check["predicate"].values() for feature in group}
                self.assertEqual(check["features"], sorted(routed))
                self.assertFalse(any(feature.startswith("evm-audit-") for feature in routed))
                if not routed:
                    self.assertTrue(check.get("always_screen"))

    def test_fee_math_check_is_linked_to_erc4626_context(self) -> None:
        self.assertIn("EVM-ERC4626-043", self.by_id["EVM-MATH-007"]["related"])
        self.assertIn("EVM-MATH-007", self.by_id["EVM-ERC4626-043"]["related"])
        self.assertIn("grossAssets", self.by_id["EVM-MATH-007"]["description"])
        self.assertIn("netAssets", self.by_id["EVM-ERC4626-043"]["description"])

    def test_source_provenance_and_legacy_aliases_are_retained(self) -> None:
        source_ids = {
            source_id
            for check in self.registry["checks"]
            for alias in check["aliases"]
            for source_id in alias.get("source_ids", [])
        }
        self.assertEqual(len(source_ids), 218)
        self.assertEqual(sum(len(check["aliases"]) for check in self.registry["checks"]), 877)
        for path in (
            ROOT / "skills/evm-audit-master/references/auditmos-provenance.md",
            ROOT / "skills/evm-audit-master/references/drozer-lite-provenance.md",
        ):
            with self.subTest(path=path):
                self.assertTrue(path.exists())
                self.assertGreater(path.read_text(encoding="utf-8").count("| `"), 0)

    def test_feature_filter_selects_relevant_checks(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as feature_file:
            json.dump(self.v4_map({"uses-erc4626": "PRESENT", "uses-oracle": "ABSENT_CONFIRMED"}), feature_file)
            feature_file.flush()
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/select_checks.py",
                    "--feature-map",
                    feature_file.name,
                    "--target-root",
                    "tests/fixtures/recon/Empty.sol",
                    "--domain",
                    "evm-audit-erc4626",
                    "--format",
                    "json",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        selected = {entry["canonical_id"] for entry in payload["selected"]}
        self.assertIn("ERC4626-ROUND-001", selected)
        self.assertIn("EVM-ERC4626-003", selected)
        self.assertNotIn("EVM-TIME-001", selected)

    def test_only_curated_false_predicates_can_filter(self) -> None:
        feature_map = {"a": {"status": "ABSENT_CONFIRMED", "evidence": ["fixture: absent"]}}
        registry = {
            "checks": [
                {
                    "canonical_id": "TEST-INFERRED-001",
                    "title": "inferred",
                    "domains": ["evm-audit-general"],
                    "primary_domain": "evm-audit-general",
                    "predicate": {"all_of": ["a"], "any_of": [], "none_of": []},
                    "predicate_source": "inferred",
                },
                {
                    "canonical_id": "TEST-CURATED-001",
                    "title": "curated",
                    "domains": ["evm-audit-general"],
                    "primary_domain": "evm-audit-general",
                    "predicate": {"all_of": ["a"], "any_of": [], "none_of": []},
                    "predicate_source": "curated",
                },
            ]
        }
        manifest, _ = select(registry, feature_map, {"a"}, ["evm-audit-general"])
        self.assertEqual([entry["canonical_id"] for entry in manifest["selected"]], ["TEST-INFERRED-001"])
        self.assertEqual([entry["canonical_id"] for entry in manifest["filtered"]], ["TEST-CURATED-001"])

    def test_predicate_truth_table_is_conservative_for_unknown(self) -> None:
        feature_map = {
            "a": {"status": "PRESENT", "evidence": []},
            "b": {"status": "ABSENT_CONFIRMED", "evidence": []},
            "c": {"status": "UNKNOWN", "evidence": []},
        }
        self.assertEqual(evaluate_group(["a"], "all_of", feature_map), "TRUE")
        self.assertEqual(evaluate_group(["a", "b"], "all_of", feature_map), "FALSE")
        self.assertEqual(evaluate_group(["b", "c"], "any_of", feature_map), "UNKNOWN")
        self.assertEqual(evaluate_group(["b"], "none_of", feature_map), "TRUE")
        self.assertEqual(evaluate_group(["a", "c"], "none_of", feature_map), "FALSE")

    def test_feature_map_requires_evidence_for_confirmed_states(self) -> None:
        feature_map = self.v4_map({"uses-erc20": "PRESENT"})
        feature_map["features"]["uses-erc20"]["evidence"] = []
        with self.assertRaises(ValueError):
            normalize_feature_map(feature_map, self.feature_names, self.feature_policies, ROOT / "tests/fixtures/recon/Empty.sol")
        with self.assertRaises(ValueError):
            normalize_feature_map({"schema_version": 2, "features": {}}, self.feature_names, self.feature_policies, ROOT / "tests/fixtures/recon/Empty.sol")

    def test_feature_map_v4_rejects_legacy_cli_and_formats(self) -> None:
        help_result = subprocess.run([sys.executable, "scripts/select_checks.py", "--help"], cwd=ROOT, capture_output=True, text=True)
        self.assertNotIn("--features", help_result.stdout)
        for version in (1, 2):
            with self.assertRaises(ValueError):
                normalize_feature_map({"schema_version": version, "features": {}}, self.feature_names, self.feature_policies, ROOT / "tests/fixtures/recon/Empty.sol")

    def test_absence_policy_downgrades_dynamic_loop(self) -> None:
        feature_map = self.v4_map({"uses-dynamic-loop": "ABSENT_CONFIRMED"})
        normalized = normalize_feature_map(
            feature_map,
            self.feature_names,
            self.feature_policies,
            ROOT / "tests/fixtures/recon/Empty.sol",
        )
        self.assertEqual(normalized["uses-dynamic-loop"]["status"], "UNKNOWN")
        self.assertIn("never-confirm-absence", normalized["uses-dynamic-loop"]["reason"])

    def test_scope_digest_mismatch_rejects_selector(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as feature_file:
            json.dump(self.empty_feature_map, feature_file)
            feature_file.flush()
            result = subprocess.run(
                [sys.executable, "scripts/select_checks.py", "--feature-map", feature_file.name, "--target-root", str(ROOT), "--domain", "evm-audit-general"],
                cwd=ROOT, capture_output=True, text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_digest", result.stderr)

    def test_incomplete_compilation_rejects_fast_filter(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            feature_path = Path(temp_dir) / "feature-map.json"
            recon = subprocess.run(
                [sys.executable, "scripts/recon.py", "tests/fixtures/recon/Empty.sol", "--audit-root", ".", "--output", str(feature_path)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(recon.returncode, 0, recon.stderr)
            self.assertFalse(load_json(feature_path)["recon_context"]["compilation_complete"])
            result = subprocess.run(
                [sys.executable, "scripts/select_checks.py", "--feature-map", str(feature_path), "--target-root", str(ROOT), "--domain", "evm-audit-general"],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("compilation_complete", result.stderr)

    def test_selector_single_snapshot_writes_manifest_and_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            feature_path = temp / "feature-map.json"
            feature_path.write_text(json.dumps(self.empty_feature_map), encoding="utf-8")
            manifest_path, checks_path, context_path = temp / "manifest.json", temp / "screen.md", temp / "context.json"
            result = subprocess.run(
                [
                    sys.executable, "scripts/select_checks.py", "--feature-map", str(feature_path),
                    "--target-root", "tests/fixtures/recon/Empty.sol", "--domain", "evm-audit-erc20",
                    "--manifest-out", str(manifest_path), "--context-out", str(context_path),
                ],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = load_json(manifest_path)
            self.assertTrue(manifest_path.exists() and context_path.exists())
            render_result = subprocess.run(
                [sys.executable, "scripts/render_runtime.py", "--manifest", str(manifest_path), "--profile", "screen", "--output", str(checks_path)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(render_result.returncode, 0, render_result.stderr)
            runtime = checks_path.read_text(encoding="utf-8")
            for entry in manifest["selected"]:
                self.assertIn(f"[{entry['canonical_id']}]", runtime)
            self.assertNotIn("LIKELY_SAFE", runtime)

    def test_domain_gate_does_not_expand_related_domains(self) -> None:
        all_absent = {
            name: {"status": "ABSENT_CONFIRMED", "evidence": [{"kind": "manual", "location": "fixture", "reason": "scope"}]}
            for name in self.feature_names
        }
        selected, filtered = select(
            self.registry, all_absent, self.feature_names, None,
            {"source_digest": "benchmark"}, load_domains(ROOT), {}, None,
        )
        self.assertEqual([entry["domain"] for entry in selected["selected_domains"]], ["evm-audit-general"])
        self.assertIn("evm-audit-erc20", {entry["domain"] for entry in selected["filtered_domains"]})

    def test_environment_gate_filters_only_confirmed_mismatch(self) -> None:
        check = {
            "canonical_id": "TEST-ENV-001", "title": "environment", "domains": ["evm-audit-general"],
            "primary_domain": "evm-audit-general", "predicate": {"all_of": [], "any_of": [], "none_of": []},
            "predicate_source": "curated", "always_screen": True,
            "applicability": {"chain_ids": [], "chain_families": ["op-stack"], "execution_environments": ["ethereum-evm"], "compiler": ">=0.8.20", "evm_fork_from": "cancun", "evm_fork_until": None, "protocol_versions": []},
        }
        confirmed = {"chain_family": "arbitrum", "execution_environment": "ethereum-evm", "compiler_version": "0.8.24", "evm_fork": "cancun", "chain_id": None, "protocol_version": None, "environment_facts": {key: {"trust": "CONFIRMED", "value": value, "source": "fixture", "evidence": ["fixture"]} for key, value in {"chain_family": "arbitrum", "execution_environment": "ethereum-evm", "compiler_version": "0.8.24", "evm_fork": "cancun"}.items()}}
        self.assertEqual(evaluate_environment(check, confirmed)[0], "FALSE")
        self.assertEqual(evaluate_environment(check, {"environment_facts": {}})[0], "UNKNOWN")

    def test_zksync_environment_gate_keeps_native_and_interpreter_distinct(self) -> None:
        check = self.by_id["EVM-CHAIN-013"]
        native = {"chain_family": "zksync-era", "execution_environment": "eravm-native", "compiler_version": None, "evm_fork": None, "chain_id": None, "protocol_version": None, "environment_facts": {"chain_family": {"trust": "CONFIRMED", "value": "zksync-era", "source": "fixture", "evidence": ["fixture"]}, "execution_environment": {"trust": "CONFIRMED", "value": "eravm-native", "source": "fixture", "evidence": ["fixture"]}}}
        interpreter = {**native, "execution_environment": "zksync-evm-interpreter", "environment_facts": {**native["environment_facts"], "execution_environment": {"trust": "CONFIRMED", "value": "zksync-evm-interpreter", "source": "fixture", "evidence": ["fixture"]}}}
        other = {**native, "execution_environment": "ethereum-evm", "environment_facts": {**native["environment_facts"], "execution_environment": {"trust": "CONFIRMED", "value": "ethereum-evm", "source": "fixture", "evidence": ["fixture"]}}}
        self.assertEqual(evaluate_environment(check, native)[0], "TRUE")
        self.assertEqual(evaluate_environment(check, interpreter)[0], "TRUE")
        self.assertEqual(evaluate_environment(check, other)[0], "FALSE")

    def test_chain_id_populates_known_chain_family(self) -> None:
        context = audit_context(ROOT, self.registry, self.empty_feature_map["recon_context"], target_root=ROOT / "tests/fixtures/recon/Empty.sol", chain_id=8453)
        self.assertEqual(context["chain_family"], "op-stack")

    def test_environment_context_rejects_conflicts(self) -> None:
        recon = self.empty_feature_map["recon_context"]
        with self.assertRaises(ValueError):
            validate_environment_context(recon, chain_id=8453, chain_family="arbitrum")
        with self.assertRaises(ValueError):
            validate_environment_context(recon, chain_id=324, execution_environment="ethereum-evm")
        with self.assertRaises(ValueError):
            validate_environment_context(recon, compiler_version="0.8.20")

    def test_unknown_domain_is_deferred_and_blocks_clean_completion(self) -> None:
        raw = self.v4_map({})
        features = normalize_feature_map(raw, self.feature_names, self.feature_policies, ROOT / "tests/fixtures/recon/Empty.sol")
        manifest, _ = select(self.registry, features, self.feature_names, None, {"source_digest": raw["recon_context"]["source_digest"]}, load_domains(ROOT), {}, raw["recon_context"])
        self.assertTrue(manifest["deferred_domains"])
        self.assertNotIn("completion_gate", manifest)

    def test_audit_state_is_derived_from_screen_coverage(self) -> None:
        manifest = self.explicit_manifest()
        screen = screen_results_template(manifest)
        evidence = [{"kind": kind, "location": "fixture", "reason": "complete evidence"} for kind in ("scope", "inheritance", "interface", "deployment")]
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
        raw = self.v4_map({})
        features = normalize_feature_map(raw, self.feature_names, self.feature_policies, ROOT / "tests/fixtures/recon/Empty.sol")
        context = audit_context(ROOT, self.registry, raw["recon_context"], target_root=ROOT / "tests/fixtures/recon/Empty.sol", audit_timestamp="test")
        environment = {**{key: context[key] for key in ("chain_id", "chain_family", "execution_environment", "compiler_version", "evm_fork", "protocol_version")}, "environment_facts": context["environment_facts"]}
        config = load_domains(ROOT)
        key = config["evm-audit-general"]["required_context"][0]["key"]
        domain_context = {"domains": {"evm-audit-general": {key: {"status": "KNOWN", "value": "fixture", "evidence": ["fixture"]}}}}
        manifest, _ = select(self.registry, features, self.feature_names, None, context, config, environment, raw["recon_context"], domain_context)
        screen = screen_results_template(manifest)
        for result in screen["results"]:
            result["result"] = "NOT_APPLICABLE_CONFIRMED"
            result["evidence"] = [{"kind": kind, "location": "fixture", "reason": "complete evidence"} for kind in ("scope", "inheritance", "interface", "deployment")]
        resolution = {"schema_version": 1, "routing_snapshot_id": manifest["routing_snapshot_id"], "registry_sha256": manifest["audit_context"]["registry_sha256"], "source_digest": manifest["audit_context"]["source_digest"], "compilation_input_digest": manifest["audit_context"]["compilation_input_digest"], "domains": {entry["domain"]: {"status": "UNKNOWN", "scope_complete": False, "evidence": []} for entry in manifest["deferred_domains"]}}
        state = validate_run(ROOT, manifest, self.registry, screen, resolution, None, [])
        self.assertEqual(state["status"], "COMPLETE_WITH_UNRESOLVED_DOMAIN_ROUTING")

    def test_global_policies_do_not_enter_deep_cards(self) -> None:
        check = next(item for item in self.registry["checks"] if item["fp_policy"] == "global" and item["proof_policy"] == "global")
        self.assertEqual(check["false_positive_gates"], [])
        self.assertEqual(check["proof"], [])

    def test_candidate_is_promoted_from_screen_to_deep(self) -> None:
        raw = self.v4_map({})
        features = normalize_feature_map(raw, self.feature_names, self.feature_policies, ROOT / "tests/fixtures/recon/Empty.sol")
        context = audit_context(ROOT, self.registry, raw["recon_context"], target_root=ROOT / "tests/fixtures/recon/Empty.sol")
        environment = {**{key: context[key] for key in ("chain_id", "chain_family", "execution_environment", "compiler_version", "evm_fork", "protocol_version")}, "environment_facts": context["environment_facts"]}
        manifest, _ = select(self.registry, features, self.feature_names, ["evm-audit-general"], context, load_domains(ROOT), environment, raw["recon_context"])
        check = next(item for item in self.registry["checks"] if item["canonical_id"] == manifest["selected"][0]["canonical_id"])
        screen = render(manifest, self.registry, "screen", set())
        deep = render(manifest, self.registry, "deep", {check["canonical_id"]})
        self.assertIn("**Trigger:**", screen)
        self.assertIn("**Risk:**", deep)

    def test_jsonl_resume_reuses_only_matching_terminal_record(self) -> None:
        raw = self.v4_map({})
        features = normalize_feature_map(raw, self.feature_names, self.feature_policies, ROOT / "tests/fixtures/recon/Empty.sol")
        context = audit_context(ROOT, self.registry, raw["recon_context"], target_root=ROOT / "tests/fixtures/recon/Empty.sol")
        environment = {**{key: context[key] for key in ("chain_id", "chain_family", "execution_environment", "compiler_version", "evm_fork", "protocol_version")}, "environment_facts": context["environment_facts"]}
        manifest, _ = select(self.registry, features, self.feature_names, ["evm-audit-general"], context, load_domains(ROOT), environment, raw["recon_context"])
        check = next(item for item in self.registry["checks"] if item["canonical_id"] == manifest["selected"][0]["canonical_id"])
        entry = manifest["selected"][0]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review.jsonl"
            record = {"canonical_id": check["canonical_id"], "owner_domain": entry["owner_domain"], "routing_snapshot_id": manifest["routing_snapshot_id"], "check_body_hash": check_body_hash(check), "review_stage": "DEEP_REVIEW", "status": "REVIEWED_SAFE", "applicability": "APPLICABLE - fixture", "code_path": "fixture entry", "preconditions": "fixture state", "exploitability": "blocked by fixture guard", "impact": "N/A - invariant holds", "proof": "fixture invariant holds", "preserved_invariant": "fixture invariant", "evidence": [{"kind": "test", "location": "fixture", "reason": "test evidence"}]}
            append(path, manifest, record)
            self.assertIn(check["canonical_id"], resumable(path, manifest, self.registry, {check["canonical_id"]}))
            self.assertIn(check["canonical_id"], merge([path], manifest, self.registry, {check["canonical_id"]}))
            changed = copy.deepcopy(manifest)
            changed["audit_context"]["source_digest"] = "0" * 64
            self.assertEqual(resumable(path, changed, self.registry, {check["canonical_id"]}), {})

    def test_knowledge_dirty_is_tristate_with_build_info_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "build-info.json").write_text(json.dumps({"source_commit": "abc123"}), encoding="utf-8")
            commit, dirty = knowledge_state(root)
            self.assertEqual(commit, "abc123")
            self.assertIsNone(dirty)

    def test_knowledge_health_classifies_transient_http_as_unknown(self) -> None:
        with patch("scripts.check_knowledge_health.urlopen", side_effect=HTTPError("https://example.invalid", 429, "rate limited", {}, None)):
            self.assertEqual(source_status("https://example.invalid", 1), (None, "transient HTTP 429"))
        with patch("scripts.check_knowledge_health.urlopen", side_effect=HTTPError("https://example.invalid", 404, "gone", {}, None)):
            self.assertEqual(source_status("https://example.invalid", 1), (False, "HTTP 404"))

    def test_curated_predicates_have_select_and_filter_fixtures(self) -> None:
        fixtures = {item["canonical_id"]: item for item in load_json(ROOT / "tests/routing/curated-predicates.json")["fixtures"]}
        for canonical_id, check in ((key, value) for key, value in self.by_id.items() if value.get("predicate_source") == "curated"):
            fixture = fixtures[canonical_id]
            with self.subTest(canonical_id=canonical_id):
                selected_map = {feature: {"status": "PRESENT", "evidence": []} for feature in fixture["select_present"]}
                filtered_map = {feature: {"status": "PRESENT", "evidence": []} for feature in fixture["select_present"]}
                for feature in fixture["filter_absent"]:
                    filtered_map[feature] = {"status": "ABSENT_CONFIRMED", "evidence": []}
                self.assertNotEqual(evaluate_check(check, selected_map, set(self.feature_names))["result"], "FALSE")
                self.assertEqual(evaluate_check(check, filtered_map, set(self.feature_names))["result"], "FALSE")

    def test_routing_benchmarks_pass_recall_and_size_gates(self) -> None:
        result = subprocess.run([sys.executable, "scripts/benchmark_routing.py"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(result.stdout.strip().splitlines()), 21)

    def test_fee_forward_inverse_algebra_and_rounding(self) -> None:
        gross = 1_000
        fee_bps = 1_000
        denominator = 10_000
        net = gross * (denominator - fee_bps) // denominator
        shares = net // 2  # pricePerShare = 2
        solved_gross = (shares * 2 * denominator + (denominator - fee_bps) - 1) // (denominator - fee_bps)
        self.assertEqual(net, 900)
        self.assertEqual(shares, 450)
        self.assertEqual(solved_gross, gross)
        self.assertNotEqual(gross // (denominator - fee_bps), net)
        self.assertEqual(
            (123 * denominator + (denominator - 0) - 1) // (denominator - 0),
            123,
        )

    def test_screen_and_deep_render_from_manifest(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as feature_file:
            json.dump(self.v4_map({"uses-erc4626": "PRESENT"}), feature_file)
            feature_file.flush()
            manifest_path = Path(feature_file.name).with_name("manifest.json")
            selector = subprocess.run([sys.executable, "scripts/select_checks.py", "--feature-map", feature_file.name, "--target-root", "tests/fixtures/recon/Empty.sol", "--domain", "evm-audit-erc4626", "--manifest-out", str(manifest_path)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(selector.returncode, 0, selector.stderr)
            manifest = load_json(manifest_path)
        screen = render(manifest, self.registry, "screen", set())
        candidate = manifest["selected"][0]["canonical_id"]
        deep = render(manifest, self.registry, "deep", {candidate})
        self.assertIn("## [EVM-ERC4626-001]", screen)
        self.assertIn("**Detection:**", screen)
        self.assertNotIn("**Risk:**", screen)
        self.assertIn(f"## [{candidate}]", deep)
        self.assertIn("**Risk:**", deep)

    def test_screen_is_smaller_than_candidate_deep_view(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as feature_file:
            json.dump(self.v4_map({name: "PRESENT" for name in self.feature_names}), feature_file)
            feature_file.flush()
            manifest_path = Path(feature_file.name).with_name("manifest.json")
            selector = subprocess.run([sys.executable, "scripts/select_checks.py", "--feature-map", feature_file.name, "--target-root", "tests/fixtures/recon/Empty.sol", "--domain", "evm-audit-general", "--manifest-out", str(manifest_path)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(selector.returncode, 0, selector.stderr)
            manifest = load_json(manifest_path)
        screen = render(manifest, self.registry, "screen", set())
        deep = render(manifest, self.registry, "deep", {entry["canonical_id"] for entry in manifest["selected"]})
        self.assertLess(len(screen), len(deep))

    def test_routing_manifest_covers_scope_and_shared_owner(self) -> None:
        raw_map = self.v4_map({name: "PRESENT" for name in self.feature_names})
        target_root = ROOT / "tests/fixtures/recon/Empty.sol"
        feature_map = normalize_feature_map(raw_map, self.feature_names, self.feature_policies, target_root)
        context = audit_context(ROOT, self.registry, raw_map["recon_context"], target_root=target_root)
        manifest, _ = select(
            self.registry,
            feature_map,
            self.feature_names,
            ["evm-audit-general", "evm-audit-precision-math"],
            context,
            load_domains(ROOT),
            {},
            raw_map["recon_context"],
        )
        self.assertEqual(manifest["schema_version"], 6)
        self.assertTrue(manifest["immutable"])
        self.assertIn("target_repo_commit", manifest["audit_context"])
        shared = next(item for item in manifest["selected"] + manifest["filtered"] if item["canonical_id"] == "EVM-TIME-001")
        self.assertEqual(shared["owner_domain"], "evm-audit-precision-math")
        validate_manifest(ROOT, manifest, self.registry)

    def test_recon_uses_slither_evidence_and_confirms_supported_absence(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/recon.py",
                "tests/fixtures/recon/ReconFixture.sol",
                "--solc",
                str(Path("/usr/local/bin/solc")) if Path("/usr/local/bin/solc").exists() else "solc",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        feature_map = json.loads(result.stdout)["features"]
        for feature in (
            "uses-assembly",
            "uses-create2",
            "uses-delegatecall",
            "uses-dynamic-loop",
            "uses-erc20",
            "uses-erc4626",
            "uses-merkle",
            "uses-msg-value",
            "uses-oracle",
            "uses-payable",
            "uses-proxy",
            "uses-signature",
        ):
            with self.subTest(feature=feature):
                self.assertEqual(feature_map[feature]["status"], "PRESENT")
                self.assertTrue(feature_map[feature]["evidence"])
        self.assertEqual(feature_map["uses-flash-loan"]["status"], "UNKNOWN")
        self.assertEqual(feature_map["uses-arbitrary-external-call"]["status"], "UNKNOWN")
        self.assertEqual(feature_map["uses-access-control"]["status"], "PRESENT")

    def test_recon_only_confirms_structurally_safe_absence(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/recon.py", "tests/fixtures/recon/Empty.sol", "--solc", str(Path("/usr/local/bin/solc")) if Path("/usr/local/bin/solc").exists() else "solc"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        features = json.loads(result.stdout)["features"]
        for feature in ("uses-assembly", "uses-msg-value", "uses-payable"):
            self.assertEqual(features[feature]["status"], "ABSENT_CONFIRMED")
        for feature in ("uses-dynamic-loop", "uses-delegatecall", "uses-proxy", "uses-oracle", "uses-signature", "uses-reentrancy-callback", "uses-arbitrary-external-call", "uses-multicall"):
            self.assertEqual(features[feature]["status"], "UNKNOWN")

    def test_routing_manifest_rejects_invalid_shape(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as manifest_file:
            json.dump({
                "schema_version": 1,
                "stage": "FAST_FILTER",
                "scope": {"domains": ["evm-audit-precision-math"], "candidate_count": 1},
                "feature_map": {"schema_version": 99, "features": {}},
                "selected_count": 0,
                "filtered_count": 0,
                "selected": [],
                "filtered": [],
            }, manifest_file)
            manifest_file.flush()
            with self.assertRaises(ValueError):
                validate_manifest(ROOT, load_json(Path(manifest_file.name)), self.registry)

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

    def test_knowledge_claim_coverage_is_complete(self) -> None:
        self.assertEqual(validate_knowledge_claims(ROOT), [])

    def test_freshness_health_has_no_unverified_versioned_knowledge(self) -> None:
        report = knowledge_health(ROOT, today=date(2026, 8, 30), check_links=False, timeout=1)
        self.assertEqual(report["error_count"], 0)
        self.assertFalse(any(item["kind"] == "unverified-freshness" for item in report["findings"]))

    def test_review_ledger_enforces_status_evidence_gate(self) -> None:
        raw = self.v4_map({})
        features = normalize_feature_map(raw, self.feature_names, self.feature_policies, ROOT / "tests/fixtures/recon/Empty.sol")
        context = audit_context(ROOT, self.registry, raw["recon_context"], target_root=ROOT / "tests/fixtures/recon/Empty.sol")
        environment = {**{key: context[key] for key in ("chain_id", "chain_family", "execution_environment", "compiler_version", "evm_fork", "protocol_version")}, "environment_facts": context["environment_facts"]}
        manifest, _ = select(self.registry, features, self.feature_names, ["evm-audit-general"], context, load_domains(ROOT), environment, raw["recon_context"])
        entry = manifest["selected"][0]
        check = next(item for item in self.registry["checks"] if item["canonical_id"] == entry["canonical_id"])
        base = {"schema_version": 2, "record_type": "review", "canonical_id": entry["canonical_id"], "owner_domain": entry["owner_domain"], "routing_snapshot_id": manifest["routing_snapshot_id"], "check_body_hash": check_body_hash(check), "review_stage": "PROOF", "applicability": "APPLICABLE - path exists", "code_path": "entry() -> call()", "preconditions": "attacker controls target", "exploitability": "attacker invokes entry", "impact": "accounting accepts false success", "proof": "test demonstrates false success", "evidence": [{"kind": "test", "location": "fixture", "reason": "executable evidence"}]}
        base.update({key: manifest["audit_context"][key] for key in ("registry_sha256", "source_digest", "compilation_input_digest")})
        suspicious = {**base, "status": "SUSPICIOUS", "unresolved_reason": "missing alternate path", "code_path": "UNRESOLVED - alternate path pending", "severity": "High"}
        self.assertTrue(any("not valid" in error or "additional" in error for error in validate_record(suspicious, manifest, self.registry, {entry["canonical_id"]})))
        confirmed = {**base, "status": "CONFIRMED"}
        self.assertEqual(validate_record(confirmed, manifest, self.registry, {entry["canonical_id"]}), [])
        incomplete = {key: value for key, value in confirmed.items() if key != "proof"}
        self.assertTrue(any("missing review fields" in error or "not valid" in error for error in validate_record(incomplete, manifest, self.registry, {entry["canonical_id"]})))


if __name__ == "__main__":
    unittest.main()
