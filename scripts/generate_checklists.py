#!/usr/bin/env python3
"""Build the runtime checklists from the canonical JSON registry.

The checked-in Markdown files are generated compatibility views.  Use
``--bootstrap`` once when migrating the legacy Markdown corpus; after the
registry exists, edit only ``data/canonical-checks.json`` and regenerate.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "canonical-checks.json"
DOMAIN_PATHS = sorted(ROOT.glob("evm-audit-*/references/checklist.md"))

SOURCE_ID_RE = re.compile(r"\b(?:SAS-AV-\d{3}|DROZER-[A-Z0-9-]+|AUDITMOS-[A-Z0-9-]+)\b")
URL_RE = re.compile(r"https?://[^\s)]+")
ITEM_RE = re.compile(r"^- \[ \] \*\*(.*?)\*\*(?::\s*|\s*)(.*)$")
FIELD_RE = re.compile(r"^(?:-\s*)?\*\*(D|FP|Methodology|Look for|Origin):\*\*\s*(.*)$", re.I)

DOMAIN_CODES = {
    "evm-audit-general": "GEN",
    "evm-audit-precision-math": "MATH",
    "evm-audit-erc20": "ERC20",
    "evm-audit-defi-amm": "AMM",
    "evm-audit-defi-lending": "LEND",
    "evm-audit-defi-staking": "STK",
    "evm-audit-erc4626": "ERC4626",
    "evm-audit-erc4337": "ERC4337",
    "evm-audit-bridges": "BRIDGE",
    "evm-audit-proxies": "PROXY",
    "evm-audit-signatures": "SIG",
    "evm-audit-governance": "GOV",
    "evm-audit-oracles": "ORACLE",
    "evm-audit-assembly": "ASM",
    "evm-audit-chain-specific": "CHAIN",
    "evm-audit-flashloans": "FLASH",
    "evm-audit-erc721": "ERC721",
    "evm-audit-dos": "DOS",
    "evm-audit-access-control": "ACCESS",
}

DOMAIN_TITLES = {
    "evm-audit-general": "General Solidity/EVM Security Checklist",
    "evm-audit-precision-math": "Precision & Math Security Checklist",
    "evm-audit-erc20": "Weird ERC20 Security Checklist",
    "evm-audit-defi-amm": "AMM & DEX Security Checklist",
    "evm-audit-defi-lending": "Lending & Liquidation Security Checklist",
    "evm-audit-defi-staking": "Staking & LSD Security Checklist",
    "evm-audit-erc4626": "ERC4626 Vault Security Checklist",
    "evm-audit-erc4337": "ERC4337 Account Abstraction Security Checklist",
    "evm-audit-bridges": "Bridge & Cross-Chain Security Checklist",
    "evm-audit-proxies": "Proxy & Upgrade Security Checklist",
    "evm-audit-signatures": "Signature Security Checklist",
    "evm-audit-governance": "Governance & DAO Security Checklist",
    "evm-audit-oracles": "Oracle & Pricing Security Checklist",
    "evm-audit-assembly": "Assembly & Opcode Security Checklist",
    "evm-audit-chain-specific": "Chain-Specific Security Checklist",
    "evm-audit-flashloans": "Flash Loan Security Checklist",
    "evm-audit-erc721": "ERC721/ERC1155 Security Checklist",
    "evm-audit-dos": "DoS & Griefing Security Checklist",
    "evm-audit-access-control": "Access Control Security Checklist",
}

COMMON_PROVENANCE = {
    "sanbir-solidity-auditor-skills": {
        "label": "sanbir/solidity-auditor-skills",
        "url": "https://github.com/sanbir/solidity-auditor-skills",
        "kind": "secondary",
        "revision": "b864c2ee3b2f63c4361a5064084ce1e99dcf7444",
    },
    "gdroz3r-drozer-lite": {
        "label": "gdroz3r/drozer-lite",
        "url": "https://github.com/gdroz3r/drozer-lite",
        "kind": "secondary",
        "revision": "fcc489d7eb14208bedcb6290b7b8ca5af6058539",
    },
    "auditmos-skills": {
        "label": "auditmos/skills",
        "url": "https://github.com/auditmos/skills",
        "kind": "secondary",
        "revision": "c9583babb0ce189d9f39a05caf94b5a5da655010",
    },
    "solidity-language-reference": {
        "label": "Solidity Language Reference",
        "url": "https://docs.soliditylang.org/en/latest/types.html",
        "kind": "official",
    },
    "eip-4626": {
        "label": "EIP-4626 Tokenized Vaults",
        "url": "https://eips.ethereum.org/EIPS/eip-4626",
        "kind": "official",
    },
    "eip-3855": {
        "label": "EIP-3855 PUSH0",
        "url": "https://eips.ethereum.org/EIPS/eip-3855",
        "kind": "official",
    },
    "eip-6780": {
        "label": "EIP-6780 SELFDESTRUCT",
        "url": "https://eips.ethereum.org/EIPS/eip-6780",
        "kind": "official",
    },
    "legacy-markdown": {
        "label": "Legacy checklist citation",
        "url": "https://github.com/austintgriffith/evm-audit-skills",
        "kind": "legacy",
    },
}


def domain_for(path: Path) -> str:
    return path.parts[-3]


def clean_title(title: str) -> str:
    title = SOURCE_ID_RE.sub("", title)
    title = re.sub(r"\[\s*\]", "", title)
    title = re.sub(r"\s+", " ", title)
    return title.strip(" -:")


def source_url(source_id: str) -> str | None:
    if source_id.startswith("SAS-AV-"):
        return COMMON_PROVENANCE["sanbir-solidity-auditor-skills"]["url"]
    if source_id.startswith("DROZER-"):
        return COMMON_PROVENANCE["gdroz3r-drozer-lite"]["url"]
    if source_id.startswith("AUDITMOS-"):
        return COMMON_PROVENANCE["auditmos-skills"]["url"]
    return None


def citation_values(block: str) -> list[str]:
    values: list[str] = []
    for value in re.findall(r"\[([^\[\]]+)\]", block):
        value = value.strip()
        if not value or value in {" ]", " ]*", "key", "user", "tokenId"}:
            continue
        if re.fullmatch(r"\d+", value):
            continue
        if value.startswith(("http://", "https://")):
            continue
        if re.search(r"[A-Z]|[-/]|\s", value) and not re.fullmatch(r"[0-9, .]+", value):
            values.append(value)
    return list(dict.fromkeys(values))


def extract_fields(summary: str, detail_lines: list[str]) -> dict[str, Any]:
    fields: dict[str, list[str]] = {"d": [], "fp": [], "methodology": [], "look_for": [], "origin": []}
    residual: list[str] = []
    for raw in detail_lines:
        line = raw.strip()
        if not line:
            continue
        match = FIELD_RE.match(line)
        if match:
            key, value = match.groups()
            fields[key.lower().replace(" ", "_")].append(value.strip())
        elif not line.startswith("- [ ]"):
            residual.append(line)

    detection = fields["d"] + fields["look_for"]
    if not detection:
        detection = [summary or "Inspect the implementation for the condition described by this check."]
    false_positive = fields["fp"] or [
        "Verify the guard, invariant, and deployment assumptions against every reachable path before confirming a finding."
    ]
    proof = fields["methodology"] or [
        "Trace a reachable path, satisfy the preconditions, quantify the impact, and provide a runnable PoC or deterministic invariant violation."
    ]
    origins = fields["origin"]
    return {
        "trigger": detection,
        "detection": detection,
        "false_positive_gates": false_positive,
        "proof": proof,
        "origin_lines": origins,
        "notes": residual,
    }


def infer_features(domain: str, text: str) -> list[str]:
    value = re.sub(r"https?://\S+", " ", text.lower())
    value = re.sub(r"\[[^\]]*\]", " ", value)
    features = {domain}
    keywords = {
        "uses-low-level-call": [".call", "staticcall", "low-level call", "returndata"],
        "uses-delegatecall": ["delegatecall"],
        "uses-multicall": ["multicall", "batch", "delegatecall loop"],
        "uses-msg-value": ["msg.value", "payable", "eth transfer", "native eth"],
        "uses-merkle": ["merkle"],
        "uses-force-feed": ["force-feed", "force feed", "selfdestruct", "coinbase"],
        "uses-reentrancy-callback": ["callback", "reentrancy", "safeMint", "safeTransfer"],
        "uses-assembly": ["assembly", "yul", "extcode", "sstore", "tstore", "precompile"],
        "uses-create2": ["create2", "metamorphic"],
        "uses-erc20": ["erc20", "token", "transferfrom", "allowance", "fee-on-transfer", "rebasing"],
        "uses-erc721": ["erc721", "erc1155", "nft", "safeMint", "royalt"],
        "uses-erc4626": ["erc4626", "vault", "share", "previewdeposit", "previewredeem"],
        "uses-signed-conversion": ["signed-to-unsigned", "signedvalue", "negative-to-unsigned", "uint(signed"],
        "uses-erc4337": ["erc4337", "useroperation", "paymaster", "bundler", "entrypoint"],
        "uses-bridge": ["bridge", "cross-chain", "layerzero", "ccip", "wormhole", "across"],
        "uses-proxy": ["proxy", "uups", "transparent", "beacon", "diamond", "upgrade"],
        "uses-signature": ["signature", "ecrecover", "eip-712", "permit", "nonce"],
        "uses-governance": ["governance", "voting", "proposal", "quorum", "timelock"],
        "uses-oracle": ["oracle", "chainlink", "twap", "pyth", "vrf", "price feed"],
        "uses-amm": ["amm", "uniswap", "pool", "swap", "liquidity", "stableswap"],
        "uses-lending": ["lending", "borrow", "loan", "collateral", "liquidat", "cdp"],
        "uses-staking": ["staking", "staked", "restaking", "validator", "lsd", "eigenlayer"],
        "uses-flash-loan": ["flash loan", "flashloan", "flash mint"],
        "uses-pause": ["pause", "paused", "unpause"],
        "uses-time": ["timestamp", "block.number", "time unit", "time-unit", "deadline", "duration", "epoch"],
        "uses-math": ["round", "division", "precision", "overflow", "underflow", "decimal", "muldiv", "downcast"],
        "uses-dynamic-loop": ["loop", "array", "unbounded", "gas limit", "dos"],
        "uses-chain-specific": ["arbitrum", "optimism", "zksync", "blast", "bnb", "polygon", "l2"],
    }
    for feature, needles in keywords.items():
        if any(needle in value for needle in needles):
            features.add(feature)
    return sorted(features)


def infer_type(domain: str, text: str) -> str:
    value = text.lower()
    if "standard compliance" in value or "eip-4626" in value and "must" in value:
        return "normative"
    if domain in {"evm-audit-general", "evm-audit-precision-math", "evm-audit-assembly", "evm-audit-chain-specific"}:
        if any(marker in value for marker in ("solidity", "opcode", "literal", "conversion", "delegatecall", "assembly", "block.number")):
            return "semantic"
    if any(marker in value for marker in ("suspicious", "too much", "could be", "may be", "centralization")):
        return "heuristic"
    return "exploit-pattern"


def infer_confidence(check_type: str) -> str:
    return {"normative": "high", "semantic": "high", "exploit-pattern": "medium", "heuristic": "contextual"}[check_type]


def parse_legacy_file(path: Path, root: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    section = ""
    current: dict[str, Any] | None = None
    items: list[dict[str, Any]] = []

    def finish() -> None:
        nonlocal current
        if current is None:
            return
        block = "\n".join([current["title"], current["summary"], *current["detail_lines"]])
        extracted = extract_fields(current["summary"], current["detail_lines"])
        source_ids = list(dict.fromkeys(SOURCE_ID_RE.findall(block)))
        urls = list(dict.fromkeys(URL_RE.findall(block)))
        citations = citation_values(block)
        check_type = infer_type(current["domain"], block)
        provenance: list[dict[str, Any]] = []
        for source_id in source_ids:
            provenance.append({"label": source_id, "locator": source_id, "url": source_url(source_id), "kind": "secondary"})
        for url in urls:
            if not any(entry.get("url") == url for entry in provenance):
                provenance.append({"label": url, "locator": url, "url": url, "kind": "secondary"})
        for citation in citations:
            if not any(entry.get("label") == citation for entry in provenance):
                provenance.append({"label": citation, "locator": citation, "url": None, "kind": "legacy"})
        relative_path = path.relative_to(root).as_posix()
        if not provenance:
            provenance.append({"label": "legacy-checklist", "locator": f"{relative_path}:{current['line']}", "url": None, "kind": "legacy"})
        code = DOMAIN_CODES[current["domain"]]
        index = len([item for item in items if item["domains"] == [current["domain"]]]) + 1
        description = current["summary"] or extracted["detection"][0] if extracted["detection"] else current["summary"]
        if not description:
            description = clean_title(current["title"])
        item = {
            "canonical_id": f"EVM-{code}-{index:03d}",
            "domains": [current["domain"]],
            "primary_domain": current["domain"],
            "section": current["section"] or "Uncategorized",
            "title": clean_title(current["title"]),
            "description": description,
            "trigger": extracted["trigger"],
            "risk": description,
            "detection": extracted["detection"],
            "false_positive_gates": extracted["false_positive_gates"],
            "proof": extracted["proof"],
            "type": check_type,
            "confidence": infer_confidence(check_type),
            "features": infer_features(current["domain"], block),
            "provenance": provenance,
            "related": [],
            "aliases": [
                {
                    "path": relative_path,
                    "line": current["line"],
                    "section": current["section"],
                    "title": current["title"],
                    "source_ids": source_ids,
                }
            ],
            "verification": {
                "status": "qualified",
                "basis": "legacy checklist migration; verify against the cited source before changing confidence",
            },
        }
        if extracted["origin_lines"]:
            item["origin_notes"] = extracted["origin_lines"]
        if extracted["notes"]:
            item["notes"] = extracted["notes"]
        items.append(item)
        current = None

    for line_number, line in enumerate(lines, 1):
        if line.startswith("## "):
            finish()
            section = line[3:].strip()
            continue
        match = ITEM_RE.match(line)
        if match:
            finish()
            title, summary = match.groups()
            current = {
                "domain": domain_for(path),
                "section": section,
                "title": title.strip(),
                "summary": summary.strip(),
                "line": line_number,
                "detail_lines": [],
            }
            continue
        if current is not None:
            current["detail_lines"].append(line)
    finish()
    return items


def alias_for(item: dict[str, Any], domain: str) -> bool:
    return domain in item.get("domains", []) and item.get("primary_domain") != domain


def find_by_title(items: list[dict[str, Any]], domain: str, needle: str) -> list[dict[str, Any]]:
    needle = needle.lower()
    return [item for item in items if domain in item.get("domains", []) and needle in item["title"].lower()]


def merge_items(target: dict[str, Any], removed: list[dict[str, Any]], domains: list[str], canonical_id: str) -> None:
    target["canonical_id"] = canonical_id
    target["domains"] = domains
    target["primary_domain"] = domains[0]
    target["features"] = sorted(
        set(target.get("features", []))
        | {feature for item in removed for feature in item.get("features", [])}
    )
    target["aliases"].extend(alias for item in removed for alias in item.get("aliases", []))
    for item in removed:
        for field in ("provenance", "origin_notes", "notes"):
            if field in item:
                target.setdefault(field, [])
                for value in item[field]:
                    if value not in target[field]:
                        target[field].append(copy.deepcopy(value))


def append_provenance(item: dict[str, Any], label: str, url: str, locator: str, source_key: str, kind: str = "official") -> None:
    if not any(entry.get("url") == url for entry in item.get("provenance", [])):
        item.setdefault("provenance", []).append({
            "label": label,
            "locator": locator,
            "url": url,
            "kind": kind,
            "source_key": source_key,
        })


def apply_knowledge_corrections(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply the reviewed P0 corrections while bootstrapping the registry."""

    precision = "evm-audit-precision-math"
    general = "evm-audit-general"

    division = next(
        item for item in items if item["canonical_id"].startswith("EVM-MATH-") and "division-before-multiplication may" in item["title"].lower()
    )
    division["title"] = "Division-before-multiplication may cause precision loss"
    division["description"] = "Division before multiplication can lose economically meaningful precision, but multiplying first is safe only when the product cannot overflow or a full-precision mulDiv is used."
    division["risk"] = "Premature truncation can change accounting or economic outcomes; an overflow-aware rewrite is required."
    division["trigger"] = [
        "A division result is later multiplied and the operands are attacker-controlled or economically material."
    ]
    division["detection"] = [
        "Inspect expression trees and helper calls for division-before-multiplication ordering.",
        "If rewriting as (a * c) / b, prove a*c cannot overflow or use full-precision mulDiv(a, c, b).",
    ]
    division["false_positive_gates"] = [
        "The truncation is proven bounded and economically harmless.",
        "The product is proven in range or a full-precision mulDiv implementation is used.",
    ]
    division["proof"] = [
        "Construct a boundary input where the intended exact result differs from the implementation and quantify the value delta; separately check the multiplication range."
    ]
    division["type"] = "semantic"
    division["confidence"] = "high"
    division["verification"] = {"status": "verified", "basis": "Solidity integer arithmetic and full-precision multiplication semantics"}

    time_precision = next(
        item for item in items if item["canonical_id"].startswith("EVM-MATH-") and "time literals" in item["title"].lower()
    )
    time_general = next(
        item for item in items if item["canonical_id"].startswith("EVM-GEN-") and "time expressions" in item["title"].lower()
    )
    time_precision["title"] = "Time-unit arithmetic inherits operand and destination type"
    time_precision["description"] = "Solidity time-unit suffixes such as days, hours, and minutes produce number literal expressions. Their eventual type and range come from the non-literal operand or destination, so the risk is in narrowing, explicit casts, storage packing, or the target type of the result."
    time_precision["risk"] = "A narrow destination or explicit conversion can truncate a time calculation; the literal itself is not a uint24 value."
    time_precision["trigger"] = ["Time-unit arithmetic is assigned to or explicitly converted to a narrow integer type."]
    time_precision["detection"] = [
        "Trace non-literal operands and the destination type of expressions using days, hours, or minutes.",
        "Inspect explicit casts, packed storage, and products such as uint32(365 days * years).",
    ]
    time_precision["false_positive_gates"] = ["The destination range is proven sufficient and no narrowing conversion or packed-storage truncation occurs."]
    time_precision["proof"] = ["Use a boundary duration that exceeds the destination range and demonstrate the resulting truncation or revert on the reachable path."]
    time_precision["verification"] = {"status": "verified", "basis": "Solidity Language Reference: time units and rational/integer literals"}
    merge_items(time_precision, [time_general], [precision, general], "EVM-TIME-001")
    items.remove(time_general)

    negative_precision = next(
        item for item in items if item["canonical_id"].startswith("EVM-MATH-") and "negative-to-unsigned" in item["title"].lower()
    )
    negative_general = next(
        item for item in items if item["canonical_id"].startswith("EVM-GEN-") and "assigning negative value" in item["title"].lower()
    )
    negative_precision["title"] = "Signed-to-unsigned explicit conversion preserves the bit pattern"
    negative_precision["description"] = "For same-width integer conversions, uint(signedValue) preserves the two's-complement bit pattern and can turn a negative value into a very large unsigned integer. Checked arithmetic does not make the explicit conversion itself revert."
    negative_precision["risk"] = "A negative oracle delta, PnL, or accounting value can become a huge unsigned amount when converted without a non-negative guard."
    negative_precision["trigger"] = ["A signed value reaches an explicit unsigned conversion, especially after oracle, PnL, or accounting calculations."]
    negative_precision["detection"] = [
        "Find uint256(signedValue), uint128(signedValue), and equivalent explicit conversions.",
        "Trace signed values derived from oracle deltas, PnL, or accounting and check signedValue >= 0 before conversion.",
    ]
    negative_precision["false_positive_gates"] = [
        "The signed value is proven non-negative on every reachable path before conversion.",
        "An explicit range check or SafeCast-style helper rejects out-of-range values.",
    ]
    negative_precision["proof"] = ["Exercise a reachable negative input such as int256(-3) and show the converted value or the invariant that prevents it."]
    negative_precision["type"] = "semantic"
    negative_precision["confidence"] = "high"
    negative_precision["verification"] = {"status": "verified", "basis": "Solidity Language Reference: explicit integer conversions and two's-complement representation"}
    merge_items(negative_precision, [negative_general], [precision, general], "EVM-TYPE-001")
    items.remove(negative_general)

    oracle_negative = next(
        item for item in items if item["canonical_id"].startswith("EVM-ORACLE-") and item["title"].lower() == "negative prices"
    )
    oracle_negative["description"] = "Some signed feeds can report negative answers; converting an unchecked negative answer to uint preserves its bit pattern and can create a huge value."
    oracle_negative["false_positive_gates"] = ["The feed answer is checked for a valid positive range before any unsigned conversion, or the integration intentionally supports signed prices."]
    oracle_negative["verification"] = {"status": "qualified", "basis": "Solidity explicit conversion semantics plus feed-specific documentation"}

    rounding_titles = {
        "converttoassets & converttoshares must round down",
        "previewdeposit must round down",
        "previewmint must round up",
        "previewwithdraw must round up",
        "previewredeem must round down",
        "all rounding must favor the vault",
    }
    rounding_items = [
        item for item in items
        if item.get("primary_domain") == "evm-audit-erc4626"
        and re.sub(r"[`*_]", "", item["title"]).lower() in rounding_titles
    ]
    if len(rounding_items) != 6:
        raise ValueError(f"expected six ERC4626 rounding rows during bootstrap, found {len(rounding_items)}")
    first = rounding_items[0]
    first["canonical_id"] = "ERC4626-ROUND-001"
    first["title"] = "Canonical ERC-4626 rounding directions"
    first["section"] = "Rounding Direction (EIP-4626 Compliance)"
    first["description"] = "Apply the EIP-4626 vault-favoring directions consistently: assets supplied to shares received DOWN; shares requested to assets supplied UP; assets requested to shares burned UP; shares burned to assets received DOWN; convertToShares DOWN; convertToAssets DOWN."
    first["risk"] = "Inconsistent rounding can transfer dust through repeated operations or make the vault insolvent."
    first["trigger"] = ["A vault converts between assets and shares or implements previewDeposit, previewMint, previewWithdraw, or previewRedeem."]
    first["detection"] = [
        "Compare every mutable and preview conversion with the canonical table: deposit DOWN, mint UP, withdraw UP, redeem DOWN, convertToShares DOWN, convertToAssets DOWN.",
        "Check every override and helper path for the same direction and fee treatment.",
    ]
    first["false_positive_gates"] = ["The implementation follows the canonical table and any fee/slippage difference is explicitly accounted for in the corresponding preview function."]
    first["proof"] = ["Construct boundary values around one wei and demonstrate that each operation favors the vault according to the canonical direction without violating solvency."]
    first["type"] = "normative"
    first["confidence"] = "high"
    first["features"] = sorted(set(first["features"]) | {"evm-audit-erc4626", "uses-erc4626", "uses-math"})
    first["provenance"].append({"label": "EIP-4626", "locator": "rounding directions", "url": COMMON_PROVENANCE["eip-4626"]["url"], "kind": "official"})
    first["verification"] = {"status": "verified", "basis": "EIP-4626 security considerations and preview/convert requirements"}
    merge_items(first, rounding_items[1:], ["evm-audit-erc4626"], "ERC4626-ROUND-001")
    for item in rounding_items[1:]:
        items.remove(item)

    sas_104 = next(item for item in items if "SAS-AV-104" in {alias_id for alias in item.get("aliases", []) for alias_id in alias.get("source_ids", [])})
    sas_104["false_positive_gates"] = [
        "Rounding follows ERC4626-ROUND-001: assets-to-shares on deposit DOWN, shares-to-assets on redeem DOWN, shares required for withdrawal UP, and assets required for mint UP.",
        "Tracked totals, actual token balances, and partial-fill accounting remain solvent after repeated boundary operations.",
    ]
    sas_104["related"] = ["ERC4626-ROUND-001"]

    return items


