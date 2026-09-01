#!/usr/bin/env python3
"""Compilation-closure provenance and build-root boundary regressions."""

from __future__ import annotations

from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
import unittest

from helpers import ROOT
from scripts.recon import build_feature_map, compilation_unit_paths
from scripts.scope_context import _submodule_commits


def fake_slither(*paths: Path) -> SimpleNamespace:
    return SimpleNamespace(
        crytic_compile=SimpleNamespace(
            compilation_units={
                "unit": SimpleNamespace(
                    filenames=[SimpleNamespace(absolute=str(path)) for path in paths]
                )
            }
        )
    )


class CompilationLineageTests(unittest.TestCase):
    def test_submodule_provenance_distinguishes_git_states_and_failures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(_submodule_commits(root, ("lib",)), "NO_GIT_WORKTREE")

            git_root = root / "git"
            git_root.mkdir()
            subprocess.run(["git", "init", str(git_root)], check=True, capture_output=True, text=True)
            self.assertEqual(_submodule_commits(git_root, ("lib",)), "NO_GITLINKS")
            gitlink_hash = "a" * 40
            subprocess.run(
                ["git", "update-index", "--add", "--cacheinfo", f"160000,{gitlink_hash},lib/vendor"],
                cwd=git_root,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(_submodule_commits(git_root, ("lib",)), f"160000 {gitlink_hash} 0\tlib/vendor")

            with patch(
                "scripts.scope_context.subprocess.run",
                side_effect=[
                    SimpleNamespace(returncode=0, stdout="true\n", stderr=""),
                    SimpleNamespace(returncode=1, stdout="", stderr="git failure"),
                ],
            ):
                with self.assertRaisesRegex(ValueError, "cannot inspect Git submodule entries"):
                    _submodule_commits(git_root, ("lib",))

    def test_exact_closure_is_returned_and_missing_api_uses_none(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src/Target.sol"
            source.parent.mkdir()
            source.write_text("pragma solidity ^0.8.0; contract Target {}", encoding="utf-8")
            self.assertEqual(compilation_unit_paths(fake_slither(source), root), ["src/Target.sol"])
            self.assertIsNone(compilation_unit_paths(SimpleNamespace(crytic_compile=SimpleNamespace(compilation_units={})), root))

    def test_out_of_root_compiled_source_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "src/Target.sol"
            sibling = root.parent / f"{root.name}-dependency.sol"
            target.parent.mkdir()
            target.write_text("pragma solidity ^0.8.0; contract Target {}", encoding="utf-8")
            sibling.write_text("pragma solidity ^0.8.0; contract Dependency {}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "compiled source is outside build_root"):
                compilation_unit_paths(fake_slither(target, sibling), root)

    def test_symlink_resolves_before_build_root_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root.parent / f"{root.name}-outside.sol"
            link = root / "src/Dependency.sol"
            link.parent.mkdir(parents=True)
            outside.write_text("pragma solidity ^0.8.0; contract Dependency {}", encoding="utf-8")
            link.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "compiled source is outside build_root"):
                compilation_unit_paths(fake_slither(link), root)

    def test_recon_does_not_downgrade_out_of_root_closure_to_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            target = project / "src/Target.sol"
            sibling = project.parent / f"{project.name}-dependency.sol"
            target.parent.mkdir()
            target.write_text("pragma solidity ^0.8.0; contract Target {}", encoding="utf-8")
            sibling.write_text("pragma solidity ^0.8.0; contract Dependency {}", encoding="utf-8")
            fake = fake_slither(target, sibling)
            with patch("scripts.recon.ensure_slither_import", return_value=lambda *_args, **_kwargs: fake):
                with self.assertRaisesRegex(ValueError, "choose a build_root"):
                    build_feature_map(ROOT, target, None, False, build_root=project)

    def test_recon_records_build_root_fallback_when_closure_api_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            target = project / "Target.sol"
            target.write_text("pragma solidity ^0.8.0; contract Target {}", encoding="utf-8")
            fake = SimpleNamespace(crytic_compile=SimpleNamespace(compilation_units={}), contracts=[])
            with patch("scripts.recon.ensure_slither_import", return_value=lambda *_args, **_kwargs: fake):
                result = build_feature_map(ROOT, target, None, False, build_root=project)
            self.assertEqual(
                result["recon_context"]["recon_quality"]["compilation_provenance"],
                "CONSERVATIVE_BUILD_ROOT_FALLBACK",
            )


if __name__ == "__main__":
    unittest.main()
