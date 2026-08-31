#!/usr/bin/env python3
"""CLI-level tests for the complete audit artifact lifecycle."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import EMPTY_TARGET, ROOT


class LifecycleTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *arguments],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    @staticmethod
    def read(path: Path) -> dict[str, object]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def write(path: Path, value: dict[str, object]) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def run_explicit(self, directory: Path) -> dict[str, Path]:
        feature_map = directory / "feature-map.json"
        manifest = directory / "manifest.json"
        context = directory / "context.json"
        resolution = directory / "domain-resolution.json"
        domain_context = directory / "domain-context.json"
        screen = directory / "screen.md"
        screen_results = directory / "screen-results.json"
        deep = directory / "deep.md"
        state = directory / "audit-state.json"

        result = self.run_cli(
            "scripts/recon.py",
            str(EMPTY_TARGET),
            "--audit-root",
            str(EMPTY_TARGET),
            "--output",
            str(feature_map),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_cli(
            "scripts/select_checks.py",
            "--feature-map",
            str(feature_map),
            "--target-root",
            str(EMPTY_TARGET),
            "--domain",
            "evm-audit-general",
            "--manifest-out",
            str(manifest),
            "--context-out",
            str(context),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_cli(
            "scripts/render_runtime.py",
            "--manifest",
            str(manifest),
            "--profile",
            "screen",
            "--output",
            str(screen),
            "--domain-resolution-out",
            str(resolution),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_cli(
            "scripts/render_runtime.py",
            "--manifest",
            str(manifest),
            "--profile",
            "screen",
            "--domain-resolution",
            str(resolution),
            "--domain-context-out",
            str(domain_context),
            "--output",
            str(screen),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return {
            "feature_map": feature_map,
            "manifest": manifest,
            "context": context,
            "resolution": resolution,
            "domain_context": domain_context,
            "screen": screen,
            "screen_results": screen_results,
            "deep": deep,
            "state": state,
        }

    def fill_domain_context(self, path: Path) -> None:
        value = self.read(path)
        for requirements in value["domains"].values():
            for item in requirements.values():
                item.update(
                    status="KNOWN",
                    value="fixture context",
                    evidence=[{"kind": "scope", "location": "fixture", "reason": "complete scope"}],
                )
        self.write(path, value)

    def render_screen_results(self, paths: dict[str, Path]) -> dict[str, object]:
        result = self.run_cli(
            "scripts/render_runtime.py",
            "--manifest",
            str(paths["manifest"]),
            "--profile",
            "screen",
            "--domain-resolution",
            str(paths["resolution"]),
            "--domain-context",
            str(paths["domain_context"]),
            "--screen-results-out",
            str(paths["screen_results"]),
            "--output",
            str(paths["screen"]),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.read(paths["screen_results"])

    def mark_all_not_applicable(self, path: Path) -> None:
        value = self.read(path)
        evidence = [
            {"kind": "scope", "location": "fixture", "reason": "complete scope"},
            {"kind": "source", "location": "fixture", "reason": "trigger absent"},
        ]
        for result in value["results"]:
            result.update(result="NOT_APPLICABLE_CONFIRMED", scope_complete=True, evidence=evidence)
        self.write(path, value)

    def finalize(self, paths: dict[str, Path], *ledger: Path) -> dict[str, object]:
        arguments = [
            "scripts/validate_audit_run.py",
            "--manifest",
            str(paths["manifest"]),
            "--context",
            str(paths["context"]),
            "--domain-resolution",
            str(paths["resolution"]),
            "--domain-context",
            str(paths["domain_context"]),
            "--screen-results",
            str(paths["screen_results"]),
        ]
        for path in ledger:
            arguments.extend(["--ledger", str(path)])
        arguments.extend(["--output", str(paths["state"])])
        result = self.run_cli(*arguments)
        self.assertTrue(paths["state"].exists(), result.stderr or result.stdout)
        return self.read(paths["state"])

    def review_one_candidate(self, paths: dict[str, Path], status: str) -> tuple[dict[str, object], Path]:
        screen = self.render_screen_results(paths)
        candidate = screen["results"][0]["canonical_id"]
        value = self.read(paths["screen_results"])
        evidence = [
            {"kind": "scope", "location": "fixture", "reason": "complete scope"},
            {"kind": "source", "location": "fixture", "reason": "candidate requires review"},
        ]
        for result in value["results"][1:]:
            result.update(result="NOT_APPLICABLE_CONFIRMED", scope_complete=True, evidence=evidence)
        self.write(paths["screen_results"], value)
        manifest = self.read(paths["manifest"])
        route = next(item for item in manifest["selected"] if item["canonical_id"] == candidate)
        record = {
            "record_type": "review",
            "schema_version": 4,
            "canonical_id": candidate,
            "owner_domain": route["owner_domain"],
            "check_body_hash": route["check_body_hash"],
            "review_stage": "PROOF" if status == "CONFIRMED" else "DEEP_REVIEW",
            "status": status,
            "applicability": "APPLICABLE — fixture path exists",
            "code_path": "fixture entry",
            "preconditions": "fixture precondition",
            "exploitability": "fixture path is reachable",
            "impact": "fixture impact",
            "proof": "deterministic fixture proof",
            "evidence": [{"kind": "test", "location": "tests/test_lifecycle.py", "reason": "deterministic fixture proof"}],
        }
        if status == "REVIEWED_SAFE":
            record["preserved_invariant"] = "fixture invariant holds"
        record_path = paths["manifest"].parent / "record.json"
        self.write(record_path, record)
        ledger = paths["manifest"].parent / "review-evm-audit-general.jsonl"
        result = self.run_cli(
            "scripts/review_ledger.py",
            "--manifest",
            str(paths["manifest"]),
            "--screen-results",
            str(paths["screen_results"]),
            "--ledger",
            str(ledger),
            "--append-record",
            str(record_path),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_cli(
            "scripts/render_runtime.py",
            "--manifest",
            str(paths["manifest"]),
            "--profile",
            "deep",
            "--domain-resolution",
            str(paths["resolution"]),
            "--domain-context",
            str(paths["domain_context"]),
            "--screen-results",
            str(paths["screen_results"]),
            "--output",
            str(paths["deep"]),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.finalize(paths, ledger), ledger

    def test_full_clean_audit_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self.run_explicit(Path(directory))
            self.fill_domain_context(paths["domain_context"])
            self.render_screen_results(paths)
            self.mark_all_not_applicable(paths["screen_results"])
            state = self.finalize(paths)
        self.assertEqual(state["status"], "COMPLETE")
        self.assertTrue(state["clean"])
        self.assertEqual(state["coverage"]["confirmed"], [])

    def test_full_reviewed_safe_audit_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self.run_explicit(Path(directory))
            self.fill_domain_context(paths["domain_context"])
            state, _ = self.review_one_candidate(paths, "REVIEWED_SAFE")
        self.assertEqual(state["status"], "COMPLETE")
        self.assertTrue(state["clean"])

    def test_full_confirmed_audit_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self.run_explicit(Path(directory))
            self.fill_domain_context(paths["domain_context"])
            state, _ = self.review_one_candidate(paths, "CONFIRMED")
        self.assertEqual(state["status"], "COMPLETE")
        self.assertFalse(state["clean"])
        self.assertEqual(len(state["coverage"]["confirmed"]), 1)

    def test_full_unresolved_context_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self.run_explicit(Path(directory))
            self.render_screen_results(paths)
            result = self.run_cli(
                "scripts/render_runtime.py",
                "--manifest",
                str(paths["manifest"]),
                "--profile",
                "deep",
                "--domain-resolution",
                str(paths["resolution"]),
                "--domain-context",
                str(paths["domain_context"]),
                "--screen-results",
                str(paths["screen_results"]),
                "--output",
                str(paths["deep"]),
            )
            self.assertNotEqual(result.returncode, 0)
            state = self.finalize(paths)
        self.assertEqual(state["status"], "COMPLETE_WITH_UNRESOLVED_CONTEXT")

    def automatic_run(self, directory: Path) -> dict[str, Path]:
        feature_map = directory / "feature-map.json"
        manifest = directory / "manifest.json"
        context = directory / "context.json"
        resolution = directory / "domain-resolution.json"
        domain_context = directory / "domain-context.json"
        screen = directory / "screen.md"
        screen_results = directory / "screen-results.json"
        deep = directory / "deep.md"
        state = directory / "audit-state.json"
        result = self.run_cli(
            "scripts/recon.py",
            str(EMPTY_TARGET),
            "--audit-root",
            str(EMPTY_TARGET),
            "--output",
            str(feature_map),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_cli(
            "scripts/select_checks.py",
            "--feature-map",
            str(feature_map),
            "--target-root",
            str(EMPTY_TARGET),
            "--manifest-out",
            str(manifest),
            "--context-out",
            str(context),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_cli(
            "scripts/render_runtime.py",
            "--manifest",
            str(manifest),
            "--profile",
            "screen",
            "--output",
            str(screen),
            "--domain-resolution-out",
            str(resolution),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return {"feature_map": feature_map, "manifest": manifest, "context": context, "resolution": resolution, "domain_context": domain_context, "screen": screen, "screen_results": screen_results, "deep": deep, "state": state}

    def resolve_deferred(self, paths: dict[str, Path], present: str | None) -> None:
        value = self.read(paths["resolution"])
        for domain in value["domains"]:
            if domain == present:
                value["domains"][domain] = {"status": "PRESENT", "scope_complete": False, "evidence": [{"kind": "source", "location": "fixture", "reason": "surface present"}]}
            else:
                value["domains"][domain] = {"status": "ABSENT_CONFIRMED", "scope_complete": True, "evidence": [{"kind": "scope", "location": "fixture", "reason": "complete scope"}]}
        self.write(paths["resolution"], value)

    def render_resolved_automatic(self, paths: dict[str, Path]) -> None:
        result = self.run_cli(
            "scripts/render_runtime.py",
            "--manifest",
            str(paths["manifest"]),
            "--profile",
            "screen",
            "--domain-resolution",
            str(paths["resolution"]),
            "--domain-context-out",
            str(paths["domain_context"]),
            "--output",
            str(paths["screen"]),
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_full_deferred_unknown_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self.automatic_run(Path(directory))
            manifest = self.read(paths["manifest"])
            self.assertTrue(manifest["deferred_domains"])
            self.render_resolved_automatic(paths)
            self.fill_domain_context(paths["domain_context"])
            self.render_screen_results(paths)
            result = self.run_cli(
                "scripts/render_runtime.py",
                "--manifest",
                str(paths["manifest"]),
                "--profile",
                "deep",
                "--domain-resolution",
                str(paths["resolution"]),
                "--domain-context",
                str(paths["domain_context"]),
                "--screen-results",
                str(paths["screen_results"]),
                "--output",
                str(paths["deep"]),
            )
            self.assertNotEqual(result.returncode, 0)
            state = self.finalize(paths)
        self.assertNotEqual(state["status"], "COMPLETE")

    def test_full_deferred_present_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = self.automatic_run(Path(directory))
            manifest = self.read(paths["manifest"])
            present = manifest["deferred_domains"][0]["domain"]
            self.resolve_deferred(paths, present)
            self.render_resolved_automatic(paths)
            self.fill_domain_context(paths["domain_context"])
            screen = self.render_screen_results(paths)
            present_ids = {
                entry["canonical_id"]
                for entry in manifest["deferred"]
                if present in entry["domains"]
            }
            screened_ids = {entry["canonical_id"] for entry in screen["results"]}
            self.assertTrue(present_ids <= screened_ids)
            result = self.run_cli(
                "scripts/render_runtime.py",
                "--manifest",
                str(paths["manifest"]),
                "--profile",
                "deep",
                "--domain-resolution",
                str(paths["resolution"]),
                "--domain-context",
                str(paths["domain_context"]),
                "--screen-results",
                str(paths["screen_results"]),
                "--output",
                str(paths["deep"]),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.mark_all_not_applicable(paths["screen_results"])
            state = self.finalize(paths)
        self.assertEqual(state["status"], "COMPLETE")

    def test_full_snapshot_drift_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target"
            target.mkdir()
            source = target / "Main.sol"
            source.write_text("pragma solidity ^0.8.0; contract Main {}\n", encoding="utf-8")
            feature_map = Path(directory) / "feature-map.json"
            manifest = Path(directory) / "manifest.json"
            result = self.run_cli("scripts/recon.py", str(source), "--audit-root", str(target), "--output", str(feature_map))
            self.assertEqual(result.returncode, 0, result.stderr)
            result = self.run_cli("scripts/select_checks.py", "--feature-map", str(feature_map), "--target-root", str(target), "--domain", "evm-audit-general", "--manifest-out", str(manifest))
            self.assertEqual(result.returncode, 0, result.stderr)
            source.write_text("pragma solidity ^0.8.0; contract Main { uint256 value; }\n", encoding="utf-8")
            result = self.run_cli("scripts/render_runtime.py", "--manifest", str(manifest), "--profile", "screen", "--output", str(Path(directory) / "screen.md"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Target source/build inputs changed after routing", result.stderr)


if __name__ == "__main__":
    unittest.main()
