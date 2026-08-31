#!/usr/bin/env python3
"""Maintain routing-scoped append-only review JSONL and Markdown views."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

try:
    from audit_artifacts import (
        absence_evidence_errors,
        check_body_hash,
        has_placeholder,
        load_json,
        validate_domain_resolution,
        validate_artifact_identity,
        validate_schema,
        validate_target_snapshot,
    )
    from render_runtime import selected_entries, validate_manifest, validate_screen_results
except ImportError:  # pragma: no cover
    from scripts.audit_artifacts import (
        absence_evidence_errors,
        check_body_hash,
        has_placeholder,
        load_json,
        validate_domain_resolution,
        validate_artifact_identity,
        validate_schema,
        validate_target_snapshot,
    )
    from scripts.render_runtime import selected_entries, validate_manifest, validate_screen_results


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 4
TERMINAL = {"NOT_APPLICABLE", "REVIEWED_SAFE", "SUSPICIOUS", "CONFIRMED"}
REVIEW_STAGES = {"DEEP_REVIEW", "PROOF"}
IDENTITY_KEYS = ("routing_snapshot_id", "registry_sha256", "source_digest", "compilation_input_digest")
def read_json(path: Path) -> dict[str, Any]:
    return load_json(path)


def checkpoint(manifest: dict[str, Any]) -> dict[str, Any]:
    audit = manifest["audit_context"]
    return {
        "record_type": "checkpoint",
        "schema_version": SCHEMA_VERSION,
        "routing_snapshot_id": manifest["routing_snapshot_id"],
        "registry_sha256": audit["registry_sha256"],
        "source_digest": audit["source_digest"],
        "compilation_input_digest": audit["compilation_input_digest"],
    }


def load(path: Path) -> list[dict[str, Any]]:
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


def _manifest_routes(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        entry["canonical_id"]: entry
        for bucket in ("selected", "deferred", "filtered")
        for entry in manifest.get(bucket, [])
    }


def _nonempty(record: dict[str, Any], fields: Iterable[str]) -> list[str]:
    return [field for field in fields if not isinstance(record.get(field), str) or not record[field].strip()]


def validate_record(record: dict[str, Any], manifest: dict[str, Any], registry: dict[str, Any], expected_ids: set[str] | None = None) -> list[str]:
    errors: list[str] = []
    try:
        validate_schema(ROOT, "review-record.schema.json", record)
    except ValueError as error:
        errors.append(str(error))
    if record.get("record_type") != "review":
        return errors or ["review record must have record_type=review"]
    canonical_id = record.get("canonical_id")
    routes = _manifest_routes(manifest)
    route = routes.get(canonical_id)
    if route is None:
        errors.append(f"unknown routed canonical ID: {canonical_id}")
    elif route.get("route_status") != "SELECTED" and (expected_ids is None or canonical_id not in expected_ids):
        errors.append(f"review record is not selected: {canonical_id}")
    elif expected_ids is not None and canonical_id not in expected_ids:
        errors.append(f"review record is not a Screen candidate: {canonical_id}")
    if route and record.get("owner_domain") != route.get("owner_domain"):
        errors.append(f"{canonical_id}: owner_domain does not match routing manifest")
    if record.get("routing_snapshot_id") != manifest.get("routing_snapshot_id"):
        errors.append(f"{canonical_id}: routing_snapshot_id does not match manifest")
    identity = checkpoint(manifest)
    for key in ("registry_sha256", "source_digest", "compilation_input_digest"):
        if record.get(key) != identity.get(key):
            errors.append(f"{canonical_id}: {key} does not match manifest")
    checks = {check["canonical_id"]: check for check in registry.get("checks", [])}
    check = checks.get(canonical_id)
    if check is None:
        errors.append(f"unknown canonical ID in registry: {canonical_id}")
    elif record.get("check_body_hash") != check_body_hash(check):
        errors.append(f"{canonical_id}: check_body_hash does not match registry")

    if record.get("review_stage") not in REVIEW_STAGES:
        errors.append(f"{canonical_id}: review_stage must be DEEP_REVIEW or PROOF")
    status = record.get("status")
    if status not in TERMINAL:
        errors.append(f"{canonical_id}: status is not terminal")
    missing = _nonempty(record, ("applicability", "code_path", "preconditions", "exploitability", "impact", "proof"))
    if missing:
        errors.append(f"{canonical_id}: missing review fields {missing}")
    evidence = record.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append(f"{canonical_id}: evidence must be a non-empty typed list")
    if status == "REVIEWED_SAFE" and _nonempty(record, ("preserved_invariant",)):
        errors.append(f"{canonical_id}: REVIEWED_SAFE requires preserved_invariant")
    if status == "REVIEWED_SAFE" and has_placeholder(*(record.get(field) for field in ("applicability", "code_path", "preconditions", "exploitability", "impact", "proof", "preserved_invariant"))):
        errors.append(f"{canonical_id}: REVIEWED_SAFE cannot contain UNKNOWN/UNRESOLVED/TODO fields")
    if status == "SUSPICIOUS":
        if _nonempty(record, ("unresolved_reason",)):
            errors.append(f"{canonical_id}: SUSPICIOUS requires unresolved_reason")
    if status == "NOT_APPLICABLE" and not str(record.get("applicability", "")).startswith("NOT_APPLICABLE"):
        errors.append(f"{canonical_id}: NOT_APPLICABLE must explain non-applicability")
    if status == "NOT_APPLICABLE" and isinstance(evidence, list):
        errors.extend(absence_evidence_errors(evidence, record.get("scope_complete"), str(canonical_id)))
    if status == "CONFIRMED" and has_placeholder(*(record.get(field) for field in ("applicability", "code_path", "preconditions", "exploitability", "impact", "proof"))):
        errors.append(f"{canonical_id}: CONFIRMED cannot contain UNKNOWN/UNRESOLVED/TODO fields")
    if status == "CONFIRMED":
        if record.get("review_stage") != "PROOF":
            errors.append(f"{canonical_id}: CONFIRMED requires review_stage=PROOF")
        if not isinstance(evidence, list) or not any(item.get("kind") in {"test", "trace", "invariant", "calculation"} for item in evidence if isinstance(item, dict)):
            errors.append(f"{canonical_id}: CONFIRMED requires strong proof evidence")
    return errors


def validate_records(records: list[dict[str, Any]], manifest: dict[str, Any], registry: dict[str, Any], expected_ids: set[str] | None = None) -> list[str]:
    errors: list[str] = []
    if not records:
        return ["ledger is empty"]
    if records[0].get("record_type") != "checkpoint":
        errors.append("first JSONL record must be a checkpoint")
    else:
        try:
            validate_schema(ROOT, "review-record.schema.json", records[0])
        except ValueError as error:
            errors.append(str(error))
        expected = checkpoint(manifest)
        for key in IDENTITY_KEYS:
            if records[0].get(key) != expected.get(key):
                errors.append(f"checkpoint {key} does not match manifest")
    seen: set[str] = set()
    for record in records[1:]:
        canonical_id = record.get("canonical_id")
        if record.get("record_type") == "checkpoint":
            errors.append("checkpoint is only allowed as the first JSONL record")
            continue
        if canonical_id in seen:
            errors.append(f"duplicate review record: {canonical_id}")
        seen.add(canonical_id)
        errors.extend(validate_record(record, manifest, registry, expected_ids))
    return errors


def collect_review_records(
    paths: list[Path],
    manifest: dict[str, Any],
    registry: dict[str, Any],
    expected_ids: set[str],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Validate and combine ledgers without allowing cross-ledger overwrites."""
    validate_target_snapshot(manifest)
    records: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for path in paths:
        if not path.exists():
            continue
        try:
            values = load(path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"{path}: {error}")
            continue
        errors.extend(f"{path}: {error}" for error in validate_records(values, manifest, registry, expected_ids))
        for record in values[1:]:
            if record.get("record_type") != "review":
                continue
            canonical_id = record.get("canonical_id")
            if canonical_id in records:
                errors.append(f"duplicate Deep record across ledgers: {canonical_id}")
            else:
                records[canonical_id] = record
    return records, errors


