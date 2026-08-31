#!/usr/bin/env python3
"""Apply the Feature Map v3 and routing-v4 registry migration once."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VERIFIED_AT = "2026-08-30"
MACHINE = ["compiler-ast", "slither-ast", "slither-ir"]

MACHINE_ONLY = {
    "uses-assembly", "uses-create2", "uses-delegatecall", "uses-external-call",
    "uses-low-level-call", "uses-math", "uses-msg-value", "uses-payable",
    "uses-signed-conversion", "uses-time",
}
MACHINE_OR_DEPLOYMENT = {"uses-chain-specific", "uses-proxy"}
NEVER_ABSENT = {
    "uses-dynamic-loop", "uses-external-control-before-accounting-finalized",
}

DOMAIN_METHODOLOGY = {
    "evm-audit-access-control": (["privileged roles and administrators"], ["trace every privilege grant, revoke, and transfer path"]),
    "evm-audit-assembly": (["compiler target and assembly call sites"], ["compare Yul/EVM behavior with the selected runtime"]),
    "evm-audit-bridges": (["source/destination chains, finality, authentication, and relayers"], ["model message lifecycle, replay, ordering, and failure recovery"]),
    "evm-audit-chain-specific": (["chain family, execution environment, fork, and deployed bytecode"], ["verify every relied-upon opcode and system-contract behavior"]),
    "evm-audit-defi-amm": (["pool model, fee tier, liquidity, hooks, and price source"], ["model price impact, slippage, callback, and accounting invariants"]),
    "evm-audit-defi-lending": (["oracle configuration, collateral parameters, caps, liquidations, and interest model"], ["model solvency, bad debt, and liquidation economics"]),
    "evm-audit-defi-staking": (["reward accounting, withdrawal queue, validator and slashing assumptions"], ["model share/reward accounting and delayed exits"]),
    "evm-audit-dos": (["bounded collections, external calls, callbacks, and returndata"], ["establish attacker-controlled work and recovery paths"]),
    "evm-audit-erc20": (["accepted tokens, balance accounting, allowances, and transfer wrappers"], ["test non-standard token behaviors against accounting invariants"]),
    "evm-audit-erc4337": (["EntryPoint version, account modules, paymasters, and bundler assumptions"], ["trace validation, replay, prefund, and execution boundaries"]),
    "evm-audit-erc4626": (["asset/share decimals, conversion formulas, fees, and initial state"], ["verify preview parity, rounding, donation, and inflation resistance"]),
    "evm-audit-erc721": (["accepted NFT standards, receivers, approvals, and custody model"], ["trace ownership, callback, and transfer compatibility"]),
    "evm-audit-flashloans": (["flash liquidity sources and same-transaction state dependencies"], ["test atomic manipulation of governance, prices, shares, and accounting"]),
    "evm-audit-general": (["scope inventory, entry points, trust boundaries, and external dependencies"], ["trace reachable state changes and cross-domain interactions"]),
    "evm-audit-governance": (["voting power, quorum, timelock, proposal, and execution model"], ["trace proposal creation through execution and cancellation"]),
    "evm-audit-oracles": (["feed contracts, decimals, heartbeat, bounds, and fallback behavior"], ["verify freshness, scaling, sequencer, and manipulation resistance"]),
    "evm-audit-precision-math": (["units, decimals, rounding directions, and numeric bounds"], ["prove conversion and accounting invariants at boundary values"]),
    "evm-audit-proxies": (["proxy kind, implementation, admin, initializer, and upgrade path"], ["trace initialization, authorization, and storage compatibility"]),
    "evm-audit-signatures": (["signed payload, domain separator, nonce, signer, and chain binding"], ["test replay, malleability, expiry, and signer ambiguity"]),
}

ZKSYNC_INTERPRETER_URL = "https://docs.zksync.io/zksync-protocol/era-vm/evm-interpreter/deployment-execution"


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def migrate_features() -> None:
    path = ROOT / "data" / "features.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    migrated = {}
    for feature, raw in data["features"].items():
        description = raw if isinstance(raw, str) else raw["description"]
        if feature in MACHINE_ONLY:
            policy, allowed = "machine-only", MACHINE
        elif feature in MACHINE_OR_DEPLOYMENT:
            policy, allowed = "machine-or-deployment", [*MACHINE, "deployment"]
        elif feature in NEVER_ABSENT:
            policy, allowed = "never-confirm-absence", []
        else:
            policy, allowed = "manual-allowed", [*MACHINE, "deployment", "manual", "source"]
        migrated[feature] = {
            "description": description,
            "absence_policy": policy,
            "allowed_absence_evidence": allowed,
        }
    dump(path, {
        "schema_version": 2,
        "description": data["description"],
        "features": migrated,
    })


def migrate_domains() -> None:
    for path in sorted((ROOT / "domains").glob("*.json")):
        if path.name == "domain.schema.json":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        required_context, review_requirements = DOMAIN_METHODOLOGY[data["id"]]
        data["always_screen"] = data["id"] == "evm-audit-general"
        data["required_context"] = required_context
        data["review_requirements"] = review_requirements
        dump(path, data)


def migrate_registry() -> None:
    path = ROOT / "data" / "canonical-checks.json"
    registry = json.loads(path.read_text(encoding="utf-8"))
    registry["schema_version"] = 4
    registry["source_catalog"]["zksync-evm-interpreter-deployment"] = {
        "label": "ZKsync EVM Interpreter contract deployment",
        "url": ZKSYNC_INTERPRETER_URL,
        "kind": "official",
        "license": None,
        "pinned_commit": None,
    }
    for check in registry["checks"]:
        chain = check.get("chain")
        if chain:
            applicability = check.setdefault("applicability", {})
            applicability.setdefault("chain_ids", [])
            applicability.setdefault("chain_families", [chain])
            applicability.setdefault("execution_environments", [])
            applicability.setdefault("compiler", None)
            applicability.setdefault("evm_fork_from", check.get("hardfork_from"))
            applicability.setdefault("evm_fork_until", check.get("hardfork_until"))
            applicability.setdefault("protocol_versions", [check["protocol_version"]] if check.get("protocol_version") else [])
            if chain == "zksync-era":
                applicability["execution_environments"] = ["eravm-native", "zksync-evm-interpreter"]
        if check.get("predicate_source") == "curated":
            fixture = f"tests/routing/curated-predicates.json#{check['canonical_id']}"
            check["routing_verification"] = {
                "basis": "The curated feature predicate was reviewed against positive and negative routing fixtures.",
                "verified_at": VERIFIED_AT,
                "tests": [f"{fixture}:select", f"{fixture}:filter"],
            }

    by_id = {check["canonical_id"]: check for check in registry["checks"]}
    chain13 = by_id["EVM-CHAIN-013"]
    chain13.update({
        "title": "ZKsync contract-address derivation depends on the execution environment",
        "description": "Native EraVM and ContractDeployer deployments use ZKsync-specific CREATE/CREATE2 derivation. EVM-bytecode contracts executed through the EVM Bytecode Interpreter use Ethereum-compatible CREATE/CREATE2 address derivation. Determine the deployed bytecode and runtime before flagging counterfactual-address logic.",
        "trigger": ["Code computes, predicts, validates, or authorizes a contract address for a ZKsync deployment."],
        "risk": "Applying the Ethereum formula to native EraVM deployment, or the EraVM formula to EVM-interpreter deployment, yields the wrong counterfactual address.",
        "detection": ["Determine whether the deployed artifact is native EraVM bytecode or EVM bytecode, then compare its CREATE/CREATE2 calculation with the matching documented derivation."],
        "false_positive_gates": ["The runtime is identified and the address formula matches that execution environment."],
        "proof": ["Deploy the exact artifact with the relevant CREATE/CREATE2 path and compare the observed address with the predicted address."],
        "verification": {"status": "verified", "basis": "Official ZKsync native-deployment and EVM Interpreter deployment documentation."},
        "freshness": "versioned",
        "verified_at": VERIFIED_AT,
    })
    if not any(source.get("source_key") == "zksync-evm-interpreter-deployment" for source in chain13["provenance"]):
        chain13["provenance"].append({
            "source_key": "zksync-evm-interpreter-deployment",
            "label": "ZKsync EVM Interpreter contract deployment",
            "url": ZKSYNC_INTERPRETER_URL,
            "kind": "official",
            "locator": "createEVM/create2EVM and EVM-compatible address derivation",
        })

    # The earlier migration marked four whole domains as versioned. Restore
    # generic invariants to static; retain versioned only where an official,
    # mutable protocol/runtime fact is already documented.
    for check in registry["checks"]:
        if check.get("freshness") != "versioned" or check.get("verified_at"):
            continue
        official = any(source.get("kind") == "official" for source in check.get("provenance", []))
        if official:
            check["verified_at"] = VERIFIED_AT
        else:
            check["freshness"] = "static"

    dump(path, registry)


def main() -> None:
    migrate_features()
    migrate_domains()
    migrate_registry()


if __name__ == "__main__":
    main()
