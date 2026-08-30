#!/usr/bin/env python3
"""Build an evidence-backed feature map from Slither's Solidity AST/IR.

Only detectors implemented below may emit ``ABSENT_CONFIRMED`` after a complete
Slither compilation. Features outside that detector set remain ``UNKNOWN`` for
an auditor or LLM to supplement; source-text keyword absence is never evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import sys
from pathlib import Path
from typing import Any


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
}


def source_evidence(value: Any, detector: str) -> str:
    mapping = getattr(value, "source_mapping", None)
    filename = getattr(getattr(mapping, "filename", None), "relative", None)
    lines = getattr(mapping, "lines", None) or []
    location = f"{filename}:{lines[0]}" if filename and lines else str(filename or "unknown")
    return f"slither:{location} detector={detector}"


def add(evidence: dict[str, set[str]], feature: str, value: Any, detector: str) -> None:
    evidence[feature].add(source_evidence(value, detector))


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
    if node is not None:
        values.append(str(getattr(node, "expression", "")))
        values.extend(f"{type(ir).__name__}:{ir}" for ir in getattr(node, "irs", []))
    return " ".join(values).lower()


def detect(slither: Any) -> dict[str, set[str]]:
    evidence = {feature: set() for feature in DETECTOR_DESCRIPTIONS}
    for contract in slither.contracts:
        contract_text = lowered_parts(contract)
        if any(term in contract_text for term in ("erc20", "ierc20", "safeerc20")):
            add(evidence, "uses-erc20", contract, "erc20-type")
        if "erc4626" in contract_text:
            add(evidence, "uses-erc4626", contract, "erc4626-type")
        if any(term in contract_text for term in ("proxy", "upgradeable", "uups")):
            add(evidence, "uses-proxy", contract, "proxy-inheritance")
        if any(term in contract_text for term in ("eip712", "signaturechecker", "ecdsa")):
            add(evidence, "uses-signature", contract, "signature-type")
        if any(term in contract_text for term in ("aggregatorv3", "pricefeed", "priceoracle", "oracle")):
            add(evidence, "uses-oracle", contract, "oracle-type")
        if "merkle" in contract_text:
            add(evidence, "uses-merkle", contract, "merkle-type")
        if any(term in contract_text for term in ("erc777", "erc721receiver", "erc1155receiver")):
            add(evidence, "uses-callback-capable-token", contract, "token-callback-type")

        for function in contract.functions_and_modifiers_declared:
            function_text = lowered_parts(contract, function)
            if getattr(function, "payable", False):
                add(evidence, "uses-payable", function, "payable-function")
            if any(str(variable).lower() == "msg.value" for variable in getattr(function, "solidity_variables_read", [])):
                add(evidence, "uses-msg-value", function, "msg-value-read")
            if any(term in function_text for term in ("multicall", "batch", "execute[]")):
                add(evidence, "uses-multicall", function, "batch-entrypoint")
            if any(term in function_text for term in ("callback", "hook", "onerc721received", "onerc1155received", "tokensreceived")):
                add(evidence, "uses-reentrancy-callback", function, "callback-entrypoint")
            if any(term in function_text for term in ("onerc721received", "onerc1155received", "tokensreceived")):
                add(evidence, "uses-callback-capable-token", function, "token-callback-entrypoint")
            if any(term in function_text for term in ("ecrecover", "permit(", "signature", "eip712")):
                add(evidence, "uses-signature", function, "signature-operation")
            if any(term in function_text for term in ("latestrounddata", "getprice", "pricefeed", "oracle")):
                add(evidence, "uses-oracle", function, "oracle-operation")
            if any(term in function_text for term in ("merkleproof", "verifycalldata", "processproof")):
                add(evidence, "uses-merkle", function, "merkle-operation")
            if any(term in function_text for term in ("transferfrom(", "safetransfer(", "approve(", "balanceof(")):
                add(evidence, "uses-erc20", function, "erc20-operation")

            for node in function.nodes:
                node_type = str(getattr(node, "type", ""))
                text = lowered_parts(contract, function, node)
                if "ASSEMBLY" in node_type:
                    add(evidence, "uses-assembly", node, "assembly-node")
                if "LOOP" in node_type:
                    add(evidence, "uses-dynamic-loop", node, "loop-node")
                if "delegatecall" in text:
                    add(evidence, "uses-delegatecall", node, "delegatecall-ir")
                    add(evidence, "uses-low-level-call", node, "delegatecall-ir")
                    add(evidence, "uses-external-call", node, "delegatecall-ir")
                if any(term in text for term in ("lowlevelcall", ".call(", ".staticcall(", "send(", "transfer(")):
                    add(evidence, "uses-low-level-call", node, "low-level-call-ir")
                    add(evidence, "uses-external-call", node, "low-level-call-ir")
                if any(type(ir).__name__ in {"HighLevelCall", "NewContract", "NewElementaryType"} for ir in getattr(node, "irs", [])):
                    add(evidence, "uses-external-call", node, "external-call-ir")
                if "create2" in text or "newcontract" in text and "salt:" in text:
                    add(evidence, "uses-create2", node, "create2-ir")
                if "msg.value" in text:
                    add(evidence, "uses-msg-value", node, "msg-value-ir")
                if any(term in text for term in ("ecrecover", "permit(", "signaturechecker", "eip712")):
                    add(evidence, "uses-signature", node, "signature-ir")
                if any(term in text for term in ("latestrounddata", "pricefeed", "priceoracle")):
                    add(evidence, "uses-oracle", node, "oracle-ir")
                if any(term in text for term in ("merkleproof", "processproof", "verifycalldata")):
                    add(evidence, "uses-merkle", node, "merkle-ir")
    return evidence


def build_feature_map(root: Path, target: Path, solc: str | None, confirm_absence: bool) -> dict[str, Any]:
    feature_data = json.loads((root / "data" / "features.json").read_text(encoding="utf-8"))
    feature_names = sorted(feature_data["features"])
    Slither = ensure_slither_import()
    kwargs: dict[str, Any] = {}
    if solc:
        kwargs["solc"] = solc
    slither = Slither(str(target.resolve()), **kwargs)
    detected = detect(slither)

    features: dict[str, Any] = {}
    for feature in feature_names:
        values = sorted(detected.get(feature, set()))
        if values:
            features[feature] = {"status": "PRESENT", "evidence": values}
        elif confirm_absence and feature in DETECTOR_DESCRIPTIONS:
            features[feature] = {
                "status": "ABSENT_CONFIRMED",
                "evidence": [f"slither:complete-ast-scan detector={DETECTOR_DESCRIPTIONS[feature]} not found"],
            }
        else:
            features[feature] = {"status": "UNKNOWN", "evidence": []}
    return {"schema_version": 1, "features": features}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="Solidity file or project accepted by Slither")
    parser.add_argument("--root", type=Path, default=ROOT, help="evm-audit-skills suite root")
    parser.add_argument("--solc", help="solc executable forwarded to Slither")
    parser.add_argument("--present-only", action="store_true", help="leave detector absences UNKNOWN")
    parser.add_argument("--output", type=Path, help="write JSON to this path instead of stdout")
    args = parser.parse_args(argv)

    try:
        payload = build_feature_map(args.root.resolve(), args.target, args.solc, not args.present_only)
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
