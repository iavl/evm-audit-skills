#!/usr/bin/env python3
"""Knowledge-content and knowledge-health behavior tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.check_knowledge_health import knowledge_health, source_status
from scripts.select_checks import knowledge_state

from helpers import ROOT, load_json, suite_inputs


class KnowledgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry, _, _ = suite_inputs()
        cls.by_id = {check["canonical_id"]: check for check in cls.registry["checks"]}

    def test_knowledge_claims_and_forbidden_regressions(self) -> None:
        claims = load_json(ROOT / "tests/knowledge/claims.json")["claims"]
        runtime_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "skills").glob("evm-audit-*/references/checklist.md")
        ).lower()
        for claim in claims:
            with self.subTest(claim=claim["id"]):
                check = self.by_id[claim["canonical_id"]]
                self.assertTrue(claim["evidence"])
                self.assertTrue(any(item["kind"] in {"official", "executable"} for item in claim["evidence"]))
                text = json.dumps(
                    {key: value for key, value in check.items() if key != "aliases"},
                    ensure_ascii=False,
                ).lower()
                for term in claim["required_terms"]:
                    self.assertIn(term.lower(), text)
                for term in claim["forbidden_terms"]:
                    self.assertNotIn(term.lower(), text)
                    self.assertNotIn(term.lower(), runtime_text)

    def test_erc4626_rounding_is_one_canonical_check(self) -> None:
        matches = [
            check for check in self.registry["checks"] if check["canonical_id"] == "ERC4626-ROUND-001"
        ]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["domains"], ["evm-audit-erc4626"])
        self.assertTrue(matches[0]["aliases"])

    def test_fee_math_check_is_linked_to_erc4626_context(self) -> None:
        self.assertIn("EVM-ERC4626-043", self.by_id["EVM-MATH-007"]["related"])
        self.assertIn("EVM-MATH-007", self.by_id["EVM-ERC4626-043"]["related"])
        self.assertIn("grossAssets", self.by_id["EVM-MATH-007"]["description"])
        self.assertIn("netAssets", self.by_id["EVM-ERC4626-043"]["description"])

    def test_fee_forward_inverse_algebra_and_rounding(self) -> None:
        gross = 1_000
        fee_bps = 1_000
        denominator = 10_000
        net = gross * (denominator - fee_bps) // denominator
        shares = net // 2
        solved_gross = (shares * 2 * denominator + (denominator - fee_bps) - 1) // (denominator - fee_bps)
        self.assertEqual(net, 900)
        self.assertEqual(shares, 450)
        self.assertEqual(solved_gross, gross)
        self.assertNotEqual(gross // (denominator - fee_bps), net)
        self.assertEqual((123 * denominator + (denominator - 0) - 1) // (denominator - 0), 123)

    def test_knowledge_dirty_is_tristate_with_build_info_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "build-info.json").write_text(json.dumps({"source_commit": "abc123"}), encoding="utf-8")
            commit, dirty = knowledge_state(root)
            self.assertEqual(commit, "abc123")
            self.assertIsNone(dirty)

    def test_knowledge_health_classifies_transient_http_as_unknown(self) -> None:
        with patch(
            "scripts.check_knowledge_health.urlopen",
            side_effect=HTTPError("https://example.invalid", 429, "rate limited", {}, None),
        ):
            self.assertEqual(source_status("https://example.invalid", 1), (None, "transient HTTP 429"))
        with patch(
            "scripts.check_knowledge_health.urlopen",
            side_effect=HTTPError("https://example.invalid", 404, "gone", {}, None),
        ):
            self.assertEqual(source_status("https://example.invalid", 1), (False, "HTTP 404"))

    def test_knowledge_health_freshness_uses_synthetic_registry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "data").mkdir()
            (root / "data/canonical-checks.json").write_text(
                json.dumps(
                    {
                        "checks": [
                            {"canonical_id": "VALID", "freshness": "versioned", "verified_at": "2026-08-30"},
                            {"canonical_id": "EXPIRED", "freshness": "versioned", "verified_at": "2025-01-01"},
                            {"canonical_id": "MISSING", "freshness": "time-sensitive"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            report = knowledge_health(root, today=date(2026, 8, 31), check_links=False, timeout=1)
        findings = {(item["canonical_id"], item["kind"]) for item in report["findings"]}
        self.assertNotIn(("VALID", "stale-knowledge"), findings)
        self.assertIn(("EXPIRED", "stale-knowledge"), findings)
        self.assertIn(("MISSING", "unverified-freshness"), findings)
        self.assertGreater(report["error_count"], 0)


if __name__ == "__main__":
    unittest.main()
