#!/usr/bin/env python3
"""Tests for the deterministic audit-run controller."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import EMPTY_TARGET, ROOT


class AuditRunTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *arguments],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    @staticmethod
    def read(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_controller_advances_templates_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            result = self.run_cli(
                "scripts/audit_run.py",
                "init",
                str(EMPTY_TARGET),
                "--run-dir",
                str(run_dir),
                "--audit-root",
                str(EMPTY_TARGET),
                "--domain",
                "evm-audit-general",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("DOMAIN_CONTEXT", result.stdout)
            result = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("DOMAIN_CONTEXT", result.stdout)
            context_path = run_dir / "reviews/domain-context.json"
            context = self.read(context_path)
            for requirements in context["domains"].values():
                for item in requirements.values():
                    item.update(
                        status="KNOWN",
                        value="fixture",
                        evidence=[{"kind": "scope", "location": "fixture", "reason": "known context"}],
                    )
            context_path.write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")

            result = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            screen_path = run_dir / "reviews/screen-results.json"
            screen = self.read(screen_path)
            for item in screen["results"]:
                item.update(
                    result="NOT_APPLICABLE_CONFIRMED",
                    scope_complete=True,
                    evidence=[
                        {"kind": "scope", "location": "fixture", "reason": "complete scope"},
                        {"kind": "source", "location": "fixture", "reason": "trigger absent"},
                    ],
                )
            screen_path.write_text(json.dumps(screen, indent=2) + "\n", encoding="utf-8")

            result = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("COMPLETE_CLEAN", result.stdout)
            result = self.run_cli("scripts/audit_run.py", "report", "--run-dir", str(run_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            report = (run_dir / "AUDIT-REPORT.md").read_text(encoding="utf-8")
            self.assertIn("COMPLETE_CLEAN", report)
            self.assertTrue((run_dir / "issue-candidates.json").exists())


if __name__ == "__main__":
    unittest.main()
