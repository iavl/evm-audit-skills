#!/usr/bin/env python3
"""Regression tests for runtime progress output and machine-output boundaries."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import EMPTY_TARGET, ROOT, synthetic_feature_map


class ObservabilityTests(unittest.TestCase):
    def run_selector(self, *extra: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            feature_map = Path(directory) / "feature-map.json"
            feature_map.write_text(json.dumps(synthetic_feature_map()), encoding="utf-8")
            return subprocess.run(
                [
                    sys.executable,
                    "scripts/select_checks.py",
                    "--feature-map",
                    str(feature_map),
                    "--target-root",
                    str(EMPTY_TARGET),
                    "--domain",
                    "evm-audit-general",
                    "--format",
                    "json",
                    *extra,
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

    def test_json_stdout_is_not_polluted_by_banner(self) -> None:
        result = self.run_selector()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsInstance(json.loads(result.stdout), dict)
        self.assertNotIn("EVM AUDIT ::", result.stdout)

    def test_banner_is_written_to_stderr(self) -> None:
        result = self.run_selector()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("EVM AUDIT :: ROUTING", result.stderr)
        self.assertIn("Routing snapshot created:", result.stderr)

    def test_quiet_suppresses_banner(self) -> None:
        result = self.run_selector("--quiet")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIsInstance(json.loads(result.stdout), dict)

    def test_quiet_does_not_suppress_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/select_checks.py",
                    "--feature-map",
                    str(Path(directory) / "missing-feature-map.json"),
                    "--target-root",
                    str(EMPTY_TARGET),
                    "--format",
                    "json",
                    "--quiet",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ERROR:", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_verbose_adds_domain_details_without_touching_stdout(self) -> None:
        result = self.run_selector("--verbose")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[DOMAIN] evm-audit-general", result.stderr)
        self.assertIsInstance(json.loads(result.stdout), dict)


if __name__ == "__main__":
    unittest.main()
