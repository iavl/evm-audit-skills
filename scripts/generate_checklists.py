#!/usr/bin/env python3
"""Render runtime Markdown views from the canonical JSON registry.

The generator is deliberately knowledge-free: it never repairs, infers, or
rewrites canonical records. Historical transformations live under
``scripts/migrations`` and normal maintenance edits ``data/canonical-checks.json``.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "canonical-checks.json"

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


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_registry(registry: dict[str, Any]) -> dict[str, Any]:
    """Compatibility helper that isolates input without changing knowledge."""

    return copy.deepcopy(registry)


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
    return "; ".join(dict.fromkeys(rendered)) or "Canonical registry entry"


def render_full_item(item: dict[str, Any]) -> list[str]:
    metadata = f"_({item['type']}; {item['confidence']})_"
    description = one_line(item["description"])
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
        f"- [ ] **[{item['canonical_id']}] {item['title']}**: Shared canonical check; "
        f"apply the primary definition and evidence requirements for `{item['primary_domain']}`."
    ]


def render_domain(registry: dict[str, Any], domain: str) -> str:
    items = [item for item in registry["checks"] if domain in item.get("domains", [])]
    sections = list(dict.fromkeys(item.get("section", "Uncategorized") for item in items))
    output = [
        "<!-- GENERATED FILE: source is ../../data/canonical-checks.json; do not edit by hand. -->",
        f"# {DOMAIN_TITLES.get(domain, domain)}",
        "",
        "Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.",
        "",
    ]
    for section in sections:
        output.extend([f"## {section}", ""])
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
        elif path.read_text(encoding="utf-8") != expected:
            errors.append(f"generated file is stale: {path}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true", help="verify generated Markdown without writing files")
    args = parser.parse_args(argv)
    root = args.root.resolve()

    try:
        registry = load_registry(root / "data" / "canonical-checks.json")
        errors = check_outputs(registry, root)
        if args.check:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            print(f"canonical_checks={len(registry.get('checks', []))} generated_errors={len(errors)}")
            return 1 if errors else 0
        write_outputs(registry, root)
        print(f"canonical_checks={len(registry.get('checks', []))} generated={len(DOMAIN_CODES)}")
        return 0
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
