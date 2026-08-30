#!/usr/bin/env python3
"""One-time migration to registry schema v3 and evidence schema v3.

This script records the knowledge corrections that were previously hidden in
generator normalization code. It is intentionally idempotent so a maintainer
can reproduce the migration, but normal generation never imports or runs it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "data" / "canonical-checks.json"
CLAIMS_PATH = ROOT / "tests" / "knowledge" / "claims.json"
VERIFIED_AT = "2026-08-30"


OFFICIAL_SOURCES = {
    "optimism-opcode-differences": {
        "label": "OP Stack opcode differences",
        "url": "https://docs.optimism.io/op-stack/protocol/differences",
        "kind": "official",
    },
    "bnb-chain-introduction": {
        "label": "BNB Smart Chain introduction",
        "url": "https://docs.bnbchain.org/bnb-smart-chain/introduction/",
        "kind": "official",
    },
    "polygon-pol": {
        "label": "Polygon POL documentation",
        "url": "https://docs.polygon.technology/pos/concepts/tokens/pol",
        "kind": "official",
    },
    "arbitrum-block-time": {
        "label": "Arbitrum block numbers and time",
        "url": "https://docs.arbitrum.io/arbitrum-essentials/arbitrum-vs-ethereum/block-numbers-and-time",
        "kind": "official",
    },
    "arbitrum-gas-fees": {
        "label": "Arbitrum gas and fees",
        "url": "https://docs.arbitrum.io/how-arbitrum-works/deep-dives/gas-and-fees",
        "kind": "official",
    },
    "arbitrum-retryables": {
        "label": "Arbitrum parent-to-child messaging",
        "url": "https://docs.arbitrum.io/how-arbitrum-works/deep-dives/l1-to-l2-messaging",
        "kind": "official",
    },
    "arbitrum-custom-gas": {
        "label": "Arbitrum custom gas token chains",
        "url": "https://docs.arbitrum.io/arbitrum-essentials/bridging/custom-gas-token-chains",
        "kind": "official",
    },
    "zksync-evm-differences": {
        "label": "ZKsync Era EVM instruction differences",
        "url": "https://docs.zksync.io/zksync-protocol/era-vm/differences/evm-instructions",
        "kind": "official",
    },
    "eip-1344": {
        "label": "EIP-1344 ChainID opcode",
        "url": "https://eips.ethereum.org/EIPS/eip-1344",
        "kind": "official",
    },
    "solidity-known-bugs": {
        "label": "Solidity known bugs",
        "url": "https://docs.soliditylang.org/en/latest/bugs.html",
        "kind": "official",
    },
    "solidity-v050-breaking": {
        "label": "Solidity 0.5.0 breaking changes",
        "url": "https://docs.soliditylang.org/en/latest/050-breaking-changes.html",
        "kind": "official",
    },
    "solidity-unicode": {
        "label": "Solidity Unicode literals",
        "url": "https://docs.soliditylang.org/en/latest/layout-of-source-files.html#unicode-literals",
        "kind": "official",
    },
    "solidity-private-information": {
        "label": "Solidity private information and randomness",
        "url": "https://docs.soliditylang.org/en/latest/security-considerations.html#private-information-and-randomness",
        "kind": "official",
    },
}


EXECUTABLE_EVIDENCE = {
    "EVM-ASM-009": "testYulDivisionByZeroReturnsZero",
    "EVM-MATH-021": "testYulDivisionByZeroReturnsZero",
    "EVM-ASM-010": "testYulArithmeticWrapsAt256Bits",
    "EVM-ASM-036": "testYulArithmeticWrapsAt256Bits",
    "EVM-ASM-014": "testFreeMemoryPointerIsNotAdvancedByMstore",
    "EVM-ASM-034": "testFreeMemoryPointerIsNotAdvancedByMstore",
    "EVM-ASM-035": "testFreeMemoryPointerIsNotAdvancedByMstore",
    "EVM-ASM-015": "testReturndataBufferIsReplacedAfterEachCall",
    "EVM-ASM-018": "testTransientStorageIsSharedThroughDelegatecall",
    "EVM-ASM-019": "testTransientStorageIsSharedThroughDelegatecall",
    "EVM-ASM-021": "testCallToNoCodeReturnsSuccessWithEmptyData",
    "EVM-ASM-022": "testDelegatecallPreservesSenderAndValue",
    "EVM-GEN-004": "testDelegatecallPreservesSenderAndValue",
    "EVM-ASM-023": "testReturndataCanBeArbitrarilyLarge",
    "EVM-GEN-002": "testReturndataCanBeArbitrarilyLarge",
    "EVM-GEN-065": "testReturndataCanBeArbitrarilyLarge",
    "EVM-ASM-027": "testNarrowAssemblyValueCanCarryDirtyUpperBits",
    "EVM-ASM-032": "testChainidAndCodeLengthHaveHighLevelSyntax",
    "EVM-ASM-033": "testExternalCallWritesToCallerSelectedMemory",
    "EVM-ASM-037": "testCreateFailureReturnsZeroInYul",
    "EVM-ASM-038": "testAssemblyCanReadNonCanonicalTrailingCalldata",
    "EVM-ASM-039": "testHardcodedCalldataOffsetReadsDynamicHead",
    "EVM-GEN-003": "testFixedGasCallCanFailWhileFullGasSucceeds",
    "EVM-GEN-048": "testCrossContractReentrancyOccursBeforeAccounting",
    "EVM-GEN-056": "testC3InheritanceOrderChangesSuperResolution",
    "EVM-GEN-059": "testExpressionWidthAndDowncastSemantics",
    "EVM-GEN-061": "testExpressionWidthAndDowncastSemantics",
    "EVM-MATH-004": "testIntegerDivisionRoundsTowardZero",
}


OFFICIAL_CLAIM_EVIDENCE = {
    "EVM-CHAIN-001": ("arbitrum-block-time", "block.number behavior"),
    "EVM-CHAIN-002": ("arbitrum-block-time", "multiple child blocks per parent block"),
    "EVM-CHAIN-008": ("optimism-opcode-differences", "NUMBER opcode behavior"),
    "EVM-CHAIN-032": ("arbitrum-custom-gas", "custom gas token behavior"),
    "EVM-CHAIN-037": ("zksync-evm-differences", "EraVM instruction differences"),
    "EVM-GEN-034": ("bnb-chain-introduction", "upgrade-dependent block cadence"),
    "EVM-GEN-035": ("arbitrum-block-time", "block production and parent-chain timing"),
    "EVM-GEN-051": ("solidity-known-bugs", "compiler known-bug list"),
    "EVM-GEN-054": ("solidity-v050-breaking", "uninitialized storage variables are disallowed"),
    "EVM-GEN-055": ("solidity-unicode", "Unicode source literal rules"),
    "EVM-GEN-057": ("solidity-private-information", "private on-chain information"),
    "EVM-GEN-077": ("arbitrum-block-time", "block-number timing assumptions"),
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def by_id(registry: dict[str, Any], canonical_id: str) -> dict[str, Any]:
    return next(check for check in registry["checks"] if check["canonical_id"] == canonical_id)


def add_official(registry: dict[str, Any], canonical_id: str, source_key: str, locator: str) -> None:
    source = OFFICIAL_SOURCES[source_key]
    check = by_id(registry, canonical_id)
    entry = {
        "label": source["label"],
        "locator": locator,
        "url": source["url"],
        "kind": "official",
        "source_key": source_key,
    }
    if entry not in check["provenance"]:
        check["provenance"].append(entry)
    check["verification"] = {"status": "verified", "basis": f"{source['label']}: {locator}"}
    check["verified_at"] = VERIFIED_AT


def rewrite(
    registry: dict[str, Any],
    canonical_id: str,
    *,
    title: str,
    description: str,
    risk: str,
    trigger: str,
    detection: str,
    false_positive: str,
    proof: str,
) -> None:
    check = by_id(registry, canonical_id)
    check.update(
        title=title,
        description=description,
        risk=risk,
        trigger=[trigger],
        detection=[detection],
        false_positive_gates=[false_positive],
        proof=[proof],
    )


def migrate_registry(registry: dict[str, Any]) -> dict[str, Any]:
    registry["schema_version"] = 3
    registry["description"] = "Canonical EVM audit checks. Generated Markdown is a pure runtime compatibility view."
    registry.setdefault("source_catalog", {}).update(OFFICIAL_SOURCES)

    versioned_domains = {
        "evm-audit-bridges",
        "evm-audit-erc4337",
        "evm-audit-oracles",
        "evm-audit-proxies",
    }
    for check in registry["checks"]:
        domains = set(check.get("domains", []))
        if "evm-audit-chain-specific" in domains:
            freshness = "time-sensitive"
        elif domains & versioned_domains:
            freshness = "versioned"
        else:
            freshness = "static"
        check["freshness"] = freshness
        check.setdefault("verified_at", None)

    rewrite(
        registry,
        "EVM-CHAIN-008",
        title="OP Stack `block.number` is an L2 block number with deployment-specific cadence",
        description="On OP Stack chains, `block.number` identifies the L2 block. Do not convert L2 block counts to elapsed time using an Ethereum or historically observed OP cadence; protocol upgrades and chain configuration can change block production behavior.",
        risk="Block-count deadlines, accrual, and cooldowns can run for the wrong wall-clock duration when calibrated to a fixed cadence.",
        trigger="Time-sensitive logic on an OP Stack deployment derives elapsed time from `block.number` deltas.",
        detection="Identify every block-count-to-time conversion and compare it with the target deployment's current documented cadence and upgrade policy.",
        false_positive="The logic intentionally measures L2 blocks rather than elapsed time, or uses timestamp-based bounds with documented drift assumptions.",
        proof="Run the logic against the declared OP Stack deployment parameters and show the resulting wall-clock window across relevant upgrades.",
    )
    add_official(registry, "EVM-CHAIN-008", "optimism-opcode-differences", "NUMBER opcode returns the L2 block number")

    rewrite(
        registry,
        "EVM-CHAIN-010",
        title="OP Stack PREVRANDAO reflects the current L1 origin",
        description="On OP Stack, `block.prevrandao` returns the PREVRANDAO value from the current L1 origin block rather than an independently generated per-L2-block randomness source. Do not assume that it provides fresh entropy for every L2 block.",
        risk="Several L2 blocks can inherit the same or predictably related L1-origin value, breaking uniqueness or randomness assumptions.",
        trigger="An OP Stack deployment uses `block.prevrandao` or `block.difficulty` for randomness, uniqueness, lotteries, or commit selection.",
        detection="Trace the L1 origin used by each relevant L2 block and determine whether repeated or known PREVRANDAO values let an actor influence the outcome.",
        false_positive="The value is mixed with an independent, manipulation-resistant randomness source and no per-L2-block entropy assumption remains.",
        proof="Demonstrate repeated L1-origin PREVRANDAO across the relevant L2 sequence or prove that independent entropy preserves the security invariant.",
    )
    add_official(registry, "EVM-CHAIN-010", "optimism-opcode-differences", "PREVRANDAO opcode behavior")

    rewrite(
        registry,
        "EVM-CHAIN-020",
        title="Do not hardcode BNB Chain block cadence",
        description="BNB Smart Chain block cadence has changed across protocol upgrades. Time-sensitive logic must not hardcode a historical block interval; use timestamp-based constraints or deployment-specific documented parameters when the operation truly depends on elapsed time.",
        risk="A later network upgrade can shorten or lengthen block-count-based windows, changing cooldowns, auctions, rewards, or governance timing without a contract change.",
        trigger="A BNB Chain deployment converts blocks to seconds or embeds a fixed number of blocks for a wall-clock requirement.",
        detection="Locate fixed block-time constants and compare the intended duration with current BNB Chain documentation and the deployment's upgrade assumptions.",
        false_positive="The invariant is explicitly block-count based, or elapsed-time logic uses timestamps with documented tolerance.",
        proof="Calculate the effective window under the current and at least one historical cadence and show whether the security requirement still holds.",
    )
    add_official(registry, "EVM-CHAIN-020", "bnb-chain-introduction", "current mainnet block time and Lorentz/Maxwell/Fermi history")

    rewrite(
        registry,
        "EVM-CHAIN-022",
        title="Polygon PoS native gas token is POL",
        description="Polygon PoS has migrated its native gas and staking token from MATIC to POL. Integrations must distinguish native POL, POL on Ethereum, legacy MATIC, and wrapped or bridged token contracts instead of treating the migration as pending.",
        risk="Stale symbols, addresses, bridge assumptions, or accounting branches can route funds incorrectly or reject the current native asset.",
        trigger="A Polygon PoS integration hardcodes MATIC/WMATIC symbols, addresses, bridge behavior, or migration-state branches.",
        detection="Trace native and ERC-20 asset identifiers on every supported chain and verify current POL bridge and wrapping behavior against the deployed contracts.",
        false_positive="The integration intentionally supports a legacy Ethereum-side MATIC migration path and separately handles Polygon PoS native POL.",
        proof="Exercise native and token paths on the declared Polygon deployment and show that every address, symbol, and accounting branch resolves to the intended asset.",
    )
    add_official(registry, "EVM-CHAIN-022", "polygon-pol", "POL native token and MATIC replacement")

    rewrite(
        registry,
        "EVM-CHAIN-003",
        title="Arbitrum L2 base fee and parent-chain data fee are separate",
        description="On Arbitrum, the child-chain base fee used for L2 execution is distinct from the estimated parent-chain base fee used for data-posting costs. Use NodeInterface or ArbGasInfo components rather than treating `block.basefee` as the L1 base fee.",
        risk="Conflating the two fee components produces incorrect gas estimation, reimbursement, or fee caps.",
        trigger="Arbitrum code uses `block.basefee` as an L1 data-price input or assumes one base-fee value covers both components.",
        detection="Trace each fee variable to its documented L2 execution or parent-chain posting component and verify units before combining them.",
        false_positive="The formula intentionally consumes the child-chain base fee and obtains parent-chain components from the documented interface.",
        proof="Compare the contract's computed fee with NodeInterface or ArbGasInfo component values for the same transaction.",
    )
    add_official(registry, "EVM-CHAIN-003", "arbitrum-gas-fees", "L2 base fee and L1 data-price components")

    rewrite(
        registry,
        "EVM-CHAIN-005",
        title="Retryable ticket failure, expiry, and refunds require explicit handling",
        description="An Arbitrum retryable ticket can fail automatic redemption and require manual redemption before its configured lifetime expires. Expiry and refund destinations are part of the value-flow model; do not summarize every failed auto-redeem as permanent fund loss.",
        risk="Ignoring retry, expiry, and refund ownership can leave messages unexecuted or make refunds inaccessible to the intended party.",
        trigger="A parent-to-child flow assumes auto-redemption always succeeds or does not track the ticket lifecycle and refund addresses.",
        detection="Trace ticket creation, auto-redeem status, manual redemption, lifetime extension, expiry, and both refund addresses.",
        false_positive="The integration monitors the complete lifecycle and proves that execution or refunds remain recoverable by the intended owner.",
        proof="Force auto-redemption failure and record the manual redemption and expiry/refund outcomes on the target Arbitrum configuration.",
    )
    add_official(registry, "EVM-CHAIN-005", "arbitrum-retryables", "retryable lifecycle and refund semantics")

    rewrite(
        registry,
        "EVM-CHAIN-029",
        title="Signature domains must handle a possible chain ID change",
        description="`block.chainid` exposes the current chain ID. A contentious split or governance decision can change chain identity; a cached EIP-712 domain separator must either be intentionally fixed or rebuilt when the runtime chain ID differs. Ordinary hard forks do not inherently change the chain ID.",
        risk="A stale cached chain ID can enable cross-fork replay or invalidate signatures after a chain identity change.",
        trigger="A signature domain caches the deployment chain ID without defining behavior for a later runtime mismatch.",
        detection="Compare cached and runtime chain IDs in the signing and verification paths and document the intended fork/replay policy.",
        false_positive="The domain separator is recomputed on mismatch, or the protocol intentionally pins one chain identity and safely rejects the other.",
        proof="Simulate a chain ID mismatch and show whether signatures replay, fail safely, or rebuild the expected domain.",
    )
    add_official(registry, "EVM-CHAIN-029", "eip-1344", "chain ID opcode rationale and fork handling")

    rewrite(
        registry,
        "EVM-CHAIN-035",
        title="Transaction ordering and order-flow visibility are chain-specific",
        description="Mempool visibility, sequencer policy, private order flow, forced inclusion, and proposer capabilities vary by chain and can change over time. Never classify front-running or ordering manipulation as impossible solely because one public mempool is absent.",
        risk="An incomplete ordering threat model can miss sequencer, builder, RPC, or delayed-inclusion strategies that reorder security-sensitive transactions.",
        trigger="A protocol omits slippage, commit-reveal, or ordering defenses based on an assumed private or nonexistent mempool.",
        detection="Document every party that can observe, delay, insert, or reorder transactions on the target deployment and its fallback paths.",
        false_positive="The invariant is order-independent or a deployment-specific mechanism cryptographically prevents the relevant ordering attack.",
        proof="Construct the strongest ordering capability available to sequencers, builders, RPC operators, and users and test the protected operation.",
    )

    rewrite(
        registry,
        "EVM-CHAIN-037",
        title="ZKsync EraVM compatibility must be checked per instruction and deployment path",
        description="ZKsync EraVM is source-compatible with much Solidity code but differs from the EVM in documented instruction, bytecode, address-derivation, and deployment behavior. Do not claim that every common opcode behaves differently; review only the documented differences reached by the target code and toolchain.",
        risk="EVM-specific bytecode, factory dependencies, address calculations, or call assumptions can fail or produce different results on EraVM.",
        trigger="A deployment targets ZKsync Era and uses low-level instructions, bytecode inspection, CREATE/CREATE2, system contracts, or EVM-specific tooling.",
        detection="Map the reached instructions and deployment artifacts to the current EraVM differences documentation and compiler mode.",
        false_positive="The target uses the supported EVM interpreter path or the reached instructions are documented as equivalent under the declared compiler and protocol version.",
        proof="Compile and execute the exact artifact on the declared ZKsync environment and compare each relied-upon behavior with the EVM baseline.",
    )
    add_official(registry, "EVM-CHAIN-037", "zksync-evm-differences", "documented EraVM instruction differences")

    rewrite(
        registry,
        "EVM-MATH-005",
        title="Choose rounding from supplied and received quantities",
        description="For every conversion, identify which quantity the caller supplies and which quantity the caller receives, then choose rounding against the value-extracting caller unless the governing standard mandates a direction. Do not infer one rule from operation names such as deposit or mint. For ERC-4626 use ERC4626-ROUND-001.",
        risk="Rounding the wrong quantity can leak value on each conversion and can conflict with a standard's required preview and state-changing semantics.",
        trigger="A conversion, fee, AMM, or vault formula divides or uses `mulDiv` without documenting the supplied quantity, received quantity, and required rounding direction.",
        detection="Name the economic input and output of each path, derive both forward and inverse formulas, and compare their rounding with the governing standard and solvency invariant.",
        false_positive="The direction is explicitly required by the applicable standard or proven to preserve the protocol's value and round-trip invariants.",
        proof="Test boundary amounts and repeated round trips, and prove that no caller can accumulate value from the selected direction.",
    )

    rewrite(
        registry,
        "EVM-GEN-034",
        title="Block cadence varies across chains and upgrades",
        description="Block production cadence and the relationship between block numbers and wall-clock time differ across chains and can change with protocol upgrades. Do not encode a chain's observed interval as a universal time unit.",
        risk="A block-count time proxy can shorten or extend deadlines, accrual periods, auctions, or cooldowns beyond the intended security window.",
        trigger="The implementation converts block-number deltas into seconds or selects a fixed block count to represent elapsed time.",
        detection="Compare every block-based duration with the target chain's documented execution model, upgrade policy, and required timestamp tolerance.",
        false_positive="The requirement is deliberately measured in blocks, or timestamp-based bounds make cadence changes harmless.",
        proof="Evaluate the effective wall-clock interval under the declared deployment and plausible cadence changes, then test the security invariant.",
    )
    rewrite(
        registry,
        "EVM-GEN-035",
        title="Block production and timestamp progress are not uniform",
        description="Block numbers, timestamps, sequencer batches, and parent-chain origins advance according to chain-specific execution rules rather than a universal constant interval. Treat monotonicity, resolution, and liveness as separate assumptions.",
        risk="A design that assumes constant block progress can accept stale state, skip required observations, or make liveness windows unpredictable.",
        trigger="Logic uses block numbers or timestamps as if every chain emits one regularly spaced block.",
        detection="Map the value to its source chain, parent origin, sequencer behavior, and documented timestamp constraints before relying on its resolution or rate.",
        false_positive="The invariant tolerates documented drift and does not depend on a fixed block frequency.",
        proof="Replay the relevant path with delayed, batched, or irregular block production and compare the observed state transition with the intended invariant.",
    )
    rewrite(
        registry,
        "EVM-GEN-077",
        title="Block number is not a timestamp",
        description="Multiplying a block-number delta by a fixed seconds-per-block constant is not a reliable elapsed-time measurement across chains, sequencers, or upgrades. Use `block.timestamp` with an explicit drift tolerance when the requirement is time-based.",
        risk="Hardcoded block-time arithmetic can release, accrue, or expire state earlier or later than the protocol's stated wall-clock requirement.",
        trigger="Time is computed from `(block.number - startBlock) * constant` or an equivalent fixed cadence assumption.",
        detection="Identify the source of every duration and compare the required wall-clock bound with the target chain's timestamp and block-number semantics.",
        false_positive="The protocol intentionally counts blocks and documents that its invariant is independent of elapsed wall-clock time.",
        proof="Run boundary cases across delayed and accelerated block production and show whether the time-based invariant still holds.",
    )

    rewrite(
        registry,
        "EVM-CHAIN-006",
        title="Arbitrum L2-to-L1 delay is deployment- and bridge-specific",
        description="Arbitrum withdrawals and L2-to-L1 messages can be subject to a configured challenge or finality period; the historical Arbitrum One window is commonly described as about a week. Do not hardcode a universal seven-day value across Arbitrum chains or bridge providers.",
        risk="Assuming a shorter or fixed finality period can release funds or advance state before the selected bridge's security window has elapsed.",
        trigger="A protocol treats an Arbitrum L2-to-L1 message as finalized after a hardcoded duration or without reading the bridge state.",
        detection="Resolve the exact chain, bridge, challenge configuration, and finality signal used by the withdrawal path.",
        false_positive="The integration consumes the bridge's current finality state and separately handles configured expiry and retry behavior.",
        proof="Measure the message lifecycle on the declared chain and bridge and compare the release condition with the configured finality requirement.",
    )
    rewrite(
        registry,
        "EVM-CHAIN-009",
        title="OP Stack execution and L1 data fees are separate components",
        description="OP Stack transactions account for L2 execution gas and an L1 data-posting component whose formula and parameters are deployment-specific. Do not use a fixed percentage or `gasleft()` alone to estimate the total fee.",
        risk="Ignoring or mispricing the parent-chain component can underfund relayed calls, misallocate reimbursements, or make a supposedly bounded operation fail.",
        trigger="Gas accounting on OP Stack derives a total cost solely from L2 execution gas or a historical percentage of the total.",
        detection="Trace the Gas Price Oracle or equivalent fee parameters and verify units, compression, and the target chain's current formula.",
        false_positive="The integration uses the chain's documented fee oracle or RPC estimate for the exact transaction payload.",
        proof="Compare the implementation's estimate with the target chain's fee components for representative calldata sizes and parameter changes.",
    )
    rewrite(
        registry,
        "EVM-CHAIN-015",
        title="Native-value reception paths are chain- and system-contract-specific",
        description="Native-value delivery on zkSync and other execution environments can involve system contracts, account abstraction, or bridge-specific paths. Do not assume that a Solidity `receive()` or `fallback()` path is the only way funds arrive or that it has identical behavior on every chain.",
        risk="A missing or misclassified reception path can strand native value, bypass accounting, or make a bridge callback fail.",
        trigger="A multichain contract assumes all native ETH/POL/ETH-like value arrives through one ordinary EVM entry point.",
        detection="Enumerate direct calls, system-contract transfers, bridge callbacks, and account-abstraction paths on the declared deployment.",
        false_positive="The target environment documents the exact reception path and the contract accounts for every reachable native-value source.",
        proof="Execute each documented value-delivery path and compare balances, events, and accounting state with the intended invariant.",
    )
    rewrite(
        registry,
        "EVM-CHAIN-019",
        title="BEP-20 allowance behavior is token-specific",
        description="BNB Smart Chain does not make all BEP-20 tokens share one allowance-reset behavior. Some deployed tokens may reject zero-to-nonzero or nonzero-to-nonzero approvals, so inspect the actual token instead of attributing a universal rule to BNB.",
        risk="A generic approval wrapper can revert, strand funds, or leave an unexpected allowance when used with a token-specific implementation.",
        trigger="A BSC integration applies one approval sequence to arbitrary BEP-20 tokens.",
        detection="Inspect the deployed token bytecode and exercise zero, nonzero, and repeated approval transitions.",
        false_positive="The token set is allowlisted and each allowance path is tested against its deployed implementation.",
        proof="Run the wrapper against every supported token and record return data, reverts, and final allowance state.",
    )
    rewrite(
        registry,
        "EVM-CHAIN-023",
        title="Confirmation depth and reorg risk are chain-specific",
        description="Reorganization frequency, finality signals, validator/sequencer behavior, and confirmation recommendations differ across chains and deployments. Do not label one chain universally more or less reorganizable than another without a declared observation window and finality model.",
        risk="A fixed confirmation count can accept reversible state or delay safe settlement beyond the intended liveness bound.",
        trigger="A bridge, indexer, or protocol uses one hardcoded confirmation depth across chains.",
        detection="Document the target chain's probabilistic/economic finality and use its finalized tag or deployment-specific threshold where available.",
        false_positive="The operation waits for the documented finality signal and handles reorg/replay recovery.",
        proof="Simulate a reorg or delayed finality event and verify that the state transition remains safe and recoverable.",
    )
    rewrite(
        registry,
        "EVM-CHAIN-024",
        title="Token return conventions are deployment-specific on Polygon",
        description="A token's return-data convention is a property of the deployed token contract, not a guaranteed consequence of its chain or symbol. Polygon deployments can include tokens and proxies whose transfer methods return data, omit it, or change through upgrades.",
        risk="A wrapper that assumes one return shape can treat a failed transfer as success or revert on a valid token implementation.",
        trigger="A Polygon integration branches on a token symbol or chain rather than handling the deployed call's return-data convention.",
        detection="Inspect the exact token implementation and use a wrapper with an explicit success and return-data policy.",
        false_positive="The supported token addresses are immutable and their return behavior is covered by integration tests.",
        proof="Call transfer and transferFrom against each supported deployment and verify state deltas for empty, boolean, and malformed return data.",
    )
    rewrite(
        registry,
        "EVM-CHAIN-030",
        title="Chainlink feed heartbeat and staleness are feed-specific",
        description="Chainlink heartbeat, deviation threshold, decimals, and sequencer behavior are properties of the selected feed and deployment. Do not copy a historical Arbitrum heartbeat or decimal value into another feed or assume it remains unchanged.",
        risk="A fixed threshold can accept stale prices or reject fresh ones, distorting collateral, liquidation, or settlement logic.",
        trigger="An integration hardcodes one Chainlink freshness interval or decimal scale for multiple chains or feeds.",
        detection="Read the selected feed's current metadata and compare `updatedAt`, decimals, heartbeat, and deviation policy with the use case.",
        false_positive="The feed address is allowlisted and its current parameters are validated at deployment and monitored for change.",
        proof="Exercise the price path at the feed's heartbeat, deviation, and stale boundaries and verify the protocol's fail-safe behavior.",
    )
    rewrite(
        registry,
        "EVM-CHAIN-031",
        title="Chainlink answer bounds are feed- and deployment-specific",
        description="Chainlink answer bounds and circuit-breaker configuration are feed-specific and may change with aggregator or proxy updates. Do not hardcode minAnswer/maxAnswer values from one Arbitrum feed; inspect the selected aggregator and define behavior for bounded or invalid answers.",
        risk="A stale bound can accept a clipped price, reject a valid extreme price, or make liquidation and solvency checks behave incorrectly.",
        trigger="The protocol uses a Chainlink answer without reading or validating the selected feed's current bounds and status.",
        detection="Resolve the proxy and aggregator, inspect bounds and answer status, and test negative, zero, clipped, and extreme values.",
        false_positive="The feed's current bounds are enforced by a trusted adapter with monitoring and an explicit fallback policy.",
        proof="Inject or observe boundary answers on a fork and show the resulting accounting, liquidation, or pause behavior.",
    )
    rewrite(
        registry,
        "EVM-CHAIN-034",
        title="The 2300-gas stipend is not portable across execution environments",
        description="Solidity `transfer()` and `send()` forward a fixed 2300-gas stipend. Whether that stipend is sufficient depends on the target chain's gas schedule and the recipient's execution path; use an explicit call pattern with checked success when portability is required.",
        risk="A recipient that needs more than the stipend can make withdrawals or callbacks fail, creating a denial of service or stuck funds.",
        trigger="A multichain path relies on `transfer()` or `send()` for recipients whose fallback or receive logic may vary.",
        detection="Trace the recipient code, gas schedule, and failure handling on every target chain.",
        false_positive="The recipient is code-free or intentionally stipend-compatible and failed sends are handled without corrupting state.",
        proof="Execute the transfer against a recipient that consumes the target stipend and verify success handling and accounting rollback.",
    )
    rewrite(
        registry,
        "EVM-CHAIN-036",
        title="Wrapped-native and token addresses are chain-specific",
        description="Wrapped-native assets and token representations use deployment-specific addresses. Do not copy an Ethereum or historical Polygon WETH address into a multichain configuration; resolve and validate the address for each chain and environment.",
        risk="A stale address can send funds to an unintended contract, an empty account, or a token with different decimals and trust assumptions.",
        trigger="A multichain deployment embeds one wrapped-native or token address in shared logic or configuration.",
        detection="Compare every configured address with the target chain's official deployment registry and verify code, decimals, and role configuration.",
        false_positive="Addresses are chain-keyed, immutable after review, and checked for code and expected interface before use.",
        proof="Run deposits, withdrawals, and balance reads against every configured chain and compare the resolved contract with the intended asset.",
    )
    rewrite(
        registry,
        "EVM-CHAIN-038",
        title="Same-name tokens can have different callback behavior",
        description="Token callback behavior is a property of the deployed token and its upgrade history, not its symbol or chain label. Historical incidents on Gnosis demonstrate why integrations must inspect the exact contract and protect accounting around arbitrary token callbacks.",
        risk="Assuming a same-name token is callback-free can expose reentrancy, unexpected control flow, or transfer-accounting errors.",
        trigger="A multichain integration grants trust based on a token symbol or origin chain without checking callback-capable behavior.",
        detection="Inspect bytecode, interfaces, hooks, proxy implementation, and transfer traces for every supported token address.",
        false_positive="The token set is immutable/allowlisted and all external control paths are protected by checks-effects-interactions or reentrancy guards.",
        proof="Use a callback-capable fixture or the deployed token trace to demonstrate whether transfer control can reenter before accounting finalizes.",
    )

    for canonical_id, (source_key, locator) in OFFICIAL_CLAIM_EVIDENCE.items():
        add_official(registry, canonical_id, source_key, locator)
    for canonical_id in ("EVM-ASM-025", "EVM-CHAIN-014"):
        by_id(registry, canonical_id)["verified_at"] = VERIFIED_AT
    for canonical_id in {
        "EVM-CHAIN-008",
        "EVM-CHAIN-010",
        "EVM-CHAIN-003",
        "EVM-CHAIN-005",
        "EVM-CHAIN-006",
        "EVM-CHAIN-009",
        "EVM-CHAIN-015",
        "EVM-CHAIN-019",
        "EVM-CHAIN-020",
        "EVM-CHAIN-022",
        "EVM-CHAIN-023",
        "EVM-CHAIN-024",
        "EVM-CHAIN-029",
        "EVM-CHAIN-030",
        "EVM-CHAIN-031",
        "EVM-CHAIN-034",
        "EVM-CHAIN-035",
        "EVM-CHAIN-036",
        "EVM-CHAIN-037",
        "EVM-CHAIN-038",
        "EVM-MATH-005",
        "EVM-GEN-034",
        "EVM-GEN-035",
        "EVM-GEN-077",
    }:
        check = by_id(registry, canonical_id)
        for alias in check.get("aliases", []):
            alias["title"] = f"Legacy alias for {canonical_id} (see canonical definition)"
    return registry


def evidence_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return item.get("kind"), item.get("url"), item.get("test"), item.get("locator")


def add_claim_evidence(claim: dict[str, Any], evidence: dict[str, Any]) -> None:
    if evidence_key(evidence) not in {evidence_key(item) for item in claim.get("evidence", [])}:
        claim.setdefault("evidence", []).append(evidence)


def supplemental_claim(
    canonical_id: str,
    source_key: str,
    required_terms: list[str],
    forbidden_terms: list[str],
) -> dict[str, Any]:
    source = OFFICIAL_SOURCES[source_key]
    return {
        "id": f"FRESH-{canonical_id}",
        "canonical_id": canonical_id,
        "supplemental": True,
        "source_url": source["url"],
        "required_terms": required_terms,
        "forbidden_terms": forbidden_terms,
        "evidence": [
            {"kind": "official", "url": source["url"], "locator": "current official protocol documentation"},
            {
                "kind": "text-regression",
                "test": "tests/test_checklists.py::ChecklistTests.test_knowledge_claims_and_forbidden_regressions",
            },
        ],
    }


def migrate_claims(claims_data: dict[str, Any]) -> dict[str, Any]:
    claims_data["schema_version"] = 3
    claims = claims_data["claims"]
    by_canonical = {claim["canonical_id"]: claim for claim in claims}
    text_test = "tests/test_checklists.py::ChecklistTests.test_knowledge_claims_and_forbidden_regressions"
    for claim in claims:
        for item in claim.get("evidence", []):
            if item.get("kind") == "executable" and item.get("test") == text_test:
                item["kind"] = "text-regression"
        canonical_id = claim["canonical_id"]
        if canonical_id in EXECUTABLE_EVIDENCE:
            test_name = EXECUTABLE_EVIDENCE[canonical_id]
            add_claim_evidence(
                claim,
                {
                    "kind": "executable",
                    "test": f"tests/semantics/test/Semantics.t.sol::SemanticsTest::{test_name}",
                },
            )
        if canonical_id in OFFICIAL_CLAIM_EVIDENCE:
            source_key, locator = OFFICIAL_CLAIM_EVIDENCE[canonical_id]
            source = OFFICIAL_SOURCES[source_key]
            claim["source_url"] = source["url"]
            add_claim_evidence(
                claim,
                {"kind": "official", "url": source["url"], "locator": locator},
            )

    supplements = [
        supplemental_claim(
            "EVM-CHAIN-010",
            "optimism-opcode-differences",
            ["current L1 origin block", "fresh entropy for every L2 block"],
            ["returns a fixed value", "It's NOT random"],
        ),
        supplemental_claim(
            "EVM-CHAIN-020",
            "bnb-chain-introduction",
            ["must not hardcode a historical block interval", "timestamp-based constraints"],
            ["BSC produces blocks every 3 seconds", "runs 4x faster"],
        ),
        supplemental_claim(
            "EVM-CHAIN-022",
            "polygon-pol",
            ["has migrated its native gas and staking token", "native POL"],
            ["MATIC is being replaced by POL"],
        ),
    ]
    for claim in supplements:
        existing = by_canonical.get(claim["canonical_id"])
        if existing is None:
            claims.append(claim)
        else:
            existing.update(claim)

    by_canonical = {claim["canonical_id"]: claim for claim in claims}
    by_canonical["EVM-CHAIN-008"]["required_terms"] = [
        "identifies the L2 block",
        "historically observed OP cadence",
    ]
    by_canonical["EVM-CHAIN-008"]["forbidden_terms"] = [
        "produced every 2 seconds",
        "will run 6x faster",
    ]
    by_canonical["EVM-CHAIN-037"]["required_terms"] = [
        "EraVM is source-compatible",
        "documented instruction",
    ]
    by_canonical["EVM-CHAIN-037"]["forbidden_terms"] = [
        "all behave differently",
        "fundamentally different opcode behavior",
    ]
    by_canonical["EVM-GEN-034"]["required_terms"] = ["Block cadence varies across chains and upgrades"]
    by_canonical["EVM-GEN-035"]["required_terms"] = ["Block production and timestamp progress are not uniform"]
    by_canonical["EVM-GEN-077"]["required_terms"] = ["Block number is not a timestamp"]
    return claims_data


def main() -> int:
    registry = migrate_registry(load(REGISTRY_PATH))
    claims = migrate_claims(load(CLAIMS_PATH))
    save(REGISTRY_PATH, registry)
    save(CLAIMS_PATH, claims)
    print(f"registry_schema={registry['schema_version']} claims_schema={claims['schema_version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
