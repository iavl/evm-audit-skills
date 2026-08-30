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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from scope_context import compilation_digests, relative_scope_path, resolve_scope_root, scope_inventory, source_digest
except ImportError:  # pragma: no cover - supports importing from another cwd
    from scripts.scope_context import compilation_digests, relative_scope_path, resolve_scope_root, scope_inventory, source_digest


ROOT = Path(__file__).resolve().parents[1]


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


DETECTOR_DESCRIPTIONS = {
    "uses-delegatecall": "delegatecall operation",
    "uses-external-call": "external call or contract creation",
    "uses-low-level-call": "call, staticcall, delegatecall, send, or transfer operation",
    "uses-assembly": "inline assembly block",
    "uses-create2": "CREATE2 operation",
    "uses-msg-value": "msg.value read",
    "uses-payable": "payable function or constructor",
    "uses-erc20": "ERC20 interface, inheritance, or token call",
    "uses-erc4626": "ERC4626 interface or inheritance",
    "uses-proxy": "proxy or upgradeable inheritance",
    "uses-signature": "ecrecover, EIP712, permit, or signature verification",
    "uses-oracle": "oracle or price-feed interface",
    "uses-multicall": "multicall or batch entry point",
    "uses-dynamic-loop": "loop node",
    "uses-merkle": "Merkle proof operation",
    "uses-reentrancy-callback": "callback or hook entry point",
    "uses-callback-capable-token": "ERC777/ERC721/ERC1155 callback surface",
    "uses-arbitrary-external-call": "caller-controlled low-level call target",
    "uses-access-control": "ownership, role, or authorization surface",
    "uses-erc721": "ERC721 or ERC1155 surface",
    "uses-erc4337": "ERC4337 account-abstraction surface",
    "uses-bridge": "cross-chain bridge or messaging surface",
    "uses-governance": "governance, voting, proposal, or timelock surface",
    "uses-amm": "AMM, DEX, swap, pool, or liquidity surface",
    "uses-lending": "lending, borrowing, collateral, or liquidation surface",
    "uses-staking": "staking, validator, restaking, or reward surface",
    "uses-flash-loan": "flash-loan or flash-mint surface",
    "uses-pause": "pause or emergency-stop surface",
    "uses-time": "timestamp, block number, deadline, or epoch surface",
    "uses-math": "arithmetic operation",
    "uses-chain-specific": "chain-specific execution surface",
    "uses-signed-conversion": "signed/unsigned conversion",
}

# Only structural Slither facts with complete traversal may prove absence.
# Name/type heuristics remain useful for presence but can never exclude checks.
ABSENCE_CAPABLE = {"uses-assembly", "uses-msg-value", "uses-payable"}


@dataclass(frozen=True)
class PresenceDetector:
    feature: str
    terms: tuple[str, ...]
    label: str


PRESENCE_DETECTORS = (
    PresenceDetector("uses-erc721", ("erc721", "ierc721", "erc1155", "ierc1155"), "nft-type-or-call"),
    PresenceDetector("uses-erc4337", ("useroperation", "entrypoint", "validateuserop", "paymaster"), "erc4337-type-or-call"),
    PresenceDetector("uses-bridge", ("layerzero", "ccip", "wormhole", "bridge", "sendmessage", "lzsend"), "bridge-type-or-call"),
    PresenceDetector("uses-governance", ("governor", "timelock", "quorum", "proposal", "castvote"), "governance-type-or-call"),
    PresenceDetector("uses-amm", ("uniswap", "swap", "getreserves", "liquidity", "poolmanager"), "amm-type-or-call"),
    PresenceDetector("uses-lending", ("borrow", "liquidat", "collateral", "healthfactor", "aave", "compound"), "lending-type-or-call"),
    PresenceDetector("uses-staking", ("stake", "unstake", "validator", "restak", "reward"), "staking-type-or-call"),
    PresenceDetector("uses-flash-loan", ("flashloan", "flashborrow", "onflashloan", "flashmint"), "flash-loan-type-or-call"),
    PresenceDetector("uses-pause", ("pausable", "whennotpaused", "whenpaused", "unpause", "paused"), "pause-type-or-call"),
    PresenceDetector("uses-chain-specific", ("arbitrum", "optimism", "zksync", "eravm", "blast", "chainid"), "chain-specific-type-or-call"),
)


def source_evidence(value: Any, detector: str, kind: str) -> tuple[str, str, str]:
    mapping = getattr(value, "source_mapping", None)
    filename = getattr(getattr(mapping, "filename", None), "relative", None)
    lines = getattr(mapping, "lines", None) or []
    location = f"{filename}:{lines[0]}" if filename and lines else str(filename or "unknown")
    return kind, location, f"Slither detector matched {detector}"


