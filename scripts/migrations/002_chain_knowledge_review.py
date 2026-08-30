#!/usr/bin/env python3
"""One-time 2026-08-30 review of chain-specific canonical knowledge."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "data" / "canonical-checks.json"
VERIFIED_AT = "2026-08-30"

SOURCES = {
    "chainlink-sequencer-feeds": ("Chainlink L2 sequencer uptime feeds", "https://docs.chain.link/data-feeds/l2-sequencer-feeds"),
    "chainlink-selecting-feeds": ("Chainlink selecting data feeds", "https://docs.chain.link/data-feeds/selecting-data-feeds"),
    "arbitrum-l1-to-l2": ("Arbitrum parent-to-child messaging", "https://docs.arbitrum.io/how-arbitrum-works/deep-dives/l1-to-l2-messaging"),
    "arbitrum-l2-to-l1": ("Arbitrum child-to-parent messaging", "https://docs.arbitrum.io/how-arbitrum-works/deep-dives/l2-to-l1-messaging"),
    "op-stack-fees": ("OP Stack transaction fees", "https://docs.optimism.io/stack/transactions/fees"),
    "zksync-account-abstraction": ("ZKsync native account abstraction", "https://docs.zksync.io/zksync-protocol/account-abstraction"),
    "blast-eth-yield": ("Blast ETH yield modes", "https://docs.blast.io/building/guides/eth-yield"),
    "blast-weth-yield": ("Blast WETH and USDB yield modes", "https://docs.blast.io/building/guides/weth-yield"),
    "blast-gas-fees": ("Blast gas modes", "https://docs.blast.io/building/guides/gas-fees"),
    "eip-1559": ("EIP-1559 fee market", "https://eips.ethereum.org/EIPS/eip-1559"),
}

OFFICIAL = {
    "EVM-CHAIN-004": ("chainlink-sequencer-feeds", "sequencer status and recovery grace period"),
    "EVM-CHAIN-006": ("arbitrum-l2-to-l1", "challenge period and outbox execution"),
    "EVM-CHAIN-007": ("arbitrum-l1-to-l2", "address aliasing for parent-chain contract senders"),
    "EVM-CHAIN-009": ("op-stack-fees", "execution gas and L1 data fee components"),
    "EVM-CHAIN-011": ("zksync-account-abstraction", "native account abstraction"),
    "EVM-CHAIN-012": ("zksync-evm-differences", "EXTCODESIZE and system-contract differences"),
    "EVM-CHAIN-013": ("zksync-evm-differences", "CREATE and CREATE2 address derivation"),
    "EVM-CHAIN-016": ("blast-eth-yield", "contract ETH yield modes and default void mode"),
    "EVM-CHAIN-017": ("blast-weth-yield", "WETH and USDB automatic default yield mode"),
    "EVM-CHAIN-018": ("blast-gas-fees", "default void gas mode and claimable mode"),
    "EVM-CHAIN-026": ("eip-1559", "fee-market parameters are protocol configuration"),
    "EVM-CHAIN-030": ("chainlink-selecting-feeds", "feed-specific heartbeat and deviation threshold"),
    "EVM-CHAIN-031": ("chainlink-selecting-feeds", "feed proxy and aggregator configuration"),
    "EVM-CHAIN-033": ("arbitrum-custom-gas", "custom gas token denomination"),
}

STATIC = {
    "EVM-CHAIN-015", "EVM-CHAIN-019", "EVM-CHAIN-021", "EVM-CHAIN-023",
    "EVM-CHAIN-024", "EVM-CHAIN-027", "EVM-CHAIN-028", "EVM-CHAIN-034",
    "EVM-CHAIN-035", "EVM-CHAIN-036", "EVM-CHAIN-038", "EVM-CHAIN-039",
}

VERSIONED = {"EVM-CHAIN-006", "EVM-CHAIN-007", "EVM-CHAIN-009", "EVM-CHAIN-011", "EVM-CHAIN-012", "EVM-CHAIN-013", "EVM-CHAIN-026", "EVM-CHAIN-030", "EVM-CHAIN-031", "EVM-CHAIN-033"}

CHAINS = {
    **{f"EVM-CHAIN-{index:03d}": "arbitrum" for index in range(1, 8)},
    **{f"EVM-CHAIN-{index:03d}": "op-stack" for index in range(8, 11)},
    **{f"EVM-CHAIN-{index:03d}": "zksync-era" for index in range(11, 16)},
    **{f"EVM-CHAIN-{index:03d}": "blast" for index in range(16, 19)},
    **{f"EVM-CHAIN-{index:03d}": "bnb-smart-chain" for index in range(19, 22)},
    "EVM-CHAIN-022": "polygon-pos",
    "EVM-CHAIN-032": "arbitrum-orbit",
    "EVM-CHAIN-033": "arbitrum-orbit",
    "EVM-CHAIN-037": "zksync-era",
}


def main() -> int:
    registry: dict[str, Any] = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    for key, (label, url) in SOURCES.items():
        registry["source_catalog"].setdefault(key, {"label": label, "url": url, "kind": "official"})

    for check in registry["checks"]:
        if "evm-audit-chain-specific" not in check.get("domains", []):
            continue
        canonical_id = check["canonical_id"]
        check["verified_at"] = VERIFIED_AT
        if canonical_id in STATIC:
            check["freshness"] = "static"
            check["verification"] = {
                "status": "verified",
                "basis": "Reviewed as a deployment-specific invariant with no mutable numeric or address claim",
            }
        elif canonical_id in VERSIONED:
            check["freshness"] = "versioned"
        if canonical_id in CHAINS:
            check["chain"] = CHAINS[canonical_id]
        if canonical_id in OFFICIAL:
            source_key, locator = OFFICIAL[canonical_id]
            source = registry["source_catalog"][source_key]
            provenance = {
                "source_key": source_key,
                "label": source["label"],
                "url": source["url"],
                "kind": "official",
                "locator": locator,
            }
            if not any(entry.get("source_key") == source_key for entry in check["provenance"]):
                check["provenance"].append(provenance)
            check["verification"] = {"status": "verified", "basis": f"{source['label']}: {locator}"}

    by_id = {check["canonical_id"]: check for check in registry["checks"]}
    by_id["EVM-CHAIN-004"].update({
        "title": "Gate L2 liquidations and auctions on sequencer status and recovery",
        "description": "A sequencer outage can prevent timely user and keeper transactions while external markets continue moving. On recovery, stale state and queued actions can make immediate liquidations or auctions unsafe. Use the target network's supported uptime signal and a documented recovery grace period when the protocol depends on continuous sequencing.",
        "risk": "Outage and recovery can concentrate stale liquidations, auctions, or keeper actions into the first executable blocks and violate assumptions about timely intervention.",
        "trigger": ["An L2 liquidation, auction, or time-sensitive keeper path assumes continuous sequencer availability."],
        "detection": ["Trace the target chain's sequencer status signal, recovery behavior, oracle updates, and the first executable liquidation or auction after recovery."],
        "false_positive_gates": ["The target has no centralized sequencer dependency, or the operation remains safe under a bounded outage and documented recovery procedure."],
        "proof": ["Simulate an outage and recovery with adverse external price movement and show whether the first executable actions preserve the protocol invariant."],
    })
    by_id["EVM-CHAIN-016"].update({
        "title": "Blast contract ETH yield depends on the configured yield mode",
        "description": "Blast smart contracts default to Void yield, so their ETH balance does not rebase. A contract balance grows only after configuring Automatic yield; Claimable mode accrues yield separately. Accounting and governor logic must match the configured mode rather than assuming every contract balance grows.",
        "risk": "Accounting can drift or promised yield can disappear when the implementation assumes a different ETH yield mode than the deployed configuration.",
        "trigger": ["A Blast deployment relies on ETH yield, stable native balances, or asynchronous yield claims."],
        "detection": ["Read the deployed contract's yield mode and governor, then trace whether accounting uses rebasing balances or separately claimable yield."],
        "false_positive_gates": ["The deployment remains in Void mode and assumes no yield, or its accounting and access control explicitly implement the selected mode."],
        "proof": ["Exercise Void, Automatic, and Claimable configurations and show that balance and claim accounting match the selected mode."],
    })
    by_id["EVM-CHAIN-018"].update({
        "title": "Blast gas fees require claimable mode and deliberate governor control",
        "description": "Blast contracts default to Void gas mode, which leaves fees with the sequencer operator. Gas fees are claimable only after configuring Claimable mode, and the governor controls configuration and claims. Treat unclaimed gas as an optional revenue decision, not automatically stuck protocol funds.",
        "risk": "A mismatched gas mode or governor can invalidate promised revenue or give an unintended party control over gas-fee claims.",
        "trigger": ["A Blast deployment promises gas-fee revenue or exposes gas-mode and governor configuration."],
        "detection": ["Inspect gas mode, governor assignment, claim authorization, recipient selection, and whether the product actually promises gas revenue."],
        "false_positive_gates": ["Void mode is intentional, or Claimable mode and governor permissions match the documented revenue policy."],
        "proof": ["Exercise configuration and claim paths from authorized and unauthorized callers and reconcile claimed value with the documented policy."],
    })
    by_id["EVM-CHAIN-038"]["description"] = "Token callback behavior is a property of the deployed token and its upgrade history, not its symbol or chain label. Inspect the exact contract and protect accounting around arbitrary token callbacks."

    REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("reviewed_chain_checks=" + str(sum("evm-audit-chain-specific" in check.get("domains", []) for check in registry["checks"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
