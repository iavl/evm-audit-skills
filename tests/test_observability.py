#!/usr/bin/env python3
"""Regression tests for controller progress and machine-output boundaries."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from helpers import EMPTY_TARGET, ROOT
from scripts.audit_run import _log_current_state, _run
from scripts.runtime_log import configure


class ObservabilityTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *arguments],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    def init_run(self, run_dir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return self.run_cli(
            "scripts/audit_run.py",
            "init",
            str(EMPTY_TARGET),
            "--run-dir",
            str(run_dir),
            "--audit-root",
            str(EMPTY_TARGET),
            "--domain",
            "evm-audit-general",
            *extra,
        )

    def test_default_controller_output_is_compact_json_plus_progress(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.init_run(Path(directory) / "run")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["next"]["stage"], "DOMAIN_CONTEXT")
        self.assertIn("EVM AUDIT :: RECON", result.stderr)
        self.assertIn("EVM AUDIT :: ROUTING", result.stderr)
        self.assertIn("Next required stage: DOMAIN CONTEXT", result.stderr)
        self.assertEqual(result.stderr.count("EVM AUDIT :: RECON"), 1)
        self.assertEqual(result.stderr.count("EVM AUDIT :: ROUTING"), 1)
        self.assertNotIn("Feature Map ready", result.stderr)
        self.assertIsInstance(payload, dict)

    def test_quiet_keeps_json_and_errors_visible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.init_run(Path(directory) / "run", "--quiet")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIsInstance(json.loads(result.stdout), dict)
            self.assertEqual(result.stderr, "")

            missing = self.run_cli(
                "scripts/audit_run.py",
                "status",
                "--run-dir",
                str(Path(directory) / "missing"),
                "--quiet",
            )
        self.assertNotEqual(missing.returncode, 0)
        self.assertEqual(missing.stdout, "")
        self.assertIn("ERROR:", missing.stderr)

    def test_verbose_forwards_low_level_diagnostics_without_polluting_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.init_run(Path(directory) / "run", "--verbose")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Feature Map ready", result.stderr)
        self.assertIn("[DOMAIN] evm-audit-general", result.stderr)
        self.assertIsInstance(json.loads(result.stdout), dict)

    def test_child_stderr_is_hidden_by_default_and_forwarded_in_verbose(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "child.py").write_text(
                "import sys\n"
                "print('child diagnostic', file=sys.stderr)\n"
                "print('{\"ok\": true}')\n",
                encoding="utf-8",
            )

            default_stderr = io.StringIO()
            with redirect_stderr(default_stderr):
                result = _run(root, "child.py", [])
            self.assertEqual(result.stdout.strip(), '{"ok": true}')
            self.assertNotIn("child diagnostic", default_stderr.getvalue())

            verbose_stderr = io.StringIO()
            with redirect_stderr(verbose_stderr):
                _run(root, "child.py", [], verbose=True)
            self.assertIn("child diagnostic", verbose_stderr.getvalue())

    def test_failing_child_keeps_a_concise_reason(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "child.py").write_text(
                "import sys\n"
                "print('ERROR: incomplete compilation coverage', file=sys.stderr)\n"
                "sys.exit(2)\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "child.py failed: incomplete compilation coverage"):
                _run(root, "child.py", [])

    def test_state_logging_matches_current_stage_without_false_completion(self) -> None:
        manifest = {
            "deferred_domains": [{"domain": "evm-audit-bridges"}],
            "required_context_requirements": {"evm-audit-general": {"price": {}}},
        }
        coverage = {
            "selected": ["A"],
            "screen_not_applicable": [],
            "deep_candidates": ["A", "B"],
            "deep_reviewed": ["A"],
            "suspicious": [],
            "confirmed": [],
        }
        cases = (
            ("INCOMPLETE_DOMAIN_ROUTING", "EVM AUDIT :: DOMAIN RESOLUTION", None, manifest, None),
            ("INCOMPLETE_CONTEXT", "EVM AUDIT :: DOMAIN CONTEXT", None, {**manifest, "deferred_domains": []}, None),
            ("INCOMPLETE_COVERAGE", "EVM AUDIT :: SCREEN", None, {**manifest, "deferred_domains": []}, {}),
            ("INCOMPLETE_REVIEW", "EVM AUDIT :: DEEP REVIEW", None, {**manifest, "deferred_domains": []}, {}),
            ("INCOMPLETE_REVIEW", "EVM AUDIT :: PROOF", ["A"], {**manifest, "deferred_domains": []}, {}),
            ("COMPLETE_CLEAN", "EVM AUDIT :: REPORT", "Audit complete", {**manifest, "deferred_domains": []}, {}),
        )
        for status, expected_stage, expected_success, current_manifest, current_context in cases:
            with self.subTest(status=status, expected_stage=expected_stage):
                current = {"status": status, "complete": status == "COMPLETE_CLEAN", "clean": True, "coverage": coverage}
                if expected_success == ["A"]:
                    current["coverage"] = {**coverage, "deep_reviewed": ["A", "B"], "suspicious": ["A"]}
                output = io.StringIO()
                configure()
                with redirect_stderr(output):
                    _log_current_state(current, current_manifest, None, current_context)
                rendered = output.getvalue()
                self.assertIn(expected_stage, rendered)
                if expected_success == "Audit complete":
                    self.assertIn(expected_success, rendered)
                else:
                    self.assertNotIn("Audit complete", rendered)


if __name__ == "__main__":
    unittest.main()
