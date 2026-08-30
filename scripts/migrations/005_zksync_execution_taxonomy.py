#!/usr/bin/env python3
"""Classify reviewed ZKsync checks by native EraVM versus EVM Interpreter."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "data" / "canonical-checks.json"
ENVIRONMENTS = {
    "EVM-CHAIN-011": ["eravm-native", "zksync-evm-interpreter"],  # native AA is chain-wide
    "EVM-CHAIN-012": ["eravm-native"],  # non-EVM account code-size behavior
    "EVM-CHAIN-013": ["eravm-native", "zksync-evm-interpreter"],  # deliberately differential
    "EVM-CHAIN-014": ["eravm-native", "zksync-evm-interpreter"],  # target/fork-specific opcode assumptions
    "EVM-CHAIN-015": ["eravm-native", "zksync-evm-interpreter"],  # chain system delivery paths
    "EVM-CHAIN-037": ["eravm-native"],  # EraVM instruction/bytecode compatibility
}


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    for check in data["checks"]:
        if check["canonical_id"] in ENVIRONMENTS:
            check["applicability"]["execution_environments"] = ENVIRONMENTS[check["canonical_id"]]
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
