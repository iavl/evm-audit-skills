#!/usr/bin/env python3
"""Append-only JSONL review checkpoints with safe resume and merge."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


TERMINAL = {"NOT_APPLICABLE", "REVIEWED_SAFE", "SUSPICIOUS", "CONFIRMED"}


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def check_body_hash(check: dict[str, Any]) -> str:
    body = json.dumps(check, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(body).hexdigest()


def checkpoint(context: dict[str, Any]) -> dict[str, Any]:
    return {"record_type": "checkpoint", "schema_version": 1, **{key: context.get(key) for key in ("registry_sha256", "source_digest", "compilation_digest")}}


def load(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{number} must be an object")
        records.append(value)
    return records


def resumable(path: Path, context: dict[str, Any], registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = load(path)
    if not records or any(records[0].get(key) != context.get(key) for key in ("source_digest", "compilation_digest")):
        return {}
    hashes = {check["canonical_id"]: check_body_hash(check) for check in registry["checks"]}
    result: dict[str, dict[str, Any]] = {}
    for record in records[1:]:
        canonical_id = record.get("canonical_id")
        if record.get("record_type") == "review" and record.get("status") in TERMINAL and record.get("check_body_hash") == hashes.get(canonical_id):
            result[canonical_id] = record
    return result


def append(path: Path, context: dict[str, Any], record: dict[str, Any]) -> None:
    if record.get("canonical_id") is None or record.get("status") not in TERMINAL or not record.get("check_body_hash"):
        raise ValueError("review needs canonical_id, terminal status, and check_body_hash")
    records = load(path)
    if records and records[0] != checkpoint(context):
        raise ValueError("checkpoint context changed; start a new ledger")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as output:
        if not records:
            output.write(json.dumps(checkpoint(context), ensure_ascii=False, sort_keys=True) + "\n")
        output.write(json.dumps({"record_type": "review", **record}, ensure_ascii=False, sort_keys=True) + "\n")


def merge(paths: list[Path], context: dict[str, Any], registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Merge independently written terminal records; conflicting IDs stay unsafe."""
    merged: dict[str, dict[str, Any]] = {}
    for path in paths:
        for canonical_id, record in resumable(path, context, registry).items():
            previous = merged.get(canonical_id)
            if previous and previous != record:
                raise ValueError(f"conflicting resumed review for {canonical_id}")
            merged[canonical_id] = record
    return merged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--pending", action="store_true")
    parser.add_argument("--append-record", type=Path)
    parser.add_argument("--merge", type=Path, nargs="+", help="merge compatible agent JSONL ledgers")
    args = parser.parse_args(argv)
    try:
        context, registry = read_json(args.context), read_json(args.registry)
        if args.append_record:
            append(args.ledger, context, read_json(args.append_record))
        if args.pending:
            done = resumable(args.ledger, context, registry)
            print(json.dumps({"resumable": sorted(done), "pending": sorted(check["canonical_id"] for check in registry["checks"] if check["canonical_id"] not in done)}))
        if args.merge:
            print(json.dumps({"merged": sorted(merge(args.merge, context, registry))}))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