def add(evidence: dict[str, set[tuple[str, str, str]]], feature: str, value: Any, detector: str, kind: str = "slither-ast") -> None:
    evidence[feature].add(source_evidence(value, detector, kind))


def add_presence_heuristics(evidence: dict[str, set[tuple[str, str, str]]], value: Any, text: str) -> None:
    for detector in PRESENCE_DETECTORS:
        if any(term in text for term in detector.terms):
            add(evidence, detector.feature, value, detector.label, "source")


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


def detect(slither: Any) -> dict[str, set[tuple[str, str, str]]]:
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

    evidence = {feature: set() for feature in DETECTOR_DESCRIPTIONS}
    for contract in slither.contracts:
        contract_text = lowered_parts(contract)
        add_presence_heuristics(evidence, contract, contract_text)
        if any(term in contract_text for term in ("erc20", "ierc20", "safeerc20")):
            add(evidence, "uses-erc20", contract, "erc20-type", "source")
        if "erc4626" in contract_text:
            add(evidence, "uses-erc4626", contract, "erc4626-type", "source")
        if any(term in contract_text for term in ("proxy", "upgradeable", "uups")):
            add(evidence, "uses-proxy", contract, "proxy-inheritance", "source")
        if any(term in contract_text for term in ("eip712", "signaturechecker", "ecdsa")):
            add(evidence, "uses-signature", contract, "signature-type", "source")
        if any(term in contract_text for term in ("aggregatorv3", "pricefeed", "priceoracle", "oracle")):
            add(evidence, "uses-oracle", contract, "oracle-type", "source")
        if "merkle" in contract_text:
            add(evidence, "uses-merkle", contract, "merkle-type", "source")
        if any(term in contract_text for term in ("erc777", "erc721receiver", "erc1155receiver")):
            add(evidence, "uses-callback-capable-token", contract, "token-callback-type", "source")
        if any(term in contract_text for term in ("ownable", "accesscontrol", "authority", "roles")):
            add(evidence, "uses-access-control", contract, "access-control-type", "source")

        for function in contract.functions_and_modifiers_declared:
            function_text = lowered_parts(contract, function)
            add_presence_heuristics(evidence, function, function_text)
            if getattr(function, "payable", False):
                add(evidence, "uses-payable", function, "payable-function")
            if any(str(variable).lower() == "msg.value" for variable in getattr(function, "solidity_variables_read", [])):
                add(evidence, "uses-msg-value", function, "msg-value-read")
            if any(term in function_text for term in ("multicall", "batch", "execute[]")):
                add(evidence, "uses-multicall", function, "batch-entrypoint", "source")
            if any(term in function_text for term in ("onlyowner", "onlyrole", "authorized", "admin")):
                add(evidence, "uses-access-control", function, "authorization-modifier", "source")
            if any(term in function_text for term in ("callback", "hook", "onerc721received", "onerc1155received", "tokensreceived")):
                add(evidence, "uses-reentrancy-callback", function, "callback-entrypoint", "source")
            if any(term in function_text for term in ("onerc721received", "onerc1155received", "tokensreceived")):
                add(evidence, "uses-callback-capable-token", function, "token-callback-entrypoint", "source")
            if any(term in function_text for term in ("ecrecover", "permit(", "signature", "eip712")):
                add(evidence, "uses-signature", function, "signature-operation", "source")
            if any(term in function_text for term in ("latestrounddata", "getprice", "pricefeed", "oracle")):
                add(evidence, "uses-oracle", function, "oracle-operation", "source")
            if any(term in function_text for term in ("merkleproof", "verifycalldata", "processproof")):
                add(evidence, "uses-merkle", function, "merkle-operation", "source")
            if any(term in function_text for term in ("transferfrom(", "safetransfer(", "approve(", "balanceof(")):
                add(evidence, "uses-erc20", function, "erc20-operation", "source")
            if any(str(variable).lower() in {"block.timestamp", "block.number"} for variable in getattr(function, "solidity_variables_read", [])):
                add(evidence, "uses-time", function, "block-time-read", "slither-ir")

            for node in function.nodes:
                node_type = str(getattr(node, "type", ""))
                text = lowered_parts(contract, function, node)
                add_presence_heuristics(evidence, node, text)
                if "ASSEMBLY" in node_type:
                    add(evidence, "uses-assembly", node, "assembly-node")
                if "LOOP" in node_type:
                    add(evidence, "uses-dynamic-loop", node, "loop-node")
                for ir in getattr(node, "irs", []):
                    if isinstance(ir, LowLevelCall):
                        call_name = str(getattr(ir, "function_name", "")).lower()
                        add(evidence, "uses-low-level-call", node, f"{call_name or 'low-level-call'}-ir", "slither-ir")
                        add(evidence, "uses-external-call", node, f"{call_name or 'low-level-call'}-ir", "slither-ir")
                        if call_name == "delegatecall":
                            add(evidence, "uses-delegatecall", node, "delegatecall-ir", "slither-ir")
                        destination = str(getattr(ir, "destination", "")).lower()
                        if any(str(parameter).lower() in destination for parameter in getattr(function, "parameters", [])):
                            add(evidence, "uses-arbitrary-external-call", node, "parameterized-call-target", "slither-ir")
                    elif isinstance(ir, (Send, Transfer)):
                        add(evidence, "uses-low-level-call", node, f"{type(ir).__name__.lower()}-ir", "slither-ir")
                        add(evidence, "uses-external-call", node, f"{type(ir).__name__.lower()}-ir", "slither-ir")
                    elif isinstance(ir, (HighLevelCall, LibraryCall, NewContract)):
                        add(evidence, "uses-external-call", node, f"{type(ir).__name__.lower()}-ir", "slither-ir")
                    if isinstance(ir, NewContract) and getattr(ir, "call_salt", None) is not None:
                        add(evidence, "uses-create2", node, "new-contract-salt-ir", "slither-ir")
                    if isinstance(ir, SolidityCall) and "create2" in str(getattr(ir, "function", "")).lower():
                        add(evidence, "uses-create2", node, "create2-solidity-call", "slither-ir")
                    if isinstance(ir, Binary):
                        add(evidence, "uses-math", node, "binary-operation", "slither-ir")
                    if isinstance(ir, TypeConversion):
                        source_type = str(getattr(getattr(ir, "variable", None), "type", "")).lower()
                        target_type = str(getattr(ir, "type", "")).lower()
                        if source_type.startswith("int") != target_type.startswith("int") and (source_type.startswith(("int", "uint")) and target_type.startswith(("int", "uint"))):
                            add(evidence, "uses-signed-conversion", node, "signed-unsigned-conversion", "slither-ir")
                if "msg.value" in text:
                    add(evidence, "uses-msg-value", node, "msg-value-text", "source")
                if any(term in text for term in ("ecrecover", "permit(", "signaturechecker", "eip712")):
                    add(evidence, "uses-signature", node, "signature-text", "source")
                if any(term in text for term in ("latestrounddata", "pricefeed", "priceoracle")):
                    add(evidence, "uses-oracle", node, "oracle-text", "source")
                if any(term in text for term in ("merkleproof", "processproof", "verifycalldata")):
                    add(evidence, "uses-merkle", node, "merkle-text", "source")
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
) -> dict[str, Any]:
    feature_data = json.loads((root / "data" / "features.json").read_text(encoding="utf-8"))
    feature_names = sorted(feature_data["features"])
    Slither = ensure_slither_import()
    kwargs: dict[str, Any] = {}
    if solc:
        kwargs["solc"] = solc
    slither = Slither(str(target.resolve()), **kwargs)
    detected = detect(slither)
    scope_root = resolve_scope_root(target, audit_root)
    scope_files, excluded_paths = scope_inventory(scope_root, exclusions)
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
        elif confirm_absence and compilation_complete and feature in ABSENCE_CAPABLE:
            features[feature] = {
                "status": "ABSENT_CONFIRMED",
                "evidence": [{
                    "kind": "slither-ast",
                    "location": str(scope_root),
                    "reason": f"Complete Slither traversal found no {DETECTOR_DESCRIPTIONS[feature]}",
                }],
            }
        else:
            features[feature] = {"status": "UNKNOWN", "evidence": []}
    solc_version = command_version(solc)
    digests = compilation_digests(scope_root, scope_files, solc_version)
    return {
        "schema_version": 3,
        "recon_context": {
            "target_root": str(scope_root),
            "files_analyzed": files_analyzed,
            "excluded_paths": excluded_paths,
            "exclusion_patterns": sorted(set(exclusions)),
            "uncompiled_paths": uncompiled_paths,
            "source_digest": digests["audit_source_digest"],
            **digests,
            "compilation_complete": compilation_complete,
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
    parser.add_argument("--exclude", action="append", default=[], help="additional audit-scope glob to exclude; repeatable")
    parser.add_argument("--present-only", action="store_true", help="leave detector absences UNKNOWN")
    parser.add_argument("--output", type=Path, help="write JSON to this path instead of stdout")
    args = parser.parse_args(argv)

    try:
        payload = build_feature_map(
            args.root.resolve(),
            args.target,
            args.solc,
            not args.present_only,
            args.audit_root,
            tuple(args.exclude),
        )
        rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        present = sum(entry["status"] == "PRESENT" for entry in payload["features"].values())
        absent = sum(entry["status"] == "ABSENT_CONFIRMED" for entry in payload["features"].values())
        print(f"recon_present={present} absent_confirmed={absent}", file=sys.stderr)
        return 0
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
