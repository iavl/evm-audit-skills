#!/usr/bin/env python3
"""Regression tests for the canonical checklist and routing workflow."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.validate_checklists import validate_review_ledger_text


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
                self.assertTrue(claim["source_url"].startswith("https://"))
                check = self.by_id[claim["canonical_id"]]
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

    def test_source_provenance_and_legacy_aliases_are_retained(self) -> None:
        source_ids = {
            source_id
            for check in self.registry["checks"]
            for alias in check["aliases"]
            for source_id in alias.get("source_ids", [])
        }
        self.assertEqual(len(source_ids), 218)
        self.assertEqual(sum(len(check["aliases"]) for check in self.registry["checks"]), 876)
        for path in (
            ROOT / "evm-audit-master/references/auditmos-provenance.md",
            ROOT / "evm-audit-master/references/drozer-lite-provenance.md",
        ):
            with self.subTest(path=path):
                self.assertTrue(path.exists())
                self.assertGreater(path.read_text(encoding="utf-8").count("| `"), 0)

    def test_feature_filter_selects_relevant_checks(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/select_checks.py",
                "--features",
                "uses-erc4626",
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

    def test_review_contract_keeps_suspicious_out_of_severity(self) -> None:
        text = (ROOT / "evm-audit-master/references/check-review-contract.md").read_text(encoding="utf-8")
        self.assertIn("`SUSPICIOUS`", text)
        self.assertIn("Do not assign severity", text)
        self.assertIn("`CONFIRMED`", text)
        self.assertIn("runnable PoC", text)

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
