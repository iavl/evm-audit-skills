#!/usr/bin/env python3
"""Inspect a source tree before opening it to audit tooling."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evm_audit_runtime.repository_trust import inspect_repository, sanitize_snapshot
from evm_audit_runtime.versions import REPOSITORY_TRUST_VERSION


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--source-trust", type=str.upper, choices=("TRUSTED", "UNTRUSTED", "UNKNOWN"), default="UNKNOWN")
    parser.add_argument("--sanitize-to", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        source = args.source.resolve()
        result = inspect_repository(source, args.source_trust)
        result = {
            "artifact_type": "repository-trust",
            "schema_version": REPOSITORY_TRUST_VERSION,
            **result,
            "original_root": str(source),
            "effective_root": str(source),
            "sanitized": False,
            "snapshot_sha256": None,
        }
        if not result["direct_agent_open_allowed"]:
            if args.sanitize_to is None:
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 1
            snapshot = sanitize_snapshot(source, args.sanitize_to)
            result.update(
                effective_root=snapshot["snapshot_root"],
                sanitized=True,
                snapshot_sha256=snapshot["snapshot_sha256"],
            )
        if args.output:
            _write_json(args.output, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
