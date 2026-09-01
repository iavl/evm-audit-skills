"""Pure, bounded queries over the optional code-index navigation hint."""

from __future__ import annotations

import json
from typing import Any

from evm_audit_runtime.limits import MAX_CODE_CONTEXT_EDGES, MAX_CODE_CONTEXT_NODES
from evm_audit_runtime.versions import CODE_CONTEXT_QUERY_VERSION


UNRESOLVED_TARGET_PREFIXES = (
    "internal-unresolved:",
    "high-level-getter:",
    "high-level-unresolved:",
    "library-unresolved:",
    "low-level:",
    "solidity:",
    "unresolved:",
)


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
    max_edges: int = MAX_CODE_CONTEXT_EDGES,
) -> dict[str, Any]:
    if depth < 0:
        raise ValueError("depth must be non-negative")
    if max_nodes < 1:
        raise ValueError("max_nodes must be positive")
    if max_edges < 1:
        raise ValueError("max_edges must be positive")
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
    caller_edges = [
        edge for edge in edges
        if include_callers and edge.get("target") in selected and edge.get("caller") in selected
    ]
    callee_edges = [
        edge for edge in edges
        if include_callees and edge.get("caller") in selected and edge.get("target") in selected
    ]
    boundary_edges = [
        edge for edge in edges
        if (edge.get("caller") in selected) != (edge.get("target") in selected)
        and edge.get("caller") in functions
        and edge.get("target") in functions
    ]
    unresolved_edges = [
        edge for edge in edges
        if edge.get("caller") in selected and edge.get("target") not in functions
    ]
    available_edges = [
        ("unresolved_edges", unresolved_edges),
        ("caller_edges", caller_edges),
        ("callee_edges", callee_edges),
        ("boundary_edges", boundary_edges),
    ]
    edge_count = sum(len(items) for _, items in available_edges)
    remaining = max_edges
    returned: dict[str, list[dict[str, Any]]] = {}
    for name, items in available_edges:
        returned[name] = items[:remaining]
        remaining -= len(returned[name])
    returned_edge_count = sum(len(items) for items in returned.values())
    return {
        "schema_version": CODE_CONTEXT_QUERY_VERSION,
        "source_digest": index["source_digest"],
        "compilation_input_digest": index["compilation_input_digest"],
        "functions": {key: functions[key] for key in sorted(selected)},
        "source_ranges": {key: index.get("source_ranges", {}).get(key) for key in sorted(selected)},
        "caller_edges": returned["caller_edges"],
        "callee_edges": returned["callee_edges"],
        "boundary_edges": returned["boundary_edges"],
        "unresolved_edges": returned["unresolved_edges"],
        "edge_count": edge_count,
        "returned_edge_count": returned_edge_count,
        "max_edges": max_edges,
        "edges_truncated": returned_edge_count < edge_count,
        "depth": depth,
        "max_nodes": max_nodes,
        "truncated": truncated,
    }


def validate_code_index(
    root: Any,
    value: dict[str, Any],
    *,
    source_digest: str | None = None,
    compilation_input_digest: str | None = None,
) -> None:
    """Validate schema, lineage, and relational consistency of a code index."""
    try:
        from scripts.audit_artifacts import validate_schema
    except ImportError:  # pragma: no cover - direct script execution
        from audit_artifacts import validate_schema

    validate_schema(root, "code-index.schema.json", value)
    if source_digest is not None and value["source_digest"] != source_digest:
        raise ValueError("code index source_digest does not match Recon")
    if compilation_input_digest is not None and value["compilation_input_digest"] != compilation_input_digest:
        raise ValueError("code index compilation_input_digest does not match Recon")
    functions = value["functions"]
    contracts = value["contracts"]
    source_ranges = value["source_ranges"]
    modifiers = value["modifiers"]
    inheritance = value["inheritance"]
    if set(functions) != set(source_ranges):
        raise ValueError("code index functions and source_ranges must have the same keys")
    if set(functions) != set(modifiers):
        raise ValueError("code index functions and modifiers must have the same keys")
    if set(contracts) != set(inheritance):
        raise ValueError("code index contracts and inheritance must have the same keys")

    for contract_id, contract in contracts.items():
        if contract["start_line"] > contract["end_line"]:
            raise ValueError(f"code index contract range is inverted: {contract_id}")
        if contract["bases"] != inheritance[contract_id]:
            raise ValueError(f"code index inheritance does not match contract bases: {contract_id}")
        for base_id in inheritance[contract_id]:
            if base_id not in contracts:
                raise ValueError(f"code index inheritance references missing contract: {base_id}")

    for function_id, function in functions.items():
        if function["function_id"] != function_id:
            raise ValueError(f"code index function_id does not match key: {function_id}")
        contract_id = function["contract_id"]
        if contract_id not in contracts:
            raise ValueError(f"code index function references missing contract: {function_id}")
        if function["start_line"] > function["end_line"]:
            raise ValueError(f"code index function range is inverted: {function_id}")
        expected_range = {
            "file": function["file"],
            "start_line": function["start_line"],
            "end_line": function["end_line"],
        }
        if source_ranges[function_id] != expected_range:
            raise ValueError(f"code index source range does not match function: {function_id}")
        if function["modifiers"] != modifiers[function_id]:
            raise ValueError(f"code index modifiers do not match function: {function_id}")
        for target in function["internal_calls"]:
            if target not in functions:
                raise ValueError(f"code index internal call references missing function: {target}")
        for target in function["external_calls"]:
            if target not in functions and not _is_unresolved_target(target):
                raise ValueError(f"code index external call references unknown concrete function: {target}")

    events_by_caller: dict[str, list[dict[str, Any]]] = {function_id: [] for function_id in functions}
    for event in value["external_calls"]:
        caller = event["caller"]
        if caller not in functions:
            raise ValueError(f"code index call event references missing caller: {caller}")
        target = event["target"]
        if target not in functions and not _is_unresolved_target(target):
            raise ValueError(f"code index call event references unknown concrete function: {target}")
        events_by_caller[caller].append(event)

    for function_id, function in functions.items():
        events = events_by_caller[function_id]
        internal_targets = {event["target"] for event in events if event["kind"] == "internal" and event["target"] in functions}
        external_targets = {event["target"] for event in events if event["kind"] != "internal"}
        if set(function["internal_calls"]) != internal_targets:
            raise ValueError(f"code index internal call list is inconsistent with call events: {function_id}")
        if set(function["external_calls"]) != external_targets:
            raise ValueError(f"code index external call list is inconsistent with call events: {function_id}")

    for write in value["storage_writes"]:
        if write["function"] not in functions:
            raise ValueError(f"code index storage write references missing function: {write['function']}")


def _is_unresolved_target(target: str) -> bool:
    return target.startswith(UNRESOLVED_TARGET_PREFIXES)
