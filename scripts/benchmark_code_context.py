#!/usr/bin/env python3
"""Measure deterministic code-index and bounded query sizes."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from slither import Slither

from evm_audit_runtime.code_index import lookup, validate_code_index
from evm_audit_runtime.limits import MAX_CODE_CONTEXT_EDGES, MAX_CODE_CONTEXT_NODES
from evm_audit_runtime.versions import CODE_CONTEXT_BENCHMARK_VERSION

try:
    from audit_artifacts import validate_schema
    from code_context import build_code_index
    from scope_context import compilation_digests, scope_inventory
except ImportError:  # pragma: no cover
    from scripts.audit_artifacts import validate_schema
    from scripts.code_context import build_code_index
    from scripts.scope_context import compilation_digests, scope_inventory


ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "simple-erc20": (ROOT / "tests/fixtures/e2e/erc20/Main.sol", "::ERC20Surface.deposit(uint256)", 50_000, 50_000),
    "inheritance-hub": (ROOT / "tests/fixtures/code_context/Main.sol", "::Main.entry(uint256)", 100_000, 100_000),
    "delegatecall-proxy": (ROOT / "tests/fixtures/e2e/proxy/Main.sol", "::UpgradeableProxySurface.forward(address,bytes)", 50_000, 50_000),
}


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def run_case(
    name: str,
    target: Path,
    suffix: str,
    solc: str,
    max_nodes: int,
    max_edges: int,
    max_index_bytes: int,
    max_query_bytes: int,
) -> dict[str, object]:
    target_root = target.parent.resolve()
    files, _ = scope_inventory(target_root)
    digests = compilation_digests(
        target_root,
        files,
        "0.8.24",
        build_root=target_root,
    )
    index = build_code_index(
        Slither(str(target), solc=solc),
        target_root,
        target_root,
        set(files),
        digests["audit_source_digest"],
        digests["compilation_input_digest"],
    )
    validate_code_index(ROOT, index)
    function = next((key for key in sorted(index["functions"]) if key.endswith(suffix)), None)
    if function is None:
        raise ValueError(f"{name}: benchmark function not found: {suffix}")
    query = lookup(
        index,
        function,
        include_callers=True,
        include_callees=True,
        depth=2,
        max_nodes=max_nodes,
        max_edges=max_edges,
    )
    validate_schema(ROOT, "code-context-query.schema.json", query)
    index_bytes = len(_json_bytes(index))
    query_bytes = len(_json_bytes(query))
    if index_bytes > max_index_bytes or query_bytes > max_query_bytes:
        raise ValueError(
            f"{name}: code-context size exceeds budget "
            f"index={index_bytes}/{max_index_bytes} query={query_bytes}/{max_query_bytes}"
        )
    result = {
        "schema_version": CODE_CONTEXT_BENCHMARK_VERSION,
        "name": name,
        "index_bytes": index_bytes,
        "query_bytes": query_bytes,
        "selected_nodes": len(query["functions"]),
        "edge_count": query["edge_count"],
        "unique_edge_count": query["unique_edge_count"],
        "returned_edge_count": query["returned_edge_count"],
        "serialized_edge_count": query["serialized_edge_count"],
        "unresolved_edge_count": len(query["unresolved_edges"]),
        "truncated": query["truncated"],
        "edges_truncated": query["edges_truncated"],
    }
    validate_schema(ROOT, "code-context-benchmark.schema.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solc", default=shutil.which("solc"))
    parser.add_argument("--max-nodes", type=int, default=MAX_CODE_CONTEXT_NODES)
    parser.add_argument("--max-edges", type=int, default=MAX_CODE_CONTEXT_EDGES)
    args = parser.parse_args(argv)
    try:
        if not args.solc:
            raise ValueError("code-context benchmark requires solc")
        if args.max_nodes < 1 or args.max_edges < 1:
            raise ValueError("code-context benchmark limits must be positive")
        for name, (target, suffix, max_index_bytes, max_query_bytes) in CASES.items():
            print(json.dumps(run_case(name, target, suffix, args.solc, args.max_nodes, args.max_edges, max_index_bytes, max_query_bytes), sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
