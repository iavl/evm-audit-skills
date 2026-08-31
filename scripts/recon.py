#!/usr/bin/env python3
"""Build an evidence-backed feature map from Slither's Solidity AST/IR.

Only detectors implemented below may emit ``ABSENT_CONFIRMED`` after a complete
Slither compilation. Features outside that detector set remain ``UNKNOWN`` for
an auditor or LLM to supplement; source-text keyword absence is never evidence.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from scope_context import DEFAULT_DEPENDENCY_ROOTS, compilation_digests, relative_scope_path, resolve_build_root, resolve_scope_root, scope_inventory, source_digest
except ImportError:  # pragma: no cover - supports importing from another cwd
    from scripts.scope_context import DEFAULT_DEPENDENCY_ROOTS, compilation_digests, relative_scope_path, resolve_build_root, resolve_scope_root, scope_inventory, source_digest

try:
    from audit_artifacts import validate_schema
except ImportError:  # pragma: no cover - supports importing from another cwd
    from scripts.audit_artifacts import validate_schema

try:
    from runtime_log import configure, error, info, stage, success
except ImportError:  # pragma: no cover - supports importing from another cwd
    from scripts.runtime_log import configure, error, info, stage, success


ROOT = Path(__file__).resolve().parents[1]

DETECTOR_IMPLEMENTATIONS = {
    "external_call_ir",
    "low_level_call_ir",
    "delegatecall_ir",
    "msg_value_read",
    "payable_function",
    "arbitrary_external_target_ir",
    "assembly_node",
    "create2_ir",
    "signed_conversion_ir",
    "time_read",
    "binary_ir",
    "loop_node",
}
SAFE_ABSENCE_IMPLEMENTATIONS = {"assembly_node", "msg_value_read", "payable_function"}


def load_detector_config(root: Path, feature_names: set[str] | None = None) -> dict[str, dict[str, Any]]:
    value = json.loads((root / "data" / "feature-detectors.json").read_text(encoding="utf-8"))
    validate_schema(root, "feature-detectors.schema.json", value)
    config = value["features"]
    if feature_names is not None:
        unknown = sorted(set(config) - feature_names)
        if unknown:
            raise ValueError(f"feature detector registry contains unknown features: {', '.join(unknown)}")
    for feature, detector in config.items():
        mode = detector["mode"]
        if mode == "heuristic" and "terms" not in detector:
            raise ValueError(f"heuristic detector has no terms: {feature}")
        if mode == "structural" and detector.get("implementation") not in DETECTOR_IMPLEMENTATIONS:
            raise ValueError(f"unknown structural detector implementation: {detector.get('implementation')}")
        if detector["absence_capable"] and detector.get("implementation") not in SAFE_ABSENCE_IMPLEMENTATIONS:
            raise ValueError(f"absence capability is not approved for detector: {feature}")
    return config


def ensure_slither_import() -> Any:
    try:
        from slither.slither import Slither

        return Slither
    except ImportError as original_error:
        if os.environ.get("EVM_RECON_REEXEC") == "1":
            raise RuntimeError("Slither Python package is unavailable") from original_error
        executable = shutil.which("slither")
        if not executable:
            raise RuntimeError("Slither is required; install slither-analyzer") from original_error
        first_line = Path(executable).read_text(encoding="utf-8").splitlines()[0]
        if not first_line.startswith("#!"):
            raise RuntimeError("cannot resolve the Python interpreter used by Slither") from original_error
        interpreter = shlex.split(first_line[2:].strip())
        if not interpreter:
            raise RuntimeError("cannot resolve the Python interpreter used by Slither") from original_error
        environment = dict(os.environ)
        environment["EVM_RECON_REEXEC"] = "1"
        os.execvpe(interpreter[0], [*interpreter, str(Path(__file__).resolve()), *sys.argv[1:]], environment)
        raise AssertionError("unreachable")


def source_evidence(value: Any, detector: str, kind: str) -> tuple[str, str, str]:
    mapping = getattr(value, "source_mapping", None)
    filename = getattr(getattr(mapping, "filename", None), "relative", None)
    lines = getattr(mapping, "lines", None) or []
    location = f"{filename}:{lines[0]}" if filename and lines else str(filename or "unknown")
    return kind, location, f"Slither detector matched {detector}"


def add(evidence: dict[str, set[tuple[str, str, str]]], feature: str, value: Any, detector: str, kind: str = "slither-ast") -> None:
    evidence[feature].add(source_evidence(value, detector, kind))


def add_presence_heuristics(
    evidence: dict[str, set[tuple[str, str, str]]],
    value: Any,
    text: str,
    detectors: dict[str, dict[str, Any]],
) -> None:
    for feature, detector in detectors.items():
        if detector["mode"] == "heuristic" and any(term in text for term in detector["terms"]):
            add(evidence, feature, value, detector["label"], "source")


def add_structural(
    evidence: dict[str, set[tuple[str, str, str]]],
    detectors: dict[str, dict[str, Any]],
    implementation: str,
    value: Any,
    detector: str,
    kind: str = "slither-ast",
) -> None:
    for feature, config in detectors.items():
        if config["mode"] == "structural" and config.get("implementation") == implementation:
            add(evidence, feature, value, detector, kind)


def lowered_parts(contract: Any, function: Any | None = None, node: Any | None = None) -> str:
    values = [getattr(contract, "name", "")]
    values.extend(getattr(base, "name", "") for base in getattr(contract, "inheritance", []))
    if function is not None:
        values.extend(
            [
                getattr(function, "name", ""),
                getattr(function, "full_name", ""),
                str(getattr(function, "return_type", "")),
            ]
        )
        values.extend(str(variable) for variable in getattr(function, "variables_read", []))
        values.extend(getattr(modifier, "name", "") for modifier in getattr(function, "modifiers", []))
    if node is not None:
        values.append(str(getattr(node, "expression", "")))
        values.extend(f"{type(ir).__name__}:{ir}" for ir in getattr(node, "irs", []))
    return " ".join(values).lower()


def detect(slither: Any, detectors: dict[str, dict[str, Any]]) -> dict[str, set[tuple[str, str, str]]]:
    from slither.slithir.operations import (
        Binary,
        HighLevelCall,
        LibraryCall,
        LowLevelCall,
        NewContract,
        Send,
        SolidityCall,
        Transfer,
        TypeConversion,
    )

    evidence = {feature: set() for feature in detectors}
    for contract in slither.contracts:
        contract_text = lowered_parts(contract)
        add_presence_heuristics(evidence, contract, contract_text, detectors)

        for function in contract.functions_and_modifiers_declared:
            function_text = lowered_parts(contract, function)
            add_presence_heuristics(evidence, function, function_text, detectors)
            if getattr(function, "payable", False):
                add_structural(evidence, detectors, "payable_function", function, "payable-function")
            if any(str(variable).lower() == "msg.value" for variable in getattr(function, "solidity_variables_read", [])):
                add_structural(evidence, detectors, "msg_value_read", function, "msg-value-read")
            if any(str(variable).lower() in {"block.timestamp", "block.number"} for variable in getattr(function, "solidity_variables_read", [])):
                add_structural(evidence, detectors, "time_read", function, "block-time-read", "slither-ir")

            for node in function.nodes:
                node_type = str(getattr(node, "type", ""))
                text = lowered_parts(contract, function, node)
                add_presence_heuristics(evidence, node, text, detectors)
                if "ASSEMBLY" in node_type:
                    add_structural(evidence, detectors, "assembly_node", node, "assembly-node")
                if "LOOP" in node_type:
                    add_structural(evidence, detectors, "loop_node", node, "loop-node")
                for ir in getattr(node, "irs", []):
                    if isinstance(ir, LowLevelCall):
                        call_name = str(getattr(ir, "function_name", "")).lower()
                        add_structural(evidence, detectors, "low_level_call_ir", node, f"{call_name or 'low-level-call'}-ir", "slither-ir")
                        add_structural(evidence, detectors, "external_call_ir", node, f"{call_name or 'low-level-call'}-ir", "slither-ir")
                        if call_name == "delegatecall":
                            add_structural(evidence, detectors, "delegatecall_ir", node, "delegatecall-ir", "slither-ir")
                        destination = str(getattr(ir, "destination", "")).lower()
                        if any(str(parameter).lower() in destination for parameter in getattr(function, "parameters", [])):
                            add_structural(evidence, detectors, "arbitrary_external_target_ir", node, "parameterized-call-target", "slither-ir")
                    elif isinstance(ir, (Send, Transfer)):
                        add_structural(evidence, detectors, "low_level_call_ir", node, f"{type(ir).__name__.lower()}-ir", "slither-ir")
                        add_structural(evidence, detectors, "external_call_ir", node, f"{type(ir).__name__.lower()}-ir", "slither-ir")
                    elif isinstance(ir, (HighLevelCall, LibraryCall, NewContract)):
                        add_structural(evidence, detectors, "external_call_ir", node, f"{type(ir).__name__.lower()}-ir", "slither-ir")
                    if isinstance(ir, NewContract) and getattr(ir, "call_salt", None) is not None:
                        add_structural(evidence, detectors, "create2_ir", node, "new-contract-salt-ir", "slither-ir")
                    if isinstance(ir, SolidityCall) and "create2" in str(getattr(ir, "function", "")).lower():
                        add_structural(evidence, detectors, "create2_ir", node, "create2-solidity-call", "slither-ir")
                    if isinstance(ir, Binary):
                        add_structural(evidence, detectors, "binary_ir", node, "binary-operation", "slither-ir")
                    if isinstance(ir, TypeConversion):
                        source_type = str(getattr(getattr(ir, "variable", None), "type", "")).lower()
                        target_type = str(getattr(ir, "type", "")).lower()
                        if source_type.startswith("int") != target_type.startswith("int") and (source_type.startswith(("int", "uint")) and target_type.startswith(("int", "uint"))):
                            add_structural(evidence, detectors, "signed_conversion_ir", node, "signed-unsigned-conversion", "slither-ir")
                if "msg.value" in text:
                    add_structural(evidence, detectors, "msg_value_read", node, "msg-value-text", "source")
    return evidence


def analyzed_source_paths(slither: Any, scope_root: Path) -> list[str]:
    analyzed: set[str] = set()
    for unit in slither.crytic_compile.compilation_units.values():
        for filename in getattr(unit, "filenames", []):
            absolute = Path(str(getattr(filename, "absolute", filename)))
            relative = relative_scope_path(scope_root, absolute)
            if relative is not None:
                analyzed.add(relative)
    return sorted(analyzed)


def command_version(command: str | None) -> str | None:
    executable = command or shutil.which("solc")
    if not executable:
        return None
    result = subprocess.run([executable, "--version"], capture_output=True, text=True, check=False)
    for line in result.stdout.splitlines():
        if line.startswith("Version:"):
            return line.removeprefix("Version:").strip()
    return None


def build_feature_map(
    root: Path,
    target: Path,
    solc: str | None,
    confirm_absence: bool,
    audit_root: Path | None = None,
    exclusions: tuple[str, ...] = (),
    build_root: Path | None = None,
    include_patterns: tuple[str, ...] = (),
    dependency_roots: tuple[str, ...] = tuple(sorted(DEFAULT_DEPENDENCY_ROOTS)),
) -> dict[str, Any]:
    feature_data = json.loads((root / "data" / "features.json").read_text(encoding="utf-8"))
    feature_names = sorted(feature_data["features"])
    detector_config = load_detector_config(root, set(feature_names))
    Slither = ensure_slither_import()
    kwargs: dict[str, Any] = {}
    if solc:
        kwargs["solc"] = solc
    slither = Slither(str(target.resolve()), **kwargs)
    detected = detect(slither, detector_config)
    scope_root = resolve_scope_root(target, audit_root)
    compilation_root = resolve_build_root(
        scope_root if build_root is None and scope_root.is_dir() else target,
        build_root,
    )
    scope_files, excluded_paths = scope_inventory(scope_root, exclusions, include_patterns, dependency_roots)
    files_analyzed = analyzed_source_paths(slither, scope_root)
    uncompiled_paths = sorted(set(scope_files) - set(files_analyzed))
    compilation_complete = not uncompiled_paths

    features: dict[str, Any] = {}
    for feature in feature_names:
        values = sorted(detected.get(feature, set()))
        if values:
            features[feature] = {
                "status": "PRESENT",
                "evidence": [{"kind": kind, "location": location, "reason": reason} for kind, location, reason in values],
            }
        elif confirm_absence and compilation_complete and detector_config.get(feature, {}).get("absence_capable") is True:
            features[feature] = {
                "status": "ABSENT_CONFIRMED",
                "evidence": [{
                    "kind": "slither-ast",
                    "location": str(scope_root),
                    "reason": f"Complete Slither traversal found no {detector_config[feature]['label']}",
                }],
            }
        else:
            features[feature] = {"status": "UNKNOWN", "evidence": []}
    solc_version = command_version(solc)
    digests = compilation_digests(
        scope_root,
        scope_files,
        solc_version,
        build_root=compilation_root,
        dependency_roots=dependency_roots,
    )
    return {
        "schema_version": 4,
        "recon_context": {
            "target_root": str(scope_root),
            "build_root": str(compilation_root),
            "files_analyzed": files_analyzed,
            "excluded_paths": excluded_paths,
            "exclusion_patterns": sorted(set(exclusions)),
            "include_patterns": sorted(set(include_patterns)),
            "dependency_roots": sorted(set(dependency_roots)),
            "uncompiled_paths": uncompiled_paths,
            "source_digest": digests["audit_source_digest"],
            **digests,
            "compilation_complete": compilation_complete,
            "recon_quality": {
                "compilation_complete": compilation_complete,
                "absence_filtering_complete": compilation_complete,
                "mode": "COMPLETE" if compilation_complete else "CONSERVATIVE_DEGRADED",
                "uncompiled_paths": uncompiled_paths,
            },
            "slither_version": importlib.metadata.version("slither-analyzer"),
            "solc_version": solc_version,
        },
        "features": features,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="Solidity file or project accepted by Slither")
    parser.add_argument("--root", type=Path, default=ROOT, help="evm-audit-skills suite root")
    parser.add_argument("--solc", help="solc executable forwarded to Slither")
    parser.add_argument("--audit-root", type=Path, help="complete audit scope; defaults to the Slither target")
    parser.add_argument("--build-root", type=Path, help="compilation/build project root; inferred for file targets")
    parser.add_argument("--exclude", action="append", default=[], help="additional audit-scope glob to exclude; repeatable")
    parser.add_argument("--include", action="append", default=[], help="include a normally dependency-only audit path; repeatable")
    parser.add_argument("--dependency-root", action="append", default=None, help="top-level dependency root; repeatable")
    parser.add_argument("--present-only", action="store_true", help="leave detector absences UNKNOWN")
    parser.add_argument("--output", type=Path, help="write JSON to this path instead of stdout")
    parser.add_argument("--quiet", action="store_true", help="suppress progress output")
    args = parser.parse_args(argv)
    configure(quiet=args.quiet)

    try:
        stage("RECON", step=1, total=7, detail="Building scope-bound Feature Map")
        payload = build_feature_map(
            args.root.resolve(),
            args.target,
            args.solc,
            not args.present_only,
            args.audit_root,
            tuple(args.exclude),
            args.build_root,
            tuple(args.include),
            tuple(args.dependency_root) if args.dependency_root is not None else tuple(sorted(DEFAULT_DEPENDENCY_ROOTS)),
        )
        rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        statuses = [entry["status"] for entry in payload["features"].values()]
        info(f"Solidity files analyzed: {len(payload['recon_context']['files_analyzed'])}")
        info(f"Compilation complete: {'yes' if payload['recon_context']['compilation_complete'] else 'no'}")
        info(f"PRESENT features: {statuses.count('PRESENT')}")
        info(f"ABSENT_CONFIRMED features: {statuses.count('ABSENT_CONFIRMED')}")
        info(f"UNKNOWN features: {statuses.count('UNKNOWN')}")
        if args.output:
            info(f"Feature Map written to {args.output}")
        success("Feature Map ready")
        return 0
    except Exception as exc:
        error(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
