"""Pure, bounded queries over the optional code-index navigation hint."""

from __future__ import annotations

import json
from typing import Any

from evm_audit_runtime.limits import MAX_CODE_CONTEXT_NODES
from evm_audit_runtime.versions import CODE_CONTEXT_QUERY_VERSION


def _select_function(functions: dict[str, Any], requested: str) -> str:
    if requested in functions:
        return requested
    matches = sorted(
        key
        for key in functions
        if key.endswith(f"::{requested}") or key.rsplit("::", 1)[-1] == requested
    )
    if not matches:
        raise ValueError(f"function not found in code index: {requested}")
    if len(matches) > 1:
        raise ValueError(f"ambiguous function in code index: {requested}; candidates: {', '.join(matches)}")
    return matches[0]


def lookup(
    index: dict[str, Any],
    function: str,
    *,
    include_callers: bool = False,
    include_callees: bool = False,
    depth: int = 1,
    max_nodes: int = MAX_CODE_CONTEXT_NODES,
) -> dict[str, Any]:
    if depth < 0:
        raise ValueError("depth must be non-negative")
    if max_nodes < 1:
        raise ValueError("max_nodes must be positive")
    functions = index.get("functions", {})
    root = _select_function(functions, function)
    selected = {root}
    outgoing = {
        key: sorted(
            set([*value.get("internal_calls", []), *value.get("external_calls", [])]) & set(functions)
        )
        for key, value in functions.items()
    }
    incoming: dict[str, list[str]] = {key: [] for key in functions}
    for caller, targets in outgoing.items():
        for target in targets:
            incoming[target].append(caller)
    for targets in incoming.values():
        targets.sort()

    frontier = [root]
    truncated = False
    for _ in range(depth):
        next_frontier: list[str] = []
        for current in frontier:
            neighbors = []
            if include_callees:
                neighbors.extend(outgoing[current])
            if include_callers:
                neighbors.extend(incoming[current])
            for neighbor in sorted(set(neighbors)):
                if neighbor in selected:
                    continue
                if len(selected) >= max_nodes:
                    truncated = True
                    continue
                selected.add(neighbor)
                next_frontier.append(neighbor)
        frontier = next_frontier
        if not frontier:
            break

    edges = list(index.get("external_calls", []))
    known_edges = {(edge.get("caller"), edge.get("target"), edge.get("kind")) for edge in edges}
    for caller, value in functions.items():
        for target in value.get("internal_calls", []):
            if (caller, target, "internal") not in known_edges:
                edges.append({
                    "caller": caller,
                    "target": target,
                    "kind": "internal",
                    "file": value["file"],
                    "start_line": value["start_line"],
                    "location_fallback": True,
                })
        for target in value.get("external_calls", []):
            if not any(edge.get("caller") == caller and edge.get("target") == target for edge in edges):
                edges.append({
                    "caller": caller,
                    "target": target,
                    "kind": "external",
                    "file": value["file"],
                    "start_line": value["start_line"],
                    "location_fallback": True,
                })
    edges.sort(key=lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return {
        "schema_version": CODE_CONTEXT_QUERY_VERSION,
        "source_digest": index["source_digest"],
        "compilation_input_digest": index["compilation_input_digest"],
        "functions": {key: functions[key] for key in sorted(selected)},
        "source_ranges": {key: index.get("source_ranges", {}).get(key) for key in sorted(selected)},
        "caller_edges": [
            edge for edge in edges
            if include_callers and edge.get("target") in selected and edge.get("caller") in selected
        ],
        "callee_edges": [
            edge for edge in edges
            if include_callees and edge.get("caller") in selected and edge.get("target") in selected
        ],
        "boundary_edges": [
            edge for edge in edges
            if (edge.get("caller") in selected) != (edge.get("target") in selected)
            and edge.get("caller") in functions
            and edge.get("target") in functions
        ],
        "unresolved_edges": [
            edge for edge in edges
            if edge.get("caller") in selected and edge.get("target") not in functions
        ],
        "depth": depth,
        "max_nodes": max_nodes,
        "truncated": truncated,
    }
