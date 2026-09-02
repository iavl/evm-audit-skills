#!/usr/bin/env python3
"""Tests for the deterministic audit-run controller."""

from __future__ import annotations

import json
import hashlib
import multiprocessing
import queue
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from helpers import EMPTY_TARGET, ROOT, build_manifest
import scripts.audit_run as audit_controller
from scripts.audit_artifacts import check_body_hash
from scripts.render_runtime import domain_context_template, screen_results_template
from scripts.review_ledger import append


def _report_worker(run_dir: str, result_queue: object) -> None:
    try:
        audit_controller.report_run(ROOT, Path(run_dir))
        result_queue.put(("ok", ""))
    except BaseException as exc:  # pragma: no cover - asserted by the parent
        result_queue.put(("error", repr(exc)))


def _publication_lock_worker(run_dir: str, ready: object, result_queue: object) -> None:
    ready.wait(10)
    try:
        with audit_controller._report_publication_lock(Path(run_dir)):
            result_queue.put(("acquired", time.monotonic()))
    except BaseException as exc:  # pragma: no cover - asserted by the parent
        result_queue.put(("error", repr(exc)))


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

    def prepare_clean_run(self, run_dir: Path) -> None:
        result = self.run_cli(
            "scripts/audit_run.py", "init", str(EMPTY_TARGET), "--run-dir", str(run_dir),
            "--audit-root", str(EMPTY_TARGET), "--domain", "evm-audit-general",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
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
                    {"kind": "inheritance", "location": "fixture", "reason": "trigger absent"},
                ],
            )
        screen_path.write_text(json.dumps(screen, indent=2) + "\n", encoding="utf-8")
        result = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_report_bundle_write_failures_never_commit_mixed_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            result = self.run_cli("scripts/audit_run.py", "report", "--run-dir", str(run_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            values = audit_controller.paths(run_dir)
            manifest = self.read(values["manifest"])
            state = self.read(values["audit_state"])
            bundle_status = audit_controller._report_bundle_status(ROOT, values, manifest, state)
            self.assertTrue(bundle_status["current"], bundle_status)
            original_pointer = values["report_current"].read_bytes()
            generation = values["report_generations"] / json.loads(original_pointer)["generation"]
            original_generation = {
                path.relative_to(generation): path.read_bytes()
                for path in generation.iterdir()
                if path.is_file()
            }
            original_atomic_text = audit_controller.atomic_write_text
            original_atomic_json = audit_controller.atomic_write_json

            def fail_report(path: Path, content: str) -> None:
                if path.name == "AUDIT-REPORT.md":
                    raise OSError("report write failure")
                original_atomic_text(path, content)

            with patch.object(audit_controller, "atomic_write_text", side_effect=fail_report):
                with self.assertRaisesRegex(OSError, "report write failure"):
                    audit_controller.report_run(ROOT, run_dir)
            self.assertEqual(values["report_current"].read_bytes(), original_pointer)
            self.assertEqual(
                {path.relative_to(generation): path.read_bytes() for path in generation.iterdir() if path.is_file()},
                original_generation,
            )
            self.assertTrue(audit_controller._report_bundle_status(ROOT, values, manifest, state)["current"])

            def fail_issue(path: Path, value: dict) -> None:
                if path.name == "issue-candidates.json":
                    raise OSError("issue-candidates write failure")
                original_atomic_json(path, value)

            with patch.object(audit_controller, "atomic_write_json", side_effect=fail_issue):
                with self.assertRaisesRegex(OSError, "issue-candidates write failure"):
                    audit_controller.report_run(ROOT, run_dir)
            self.assertEqual(values["report_current"].read_bytes(), original_pointer)
            self.assertTrue(audit_controller._report_bundle_status(ROOT, values, manifest, state)["current"])

            def fail_bundle(path: Path, value: dict) -> None:
                if path.name == "report-bundle.json":
                    raise OSError("metadata write failure")
                original_atomic_json(path, value)

            with patch.object(audit_controller, "atomic_write_json", side_effect=fail_bundle):
                with self.assertRaisesRegex(OSError, "metadata write failure"):
                    audit_controller.report_run(ROOT, run_dir)
            self.assertEqual(values["report_current"].read_bytes(), original_pointer)
            self.assertTrue(audit_controller._report_bundle_status(ROOT, values, manifest, state)["current"])

            audit_controller.report_run(ROOT, run_dir)
            self.assertEqual(values["report_current"].read_bytes(), original_pointer)

    def test_report_result_points_to_current_generation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            run_dir = run_dir.resolve()
            result = audit_controller.report_run(ROOT, run_dir)
            pointer = self.read(run_dir / "report-current.json")
            generation = run_dir / "report-generations" / pointer["generation"]
            self.assertEqual(result["generation"], pointer["generation"])
            self.assertEqual(result["report"], str(generation / "AUDIT-REPORT.md"))
            self.assertEqual(result["issue_candidates"], str(generation / "issue-candidates.json"))
            self.assertEqual(result["report_bundle_path"], str(generation / "report-bundle.json"))
            self.assertEqual(result["report_current"], str(run_dir / "report-current.json"))
            self.assertTrue(result["convenience"]["synced"])

    def test_convenience_copy_failure_returns_authoritative_generation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            run_dir = run_dir.resolve()
            original = audit_controller.atomic_write_bytes

            def fail_convenience(path: Path, content: bytes) -> None:
                if path == run_dir / "AUDIT-REPORT.md":
                    raise OSError("convenience report copy failure")
                original(path, content)

            with patch.object(audit_controller, "atomic_write_bytes", side_effect=fail_convenience):
                result = audit_controller.report_run(ROOT, run_dir)
            self.assertFalse(result["convenience"]["synced"])
            self.assertIn(str(run_dir / "AUDIT-REPORT.md"), result["convenience"]["failed_paths"])
            self.assertTrue(Path(result["report"]).is_file())
            self.assertTrue(audit_controller._report_bundle_status(
                ROOT,
                audit_controller.paths(run_dir),
                self.read(run_dir / "routing/manifest.json"),
                self.read(run_dir / "audit-state.json"),
            )["current"])

    def test_status_reports_authoritative_report_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            run_dir = run_dir.resolve()
            audit_controller.report_run(ROOT, run_dir)
            result = audit_controller.status_run(ROOT, run_dir, emit=False, include_execution=True)
            pointer = self.read(run_dir / "report-current.json")
            generation = run_dir / "report-generations" / pointer["generation"]
            authority = result["report_generation"]
            self.assertEqual(authority["status"], "CURRENT")
            self.assertEqual(authority["generation"], pointer["generation"])
            self.assertEqual(authority["report"], str(generation / "AUDIT-REPORT.md"))
            self.assertEqual(authority["issue_candidates"], str(generation / "issue-candidates.json"))
            self.assertEqual(authority["bundle"], str(generation / "report-bundle.json"))
            self.assertEqual(authority["current_pointer"], str(run_dir / "report-current.json"))

    def test_report_lock_is_cross_process(self) -> None:
        context = multiprocessing.get_context("spawn")
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            ready = context.Event()
            result_queue = context.Queue()
            process = context.Process(target=_publication_lock_worker, args=(str(run_dir), ready, result_queue))
            with audit_controller._report_publication_lock(run_dir):
                process.start()
                ready.set()
                with self.assertRaises(queue.Empty):
                    result_queue.get(timeout=0.25)
            kind, detail = result_queue.get(timeout=10)
            process.join(10)
            self.assertEqual(process.exitcode, 0)
            self.assertEqual(kind, "acquired", detail)

    def test_report_lock_does_not_silently_disable_on_windows(self) -> None:
        import scripts.review_ledger as review_ledger

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(review_ledger, "fcntl", None), patch.object(review_ledger, "msvcrt", None):
                with self.assertRaisesRegex(RuntimeError, "locking is unavailable"):
                    with audit_controller._report_publication_lock(Path(directory)):
                        pass

    def test_concurrent_report_publications_leave_pointer_and_convenience_copies_consistent(self) -> None:
        context = multiprocessing.get_context("spawn")
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            result_queue = context.Queue()
            processes = [
                context.Process(target=_report_worker, args=(str(run_dir), result_queue))
                for _ in range(2)
            ]
            for process in processes:
                process.start()
            outcomes = [result_queue.get(timeout=30) for _ in processes]
            for process in processes:
                process.join(30)
                self.assertEqual(process.exitcode, 0)
            self.assertEqual([kind for kind, _ in outcomes], ["ok", "ok"])
            pointer = self.read(run_dir / "report-current.json")
            generation = run_dir / "report-generations" / pointer["generation"]
            for name in ("AUDIT-REPORT.md", "issue-candidates.json", "report-bundle.json"):
                self.assertEqual((run_dir / name).read_bytes(), (generation / name).read_bytes())

    def test_report_aborts_if_review_state_changes_before_pointer_commit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            run_dir = run_dir.resolve()
            values = audit_controller.paths(run_dir)
            original_status = audit_controller.status_run
            calls = 0

            def changed_status(*args: object, **kwargs: object) -> dict:
                nonlocal calls
                calls += 1
                state = original_status(*args, **kwargs)
                if calls == 2:
                    return {**state, "review_state_digest": "0" * 64}
                return state

            with patch.object(audit_controller, "status_run", side_effect=changed_status):
                with self.assertRaisesRegex(ValueError, "changed during report publication"):
                    audit_controller.report_run(ROOT, run_dir)
            self.assertFalse(values["report_current"].exists())
            self.assertFalse(any(values["report_generations"].glob("generation-*")))

    def test_complete_report_cannot_return_success_with_stale_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            original = audit_controller._report_bundle_status

            def stale(*args: object, **kwargs: object) -> dict:
                result = original(*args, **kwargs)
                return {**result, "status": "STALE", "current": False, "message": "changed after commit"}

            with patch.object(audit_controller, "_report_bundle_status", side_effect=stale):
                with self.assertRaisesRegex(ValueError, "report publication is stale"):
                    audit_controller.report_run(ROOT, run_dir)

    def test_tmp_generation_without_pointer_is_ignored_as_uncommitted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            values = audit_controller.paths(run_dir)
            staging = values["report_generations"] / ".tmp-crashed-publication"
            staging.mkdir(parents=True)
            manifest = self.read(values["manifest"])
            state = self.read(values["audit_state"])
            status = audit_controller._report_bundle_status(ROOT, values, manifest, state)
            self.assertEqual(status["status"], "ABSENT", status)
            self.assertFalse(status["current"])
            self.assertIn(staging.name, status["staging_artifacts"])

    def test_pointer_write_failure_after_rename_is_retryable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            run_dir = run_dir.resolve()
            values = audit_controller.paths(run_dir)
            original = audit_controller.atomic_write_json

            def fail_pointer(path: Path, value: dict) -> None:
                if path == values["report_current"]:
                    raise OSError("pointer write failure")
                original(path, value)

            with patch.object(audit_controller, "atomic_write_json", side_effect=fail_pointer):
                with self.assertRaisesRegex(OSError, "pointer write failure"):
                    audit_controller.report_run(ROOT, run_dir)
            self.assertFalse(values["report_current"].exists())
            self.assertFalse(any(values["report_generations"].glob("generation-*")))
            audit_controller.report_run(ROOT, run_dir)
            self.assertTrue(values["report_current"].exists())

    def test_orphan_generation_is_reported_but_not_current(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            audit_controller.report_run(ROOT, run_dir)
            values = audit_controller.paths(run_dir)
            orphan = values["report_generations"] / "generation-orphan"
            orphan.mkdir()
            manifest = self.read(values["manifest"])
            state = self.read(values["audit_state"])
            status = audit_controller._report_bundle_status(ROOT, values, manifest, state)
            self.assertTrue(status["current"], status)
            self.assertIn(orphan.name, status["orphaned_generations"])
            self.assertNotEqual(status["generation"], orphan.name)

    def test_identical_report_reuses_generation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            first = audit_controller.report_run(ROOT, run_dir)
            pointer = (run_dir / "report-current.json").read_bytes()
            pointer_value = json.loads(pointer)
            self.assertEqual(pointer_value["generation"], f"generation-{pointer_value['report_bundle_sha256']}")
            generations = sorted(path.name for path in (run_dir / "report-generations").glob("generation-*"))
            second = audit_controller.report_run(ROOT, run_dir)
            self.assertEqual((run_dir / "report-current.json").read_bytes(), pointer)
            self.assertEqual(
                sorted(path.name for path in (run_dir / "report-generations").glob("generation-*")),
                generations,
            )
            self.assertEqual(first["generation"], second["generation"])

    def test_changed_report_inputs_create_new_generation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            audit_controller.report_run(ROOT, run_dir)
            before = self.read(run_dir / "report-current.json")
            screen_path = run_dir / "reviews/screen-results.json"
            screen = self.read(screen_path)
            screen["results"][0].update(result="CANDIDATE", scope_complete=False, evidence=[])
            screen_path.write_text(json.dumps(screen, indent=2) + "\n", encoding="utf-8")
            result = audit_controller.report_run(ROOT, run_dir)
            after = self.read(run_dir / "report-current.json")
            self.assertNotEqual(after["generation"], before["generation"])
            self.assertEqual(result["generation"], after["generation"])

    def test_existing_content_address_with_mismatched_contents_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            audit_controller.report_run(ROOT, run_dir)
            pointer_path = run_dir / "report-current.json"
            pointer = self.read(pointer_path)
            bundle_path = run_dir / "report-generations" / pointer["generation"] / "report-bundle.json"
            bundle_path.write_bytes(b"{}\n")
            with self.assertRaisesRegex(ValueError, "mismatched contents"):
                audit_controller.report_run(ROOT, run_dir)
            self.assertEqual(self.read(pointer_path), pointer)

    def test_generation_rename_is_durable_before_pointer_commit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            run_dir = run_dir.resolve()
            events: list[str] = []
            original_json = audit_controller.atomic_write_json

            def durable(source: Path, destination: Path) -> bool:
                events.append("rename")
                source.replace(destination)
                return True

            def write_json(path: Path, value: dict) -> None:
                if path == run_dir / "report-current.json":
                    self.assertEqual(events, ["rename"])
                    events.append("pointer")
                original_json(path, value)

            with patch.object(audit_controller, "durable_replace_directory", side_effect=durable), patch.object(
                audit_controller, "atomic_write_json", side_effect=write_json
            ):
                audit_controller.report_run(ROOT, run_dir)
            self.assertEqual(events, ["rename", "pointer"])

    def test_internal_status_skips_report_resynthesis(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            audit_controller.report_run(ROOT, run_dir)
            with patch.object(audit_controller, "synthesize", side_effect=AssertionError("unexpected synthesis")):
                state = audit_controller.status_run(ROOT, run_dir, emit=False)
            self.assertEqual(state["status"], "COMPLETE_CLEAN")

    def test_reports_list_diagnoses_staging_and_orphans(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            audit_controller.report_run(ROOT, run_dir)
            values = audit_controller.paths(run_dir)
            first = self.read(values["report_current"])["generation"]
            screen = self.read(values["screen_results"])
            screen["results"][0].update(result="CANDIDATE", scope_complete=False, evidence=[])
            values["screen_results"].write_text(json.dumps(screen, indent=2) + "\n", encoding="utf-8")
            audit_controller.report_run(ROOT, run_dir)
            staging = values["report_generations"] / ".tmp-crashed-publication"
            staging.mkdir()
            result = audit_controller.reports_run(ROOT, run_dir, list_only=True)
            self.assertIn(first, result["orphaned_generations"])
            self.assertIn(staging.name, result["staging_artifacts"])

    def test_reports_gc_dry_run_and_apply_preserve_current_and_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            audit_controller.report_run(ROOT, run_dir)
            values = audit_controller.paths(run_dir)
            first = self.read(values["report_current"])["generation"]
            screen = self.read(values["screen_results"])
            screen["results"][0].update(result="CANDIDATE", scope_complete=False, evidence=[])
            values["screen_results"].write_text(json.dumps(screen, indent=2) + "\n", encoding="utf-8")
            audit_controller.report_run(ROOT, run_dir)
            current = self.read(values["report_current"])["generation"]
            staging = values["report_generations"] / ".tmp-crashed-publication"
            unknown = values["report_generations"] / "unrelated-directory"
            staging.mkdir()
            unknown.mkdir()
            dry_run = audit_controller.reports_run(ROOT, run_dir, gc=True, dry_run=True)
            self.assertIn(first, dry_run["gc"]["candidates"])
            self.assertIn(staging.name, dry_run["gc"]["candidates"])
            self.assertFalse(dry_run["gc"]["applied"])
            self.assertTrue(staging.exists())
            applied = audit_controller.reports_run(ROOT, run_dir, gc=True, apply=True)
            self.assertTrue(applied["gc"]["applied"])
            self.assertFalse(staging.exists())
            self.assertTrue(unknown.exists())
            self.assertTrue((values["report_generations"] / current).exists())

    def test_legacy_top_level_outputs_require_explicit_republication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            values = audit_controller.paths(run_dir)
            values["report"].write_text("legacy report\n", encoding="utf-8")
            values["issue_candidates"].write_text("{}\n", encoding="utf-8")
            values["report_bundle"].write_text("{}\n", encoding="utf-8")
            manifest = self.read(values["manifest"])
            state = self.read(values["audit_state"])
            self.assertEqual(audit_controller._report_bundle_status(ROOT, values, manifest, state)["status"], "ABSENT")
            result = audit_controller.report_run(ROOT, run_dir)
            self.assertTrue(Path(result["report"]).is_file())
            self.assertTrue(values["report_current"].exists())

    def test_reports_cli_defaults_gc_to_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            listed = self.run_cli("scripts/audit_run.py", "reports", "--run-dir", str(run_dir), "--list")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertEqual(json.loads(listed.stdout)["stage"], "REPORTS")
            preview = self.run_cli("scripts/audit_run.py", "reports", "--run-dir", str(run_dir), "--gc", "--dry-run")
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertTrue(json.loads(preview.stdout)["gc"]["dry_run"])

    def test_first_report_failure_does_not_create_fake_current_generation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            values = audit_controller.paths(run_dir)
            original_atomic_text = audit_controller.atomic_write_text

            def fail_report(path: Path, content: str) -> None:
                if path.name == "AUDIT-REPORT.md":
                    raise OSError("first report write failure")
                original_atomic_text(path, content)

            with patch.object(audit_controller, "atomic_write_text", side_effect=fail_report):
                with self.assertRaisesRegex(OSError, "first report write failure"):
                    audit_controller.report_run(ROOT, run_dir)
            self.assertFalse(values["report_current"].exists())
            self.assertFalse(any(values["report_generations"].glob("generation-*")))
            audit_controller.report_run(ROOT, run_dir)
            self.assertTrue(values["report_current"].exists())

    def test_bundle_rederivation_accepts_official_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            audit_controller.report_run(ROOT, run_dir)
            values = audit_controller.paths(run_dir)
            manifest = self.read(values["manifest"])
            state = self.read(values["audit_state"])
            status = audit_controller._report_bundle_status(ROOT, values, manifest, state)
            self.assertEqual(status["status"], "CURRENT", status)
            self.assertTrue(status["generation"])

    def test_bundle_rejects_coordinated_report_and_marker_edit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            self.prepare_clean_run(run_dir)
            audit_controller.report_run(ROOT, run_dir)
            values = audit_controller.paths(run_dir)
            manifest = self.read(values["manifest"])
            state = self.read(values["audit_state"])
            pointer = self.read(values["report_current"])
            generation = values["report_generations"] / pointer["generation"]
            report_path = generation / "AUDIT-REPORT.md"
            report_path.write_text(report_path.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")
            bundle_path = generation / "report-bundle.json"
            bundle = self.read(bundle_path)
            bundle["report_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
            bundle_path.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
            pointer["report_bundle_sha256"] = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
            values["report_current"].write_text(json.dumps(pointer, indent=2) + "\n", encoding="utf-8")
            status = audit_controller._report_bundle_status(ROOT, values, manifest, state)
            self.assertEqual(status["status"], "STALE", status)

    def test_init_failures_leave_no_partial_run_and_allow_safe_retry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            for failure_args in (
                ["--solc", str(parent / "missing-solc")],
                ["--domain", "evm-audit-does-not-exist"],
            ):
                run_dir = parent / ("run-" + str(len(list(parent.iterdir()))))
                result = self.run_cli(
                    "scripts/audit_run.py", "init", str(EMPTY_TARGET), "--run-dir", str(run_dir),
                    "--audit-root", str(EMPTY_TARGET), *failure_args,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(run_dir.exists())
                result = self.run_cli(
                    "scripts/audit_run.py", "init", str(EMPTY_TARGET), "--run-dir", str(run_dir),
                    "--audit-root", str(EMPTY_TARGET), "--domain", "evm-audit-general",
                )
                self.assertEqual(result.returncode, 0, result.stderr)

            existing = parent / "existing"
            existing.mkdir()
            keep = existing / "keep.txt"
            keep.write_text("user content", encoding="utf-8")
            result = self.run_cli(
                "scripts/audit_run.py", "init", str(EMPTY_TARGET), "--run-dir", str(existing),
                "--audit-root", str(EMPTY_TARGET), "--domain", "evm-audit-general",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(keep.read_text(encoding="utf-8"), "user content")

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
            self.assertEqual(
                json.loads(result.stdout)["next"]["recommended_execution"],
                {"provider": "codex", "model": "gpt-5.6-terra", "reasoning_effort": "medium"},
            )
            result = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("DOMAIN_CONTEXT", result.stdout)
            self.assertEqual(json.loads(result.stdout)["progress"]["label"], "DOMAIN CONTEXT")
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
            screen_payload = json.loads(result.stdout)
            self.assertEqual(screen_payload["progress"]["step"], 4)
            self.assertEqual(screen_payload["progress"]["label"], "SCREEN")
            screen_path = run_dir / "reviews/screen-results.json"
            screen = self.read(screen_path)
            for item in screen["results"]:
                item.update(
                    result="NOT_APPLICABLE_CONFIRMED",
                    scope_complete=True,
                    evidence=[
                        {"kind": "scope", "location": "fixture", "reason": "complete scope"},
                        {"kind": "inheritance", "location": "fixture", "reason": "trigger absent"},
                    ],
                )
            screen_path.write_text(json.dumps(screen, indent=2) + "\n", encoding="utf-8")

            result = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("COMPLETE_CLEAN", result.stdout)
            report_payload = json.loads(result.stdout)
            self.assertEqual(report_payload["progress"]["step"], 7)
            self.assertEqual(report_payload["progress"]["label"], "REPORT")
            self.assertEqual(
                report_payload["recommended_execution"],
                {"provider": "codex", "model": "gpt-5.6-terra", "reasoning_effort": "medium"},
            )
            manifest = self.read(run_dir / "routing/manifest.json")
            state = self.read(run_dir / "audit-state.json")
            identity = {
                "schema_version": 2,
                "routing_snapshot_id": manifest["routing_snapshot_id"],
                "review_state_digest": state["review_state_digest"],
                **{
                    key: manifest["audit_context"][key]
                    for key in ("registry_sha256", "source_digest", "compilation_input_digest")
                },
            }
            severity_path = run_dir / "severity-decisions.json"
            severity_path.write_text(json.dumps({**identity, "decisions": {}}) + "\n", encoding="utf-8")
            details_path = run_dir / "finding-details.json"
            details_path.write_text(json.dumps({**identity, "findings": []}) + "\n", encoding="utf-8")
            result = self.run_cli(
                "scripts/audit_run.py",
                "report",
                "--run-dir",
                str(run_dir),
                "--severity-decisions",
                str(severity_path),
                "--finding-details",
                str(details_path),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report_command = json.loads(result.stdout)
            self.assertEqual(report_command["progress"]["step"], 7)
            self.assertEqual(report_command["progress"]["label"], "REPORT")
            report = (run_dir / "AUDIT-REPORT.md").read_text(encoding="utf-8")
            self.assertIn("COMPLETE_CLEAN", report)
            self.assertTrue((run_dir / "issue-candidates.json").exists())
            previous_report = (run_dir / "AUDIT-REPORT.md").read_text(encoding="utf-8")
            previous_issues = (run_dir / "issue-candidates.json").read_text(encoding="utf-8")
            bad_severity = run_dir / "bad-severity.json"
            bad_severity.write_text("{\n", encoding="utf-8")
            result = self.run_cli(
                "scripts/audit_run.py",
                "report",
                "--run-dir",
                str(run_dir),
                "--severity-decisions",
                str(bad_severity),
                "--finding-details",
                str(details_path),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((run_dir / "AUDIT-REPORT.md").read_text(encoding="utf-8"), previous_report)
            self.assertEqual((run_dir / "issue-candidates.json").read_text(encoding="utf-8"), previous_issues)
            result = self.run_cli(
                "scripts/audit_run.py",
                "report",
                "--run-dir",
                str(run_dir),
                "--severity-decisions",
                str(severity_path),
                "--finding-details",
                str(details_path),
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_optional_code_index_does_not_block_authoritative_status(self) -> None:
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
            code_index = run_dir / "recon/code-index.json"
            original = code_index.read_text(encoding="utf-8")
            result = self.run_cli("scripts/audit_run.py", "status", "--run-dir", str(run_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            current = json.loads(result.stdout)
            self.assertEqual(current["navigation"]["status"], "CURRENT")
            authoritative_status = current["status"]
            for invalid in ({"broken": True}, {**json.loads(original), "source_digest": "0" * 64}):
                code_index.write_text(json.dumps(invalid) + "\n", encoding="utf-8")
                result = self.run_cli("scripts/audit_run.py", "status", "--run-dir", str(run_dir))
                self.assertEqual(result.returncode, 0, result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual(payload["navigation"]["status"], "TAMPERED")
                self.assertFalse(payload["navigation"]["available"])
                self.assertEqual(payload["status"], authoritative_status)
                self.assertNotEqual(payload["status"], "INVALID_SNAPSHOT")
            code_index.write_text(original, encoding="utf-8")
            result = self.run_cli("scripts/audit_run.py", "status", "--run-dir", str(run_dir))
            self.assertEqual(json.loads(result.stdout)["navigation"]["status"], "CURRENT")
            code_index.unlink()
            result = self.run_cli("scripts/audit_run.py", "status", "--run-dir", str(run_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["navigation"]["status"], "MISSING")

    def test_unbound_missing_code_index_is_reported_absent(self) -> None:
        _, _, _, manifest = build_manifest()
        with tempfile.TemporaryDirectory() as directory:
            values = {"code_index": Path(directory) / "recon/code-index.json"}
            status = audit_controller._optional_code_index_status(ROOT, values, manifest)
        self.assertEqual(status["status"], "ABSENT")
        self.assertFalse(status["available"])

    def test_finding_report_snapshots_inputs_and_requires_both_for_current_bundle(self) -> None:
        registry, _, _, manifest = build_manifest()
        screen = screen_results_template(manifest)
        candidate_id = screen["results"][0]["canonical_id"]
        evidence = [
            {"kind": "scope", "location": "fixture", "reason": "complete scope"},
            {"kind": "inheritance", "location": "fixture", "reason": "screen disposition"},
        ]
        for item in screen["results"]:
            if item["canonical_id"] == candidate_id:
                item.update(result="CANDIDATE", scope_complete=False, evidence=[])
            else:
                item.update(result="NOT_APPLICABLE_CONFIRMED", scope_complete=True, evidence=evidence)
        domain_context = domain_context_template(manifest)
        for requirements in domain_context["domains"].values():
            for item in requirements.values():
                item.update(status="KNOWN", value="fixture", evidence=[evidence[0]])
        context = {**manifest["audit_context"], "routing_snapshot_id": manifest["routing_snapshot_id"]}
        route = next(item for item in manifest["selected"] if item["canonical_id"] == candidate_id)
        check = next(item for item in registry["checks"] if item["canonical_id"] == candidate_id)
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            values = audit_controller.paths(run_dir)
            values["manifest"].parent.mkdir(parents=True)
            values["domain_context"].parent.mkdir(parents=True, exist_ok=True)
            values["context"].write_text(json.dumps(context) + "\n", encoding="utf-8")
            values["manifest"].write_text(json.dumps(manifest) + "\n", encoding="utf-8")
            values["domain_context"].write_text(json.dumps(domain_context) + "\n", encoding="utf-8")
            values["screen_results"].write_text(json.dumps(screen) + "\n", encoding="utf-8")
            deep = {
                "record_type": "review",
                "schema_version": 7,
                "canonical_id": candidate_id,
                "owner_domain": route["owner_domain"],
                "check_body_hash": check_body_hash(check),
                "review_stage": "DEEP_REVIEW",
                "status": "SUSPICIOUS",
                "code_path": "fixture entry",
                "unresolved_reason": "proof pending",
                "evidence": [{"kind": "manual", "location": "fixture", "reason": "deep review"}],
            }
            ledger = run_dir / "reviews/review-evm-audit-general.jsonl"
            append(ledger, manifest, deep, registry, {candidate_id}, domain_context=domain_context, screen_results=screen)
            proof = {
                **deep,
                "review_stage": "PROOF",
                "status": "CONFIRMED",
                "applicability": "APPLICABLE - fixture",
                "preconditions": "fixture state",
                "exploitability": "fixture path is reachable",
                "impact": "fixture impact",
                "proof": "deterministic fixture trace",
                "evidence": [{"kind": "trace", "location": "fixture", "reason": "proof trace"}],
            }
            append(ledger, manifest, proof, registry, {candidate_id}, domain_context=domain_context, screen_results=screen)
            state = audit_controller.status_run(ROOT, run_dir, emit=False)
            self.assertEqual(state["status"], "COMPLETE_WITH_FINDINGS")
            identity = {
                "schema_version": 2,
                "routing_snapshot_id": manifest["routing_snapshot_id"],
                "review_state_digest": state["review_state_digest"],
                **{
                    key: manifest["audit_context"][key]
                    for key in ("registry_sha256", "source_digest", "compilation_input_digest")
                },
            }
            severity = {
                **identity,
                "decisions": {
                    candidate_id: {
                        "severity": "High",
                        "rationale": "fixture proof",
                        "dimensions": {
                            "impact": "fund_loss", "exploitability": "permissionless", "privileges": "none",
                            "capital_required": "none", "repeatability": "one_shot", "user_interaction": "none",
                            "loss_bound": "single_user", "protocol_exposure": "single_position", "recoverability": "irreversible",
                        },
                    }
                },
            }
            details = {
                **identity,
                "findings": [{
                    "canonical_id": candidate_id,
                    "location": "Fixture.sol:1",
                    "description": "fixture finding",
                    "recommendation": "fix fixture",
                }],
            }
            severity_path = run_dir / "external-severity.json"
            details_path = run_dir / "external-details.json"
            severity_path.write_text(json.dumps(severity, indent=2) + "\n", encoding="utf-8")
            details_path.write_text(json.dumps(details, indent=2) + "\n", encoding="utf-8")
            report = audit_controller.report_run(ROOT, run_dir, severity_path, details_path)
            self.assertTrue(report["complete"])
            self.assertEqual(values["report_input_severity"].read_bytes(), severity_path.read_bytes())
            self.assertEqual(values["report_input_details"].read_bytes(), details_path.read_bytes())
            bundle_status = audit_controller._report_bundle_status(ROOT, values, manifest, state)
            self.assertTrue(bundle_status["current"], bundle_status)
            generation = values["report_generations"] / json.loads(values["report_current"].read_bytes())["generation"]
            details_snapshot = generation / "finding-details.json"
            details_bytes = details_snapshot.read_bytes()
            details_snapshot.write_bytes(details_bytes + b"\n")
            self.assertFalse(audit_controller._report_bundle_status(ROOT, values, manifest, state)["current"])
            details_snapshot.write_bytes(details_bytes)
            self.assertTrue(audit_controller._report_bundle_status(ROOT, values, manifest, state)["current"])
            details_snapshot.unlink()
            self.assertFalse(audit_controller._report_bundle_status(ROOT, values, manifest, state)["current"])

    def test_failed_finding_report_preserves_previous_current_generation(self) -> None:
        registry, _, _, manifest = build_manifest()
        screen = screen_results_template(manifest)
        candidate_id = screen["results"][0]["canonical_id"]
        evidence = [
            {"kind": "scope", "location": "fixture", "reason": "complete scope"},
            {"kind": "inheritance", "location": "fixture", "reason": "screen disposition"},
        ]
        for item in screen["results"]:
            is_candidate = item["canonical_id"] == candidate_id
            item.update(
                result="CANDIDATE" if is_candidate else "NOT_APPLICABLE_CONFIRMED",
                scope_complete=not is_candidate,
                evidence=[] if is_candidate else evidence,
            )
        domain_context = domain_context_template(manifest)
        for requirements in domain_context["domains"].values():
            for item in requirements.values():
                item.update(status="KNOWN", value="fixture", evidence=[evidence[0]])
        context = {**manifest["audit_context"], "routing_snapshot_id": manifest["routing_snapshot_id"]}
        route = next(item for item in manifest["selected"] if item["canonical_id"] == candidate_id)
        check = next(item for item in registry["checks"] if item["canonical_id"] == candidate_id)
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            values = audit_controller.paths(run_dir)
            values["manifest"].parent.mkdir(parents=True)
            values["domain_context"].parent.mkdir(parents=True, exist_ok=True)
            values["context"].write_text(json.dumps(context) + "\n", encoding="utf-8")
            values["manifest"].write_text(json.dumps(manifest) + "\n", encoding="utf-8")
            values["domain_context"].write_text(json.dumps(domain_context) + "\n", encoding="utf-8")
            values["screen_results"].write_text(json.dumps(screen) + "\n", encoding="utf-8")
            deep = {
                "record_type": "review", "schema_version": 7, "canonical_id": candidate_id,
                "owner_domain": route["owner_domain"], "check_body_hash": check_body_hash(check),
                "review_stage": "DEEP_REVIEW", "status": "SUSPICIOUS", "code_path": "fixture entry",
                "unresolved_reason": "proof pending", "evidence": [{"kind": "manual", "location": "fixture", "reason": "deep review"}],
            }
            ledger = run_dir / "reviews/review-evm-audit-general.jsonl"
            append(ledger, manifest, deep, registry, {candidate_id}, domain_context=domain_context, screen_results=screen)
            proof = {
                **deep, "review_stage": "PROOF", "status": "CONFIRMED",
                "applicability": "APPLICABLE - fixture", "preconditions": "fixture state",
                "exploitability": "fixture path is reachable", "impact": "fixture impact",
                "proof": "deterministic fixture trace", "evidence": [{"kind": "trace", "location": "fixture", "reason": "proof trace"}],
            }
            append(ledger, manifest, proof, registry, {candidate_id}, domain_context=domain_context, screen_results=screen)
            state = audit_controller.status_run(ROOT, run_dir, emit=False)
            identity = {
                "schema_version": 2, "routing_snapshot_id": manifest["routing_snapshot_id"],
                "review_state_digest": state["review_state_digest"],
                **{key: manifest["audit_context"][key] for key in ("registry_sha256", "source_digest", "compilation_input_digest")},
            }
            severity_path = run_dir / "severity.json"
            severity_path.write_text(json.dumps({**identity, "decisions": {
                candidate_id: {
                    "severity": "High", "rationale": "fixture proof", "dimensions": {
                        "impact": "fund_loss", "exploitability": "permissionless", "privileges": "none",
                        "capital_required": "none", "repeatability": "one_shot", "user_interaction": "none",
                        "loss_bound": "single_user", "protocol_exposure": "single_position", "recoverability": "irreversible",
                    },
                },
            }}) + "\n", encoding="utf-8")
            details_path = run_dir / "details.json"
            details_path.write_text(json.dumps({**identity, "findings": [{
                "canonical_id": candidate_id, "location": "Fixture.sol:1", "description": "fixture finding", "recommendation": "fix fixture",
            }]}) + "\n", encoding="utf-8")
            audit_controller.report_run(ROOT, run_dir, severity_path, details_path)

            def snapshot() -> tuple[bytes, dict[Path, bytes]]:
                pointer = values["report_current"].read_bytes()
                generation = values["report_generations"] / json.loads(pointer)["generation"]
                return pointer, {
                    path.relative_to(generation): path.read_bytes()
                    for path in generation.iterdir()
                    if path.is_file()
                }

            failure_cases = (
                ("severity", "bytes", "severity-decisions.json"),
                ("details", "bytes", "finding-details.json"),
                ("report", "text", "AUDIT-REPORT.md"),
                ("issues", "json", "issue-candidates.json"),
                ("bundle", "json", "report-bundle.json"),
            )
            for name, writer, filename in failure_cases:
                with self.subTest(boundary=name):
                    original_pointer, original_generation = snapshot()
                    if writer == "bytes":
                        original = audit_controller.atomic_write_bytes

                        def fail(path: Path, content: bytes, *, original=original, filename=filename) -> None:
                            if path.name == filename:
                                raise OSError(f"{name} write failure")
                            original(path, content)

                        context_manager = patch.object(audit_controller, "atomic_write_bytes", side_effect=fail)
                    elif writer == "text":
                        original = audit_controller.atomic_write_text

                        def fail(path: Path, content: str, *, original=original, filename=filename) -> None:
                            if path.name == filename:
                                raise OSError(f"{name} write failure")
                            original(path, content)

                        context_manager = patch.object(audit_controller, "atomic_write_text", side_effect=fail)
                    else:
                        original = audit_controller.atomic_write_json

                        def fail(path: Path, value: dict, *, original=original, filename=filename) -> None:
                            if path.name == filename:
                                raise OSError(f"{name} write failure")
                            original(path, value)

                        context_manager = patch.object(audit_controller, "atomic_write_json", side_effect=fail)
                    with context_manager:
                        with self.assertRaisesRegex(OSError, f"{name} write failure"):
                            audit_controller.report_run(ROOT, run_dir, severity_path, details_path)
                    self.assertEqual(values["report_current"].read_bytes(), original_pointer)
                    self.assertEqual(snapshot()[1], original_generation)
                    self.assertTrue(audit_controller._report_bundle_status(ROOT, values, manifest, state)["current"])
                    audit_controller.report_run(ROOT, run_dir, severity_path, details_path)

    def test_report_rederives_state_after_current_ledger_is_removed(self) -> None:
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
            candidate = screen["results"][0]
            candidate.update(result="CANDIDATE", scope_complete=False, evidence=[])
            evidence = [
                {"kind": "scope", "location": "fixture", "reason": "complete scope"},
                {"kind": "inheritance", "location": "fixture", "reason": "screen disposition"},
            ]
            for item in screen["results"][1:]:
                item.update(result="NOT_APPLICABLE_CONFIRMED", scope_complete=True, evidence=evidence)
            screen_path.write_text(json.dumps(screen, indent=2) + "\n", encoding="utf-8")

            result = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            self.assertIn("DEEP_REVIEW", result.stdout)
            deep_payload = json.loads(result.stdout)
            self.assertEqual(deep_payload["progress"]["step"], 5)
            self.assertEqual(deep_payload["progress"]["label"], "DEEP REVIEW")
            self.assertIn("Deep Review candidates remain", deep_payload["progress"]["summary"])
            self.assertEqual(
                deep_payload["recommended_execution"],
                {"provider": "codex", "model": "gpt-5.6-sol", "reasoning_effort": "high"},
            )
            manifest = self.read(run_dir / "routing/manifest.json")
            route = next(item for item in manifest["selected"] if item["canonical_id"] == candidate["canonical_id"])
            record = {
                "record_type": "review",
                "schema_version": 7,
                "canonical_id": candidate["canonical_id"],
                "owner_domain": route["owner_domain"],
                "check_body_hash": route["check_body_hash"],
                "review_stage": "DEEP_REVIEW",
                "status": "REVIEWED_SAFE",
                "applicability": "APPLICABLE - fixture",
                "code_path": "fixture entry",
                "preconditions": "fixture state",
                "exploitability": "guard holds",
                "impact": "none",
                "proof": "fixture invariant",
                "preserved_invariant": "fixture invariant",
                "evidence": [{"kind": "test", "location": "fixture", "reason": "test evidence"}],
            }
            ledger = run_dir / "reviews/review-evm-audit-general.jsonl"
            append(
                ledger,
                manifest,
                record,
                self.read(ROOT / "data/canonical-checks.json"),
                {candidate["canonical_id"]},
                domain_context=context,
                screen_results=screen,
            )

            result = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("COMPLETE_CLEAN", result.stdout)
            result = self.run_cli("scripts/audit_run.py", "report", "--run-dir", str(run_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            ledger.unlink()

            result = self.run_cli("scripts/audit_run.py", "report", "--run-dir", str(run_dir))
            self.assertNotEqual(result.returncode, 0)
            state = self.read(run_dir / "audit-state.json")
            self.assertEqual(state["status"], "INCOMPLETE_REVIEW")
            self.assertFalse(state["complete"])
            report = (run_dir / "AUDIT-REPORT.md").read_text(encoding="utf-8")
            self.assertIn("# INCOMPLETE AUDIT", report)
            self.assertNotIn("COMPLETE_CLEAN", report)

    def test_controller_routes_suspicious_records_to_proof(self) -> None:
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
            poc_path = run_dir / "poc/RetainedPoC.t.sol"
            poc_source = """// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.26;

contract RetainedPoC {
    function proof() external pure returns (uint256) {
        return 1;
    }
}
"""
            poc_path.parent.mkdir(parents=True)
            poc_path.write_text(poc_source, encoding="utf-8")
            poc_location = poc_path.relative_to(run_dir).as_posix()
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
            self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            screen_path = run_dir / "reviews/screen-results.json"
            screen = self.read(screen_path)
            candidate = screen["results"][0]
            candidate.update(result="CANDIDATE", scope_complete=False, evidence=[])
            evidence = [
                {"kind": "scope", "location": "fixture", "reason": "complete scope"},
                {"kind": "inheritance", "location": "fixture", "reason": "screen disposition"},
            ]
            for item in screen["results"][1:]:
                item.update(result="NOT_APPLICABLE_CONFIRMED", scope_complete=True, evidence=evidence)
            screen_path.write_text(json.dumps(screen, indent=2) + "\n", encoding="utf-8")
            result = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            self.assertIn("DEEP_REVIEW", result.stdout)
            self.assertEqual(
                json.loads(result.stdout)["recommended_execution"],
                {"provider": "codex", "model": "gpt-5.6-sol", "reasoning_effort": "high"},
            )

            manifest = self.read(run_dir / "routing/manifest.json")
            route = next(item for item in manifest["selected"] if item["canonical_id"] == candidate["canonical_id"])
            suspicious = {
                "record_type": "review",
                "schema_version": 7,
                "canonical_id": candidate["canonical_id"],
                "owner_domain": route["owner_domain"],
                "check_body_hash": route["check_body_hash"],
                "review_stage": "DEEP_REVIEW",
                "status": "SUSPICIOUS",
                "applicability": "APPLICABLE - fixture",
                "code_path": "fixture entry",
                "preconditions": "fixture state",
                "exploitability": "alternate path unresolved",
                "impact": "potential issue",
                "proof": "proof pending",
                "unresolved_reason": "proof pending",
                "evidence": [{"kind": "manual", "location": "fixture", "reason": "deep review"}],
            }
            ledger = run_dir / "reviews/review-evm-audit-general.jsonl"
            append(
                ledger,
                manifest,
                suspicious,
                self.read(ROOT / "data/canonical-checks.json"),
                {candidate["canonical_id"]},
                domain_context=context,
                screen_results=screen,
            )
            result = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PROOF", result.stdout)
            self.assertIn(candidate["canonical_id"], result.stdout)
            proof_payload = json.loads(result.stdout)
            self.assertEqual(proof_payload["progress"]["step"], 6)
            self.assertEqual(proof_payload["progress"]["label"], "PROOF")
            self.assertIn("suspicious findings require Proof", proof_payload["progress"]["summary"])
            proof_views = [Path(path) for path in proof_payload["runtime_views"]]
            self.assertEqual(len(proof_views), 1)
            self.assertTrue(proof_views[0].exists())
            proof_text = proof_views[0].read_text(encoding="utf-8")
            self.assertIn(f"[{candidate['canonical_id']}]", proof_text)
            self.assertNotIn("REVIEWED_SAFE", proof_text)
            proof_views[0].write_text(proof_text + "\nTAMPERED\n", encoding="utf-8")
            regenerated = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            self.assertEqual(regenerated.returncode, 0, regenerated.stderr)
            self.assertNotIn("TAMPERED", proof_views[0].read_text(encoding="utf-8"))
            proof_mtime = proof_views[0].stat().st_mtime_ns
            cached = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            self.assertEqual(cached.returncode, 0, cached.stderr)
            self.assertEqual(proof_views[0].stat().st_mtime_ns, proof_mtime)
            self.assertEqual(
                proof_payload["recommended_execution"],
                {"provider": "codex", "model": "gpt-5.6-sol", "reasoning_effort": "max"},
            )
            resolved = {
                **{key: value for key, value in suspicious.items() if key != "unresolved_reason"},
                "review_stage": "PROOF",
                "status": "REVIEWED_SAFE",
                "exploitability": "guard holds",
                "impact": "none",
                "proof": f"POC source retained at {poc_location}; fixture invariant holds",
                "preserved_invariant": "fixture invariant",
                "evidence": [{"kind": "test", "location": poc_location, "reason": "proof source and test result"}],
            }
            append(
                ledger,
                manifest,
                resolved,
                self.read(ROOT / "data/canonical-checks.json"),
                {candidate["canonical_id"]},
                domain_context=context,
                screen_results=screen,
            )
            result = self.run_cli("scripts/audit_run.py", "next", "--run-dir", str(run_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("REPORT", result.stdout)
            self.assertIn("COMPLETE_CLEAN", result.stdout)
            report_payload = json.loads(result.stdout)
            self.assertEqual(report_payload["progress"]["step"], 7)
            self.assertEqual(report_payload["progress"]["label"], "REPORT")
            for _ in range(2):
                result = self.run_cli("scripts/audit_run.py", "report", "--run-dir", str(run_dir))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(poc_path.read_text(encoding="utf-8"), poc_source)
                self.assertIn(poc_location, (run_dir / "reviews/review-evm-audit-general.jsonl").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