def bootstrap_registry(root: Path) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for path in sorted(root.glob("evm-audit-*/references/checklist.md")):
        if domain_for(path) not in DOMAIN_CODES:
            continue
        items.extend(parse_legacy_file(path, root))
    if len(items) != 876:
        raise ValueError(f"expected the current legacy corpus to contain 876 items, found {len(items)}")
    items = apply_knowledge_corrections(items)
    registry = {
        "schema_version": 1,
        "description": "Canonical EVM audit checks. Generated Markdown is a runtime compatibility view.",
        "source_catalog": COMMON_PROVENANCE,
        "checks": items,
        "dedup_decisions": {
            "policy": "Merge only when root cause, trigger, proof obligation, and impact are the same; retain contextual near-matches with related IDs.",
            "reviewed_candidates": [],
        },
    }
    return normalize_registry(registry)


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_registry(registry: dict[str, Any]) -> dict[str, Any]:
    """Apply idempotent metadata cleanup to registries created by early runs."""
    registry.setdefault("dedup_decisions", {})["reviewed_candidates"] = [
        {
            "canonical_id": "EVM-TYPE-001",
            "decision": "MERGED",
            "reason": "Same explicit signed-to-unsigned conversion semantics and proof obligation across precision and general domains.",
        },
        {
            "canonical_id": "EVM-TIME-001",
            "decision": "MERGED",
            "reason": "Same time-literal typing and narrowing-conversion proof obligation across precision and general domains.",
        },
        {
            "canonical_id": "ERC4626-ROUND-001",
            "decision": "MERGED",
            "reason": "One normative EIP-4626 rounding table replaces six overlapping runtime rows.",
        },
        {
            "canonical_id": "EVM-ASM-025",
            "decision": "MERGED",
            "reason": "Compiler-target and chain-fork PUSH0 behavior is one semantic rule with two runtime contexts.",
        },
    ]
    for source_key, source in COMMON_PROVENANCE.items():
        registry.setdefault("source_catalog", {}).setdefault(source_key, source)
    for item in registry.get("checks", []):
        if item.get("description") == item.get("title") and item.get("trigger"):
            item["description"] = one_line(item["trigger"][:1])
        if item.get("risk") == item.get("title") and item.get("description"):
            item["risk"] = item["description"]
        if len(item.get("domains", [])) > 1:
            item["features"] = sorted(set(item.get("features", [])) | set(item["domains"]))
        if not item.get("provenance"):
            aliases = item.get("aliases", [])
            if aliases:
                first_alias = aliases[0]
                item["provenance"] = [{
                    "label": "legacy-checklist",
                    "locator": f"{first_alias.get('path', 'unknown')}:{first_alias.get('line', 0)}",
                    "url": None,
                    "kind": "legacy",
                }]
        for entry in item.get("provenance", []):
            if entry.get("source_key"):
                continue
            label = str(entry.get("label", ""))
            url = str(entry.get("url", ""))
            if label.startswith("SAS-AV-"):
                source_key = "sanbir-solidity-auditor-skills"
            elif label.startswith("DROZER-") or "drozer-lite" in url:
                source_key = "gdroz3r-drozer-lite"
            elif label.startswith("AUDITMOS-") or "auditmos/skills" in url:
                source_key = "auditmos-skills"
            elif "docs.soliditylang.org" in url or label == "Solidity Language Reference":
                source_key = "solidity-language-reference"
            elif "eips.ethereum.org/EIPS/eip-4626" in url or label == "EIP-4626":
                source_key = "eip-4626"
            else:
                source_key = "legacy-markdown"
            entry["source_key"] = source_key
        feature_text = " ".join([
            item.get("title", ""),
            item.get("description", ""),
            *item.get("trigger", []),
            *item.get("detection", []),
        ])
        inferred = infer_type(
            item.get("primary_domain", item.get("domains", ["evm-audit-general"])[0]),
            feature_text,
        )
        item["features"] = infer_features(
            item.get("primary_domain", item.get("domains", ["evm-audit-general"])[0]),
            feature_text,
        )
        if len(item.get("domains", [])) > 1:
            item["features"] = sorted(set(item["features"]) | set(item["domains"]))
        if item.get("canonical_id") == "ERC4626-ROUND-001":
            item["features"] = sorted(set(item["features"]) | {"uses-erc4626", "uses-math"})
        if item.get("canonical_id") == "EVM-TYPE-001":
            item["features"] = [
                "evm-audit-general",
                "evm-audit-precision-math",
                "uses-math",
                "uses-signed-conversion",
            ]
        if item.get("canonical_id") not in {"EVM-MATH-001", "EVM-TYPE-001", "EVM-TIME-001", "ERC4626-ROUND-001"}:
            item["type"] = inferred
            item["confidence"] = infer_confidence(inferred)

    corrections = {
        "EVM-MATH-001": ("semantic", "high"),
        "EVM-TYPE-001": ("semantic", "high"),
        "EVM-TIME-001": ("semantic", "high"),
    }
    official_sources = {
        "EVM-MATH-001": ("Solidity Language Reference", "https://docs.soliditylang.org/en/latest/types.html#integers", "integer arithmetic and overflow-aware multiplication"),
        "EVM-TYPE-001": ("Solidity Language Reference", "https://docs.soliditylang.org/en/latest/types.html#explicit-conversions", "explicit integer conversions and two's-complement representation"),
        "EVM-TIME-001": ("Solidity Language Reference", "https://docs.soliditylang.org/en/latest/units-and-global-variables.html#time-units", "time units and rational/integer literals"),
    }
    for canonical_id, (check_type, confidence) in corrections.items():
        for item in registry.get("checks", []):
            if item.get("canonical_id") == canonical_id:
                item["type"] = check_type
                item["confidence"] = confidence
                label, url, locator = official_sources[canonical_id]
                append_provenance(item, label, url, locator, "solidity-language-reference")
                item["verification"] = {"status": "verified", "basis": f"{label}: {locator}"}

    def by_id(canonical_id: str) -> dict[str, Any] | None:
        return next((item for item in registry.get("checks", []) if item.get("canonical_id") == canonical_id), None)

    def set_semantic(
        canonical_id: str,
        title: str,
        description: str,
        risk: str,
        trigger: list[str],
        detection: list[str],
        false_positive_gates: list[str],
        proof: list[str],
        check_type: str,
        confidence: str,
        basis: str,
    ) -> None:
        item = by_id(canonical_id)
        if item is None:
            return
        item.update({
            "title": title,
            "description": description,
            "risk": risk,
            "trigger": trigger,
            "detection": detection,
            "false_positive_gates": false_positive_gates,
            "proof": proof,
            "type": check_type,
            "confidence": confidence,
            "verification": {"status": "verified" if "official" in basis.lower() else "qualified", "basis": basis},
        })

    set_semantic(
        "EVM-ASM-001",
        "CREATE2 and SELFDESTRUCT redeployment is fork- and transaction-dependent",
        "After EIP-6780, SELFDESTRUCT in an existing contract transfers its balance but does not delete code or storage. Code deletion and subsequent redeployment remain possible only for a contract created in the same transaction, so CREATE2 plus SELFDESTRUCT is not a general metamorphic upgrade primitive.",
        "A protocol that relies on code replacement may be unsafe only on pre-EIP-6780 chains or same-transaction-created paths; verify the target fork and lifecycle.",
        ["A protocol assumes a CREATE2 address can be destroyed and later redeployed with different code."],
        ["Check the target chain fork, whether the contract was created in the same transaction, and whether the design relies on post-deployment code replacement."],
        ["The deployment chain implements EIP-6780 and no same-transaction-created contract can reach the replacement path."],
        ["Build the exact create, SELFDESTRUCT, and redeployment transaction sequence for the declared fork and observe code/storage at each step."],
        "semantic",
        "high",
        "EIP-6780 official semantics",
    )
    set_semantic(
        "EVM-ASM-002",
        "CREATE2 address lifecycle depends on EIP-6780 and transaction context",
        "Before deployment a CREATE2 address has no code or storage. After deployment it has code and storage. On a post-EIP-6780 chain, SELFDESTRUCT of an existing contract leaves code and storage in place; deletion semantics are retained only when the contract was created in the same transaction.",
        "Treating an address as permanently empty or redeployable without checking the fork and creation transaction can invalidate identity and code-integrity assumptions.",
        ["Code relies on a CREATE2 address changing between deployed, destroyed, and redeployed states."],
        ["Model the address state before deployment, after deployment, after SELFDESTRUCT, and in the next transaction under the target fork."],
        ["The implementation verifies code and storage state at the point of use and documents the target chain fork."],
        ["Execute or statically prove the lifecycle for both an existing contract and a same-transaction-created contract."],
        "semantic",
        "high",
        "EIP-6780 official semantics",
    )
    set_semantic(
        "EVM-ASM-004",
        "CREATE inside CREATE2 does not guarantee metamorphic child replacement",
        "A CREATE2 factory's child nonce and address assumptions must be evaluated together with the chain's SELFDESTRUCT rules. After EIP-6780, an existing factory cannot generally be destroyed and redeployed to reset its child-creation state.",
        "Assuming a factory or child can be replaced at the same address can break code identity and deployment invariants when the assumed lifecycle is unavailable.",
        ["A CREATE2-deployed factory uses CREATE for children and the design relies on factory redeployment or nonce reset."],
        ["Trace factory creation, child nonce/address derivation, SELFDESTRUCT, and any attempted redeployment on the target fork."],
        ["The design does not rely on post-EIP-6780 metamorphic replacement, or it proves the same-transaction creation path."],
        ["Reproduce the complete lifecycle and compare the observed child code/address with the assumed deployment model."],
        "semantic",
        "high",
        "EIP-6780 official semantics",
    )
    set_semantic(
        "EVM-ASM-005",
        "One-time code verification may not establish ongoing code identity",
        "A code-hash check made at registration proves only the state observed at that time. Ongoing identity requires verifying the code at each security-sensitive use and accounting for proxy upgrades, same-transaction creation/destruction, and the target chain's SELFDESTRUCT rules.",
        "Trusting a stale code check can route calls or assets to code that no longer satisfies the intended identity invariant.",
        ["A trusted address is registered once and later used without rechecking code identity."],
        ["Trace upgrades, code replacement, proxy implementation changes, and the exact use-time code check."],
        ["The address is immutable and the deployment model proves code cannot change, or use-time code identity is checked."],
        ["Provide a lifecycle trace showing whether the registered code hash can differ from the code used by the protected operation."],
        "semantic",
        "high",
        "EIP-6780 official semantics and deployment model",
    )
    set_semantic(
        "EVM-ASM-008",
        "`extcodecopy` after SELFDESTRUCT depends on fork and creation lifecycle",
        "On post-EIP-6780 chains, SELFDESTRUCT of an existing contract does not remove its code, so extcodecopy does not generally become empty in the next transaction. Empty-code behavior remains relevant for a contract created and destroyed in the same transaction and for pre-EIP-6780 forks.",
        "Code-integrity checks that assume every SELFDESTRUCT empties code can accept or reject the wrong target state.",
        ["The implementation copies or checks code after a target may execute SELFDESTRUCT."],
        ["Identify the target chain fork and whether the target was created in the same transaction as SELFDESTRUCT; inspect both same-transaction and later reads."],
        ["The code-state assertion matches the target fork and creation lifecycle, and identity is checked at use time."],
        ["Run a fork-appropriate trace of extcodesize/extcodecopy before and after SELFDESTRUCT and compare it with the invariant."],
        "semantic",
        "high",
        "EIP-6780 official semantics",
    )
    set_semantic(
        "EVM-ASM-025",
        "`PUSH0` availability depends on compiler target and chain fork",
        "PUSH0 is an EVM instruction introduced by Shanghai. A compiler version alone does not determine whether deployed bytecode contains it: inspect the compiler EVM target and verify that the destination chain supports the instruction.",
        "Deploying bytecode containing PUSH0 to a chain or fork without support can fail at deployment or execution.",
        ["Deployment uses compiler output that may contain PUSH0 and targets a non-mainnet or older fork."],
        ["Inspect compiler version and evmVersion, disassemble the artifact for PUSH0, and compare the target chain fork's opcode support."],
        ["The artifact targets a fork with PUSH0 support, or compilation explicitly targets a compatible earlier EVM version."],
        ["Compile the declared artifact, identify PUSH0 bytes, and deploy or execute against the declared chain fork."],
        "semantic",
        "high",
        "EIP-3855 official semantics and compiler target documentation",
    )
    asm_push0 = by_id("EVM-ASM-025")
    chain_push0 = by_id("EVM-CHAIN-025")
    if asm_push0 is not None and chain_push0 is not None:
        merge_items(asm_push0, [chain_push0], ["evm-audit-assembly", "evm-audit-chain-specific"], "EVM-ASM-025")
        registry["checks"].remove(chain_push0)
        set_semantic(
            "EVM-ASM-025",
            "`PUSH0` availability depends on compiler target and chain fork",
            "PUSH0 is an EVM instruction introduced by Shanghai. A compiler version alone does not determine whether deployed bytecode contains it: inspect the compiler EVM target and verify that the destination chain supports the instruction.",
            "Deploying bytecode containing PUSH0 to a chain or fork without support can fail at deployment or execution.",
            ["Deployment uses compiler output that may contain PUSH0 and targets a non-mainnet or older fork."],
            ["Inspect compiler version and evmVersion, disassemble the artifact for PUSH0, and compare the target chain fork's opcode support."],
            ["The artifact targets a fork with PUSH0 support, or compilation explicitly targets a compatible earlier EVM version."],
            ["Compile the declared artifact, identify PUSH0 bytes, and deploy or execute against the declared chain fork."],
            "semantic",
            "high",
            "EIP-3855 official semantics and compiler target documentation",
        )
        asm_push0["features"] = sorted(set(asm_push0.get("features", [])) | {"uses-chain-specific", "uses-assembly"})
    set_semantic(
        "EVM-CHAIN-014",
        "Opcode support and SELFDESTRUCT semantics are chain- and fork-specific",
        "Do not assume that an opcode's availability or behavior is identical across EVM-compatible chains. In particular, SELFDESTRUCT behavior depends on the chain's adopted fork rules, while custom execution environments may differ in supported opcodes or precompiles.",
        "A deployment that relies on unsupported or differently specified opcode behavior can fail or violate a code/lifecycle invariant.",
        ["The contract uses an opcode whose support or semantics may differ on the declared target chain."],
        ["Compare the bytecode and opcode behavior with the target chain's documented fork and execution environment."],
        ["The target chain explicitly supports the opcode and the implementation's assumptions match its documented semantics."],
        ["Execute the relevant opcode path against the target chain or a matching fork and record the observed result."],
        "semantic",
        "high",
        "EIP-6780 official semantics and target-chain documentation",
    )
    set_semantic(
        "EVM-ERC4626-003",
        "Asymmetric virtual shares/assets require invariant analysis",
        "Virtual shares and virtual assets do not universally have to be equal. An offset may be chosen to address decimals, inflation resistance, or another accounting design; assess the resulting conversion, rounding, and donation invariants instead of treating asymmetry as an automatic vulnerability.",
        "An unjustified offset can distort share value or leave an inflation path, but the defect is the violated invariant rather than inequality alone.",
        ["An ERC4626 implementation uses virtual assets, virtual shares, or a decimals offset."],
        ["Derive the exact conversion formulas at empty and non-empty states and test donation, deposit, mint, withdraw, and redeem boundaries."],
        ["The offset is documented and the resulting conversions preserve ERC4626-ROUND-001 and the vault's solvency invariant."],
        ["Construct boundary deposits and donations and quantify any share-price or solvency deviation caused by the selected offsets."],
        "exploit-pattern",
        "medium",
        "ERC4626 implementation and vault-specific invariant review",
    )
    set_semantic(
        "EVM-ERC4626-018",
        "`preview*` functions may revert for operation-level conditions",
        "ERC-4626 preview functions should reflect the corresponding operation and may revert for conditions that would also make that operation revert, including unreasonably large inputs. They must not revert merely because a vault-specific limit such as maxDeposit or maxWithdraw is exceeded.",
        "Treating preview calls as unconditionally non-reverting can hide a required error path or make an integration rely on a value that cannot be produced by the operation.",
        ["An integration assumes every preview call always succeeds or uses a preview value without handling operation-level failures."],
        ["Compare each preview function with its corresponding mutable operation, vault-specific limits, fees, slippage conditions, and overflow behavior."],
        ["The preview function does not fail solely on vault limits and the caller handles other failures that the operation can also produce."],
        ["Exercise the operation-level failure conditions and verify preview and mutable-call behavior match the declared EIP-4626 semantics."],
        "normative",
        "high",
        "EIP-4626 official requirements",
    )
    set_semantic(
        "EVM-GEN-005",
        "`try/catch` does not make external-call failure harmless",
        "A failure in an external call, including an out-of-gas failure in that call, can enter a catch block when the caller retains enough gas to execute it. `try/catch` only covers the external call or contract creation expression; errors in surrounding expressions, return-data decoding, or the catch block itself are not automatically handled.",
        "Security-critical logic can still fail open or run out of gas if it assumes the success branch, ignores catch behavior, or performs unsafe work before or inside the catch path.",
        ["Security-sensitive behavior depends on the success or catch branch of an external call."],
        ["Trace gas forwarding, external-call failure, return-data decoding, and every statement in the success and catch paths."],
        ["The catch branch preserves the required invariant, has enough bounded gas, and all errors outside the covered external expression are handled separately."],
        ["Use a controlled callee to trigger revert and out-of-gas cases and verify state deltas and post-catch behavior."],
        "semantic",
        "high",
        "Solidity Language Reference: try/catch and external-call failures",
    )
    for canonical_id in ("EVM-ASM-001", "EVM-ASM-002", "EVM-ASM-004", "EVM-ASM-005", "EVM-ASM-008", "EVM-CHAIN-014"):
        item = by_id(canonical_id)
        if item is not None:
            append_provenance(item, "EIP-6780 SELFDESTRUCT", "https://eips.ethereum.org/EIPS/eip-6780", "SELFDESTRUCT lifecycle", "eip-6780")
    push0 = by_id("EVM-ASM-025")
    if push0 is not None:
        append_provenance(push0, "EIP-3855 PUSH0", "https://eips.ethereum.org/EIPS/eip-3855", "PUSH0 instruction", "eip-3855")
    preview = by_id("EVM-ERC4626-018")
    if preview is not None:
        append_provenance(preview, "EIP-4626 Tokenized Vaults", "https://eips.ethereum.org/EIPS/eip-4626", "preview methods", "eip-4626")
    corrected_ids = {
        "EVM-ASM-001",
        "EVM-ASM-002",
        "EVM-ASM-004",
        "EVM-ASM-005",
        "EVM-ASM-008",
        "EVM-ASM-025",
        "EVM-CHAIN-014",
        "EVM-ERC4626-003",
        "EVM-ERC4626-018",
        "EVM-GEN-005",
        "EVM-TIME-001",
        "EVM-TYPE-001",
        "ERC4626-ROUND-001",
    }
    for item in registry.get("checks", []):
        if item.get("canonical_id") in corrected_ids:
            for alias in item.get("aliases", []):
                alias["title"] = f"Legacy alias for {item['canonical_id']} (see canonical definition)"
    return registry


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def one_line(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(str(part).strip() for part in value if str(part).strip())
    return str(value).strip()


def render_provenance(item: dict[str, Any]) -> str:
    rendered: list[str] = []
    for entry in item.get("provenance", []):
        label = entry.get("label", "unknown source")
        url = entry.get("url")
        rendered.append(f"[{label}]({url})" if url else str(label))
    return "; ".join(dict.fromkeys(rendered)) or "Canonical check authored in this registry; verify against the implementation and stated standards."


def render_full_item(item: dict[str, Any]) -> list[str]:
    metadata = f"_({item['type']}; {item['confidence']})_"
    description = one_line(item['description'])
    lines = [f"- [ ] **[{item['canonical_id']}] {item['title']}** {metadata}: {description}"]
    seen = {description}
    for label, field in (
        ("Trigger", "trigger"),
        ("Risk", "risk"),
        ("Detection", "detection"),
        ("FP", "false_positive_gates"),
        ("Proof", "proof"),
    ):
        value = one_line(item[field])
        if value and value not in seen:
            lines.append(f"  - **{label}:** {value}")
            seen.add(value)
    lines.append(f"  - **Provenance:** {render_provenance(item)}")
    if item.get("related"):
        lines.append(f"  - **Related:** {', '.join(item['related'])}")
    if item.get("origin_notes"):
        lines.append(f"  - **Source detail:** {one_line(item['origin_notes'])}")
    if item.get("notes"):
        lines.append(f"  - **Notes:** {one_line(item['notes'])}")
    return lines


def render_alias(item: dict[str, Any]) -> list[str]:
    return [
        f"- [ ] **[{item['canonical_id']}] {item['title']}**: Shared canonical check; apply the primary definition and evidence requirements for `{item['primary_domain']}`.",
    ]


def render_domain(registry: dict[str, Any], domain: str) -> str:
    items = [item for item in registry["checks"] if domain in item.get("domains", [])]
    sections: list[str] = []
    for item in items:
        section = item.get("section", "Uncategorized")
        if section not in sections:
            sections.append(section)
    output = [
        "<!-- GENERATED FILE: source is ../../data/canonical-checks.json; do not edit by hand. -->",
        f"# {DOMAIN_TITLES.get(domain, domain)}",
        "",
        "Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.",
        "",
    ]
    for section in sections:
        output.append(f"## {section}")
        output.append("")
        for item in items:
            if item.get("section") != section:
                continue
            output.extend(render_full_item(item) if item.get("primary_domain") == domain else render_alias(item))
            output.append("")
    return "\n".join(output).rstrip() + "\n"


def generated_outputs(registry: dict[str, Any], root: Path) -> dict[Path, str]:
    return {
        root / domain / "references" / "checklist.md": render_domain(registry, domain)
        for domain in DOMAIN_CODES
    }


def write_outputs(registry: dict[str, Any], root: Path) -> None:
    for path, content in generated_outputs(registry, root).items():
        path.write_text(content, encoding="utf-8")


def check_outputs(registry: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    for path, expected in generated_outputs(registry, root).items():
        if not path.exists():
            errors.append(f"missing generated file: {path}")
            continue
        actual = path.read_text(encoding="utf-8")
        if actual != expected:
            errors.append(f"generated file is stale: {path}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--bootstrap", action="store_true", help="convert the current 876-item Markdown corpus into the registry")
    parser.add_argument("--force", action="store_true", help="allow --bootstrap to replace an existing registry")
    parser.add_argument("--check", action="store_true", help="verify generated Markdown without writing files")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    registry_path = root / "data" / "canonical-checks.json"

    try:
        if args.bootstrap:
            if registry_path.exists() and not args.force:
                raise ValueError(f"registry already exists; use --force only after reviewing {registry_path}")
            registry = bootstrap_registry(root)
            if not args.check:
                write_json(registry_path, registry)
        else:
            if not registry_path.exists():
                raise ValueError(f"missing registry: {registry_path}; run --bootstrap once")
            registry = normalize_registry(load_registry(registry_path))

        errors = check_outputs(registry, root)
        if args.check:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            print(f"canonical_checks={len(registry.get('checks', []))} generated_errors={len(errors)}")
            return 1 if errors else 0
        write_json(registry_path, registry)
        write_outputs(registry, root)
        print(f"canonical_checks={len(registry.get('checks', []))} generated={len(DOMAIN_CODES)}")
        return 0
    except (OSError, ValueError, KeyError, StopIteration) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
