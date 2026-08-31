#!/usr/bin/env python3
"""One-time schema-v5 migration for runtime-efficient review knowledge."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "data" / "canonical-checks.json"

GENERIC_FP = {
    "Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding.",
    "No finding when the source checklist's required invariant or validation is enforced on every reachable path and attacker-controlled inputs cannot trigger the described condition.",
}
GENERIC_PROOF = {
    "Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation.",
}

SCREENING_TERMS = {
    "evm-audit-access-control": ["owner", "role", "admin", "authorization", "governance"],
    "evm-audit-defi-amm": ["swap", "pool", "liquidity", "reserve", "hook", "slippage"],
    "evm-audit-assembly": ["assembly", "opcode", "create2", "delegatecall", "extcodesize"],
    "evm-audit-bridges": ["bridge", "cross-chain", "message", "relayer", "finality"],
    "evm-audit-chain-specific": ["chain id", "L2", "system contract", "fork", "opcode"],
    "evm-audit-defi-lending": ["borrow", "repay", "collateral", "debt", "liquidation", "interest", "bad debt"],
    "evm-audit-defi-staking": ["stake", "unstake", "reward", "validator", "slashing", "restaking"],
    "evm-audit-dos": ["loop", "batch", "external call", "gas", "revert", "queue"],
    "evm-audit-erc20": ["ERC20", "transfer", "allowance", "balance", "token"],
    "evm-audit-erc4337": ["UserOperation", "EntryPoint", "paymaster", "bundler", "account abstraction"],
    "evm-audit-erc4626": ["ERC4626", "vault", "shares", "deposit", "withdraw", "preview"],
    "evm-audit-erc721": ["ERC721", "ERC1155", "NFT", "safeTransfer", "tokenURI"],
    "evm-audit-flashloans": ["flash loan", "flash mint", "callback", "same transaction"],
    "evm-audit-general": ["state change", "external call", "trust boundary", "asset flow"],
    "evm-audit-governance": ["proposal", "vote", "quorum", "timelock", "delegate"],
    "evm-audit-oracles": ["oracle", "price", "feed", "TWAP", "staleness", "sequencer"],
    "evm-audit-precision-math": ["division", "rounding", "decimal", "scaling", "conversion"],
    "evm-audit-proxies": ["proxy", "upgrade", "implementation", "initializer", "storage slot"],
    "evm-audit-signatures": ["signature", "permit", "EIP-712", "nonce", "replay", "ecrecover"],
}


def dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def context_key(value: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return key[:64]


def main() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    registry["schema_version"] = 5
    for check in registry["checks"]:
        fp = check.get("false_positive_gates", [])
        proof = check.get("proof", [])
        if not fp or set(fp) <= GENERIC_FP:
            check["fp_policy"], check["false_positive_gates"] = "global", []
        else:
            check["fp_policy"] = "specific"
        if not proof or set(proof) <= GENERIC_PROOF:
            check["proof_policy"], check["proof"] = "global", []
        else:
            check["proof_policy"] = "specific"
    dump(REGISTRY, registry)

    for path in sorted((ROOT / "domains").glob("*.json")):
        if path.name == "domain.schema.json":
            continue
        domain = json.loads(path.read_text(encoding="utf-8"))
        domain["screening_terms"] = SCREENING_TERMS[domain["id"]]
        domain["required_context"] = [
            value if isinstance(value, dict) else {"key": context_key(value), "required": True, "description": value}
            for value in domain["required_context"]
        ]
        dump(path, domain)


if __name__ == "__main__":
    main()
