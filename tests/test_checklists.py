#!/usr/bin/env python3
"""Regression tests for the canonical checklist and routing workflow."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.select_checks import evaluate_group, normalize_feature_map, select, vocabulary
from scripts.validate_checklists import validate_knowledge_claims, validate_review_ledger_text, validate_routing_manifest


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ChecklistTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_json(ROOT / "data" / "canonical-checks.json")
        cls.by_id = {check["canonical_id"]: check for check in cls.registry["checks"]}

    def test_generated_markdown_is_current(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/generate_checklists.py", "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

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
                    for path in ROOT.glob("evm-audit-*/references/checklist.md")
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
            ROOT / "evm-audit-master/references/auditmos-provenance.md",
            ROOT / "evm-audit-master/references/drozer-lite-provenance.md",
        ):
            with self.subTest(path=path):
                self.assertTrue(path.exists())
                self.assertGreater(path.read_text(encoding="utf-8").count("| `"), 0)

    def test_feature_filter_selects_relevant_checks(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as feature_file:
            json.dump({
                "schema_version": 1,
                "features": {
                    "uses-erc4626": {"status": "PRESENT", "evidence": ["Vault.sol:1"]},
                    "uses-math": {"status": "ABSENT_CONFIRMED", "evidence": ["scope: no arithmetic conversion"]},
                    "uses-oracle": {"status": "ABSENT_CONFIRMED", "evidence": ["scope: no price feed"]},
                },
            }, feature_file)
            feature_file.flush()
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/select_checks.py",
                    "--feature-map",
                    feature_file.name,
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
        self.assertNotIn("EVM-TIME-001", selected)
        self.assertIn("EVM-ERC4626-003", selected)

    def test_predicate_truth_table_is_conservative_for_unknown(self) -> None:
        feature_map = normalize_feature_map({
            "schema_version": 1,
            "features": {
                "a": {"status": "PRESENT", "evidence": ["A.sol:1"]},
                "b": {"status": "ABSENT_CONFIRMED", "evidence": ["scope: absent"]},
                "c": {"status": "UNKNOWN"},
            },
        }, {"a", "b", "c"})
        self.assertEqual(evaluate_group(["a"], "all_of", feature_map), "TRUE")
        self.assertEqual(evaluate_group(["a", "b"], "all_of", feature_map), "FALSE")
        self.assertEqual(evaluate_group(["b", "c"], "any_of", feature_map), "UNKNOWN")
        self.assertEqual(evaluate_group(["b"], "none_of", feature_map), "TRUE")
        self.assertEqual(evaluate_group(["a", "c"], "none_of", feature_map), "FALSE")

    def test_feature_map_requires_evidence_for_confirmed_states(self) -> None:
        with self.assertRaises(ValueError):
            normalize_feature_map({
                "schema_version": 1,
                "features": {"a": {"status": "ABSENT_CONFIRMED"}},
            }, {"a"})

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

    def test_selected_markdown_contains_bodies_only(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as feature_file:
            json.dump({
                "schema_version": 1,
                "features": {
                    "uses-erc4626": {"status": "PRESENT", "evidence": ["Vault.sol:1"]},
                    "uses-math": {"status": "ABSENT_CONFIRMED", "evidence": ["scope: no arithmetic conversion"]},
                },
            }, feature_file)
            feature_file.flush()
            result = subprocess.run(
                [sys.executable, "scripts/select_checks.py", "--feature-map", feature_file.name, "--domain", "evm-audit-erc4626", "--emit-checks", "--format", "markdown"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("## [EVM-ERC4626-001]", result.stdout)
        self.assertIn("**Detection:**", result.stdout)
        self.assertNotIn("## [EVM-TIME-001]", result.stdout)

    def test_selected_markdown_is_smaller_than_full_domain_view(self) -> None:
        feature_data = load_json(ROOT / "data/features.json")
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as feature_file:
            json.dump({
                "schema_version": 1,
                "features": {
                    name: {"status": "ABSENT_CONFIRMED", "evidence": ["scope: explicit fixture absence"]}
                    for name in feature_data["features"]
                },
            }, feature_file)
            feature_file.flush()
            result = subprocess.run(
                [sys.executable, "scripts/select_checks.py", "--feature-map", feature_file.name, "--domain", "evm-audit-general", "--emit-checks", "--format", "markdown"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLess(len(result.stdout), (ROOT / "evm-audit-general/references/checklist.md").stat().st_size)

    def test_routing_manifest_covers_scope_and_shared_owner(self) -> None:
        feature_data = load_json(ROOT / "data/features.json")
        names, _ = vocabulary(feature_data)
        feature_map = {
            name: {
                "status": "PRESENT" if name == "uses-math" else "ABSENT_CONFIRMED",
                "evidence": ["fixture: explicit scope evidence"],
            }
            for name in names
        }
        manifest, _ = select(
            self.registry,
            feature_map,
            names,
            ["evm-audit-general", "evm-audit-precision-math"],
        )
        shared = next(item for item in manifest["selected"] + manifest["filtered"] if item["canonical_id"] == "EVM-TIME-001")
        self.assertEqual(shared["owner_domain"], "evm-audit-precision-math")
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as manifest_file:
            json.dump(manifest, manifest_file)
            manifest_file.flush()
            with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8") as ledger_file:
                for entry in manifest["selected"]:
                    ledger_file.write(
                        f"### {entry['canonical_id']} — Example\n"
                        "- **Review stage**: DEEP_REVIEW\n"
                        "- **Routing basis**: fixture\n"
                        "- **Status**: REVIEWED_SAFE\n"
                        "- **Applicability**: APPLICABLE — fixture\n"
                        "- **Code path**: fixture\n"
                        "- **Preconditions**: fixture\n"
                        "- **Exploitability**: fixture\n"
                        "- **Impact**: N/A — invariant holds\n"
                        "- **PoC / Invariant violation**: fixture invariant holds\n"
                        "- **Evidence**: fixture\n\n"
                    )
                ledger_file.flush()
                self.assertEqual(validate_routing_manifest(ROOT, Path(manifest_file.name), [Path(ledger_file.name)]), [])

    def test_routing_manifest_reports_invalid_feature_map_without_crashing(self) -> None:
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
            errors = validate_routing_manifest(ROOT, Path(manifest_file.name))
        self.assertTrue(any("invalid feature_map" in error for error in errors))

    def test_domain_skills_embed_the_evidence_gate(self) -> None:
        for skill_path in sorted(ROOT.glob("evm-audit-*/SKILL.md")):
            if skill_path.parent.name == "evm-audit-master":
                continue
            text = skill_path.read_text(encoding="utf-8")
            with self.subTest(skill=skill_path.parent.name):
                self.assertIn("## Audit Contract", text)
                self.assertIn("check-review-contract.md", text)
                self.assertIn("Pattern matches are candidates, not findings", text)
                self.assertIn("reachable path", text)
                self.assertIn("tri-state predicate router", text)
                self.assertIn("Do not load `../data/canonical-checks.json`", text)

    def test_review_contract_keeps_suspicious_out_of_severity(self) -> None:
        text = (ROOT / "evm-audit-master/references/check-review-contract.md").read_text(encoding="utf-8")
        self.assertIn("`SUSPICIOUS`", text)
        self.assertIn("Do not assign severity", text)
        self.assertIn("`CONFIRMED`", text)
        self.assertIn("runnable PoC", text)

    def test_knowledge_claim_coverage_is_complete(self) -> None:
        self.assertEqual(validate_knowledge_claims(ROOT), [])

    def test_review_ledger_enforces_status_evidence_gate(self) -> None:
        suspicious = """### EVM-GEN-001 — Example
