#!/usr/bin/env python3
"""Shared hashing and schema checks for immutable audit-run artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PLACEHOLDER_RE = re.compile(r"\b(?:UNKNOWN|UNRESOLVED|TODO|TBD)\b", re.IGNORECASE)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def check_body_hash(check: dict[str, Any]) -> str:
    return canonical_sha256(check)


def registry_sha256(registry: dict[str, Any]) -> str:
    return canonical_sha256(registry)


def routing_snapshot_id(manifest: dict[str, Any]) -> str:
    payload = {key: value for key, value in manifest.items() if key != "routing_snapshot_id"}
    return canonical_sha256(payload)


def bind_routing_snapshot(manifest: dict[str, Any]) -> dict[str, Any]:
    result = dict(manifest)
    result["routing_snapshot_id"] = routing_snapshot_id(result)
    return result


def validate_routing_snapshot(manifest: dict[str, Any]) -> str:
    snapshot = manifest.get("routing_snapshot_id")
    if not isinstance(snapshot, str) or not SHA256_RE.fullmatch(snapshot):
        raise ValueError("routing manifest has no valid routing_snapshot_id")
    expected = routing_snapshot_id(manifest)
    if snapshot != expected:
        raise ValueError("routing manifest snapshot hash is stale or invalid")
    return snapshot


def validate_schema(root: Path, schema_name: str, value: Any) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as error:  # pragma: no cover - dependency failure is operational
        raise ValueError("jsonschema is required; install requirements-runtime.txt") from error
    schema = load_json(root / "schemas" / schema_name)
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda item: list(item.path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise ValueError(f"{schema_name}:{location}: {error.message}")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{number} must contain an object")
        records.append(value)
    return records


def has_placeholder(*values: Any) -> bool:
    return any(PLACEHOLDER_RE.search(str(value or "")) for value in values)


def artifact_identity(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return the hashes every post-routing artifact must carry."""
    audit = manifest.get("audit_context", {})
    return {
        "routing_snapshot_id": manifest.get("routing_snapshot_id"),
        "registry_sha256": audit.get("registry_sha256"),
        "source_digest": audit.get("source_digest"),
        "compilation_input_digest": audit.get("compilation_input_digest"),
    }


def validate_artifact_identity(value: dict[str, Any], manifest: dict[str, Any]) -> None:
    expected = artifact_identity(manifest)
    for key, wanted in expected.items():
        if value.get(key) != wanted:
            raise ValueError(f"artifact has incompatible {key}")
