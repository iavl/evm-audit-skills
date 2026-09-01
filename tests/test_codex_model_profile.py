"""Tests for the Codex-only stage execution policy."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import EMPTY_TARGET, ROOT, build_manifest, review_inputs
from scripts.audit_artifacts import review_state_digest
from scripts.audit_run import recommended_execution
from scripts.codex_model_profile import (
    DEFAULT_CODEX_MODEL_PROFILE,
    STAGES,
    default_profile,
    validate_profile,
    write_profile,
)


class CodexModelProfileTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *arguments],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    def test_default_profile_is_exact_and_schema_valid(self) -> None:
        expected = {
            "RECON": ("gpt-5.6-luna", "max"),
            "ROUTING": ("gpt-5.6-luna", "max"),
            "DOMAIN_RESOLUTION": ("gpt-5.6-terra", "medium"),
            "DOMAIN_CONTEXT": ("gpt-5.6-terra", "medium"),
            "SCREEN": ("gpt-5.6-terra", "high"),
            "DEEP_REVIEW": ("gpt-5.6-sol", "high"),
            "PROOF": ("gpt-5.6-sol", "xhigh"),
            "REPORT": ("gpt-5.6-terra", "medium"),
        }
        self.assertEqual(DEFAULT_CODEX_MODEL_PROFILE, default_profile())
        self.assertEqual(
            {stage: (default_profile()["stages"][stage]["model"], default_profile()["stages"][stage]["reasoning_effort"]) for stage in STAGES},
            expected,
        )
        validate_profile(default_profile())

    def test_invalid_model_and_effort_are_rejected(self) -> None:
        invalid = default_profile()
        invalid["stages"]["SCREEN"]["model"] = "gpt-5.5"
        with self.assertRaisesRegex(ValueError, "unsupported Codex model"):
            validate_profile(invalid)
        invalid = default_profile()
        invalid["stages"]["SCREEN"]["reasoning_effort"] = "turbo"
        with self.assertRaisesRegex(ValueError, "invalid reasoning effort"):
            validate_profile(invalid)

    def test_init_persists_default_profile_and_next_recommendation(self) -> None:
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
                "--accept-default-models",
                "--quiet",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            profile_path = run_dir / "config/codex-model-profile.json"
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            self.assertEqual(profile, default_profile())
            from scripts.audit_artifacts import validate_schema

            validate_schema(ROOT, "codex-model-profile.schema.json", profile)
            payload = json.loads(result.stdout)
            self.assertEqual(
                payload["next"]["recommended_execution"],
                {"provider": "codex", "model": "gpt-5.6-terra", "reasoning_effort": "medium"},
            )

    def test_custom_profile_is_copied_and_models_reset_restores_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir = root / "run"
            custom = default_profile()
            custom["profile_name"] = "custom-audit"
            custom["stages"]["SCREEN"] = {"model": "gpt-5.6-sol", "reasoning_effort": "xhigh"}
            source = root / "custom.json"
            source.write_text(json.dumps(custom) + "\n", encoding="utf-8")
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
                "--model-profile",
                str(source),
                "--quiet",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads((run_dir / "config/codex-model-profile.json").read_text()), custom)
            result = self.run_cli(
                "scripts/audit_run.py",
                "models",
                "--run-dir",
                str(run_dir),
                "--reset-defaults",
                "--quiet",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["profile"], default_profile())
            self.assertEqual(
                json.loads((run_dir / "config/codex-model-profile.json").read_text()),
                default_profile(),
            )

    def test_all_stage_recommendations_and_identity_independence(self) -> None:
        expected = {
            "RECON": ("gpt-5.6-luna", "max"),
            "ROUTING": ("gpt-5.6-luna", "max"),
            "DOMAIN_RESOLUTION": ("gpt-5.6-terra", "medium"),
            "DOMAIN_CONTEXT": ("gpt-5.6-terra", "medium"),
            "SCREEN": ("gpt-5.6-terra", "high"),
            "DEEP_REVIEW": ("gpt-5.6-sol", "high"),
            "PROOF": ("gpt-5.6-sol", "xhigh"),
            "REPORT": ("gpt-5.6-terra", "medium"),
        }
        _, _, _, manifest = build_manifest()
        screen, context, review_snapshot = review_inputs(manifest)
        before = (
            manifest["routing_snapshot_id"],
            review_snapshot,
            review_state_digest({}, set()),
            manifest["audit_context"]["compilation_input_digest"],
        )
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            write_profile(run_dir / "config/codex-model-profile.json", default_profile())
            for stage, (model, effort) in expected.items():
                recommendation = recommended_execution(run_dir, stage)
                self.assertEqual(recommendation, {"provider": "codex", "model": model, "reasoning_effort": effort})
            custom = default_profile()
            custom["stages"]["DEEP_REVIEW"] = {"model": "gpt-5.6-sol", "reasoning_effort": "max"}
            write_profile(run_dir / "config/codex-model-profile.json", custom)
            self.assertEqual(
                recommended_execution(run_dir, "DEEP_REVIEW"),
                {"provider": "codex", "model": "gpt-5.6-sol", "reasoning_effort": "max"},
            )
            custom["stages"]["PROOF"] = {"model": "gpt-5.6-luna", "reasoning_effort": "max"}
            write_profile(run_dir / "config/codex-model-profile.json", custom)
            after = (
                manifest["routing_snapshot_id"],
                review_snapshot,
                review_state_digest({}, set()),
                manifest["audit_context"]["compilation_input_digest"],
            )
        self.assertEqual(before, after)

    def test_legacy_run_without_profile_stays_valid(self) -> None:
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
                "--quiet",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            profile_path = run_dir / "config/codex-model-profile.json"
            self.assertFalse(profile_path.exists())
            status = self.run_cli("scripts/audit_run.py", "status", "--run-dir", str(run_dir), "--quiet")
            self.assertEqual(status.returncode, 0, status.stderr)
            payload = json.loads(status.stdout)
            self.assertEqual(payload["recommended_execution"]["model"], "gpt-5.6-terra")
            report = self.run_cli("scripts/audit_run.py", "report", "--run-dir", str(run_dir), "--quiet")
            self.assertNotEqual(report.returncode, 0)
            state = json.loads((run_dir / "audit-state.json").read_text(encoding="utf-8"))
            self.assertNotEqual(state["status"], "INVALID_SNAPSHOT")


if __name__ == "__main__":
    unittest.main()
