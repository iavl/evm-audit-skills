#!/usr/bin/env python3
"""Real Slither regressions for the source navigation index."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from slither import Slither

from helpers import ROOT
from scripts.audit_artifacts import validate_schema
from scripts.code_context import _concrete_function, _slither_api, build_code_index, lookup, validate_code_index
from scripts.scope_context import scope_inventory


FIXTURE = ROOT / "tests/fixtures/code_context"


class CodeContextIntegrationTests(unittest.TestCase):
    def test_unsupported_slither_shape_names_pinned_version(self) -> None:
        api = _slither_api()
        with self.assertRaisesRegex(ValueError, rf"unsupported Slither callee shape.*{api['version']}"):
            _concrete_function(object(), api)

    def test_build_code_index_uses_real_slither_ir(self) -> None:
        solc = shutil.which("solc")
        if solc is None:
            self.fail("real Slither code-index coverage requires solc")
        slither = Slither(str(FIXTURE / "Main.sol"), solc=solc)
        files, _ = scope_inventory(FIXTURE)
        index = build_code_index(
            slither,
            FIXTURE,
            FIXTURE,
            set(files),
            "a" * 64,
            "b" * 64,
        )
        validate_code_index(ROOT, index)

        entry = next(key for key in index["functions"] if key.endswith("::Main.entry(uint256)"))
        helper = next(key for key in index["functions"] if key.endswith("::Main._helper(uint256)"))
        callee = next(key for key in index["functions"] if key.endswith("::Main._callee(uint256)"))
        service = next(key for key in index["functions"] if key.endswith("::Service.ping(uint256)"))
        library = next(key for key in index["functions"] if key.endswith("::MathLib.bump(uint256)"))

        self.assertIn(helper, index["functions"][entry]["internal_calls"])
        self.assertIn(callee, index["functions"][helper]["internal_calls"])
        self.assertIn(service, index["functions"][entry]["external_calls"])
        getter_edges = [
            call for call in index["external_calls"]
            if call["caller"] == entry and call["target"].startswith("high-level-getter:")
        ]
        self.assertTrue(getter_edges)
        self.assertTrue(all(call["target"] not in index["functions"] for call in getter_edges))
        self.assertEqual(
            sum(call["target"] == library for call in index["external_calls"]),
            1,
        )
        low_level = [call for call in index["external_calls"] if call["caller"] == entry and call["kind"] in {"call", "delegatecall"}]
        self.assertEqual({call["kind"] for call in low_level}, {"call", "delegatecall"})
        self.assertTrue(all(call["target"] not in index["functions"] for call in low_level))
        self.assertTrue(all(call["start_line"] > index["functions"][entry]["start_line"] for call in low_level))
        query = lookup(index, entry, include_callers=True, include_callees=True, depth=2)
        validate_schema(ROOT, "code-context-query.schema.json", query)
        self.assertIn(callee, query["functions"])
        self.assertTrue(any(edge["kind"] == "delegatecall" for edge in query["unresolved_edges"]))

        writes = [write for write in index["storage_writes"] if write["function"] in {entry, helper}]
        self.assertTrue(writes)
        self.assertTrue(all(write["variable"].endswith(".value") or write["variable"] == "value" for write in writes))
        self.assertTrue(all(write["start_line"] > index["functions"][write["function"]]["start_line"] for write in writes))
        self.assertNotIn("local", {write["variable"] for write in index["storage_writes"]})
        self.assertIn("local", index["functions"][entry]["local_writes"])

        self.assertIn(next(key for key in index["functions"] if key.endswith("::Base.auth()")), index["modifiers"])
        self.assertTrue(any(key.endswith("::Main.overloaded(uint256)") for key in index["functions"]))
        self.assertTrue(any(key.endswith("::Main.overloaded(address)") for key in index["functions"]))

        with self.assertRaisesRegex(ValueError, "ambiguous"):
            lookup(index, "Duplicate.same(uint256)")
        expanded = lookup(index, entry, include_callees=True)
        self.assertIn(entry, expanded["functions"])
        self.assertIn(helper, expanded["functions"])
        capped = lookup(index, entry, include_callees=True, depth=3, max_nodes=2)
        self.assertTrue(capped["truncated"])
        index["functions"][callee]["internal_calls"] = [entry]
        cycled = lookup(index, entry, include_callees=True, depth=50)
        self.assertLessEqual(len(cycled["functions"]), len(index["functions"]))
        self.assertFalse(cycled["truncated"])

    def test_index_paths_are_collision_safe_and_host_independent(self) -> None:
        solc = shutil.which("solc")
        if solc is None:
            self.fail("real Slither code-index coverage requires solc")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src"
            for subdir in (source / "a", source / "b"):
                subdir.mkdir(parents=True)
            (source / "Main.sol").write_text(
                'pragma solidity ^0.8.0; import "./a/Shared.sol"; import "./b/Shared.sol"; contract Main {}',
                encoding="utf-8",
            )
            for subdir, name in ((source / "a", "SharedA"), (source / "b", "SharedB")):
                (subdir / "Shared.sol").write_text(
                    f"pragma solidity ^0.8.0; contract {name} {{ function ping() external pure returns (uint256) {{ return 1; }} }}",
                    encoding="utf-8",
                )
            slither = Slither(str(source / "Main.sol"), solc=solc)
            files, _ = scope_inventory(source)
            index = build_code_index(slither, source, root, set(files), "a" * 64, "b" * 64)
            self.assertEqual(index["target_root"], "build://src")
            self.assertEqual(index["build_root"], "build://")
            self.assertEqual(
                {record["file"] for record in index["contracts"].values()},
                {"build://src/Main.sol", "build://src/a/Shared.sol", "build://src/b/Shared.sol"},
            )
            self.assertEqual(len(index["functions"]), 2)
            self.assertEqual(
                {key.split("::", 1)[0] for key in index["functions"]},
                {"build://src/a/Shared.sol", "build://src/b/Shared.sol"},
            )

    def test_dependency_paths_inside_build_root_are_not_reduced_to_basenames(self) -> None:
        solc = shutil.which("solc")
        if solc is None:
            self.fail("real Slither code-index coverage requires solc")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src"
            vendor = root / "vendor"
            source.mkdir()
            vendor.mkdir()
            target = root / "Target.sol"
            target.write_text(
                'pragma solidity ^0.8.0; import "./vendor/Shared.sol"; contract Target { Shared shared; }',
                encoding="utf-8",
            )
            (vendor / "Shared.sol").write_text(
                "pragma solidity ^0.8.0; contract Shared { function ping() external pure returns (uint256) { return 1; } }",
                encoding="utf-8",
            )
            slither = Slither(str(target), solc=solc)
            index = build_code_index(slither, root, root, {"Target.sol"}, "a" * 64, "b" * 64)
            self.assertTrue(any(record["file"] == "build://vendor/Shared.sol" for record in index["contracts"].values()))
            self.assertTrue(all(not str(value.get("file", "")).startswith("/") for value in index["contracts"].values()))
            self.assertTrue(all(not str(value.get("file", "")).startswith("/") for value in index["functions"].values()))


if __name__ == "__main__":
    unittest.main()
