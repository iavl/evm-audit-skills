from __future__ import annotations

import contextlib
import hashlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evm_audit_runtime.repository_trust import (
    git_metadata_kind,
    inspect_repository,
    prepare_repository,
    sanitize_snapshot,
)
from scripts.recon import build_feature_map
from scripts.repository_preflight import main as preflight_main
from helpers import ROOT


class RepositoryTrustTests(unittest.TestCase):
    def test_trust_gate_matrix_and_all_git_metadata_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            for trust in ("TRUSTED", "UNTRUSTED", "UNKNOWN"):
                result = inspect_repository(root, trust)
                self.assertEqual(result["git_metadata"], "ABSENT")
                self.assertTrue(result["direct_agent_open_allowed"])
                self.assertEqual(result["required_action"], "OPEN")

            shapes = {
                "DIRECTORY": lambda marker: marker.mkdir(),
                "FILE": lambda marker: marker.write_text("gitdir: /tmp/elsewhere\n", encoding="utf-8"),
                "SYMLINK": lambda marker: marker.symlink_to(root / "missing-git"),
            }
            for expected, create in shapes.items():
                marker = root / ".git"
                create(marker)
                self.assertEqual(git_metadata_kind(root), expected)
                for trust in ("UNTRUSTED", "UNKNOWN"):
                    result = inspect_repository(root, trust)
                    self.assertEqual(result["git_metadata"], "PRESENT")
                    self.assertEqual(result["git_metadata_kind"], expected)
                    self.assertFalse(result["direct_agent_open_allowed"])
                    self.assertEqual(result["required_action"], "SANITIZE")
                self.assertTrue(inspect_repository(root, "TRUSTED")["direct_agent_open_allowed"])
                marker.unlink() if marker.is_symlink() or marker.is_file() else marker.rmdir()

            marker = root / ".git"
            if hasattr(os, "mkfifo"):
                os.mkfifo(marker)
                self.assertEqual(git_metadata_kind(root), "OTHER")
                self.assertFalse(inspect_repository(root, "UNKNOWN")["direct_agent_open_allowed"])

    def test_sanitized_snapshot_preserves_sources_and_omits_git(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            destination = base / "snapshot"
            (source / "src").mkdir(parents=True)
            (source / "src/Target.sol").write_bytes(b"contract Target {}\n")
            (source / ".git").mkdir()
            (source / ".git/HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            result = sanitize_snapshot(source, destination)
            self.assertEqual((destination / "src/Target.sol").read_bytes(), b"contract Target {}\n")
            self.assertFalse((destination / ".git").exists())
            self.assertEqual(result["snapshot_root"], str(destination.resolve()))
            expected = hashlib.sha256()
            data = b"contract Target {}\n"
            expected.update(b"src/Target.sol\0")
            expected.update(str(len(data)).encode("ascii"))
            expected.update(b"\0" + data + b"\0")
            self.assertEqual(result["snapshot_sha256"], expected.hexdigest())
            self.assertTrue((source / ".git/HEAD").exists())

    def test_sanitization_rejects_external_symlink_without_partial_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            destination = base / "snapshot"
            source.mkdir()
            (source / "Target.sol").write_text("contract Target {}\n", encoding="utf-8")
            (source / "external").symlink_to(base / "outside")
            with self.assertRaisesRegex(ValueError, "rejects symlink"):
                sanitize_snapshot(source, destination)
            self.assertFalse(destination.exists())

    def test_prepare_repository_relocates_blocked_original_without_git_calls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "repo"
            target = source / "src/Target.sol"
            target.parent.mkdir(parents=True)
            target.write_text("pragma solidity ^0.8.0; contract Target {}\n", encoding="utf-8")
            (source / ".git").mkdir()
            prepared = prepare_repository(
                target,
                source / "src",
                source,
                source_trust="UNKNOWN",
                snapshot_destination=base / "sanitized",
            )
            self.assertTrue(prepared.trust["sanitized"])
            self.assertEqual(prepared.build_root, (base / "sanitized").resolve())
            self.assertEqual(prepared.target, (base / "sanitized/src/Target.sol").resolve())
            self.assertFalse((prepared.build_root / ".git").exists())
            self.assertTrue((source / ".git").exists())

    def test_recon_blocks_original_before_slither(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "repo"
            target = source / "Target.sol"
            source.mkdir()
            target.write_text("pragma solidity ^0.8.0; contract Target {}\n", encoding="utf-8")
            (source / ".git").mkdir()
            with patch("scripts.recon.ensure_slither_import") as slither:
                with self.assertRaisesRegex(ValueError, "repository trust gate blocked"):
                    build_feature_map(ROOT, target, None, False, build_root=source)
            slither.assert_not_called()

    def test_preflight_can_sanitize_without_target_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "repo"
            source.mkdir()
            (source / "Target.sol").write_text("contract Target {}\n", encoding="utf-8")
            (source / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    preflight_main([
                        str(source), "--source-trust", "UNKNOWN",
                        "--sanitize-to", str(base / "snapshot"),
                    ]),
                    0,
                )
            self.assertTrue((base / "snapshot/Target.sol").exists())
            self.assertNotIn(".git", list(path.name for path in (base / "snapshot").iterdir()))
            self.assertIn('"required_action": "SANITIZE"', output.getvalue())


if __name__ == "__main__":
    unittest.main()
