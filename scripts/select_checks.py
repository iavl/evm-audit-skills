#!/usr/bin/env python3
"""Select canonical checks from a reconnaissance feature map.

Example:
    python3 scripts/select_checks.py --features uses-erc20,uses-oracle
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "canonical-checks.json"
FEATURES_PATH = ROOT / "data" / "features.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def selected_checks(registry: dict[str, Any], features: set[str], domain: str | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected: list[dict[str, Any]] = []
    filtered: list[dict[str, Any]] = []
    for check in registry.get("checks", []):
        if domain and domain not in check.get("domains", []):
            continue
        check_features = set(check.get("features", []))
        if check.get("always_screen") or check_features & features:
            selected.append(check)
        else:
            filtered.append(check)
    return selected, filtered


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--features", required=True, help="comma-separated reconnaissance feature IDs")
    parser.add_argument("--domain", help="limit selection to one domain skill")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    registry = load_json(root / "data" / "canonical-checks.json")
    feature_data = load_json(root / "data" / "features.json")
    vocabulary = set(feature_data.get("features", {}))
    requested = {value.strip() for value in args.features.split(",") if value.strip()}
    unknown = sorted(requested - vocabulary)
    if unknown:
        print(f"ERROR: unknown features: {', '.join(unknown)}", file=sys.stderr)
        return 1

    selected, filtered = selected_checks(registry, requested, args.domain)
    result = {
        "stage": "FAST_FILTER",
        "features": sorted(requested),
        "domain": args.domain,
        "selected_count": len(selected),
        "filtered_count": len(filtered),
        "selected": [
            {
                "canonical_id": check["canonical_id"],
                "title": check["title"],
                "domains": check.get("domains", []),
                "matched_features": sorted(set(check.get("features", [])) & requested),
            }
            for check in selected
        ],
        "filtered_out": [check["canonical_id"] for check in filtered],
    }
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"stage={result['stage']} selected={result['selected_count']} filtered={result['filtered_count']}")
        for entry in result["selected"]:
            matched = ",".join(entry["matched_features"]) or "always_screen"
            print(f"{entry['canonical_id']}\t{matched}\t{entry['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