- **Review stage**: DEEP_REVIEW
- **Routing basis**: uses-low-level-call
- **Status**: SUSPICIOUS
- **Applicability**: APPLICABLE — call path exists
- **Code path**: UNRESOLVED — alternate path pending
- **Preconditions**: UNRESOLVED — missing deployment state
- **Exploitability**: UNRESOLVED — missing proof
- **Impact**: UNRESOLVED — missing bound
- **PoC / Invariant violation**: UNRESOLVED — test unavailable
- **Evidence**: source:line
- **Severity**: High
"""
        self.assertTrue(any("assigns severity" in error for error in validate_review_ledger_text(suspicious)))

        confirmed = """### EVM-GEN-001 — Example
- **Review stage**: PROOF
- **Routing basis**: uses-low-level-call
- **Status**: CONFIRMED
- **Applicability**: APPLICABLE — call path exists
- **Code path**: entry() → call()
- **Preconditions**: attacker controls target address
- **Exploitability**: attacker calls entry() with a no-code target
- **Impact**: accounting accepts a false success
- **PoC / Invariant violation**: Foundry test demonstrates success=true with empty returndata
- **Evidence**: test/Example.t.sol:42
"""
        self.assertEqual(validate_review_ledger_text(confirmed, {"EVM-GEN-001"}), [])

        incomplete = confirmed.replace("- **PoC / Invariant violation**: Foundry test demonstrates success=true with empty returndata\n", "")
        self.assertTrue(any("missing deep-review fields" in error for error in validate_review_ledger_text(incomplete)))


if __name__ == "__main__":
    unittest.main()
