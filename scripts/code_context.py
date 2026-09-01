#!/usr/bin/env python3
"""Build and query a small, snapshot-bound Solidity navigation index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from audit_artifacts import load_json, validate_schema
    from scope_context import relative_scope_path
except ImportError:  # pragma: no cover
    from scripts.audit_artifacts import load_json, validate_schema
    from scripts.scope_context import relative_scope_path


ROOT = Path(__file__).resolve().parents[1]


def _location(value: Any, scope_root: Path, audit_files: set[str]) -> tuple[str, int, int, str]:
    mapping = getattr(value, "source_mapping", None)
    filename = getattr(getattr(mapping, "filename", None), "absolute", None)
    lines = getattr(mapping, "lines", None) or []
    if not filename or not lines:
        return "unknown", 1, 1, "UNKNOWN"
    absolute = Path(str(filename)).resolve()
    if scope_root.is_file():
        relative = scope_root.name if absolute == scope_root.resolve() else absolute.name
        origin = "AUDIT_SCOPE" if absolute == scope_root.resolve() else "DEPENDENCY"
    else:
        relative = relative_scope_path(scope_root, absolute) or str(absolute)
        origin = "AUDIT_SCOPE" if relative in audit_files else "DEPENDENCY"
    values = [int(line) for line in lines if isinstance(line, int) and line > 0]
    return relative, min(values or [1]), max(values or [1]), origin


def _name(value: Any) -> str:
    full_name = getattr(value, "full_name", None)
    name = full_name if isinstance(full_name, str) and full_name else getattr(value, "name", "")
    contract = getattr(getattr(value, "contract", None), "name", "")
    if contract and isinstance(name, str) and not name.startswith(f"{contract}."):
        return f"{contract}.{name}"
    return str(name)


def _text_values(values: Any) -> list[str]:
    return sorted({str(value) for value in (values or []) if str(value).strip()})


def _function_key(contract: Any, function: Any) -> str:
    full_name = getattr(function, "full_name", None)
    name = full_name if isinstance(full_name, str) and full_name else getattr(function, "name", "")
    return f"{getattr(contract, 'name', '')}.{name}"


def build_code_index(
    slither: Any,
    scope_root: Path,
    build_root: Path,
    audit_files: set[str],
    source_digest: str,
    compilation_input_digest: str,
) -> dict[str, Any]:
    contracts: dict[str, Any] = {}
    functions: dict[str, Any] = {}
    inheritance: dict[str, list[str]] = {}
    external_calls: list[dict[str, Any]] = []
    storage_writes: list[dict[str, Any]] = []
    modifiers: dict[str, list[str]] = {}
    source_ranges: dict[str, dict[str, Any]] = {}

    for contract in sorted(getattr(slither, "contracts", []), key=lambda value: getattr(value, "name", "")):
        file, start, end, origin = _location(contract, scope_root, audit_files)
        name = str(getattr(contract, "name", ""))
        bases = sorted({str(getattr(base, "name", base)) for base in getattr(contract, "inheritance", [])})
        contracts[name] = {"file": file, "start_line": start, "end_line": end, "bases": bases, "scope_origin": origin}
        inheritance[name] = bases
        for function in sorted(getattr(contract, "functions_and_modifiers_declared", []), key=lambda value: _function_key(contract, value)):
            key = _function_key(contract, function)
            file, start, end, origin = _location(function, scope_root, audit_files)
            modifier_names = _text_values(getattr(modifier, "name", modifier) for modifier in getattr(function, "modifiers", []))
            internal = sorted({_name(value) for value in getattr(function, "internal_calls", []) if _name(value)})
            high_level = list(getattr(function, "high_level_calls", []) or [])
            low_level = list(getattr(function, "low_level_calls", []) or [])
            library = list(getattr(function, "library_calls", []) or [])
            external = sorted({_name(value) for value in [*high_level, *low_level, *library] if _name(value)})
            functions[key] = {
                "contract": name,
                "name": str(getattr(function, "name", "")),
                "file": file,
                "start_line": start,
                "end_line": end,
                "visibility": str(getattr(function, "visibility", "")),
                "modifiers": modifier_names,
                "reads": _text_values(getattr(function, "variables_read", [])),
                "writes": _text_values(getattr(function, "variables_written", [])),
                "internal_calls": internal,
                "external_calls": external,
                "scope_origin": origin,
            }
            modifiers[key] = modifier_names
            source_ranges[key] = {"file": file, "start_line": start, "end_line": end}
            for target in external:
                external_calls.append({"caller": key, "target": target, "kind": "external", "file": file, "start_line": start})
            for variable in functions[key]["writes"]:
                storage_writes.append({"function": key, "variable": variable, "file": file, "start_line": start})

    return {
        "schema_version": 1,
        "target_root": str(scope_root),
        "build_root": str(build_root),
        "source_digest": source_digest,
        "compilation_input_digest": compilation_input_digest,
        "contracts": contracts,
        "functions": functions,
        "inheritance": inheritance,
        "external_calls": external_calls,
        "storage_writes": storage_writes,
        "modifiers": modifiers,
        "source_ranges": source_ranges,
    }


def validate_code_index(root: Path, value: dict[str, Any], *, source_digest: str | None = None, compilation_input_digest: str | None = None) -> None:
    validate_schema(root, "code-index.schema.json", value)
    if source_digest is not None and value["source_digest"] != source_digest:
        raise ValueError("code index source_digest does not match Recon")
    if compilation_input_digest is not None and value["compilation_input_digest"] != compilation_input_digest:
        raise ValueError("code index compilation_input_digest does not match Recon")


def lookup(index: dict[str, Any], function: str, *, include_callers: bool = False, include_callees: bool = False) -> dict[str, Any]:
    functions = index.get("functions", {})
    if function in functions:
        selected = {function}
    else:
        selected = {key for key in functions if key.endswith(f".{function}") or key == function}
    if not selected:
        raise ValueError(f"function not found in code index: {function}")
    if include_callees:
        selected |= {
            callee
            for key in tuple(selected)
            for callee in [*functions[key].get("internal_calls", []), *functions[key].get("external_calls", [])]
            if callee in functions
        }
    if include_callers:
        selected |= {
            key
            for key, value in functions.items()
            if selected & set([*value.get("internal_calls", []), *value.get("external_calls", [])])
        }
    return {
        "source_digest": index["source_digest"],
        "compilation_input_digest": index["compilation_input_digest"],
        "functions": {key: functions[key] for key in sorted(selected)},
        "source_ranges": {key: index.get("source_ranges", {}).get(key) for key in sorted(selected)},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--function", required=True)
    parser.add_argument("--include-callers", action="store_true")
    parser.add_argument("--include-callees", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        index = load_json(args.index)
        validate_code_index(args.root.resolve(), index)
        print(json.dumps(lookup(index, args.function, include_callers=args.include_callers, include_callees=args.include_callees), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