def append(path: Path, manifest: dict[str, Any], record: dict[str, Any], registry: dict[str, Any] | None = None, expected_ids: set[str] | None = None) -> None:
    validate_target_snapshot(manifest)
    if record.get("record_type") != "review":
        raise ValueError("append requires record_type=review")
    if record.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"append requires schema_version={SCHEMA_VERSION}")
    identity = checkpoint(manifest)
    for key in IDENTITY_KEYS:
        if key in record and record[key] != identity[key]:
            raise ValueError(f"append record {key} does not match manifest")
    record = {**record, **{key: identity[key] for key in IDENTITY_KEYS}}
    registry_value = registry or read_json(ROOT / "data/canonical-checks.json")
    errors = validate_record(record, manifest, registry_value, expected_ids)
    if errors:
        raise ValueError("; ".join(errors))
    records = load(path)
    if records:
        existing_errors = validate_records(records, manifest, registry_value, expected_ids)
        if existing_errors:
            raise ValueError(f"invalid existing ledger: {'; '.join(existing_errors)}")
        if any(item.get("canonical_id") == record.get("canonical_id") for item in records[1:]):
            raise ValueError(f"duplicate review record: {record['canonical_id']}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as output:
        if not records:
            output.write(json.dumps(checkpoint(manifest), ensure_ascii=False, sort_keys=True) + "\n")
        output.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def pending(manifest: dict[str, Any], screen: dict[str, Any], ledgers: list[Path], registry: dict[str, Any], domain_resolution: dict[str, Any] | None = None) -> dict[str, list[str]]:
    validate_target_snapshot(manifest)
    validate_schema(ROOT, "screen-results.schema.json", screen)
    validate_artifact_identity(screen, manifest)
    selected = {entry["canonical_id"] for entry in selected_entries(manifest, domain_resolution=domain_resolution)}
    screen_records = screen.get("results", [])
    screened = {entry["canonical_id"] for entry in screen_records}
    if len(screened) != len(screen_records) or not screened <= selected:
        raise ValueError("partial screen results contain duplicate or non-selected IDs")
    for entry in screen_records:
        if entry["result"] == "NOT_APPLICABLE_CONFIRMED":
            errors = absence_evidence_errors(
                entry["evidence"], entry.get("scope_complete"), entry["canonical_id"]
            )
            if errors:
                raise ValueError("; ".join(errors))
    candidates = {entry["canonical_id"] for entry in screen_records if entry["result"] == "CANDIDATE"}
    records, errors = collect_review_records(ledgers, manifest, registry, candidates)
    if errors:
        raise ValueError("; ".join(errors))
    safe_done = {canonical_id for canonical_id, record in records.items() if record["status"] in {"NOT_APPLICABLE", "REVIEWED_SAFE", "CONFIRMED"}}
    return {
        "screen_pending": sorted(selected - screened),
        "deep_pending": sorted(candidates - set(records)),
        "suspicious": sorted(canonical_id for canonical_id, record in records.items() if record["status"] == "SUSPICIOUS"),
        "complete": sorted((selected - candidates) | safe_done),
    }


def render_markdown(records: list[dict[str, Any]], manifest: dict[str, Any], registry: dict[str, Any] | None = None) -> str:
    if not records:
        return ""
    checkpoint_record = records[0]
    lines = [
        "<!-- GENERATED REVIEW VIEW: JSONL is authoritative; do not edit by hand. -->",
        f"- **Routing snapshot:** `{checkpoint_record.get('routing_snapshot_id')}`",
        f"- **Registry:** `{checkpoint_record.get('registry_sha256')}`",
        f"- **Source digest:** `{checkpoint_record.get('source_digest')}`",
        f"- **Compilation input digest:** `{checkpoint_record.get('compilation_input_digest')}`",
        "",
    ]
    checks = {check["canonical_id"]: check for check in (registry or read_json(ROOT / "data/canonical-checks.json")).get("checks", [])}
    for record in records[1:]:
        canonical_id = record.get("canonical_id", "unknown")
        title = checks.get(canonical_id, {}).get("title", "")
        lines.extend([f"### {canonical_id} — {title}"])
        for key, label in (
            ("review_stage", "Review stage"), ("owner_domain", "Owner Domain"), ("check_body_hash", "Check body hash"),
            ("status", "Status"), ("applicability", "Applicability"), ("code_path", "Code path"),
            ("preconditions", "Preconditions"), ("exploitability", "Exploitability"), ("impact", "Impact"),
            ("proof", "PoC / Invariant violation"), ("preserved_invariant", "Preserved invariant"),
            ("unresolved_reason", "Unresolved reason"),
        ):
            if key in record:
                lines.append(f"- **{label}:** {record[key]}")
        if "evidence" in record:
            lines.append("- **Evidence:** " + "; ".join(f"{item['kind']}:{item['location']} — {item['reason']}" for item in record["evidence"]))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_ledger(path: Path, manifest: dict[str, Any], records: Iterable[dict[str, Any]], registry: dict[str, Any] | None = None, expected_ids: set[str] | None = None) -> None:
    validate_target_snapshot(manifest)
    if path.exists():
        raise ValueError(f"refusing to overwrite existing ledger: {path}")
    values = [checkpoint(manifest), *records]
    errors = validate_records(values, manifest, registry or read_json(ROOT / "data/canonical-checks.json"), expected_ids)
    if errors:
        raise ValueError("; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n" for value in values), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--screen-results", type=Path, required=True)
    parser.add_argument("--domain-resolution", type=Path)
    parser.add_argument("--registry", type=Path, default=ROOT / "data/canonical-checks.json")
    parser.add_argument("--ledger", type=Path, action="append", default=[])
    parser.add_argument("--pending", action="store_true")
    parser.add_argument("--append-record", type=Path)
    parser.add_argument("--render-markdown", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest, registry = read_json(args.manifest), read_json(args.registry)
        validate_manifest(ROOT, manifest, registry)
        validate_target_snapshot(manifest)
        screen = read_json(args.screen_results)
        domain_resolution = read_json(args.domain_resolution) if args.domain_resolution else None
        if domain_resolution is not None:
            validate_domain_resolution(ROOT, manifest, domain_resolution)
        if args.pending:
            print(json.dumps(pending(manifest, screen, args.ledger, registry, domain_resolution), ensure_ascii=False, sort_keys=True))
            return 0
        candidates = validate_screen_results(ROOT, manifest, screen, domain_resolution)
        if args.append_record:
            if len(args.ledger) != 1:
                raise ValueError("--append-record requires exactly one --ledger output")
            append(args.ledger[0], manifest, read_json(args.append_record), registry, candidates)
        if args.render_markdown:
            records, errors = collect_review_records(args.ledger, manifest, registry, candidates)
            if errors:
                raise ValueError("; ".join(errors))
            values = [checkpoint(manifest), *records.values()]
            args.render_markdown.parent.mkdir(parents=True, exist_ok=True)
            args.render_markdown.write_text(render_markdown(values, manifest, registry), encoding="utf-8")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
