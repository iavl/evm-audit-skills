#!/usr/bin/env python3
"""Tests for Slither-backed reconnaissance and compilation safety."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.recon import DETECTOR_IMPLEMENTATIONS, SAFE_ABSENCE_IMPLEMENTATIONS, load_detector_config

from helpers import ROOT, load_json


def run_recon(target: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    solc = shutil.which("solc") or "solc"
    return subprocess.run(
        [sys.executable, "scripts/recon.py", str(target), "--solc", solc, *extra],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


class ReconTests(unittest.TestCase):
    def test_detector_registry_matches_python_implementations(self) -> None:
        features = set(load_json(ROOT / "data/features.json")["features"])
        detectors = load_detector_config(ROOT, features)
        self.assertTrue(detectors)
        for feature, detector in detectors.items():
            with self.subTest(feature=feature):
                if detector["mode"] == "structural":
                    self.assertIn(detector["implementation"], DETECTOR_IMPLEMENTATIONS)
                    if detector["absence_capable"]:
                        self.assertIn(detector["implementation"], SAFE_ABSENCE_IMPLEMENTATIONS)
                else:
                    self.assertTrue(detector["terms"])

    def test_recon_uses_slither_evidence_and_confirms_supported_absence(self) -> None:
        result = run_recon(ROOT / "tests/fixtures/recon/ReconFixture.sol")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["recon_context"]["recon_quality"]["compilation_provenance"],
            "EXACT_COMPILATION_CLOSURE",
        )
        feature_map = payload["features"]
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
        result = run_recon(ROOT / "tests/fixtures/recon/Empty.sol")
        self.assertEqual(result.returncode, 0, result.stderr)
        features = json.loads(result.stdout)["features"]
        for feature in ("uses-assembly", "uses-msg-value", "uses-payable"):
            self.assertEqual(features[feature]["status"], "ABSENT_CONFIRMED")
        for feature in (
            "uses-dynamic-loop",
            "uses-delegatecall",
            "uses-proxy",
            "uses-oracle",
            "uses-signature",
            "uses-reentrancy-callback",
            "uses-arbitrary-external-call",
            "uses-multicall",
        ):
            self.assertEqual(features[feature]["status"], "UNKNOWN")

    def test_incomplete_compilation_uses_conservative_degraded_routing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            feature_path = Path(temp_dir) / "feature-map.json"
            recon = run_recon(
                ROOT / "tests/fixtures/recon/Empty.sol",
                "--audit-root",
                ".",
                "--output",
                str(feature_path),
            )
            self.assertEqual(recon.returncode, 0, recon.stderr)
            self.assertFalse(load_json(feature_path)["recon_context"]["compilation_complete"])
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/select_checks.py",
                    "--feature-map",
                    str(feature_path),
                    "--target-root",
                    str(ROOT),
                    "--domain",
                    "evm-audit-general",
                    "--manifest-out",
                    str(Path(temp_dir) / "manifest.json"),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = load_json(Path(temp_dir) / "manifest.json")
            self.assertEqual(
                manifest["feature_map"]["recon_context"]["recon_quality"]["mode"],
                "CONSERVATIVE_DEGRADED",
            )
            self.assertEqual(manifest["filtered_count"], 0)

            strict = subprocess.run(
                [
                    sys.executable,
                    "scripts/select_checks.py",
                    "--feature-map",
                    str(feature_path),
                    "--target-root",
                    str(ROOT),
                    "--domain",
                    "evm-audit-general",
                    "--require-complete-compilation",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(strict.returncode, 0)
            self.assertIn("complete compilation", strict.stderr)


if __name__ == "__main__":
    unittest.main()
