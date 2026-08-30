#!/usr/bin/env python3
"""Smoke-test the supported suite installation layout."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_suite_symlinks_resolve_shared_runtime_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="evm-audit-suite-") as temp_dir:
            skills_root = Path(temp_dir) / "skills"
            suite = skills_root / "evm-audit-skills"
            shutil.copytree(ROOT, suite, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
            skills_root.mkdir(exist_ok=True)
            for domain in sorted(suite.glob("evm-audit-*")):
                (skills_root / domain.name).symlink_to(domain, target_is_directory=True)

            for link in sorted(skills_root.glob("evm-audit-*/SKILL.md")):
                resolved = link.resolve()
                self.assertTrue(resolved.exists(), link)
                text = resolved.read_text(encoding="utf-8")
                if resolved.parent.name == "evm-audit-master":
                    self.assertTrue((resolved.parent.parent / "data" / "features.json").exists())
                    self.assertTrue((resolved.parent.parent / "scripts" / "select_checks.py").exists())
                else:
                    self.assertTrue((resolved.parent.parent.parent / "evm-audit-master" / "references" / "check-review-contract.runtime.md").exists())
                    self.assertNotIn("use the canonical IDs from `../data/canonical-checks.json`", text)

            feature_map = suite / "feature-map.json"
            recon = subprocess.run(
                [sys.executable, "scripts/recon.py", "tests/fixtures/recon/Empty.sol", "--output", str(feature_map)],
                cwd=suite,
                capture_output=True,
                text=True,
            )
            self.assertEqual(recon.returncode, 0, recon.stderr)
            result = subprocess.run(
                [sys.executable, "scripts/select_checks.py", "--feature-map", str(feature_map), "--target-root", "tests/fixtures/recon/Empty.sol", "--domain", "evm-audit-erc4626", "--format", "json"],
                cwd=suite,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
