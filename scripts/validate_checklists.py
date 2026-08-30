#!/usr/bin/env python3
"""Validate EVM audit checklist structure and report semantic dedup candidates.

The validator deliberately does not decide semantic equivalence. It fails only
on deterministic repository invariants and reports cross-file similarity for
human review.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from generate_checklists import DOMAIN_CODES, check_outputs, load_registry, normalize_registry
    from select_checks import (
        FEATURE_STATES,
        PREDICATE_KEYS,
        check_predicate,
        evaluate_check,
        normalize_feature_map,
        registry_sha256,
        vocabulary as feature_vocabulary,
    )
except ImportError:  # pragma: no cover - supports importing this file from another cwd
    from scripts.generate_checklists import DOMAIN_CODES, check_outputs, load_registry, normalize_registry
    from scripts.select_checks import (
        FEATURE_STATES,
        PREDICATE_KEYS,
        check_predicate,
        evaluate_check,
        normalize_feature_map,
        registry_sha256,
        vocabulary as feature_vocabulary,
    )


ITEM_RE = re.compile(r"^- \[ \] \*\*(.*?)\*\*")
SOURCE_ID_RE = re.compile(r"\b(?:SAS-AV-\d{3}|DROZER-[A-Z0-9-]+|AUDITMOS-[A-Z0-9-]+)\b")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
MASTER_ROW_RE = re.compile(
    r"^\|\s*\d+\s*\|\s*\*\*(evm-audit-[^*]+)\*\*.*\|\s*(\d+)\s*\|\s*$"
)
README_CANONICAL_RE = re.compile(r"(\d[\d,]*)\s+canonical checks")
README_RUNTIME_RE = re.compile(r"(\d[\d,]*)\s+generated runtime entries")
MASTER_CANONICAL_RE = re.compile(r"Total:\s+(\d[\d,]*)\s+canonical checks")
MASTER_RUNTIME_RE = re.compile(r"and\s+(\d[\d,]*)\s+generated runtime entries")
REVIEW_ROW_RE = re.compile(
    r"^\|\s*([A-Z]+-\d+)\s*\|.*\|\s*(MERGED|MERGE|KEEP_DISTINCT|PENDING_USER_CONFIRMATION)\s*\|\s*$"
)
LEDGER_HEADING_RE = re.compile(r"^###\s+([^\s]+)\s+—\s+(.+?)\s*$")
LEDGER_FIELD_RE = re.compile(r"^-\s+\*\*(.+?)\*\*:\s*(.*)$")
LEDGER_STATUSES = {"NOT_APPLICABLE", "REVIEWED_SAFE", "SUSPICIOUS", "CONFIRMED"}
LEDGER_STAGES = {"FAST_FILTER", "DEEP_REVIEW", "PROOF"}
CANONICAL_ID_RE = re.compile(r"\[([A-Z0-9]+(?:-[A-Z0-9]+)+-\d{3})\]")
URL_VALUE_RE = re.compile(r"^https?://[^\s]+$")
CHECK_TYPES = {"normative", "semantic", "exploit-pattern", "heuristic"}
CONFIDENCES = {"high", "medium", "contextual"}
VERIFICATION_STATUSES = {"verified", "qualified"}
ROUTING_MANIFEST_VERSION = 2
CLAIMS_SCHEMA_VERSION = 3
CLAIM_EVIDENCE_KINDS = {"official", "executable", "text-regression"}
FRESHNESS_CLASSES = {"static", "versioned", "time-sensitive"}
REGISTRY_REQUIRED_FIELDS = {
    "canonical_id",
    "domains",
    "primary_domain",
    "section",
    "title",
    "description",
    "trigger",
    "risk",
    "detection",
    "false_positive_gates",
    "proof",
    "type",
    "confidence",
    "features",
    "predicate",
    "predicate_source",
    "provenance",
    "related",
    "aliases",
    "verification",
    "freshness",
    "verified_at",
}

STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "if",
    "when",
    "then",
    "from",
    "to",
    "of",
    "for",
    "with",
    "without",
    "via",
    "is",
    "are",
    "be",
    "can",
    "may",
    "must",
    "should",
    "use",
    "used",
    "using",
    "not",
    "no",
    "on",
    "in",
    "into",
    "as",
    "by",
    "across",
    "all",
    "any",
    "every",
    "this",
    "that",
    "its",
    "their",
    "one",
    "same",
    "different",
    "only",
    "more",
    "less",
    "after",
    "before",
    "during",
    "than",
}


@dataclass(frozen=True)
class Item:
    path: Path
    line: int
    section: str
    title: str
    raw: str

    @property
    def ref(self) -> str:
        return f"{self.path}:{self.line}"


def normalize_title(title: str) -> str:
    title = SOURCE_ID_RE.sub(" ", title.lower())
    title = re.sub(r"\[[A-Z0-9]+(?:-[A-Z0-9]+)+-\d{3}\]", " ", title)
    title = re.sub(r"[`*_]", "", title)
    title = re.sub(r"[^a-z0-9]+", " ", title)
    return " ".join(title.split())


def title_tokens(title: str) -> set[str]:
    return {
        token
        for token in normalize_title(title).split()
        if len(token) > 2 and token not in STOPWORDS
    }


def parse_checklist(path: Path) -> tuple[list[Item], list[str], dict[str, int]]:
    items: list[Item] = []
    errors: list[str] = []
    source_ids: dict[str, int] = {}
    section = ""
    lines = path.read_text(encoding="utf-8").splitlines()

    for line_number, line in enumerate(lines, 1):
        if line.startswith("## "):
            section = line[3:].strip()

        if line.startswith("- [ ]"):
            match = ITEM_RE.match(line)
            if not match:
                errors.append(f"{path}:{line_number}: malformed checklist item")
                continue

            title = match.group(1).strip()
            item = Item(path, line_number, section, title, line)
            items.append(item)
            for source_id in SOURCE_ID_RE.findall(title):
                source_ids[source_id] = source_ids.get(source_id, 0) + 1

    return items, errors, source_ids


def validate_registry(root: Path) -> list[str]:
    errors: list[str] = []
    path = root / "data" / "canonical-checks.json"
    feature_path = root / "data" / "features.json"
    feature_schema_path = root / "data" / "feature-map.schema.json"
    if not feature_schema_path.exists():
        errors.append(f"missing feature-map schema: {feature_schema_path}")
    else:
        try:
            feature_schema = json.loads(feature_schema_path.read_text(encoding="utf-8"))
            if not isinstance(feature_schema, dict) or feature_schema.get("properties", {}).get("schema_version", {}).get("const") != 1:
                errors.append(f"{feature_schema_path}: invalid feature-map schema")
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{feature_schema_path}: cannot parse JSON: {error}")
    if not path.exists():
        return [f"missing canonical registry: {path}"]
    if not feature_path.exists():
        errors.append(f"missing feature registry: {feature_path}")
        feature_names: set[str] = set()
    else:
        try:
            feature_data = json.loads(feature_path.read_text(encoding="utf-8"))
            if feature_data.get("schema_version") != 1 or not isinstance(feature_data.get("features"), dict):
                errors.append(f"{feature_path}: invalid feature registry schema")
            try:
                feature_names, _ = feature_vocabulary(feature_data)
            except ValueError as error:
                errors.append(f"{feature_path}: invalid feature registry: {error}")
                feature_names = set(feature_data.get("features", {}))
            domain_features = sorted(name for name in feature_names if name.startswith("evm-audit-"))
            if domain_features:
                errors.append(f"{feature_path}: domain names must not be routable features: {domain_features}")
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{feature_path}: cannot parse JSON: {error}")
            feature_names = set()

    try:
        registry = normalize_registry(load_registry(path))
    except (OSError, json.JSONDecodeError) as error:
        return errors + [f"{path}: cannot parse JSON: {error}"]
    if registry.get("schema_version") != 3:
        errors.append(f"{path}: unsupported schema_version {registry.get('schema_version')!r}")
    source_catalog = registry.get("source_catalog")
    if not isinstance(source_catalog, dict) or not source_catalog:
        errors.append(f"{path}: source_catalog must be a non-empty object")
        source_catalog_keys: set[str] = set()
    else:
        source_catalog_keys = set(source_catalog)
        for source_key, source in source_catalog.items():
            if not isinstance(source, dict) or not source.get("label") or not source.get("url"):
                errors.append(f"{path}: source_catalog entry {source_key!r} needs label and URL")
                continue
            if not URL_VALUE_RE.match(str(source["url"])):
                errors.append(f"{path}: source_catalog entry {source_key!r} has invalid URL {source['url']!r}")
    checks = registry.get("checks")
    if not isinstance(checks, list) or not checks:
        return errors + [f"{path}: checks must be a non-empty list"]

    dedup = registry.get("dedup_decisions")
    if not isinstance(dedup, dict) or not isinstance(dedup.get("reviewed_candidates"), list):
        errors.append(f"{path}: dedup_decisions.reviewed_candidates must be a list")
    else:
        decision_ids: set[str] = set()
        for decision in dedup["reviewed_candidates"]:
            if not isinstance(decision, dict) or decision.get("decision") not in {"MERGED", "KEEP_DISTINCT"} or not decision.get("canonical_id") or not decision.get("reason"):
                errors.append(f"{path}: malformed dedup decision {decision!r}")
                continue
            if decision["canonical_id"] in decision_ids:
                errors.append(f"{path}: duplicate dedup decision {decision['canonical_id']}")
            decision_ids.add(decision["canonical_id"])

    ids: set[str] = set()
    alias_keys: set[tuple[str, int]] = set()
    source_ids: dict[str, str] = {}
    valid_domains = set(DOMAIN_CODES)
    for index, check in enumerate(checks, 1):
        prefix = f"{path}:checks[{index}]"
        if not isinstance(check, dict):
            errors.append(f"{prefix}: entry must be an object")
            continue
        missing = sorted(REGISTRY_REQUIRED_FIELDS - set(check))
        if missing:
            errors.append(f"{prefix}: missing fields {missing}")
        canonical_id = check.get("canonical_id")
        if not isinstance(canonical_id, str) or not CANONICAL_ID_RE.fullmatch(f"[{canonical_id}]"):
            errors.append(f"{prefix}: invalid canonical_id {canonical_id!r}")
        elif canonical_id in ids:
            errors.append(f"{prefix}: duplicate canonical_id {canonical_id}")
        else:
            ids.add(canonical_id)

        domains = check.get("domains")
        if not isinstance(domains, list) or not domains or any(domain not in valid_domains for domain in domains):
            errors.append(f"{prefix}: invalid domains {domains!r}")
        if check.get("primary_domain") not in (domains or []):
            errors.append(f"{prefix}: primary_domain is not listed in domains")
        for field in ("section", "title", "description", "risk", "type", "confidence"):
            if not isinstance(check.get(field), str) or not check[field].strip():
                errors.append(f"{prefix}: {field} must be a non-empty string")
        if check.get("type") not in CHECK_TYPES:
            errors.append(f"{prefix}: unknown type {check.get('type')!r}")
        if check.get("confidence") not in CONFIDENCES:
            errors.append(f"{prefix}: unknown confidence {check.get('confidence')!r}")
        if check.get("type") == "heuristic" and check.get("confidence") != "contextual":
            errors.append(f"{prefix}: heuristic checks must have contextual confidence")
        if check.get("type") in {"normative", "semantic"} and check.get("confidence") != "high":
            errors.append(f"{prefix}: normative/semantic checks must have high confidence")
        for field in ("trigger", "detection", "false_positive_gates", "proof"):
            value = check.get(field)
            if not isinstance(value, list) or not value or any(not isinstance(part, str) or not part.strip() for part in value):
                errors.append(f"{prefix}: {field} must be a non-empty string list")
        predicate = check.get("predicate")
        if not isinstance(predicate, dict):
            errors.append(f"{prefix}: predicate must be an object")
        else:
            for key in PREDICATE_KEYS:
                values = predicate.get(key)
                if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
                    errors.append(f"{prefix}: predicate.{key} must be a string list")
            try:
                check_predicate(check, feature_names)
            except ValueError as error:
                errors.append(f"{prefix}: {error}")
            if not any(predicate.get(key, []) for key in PREDICATE_KEYS) and check.get("always_screen") is not True:
                errors.append(f"{prefix}: empty predicate requires always_screen=true")
            if check.get("always_screen") is not None and not isinstance(check.get("always_screen"), bool):
                errors.append(f"{prefix}: always_screen must be boolean when present")
            if check.get("always_screen") is True and any(predicate.get(key, []) for key in PREDICATE_KEYS):
                errors.append(f"{prefix}: always_screen=true cannot be combined with a non-empty predicate")
        if check.get("predicate_source") not in {"inferred", "curated"}:
            errors.append(f"{prefix}: predicate_source must be inferred or curated")
        features = check.get("features")
        if not isinstance(features, list) or any(not isinstance(feature, str) or not feature.strip() for feature in features):
            errors.append(f"{prefix}: features must be a string list")
        else:
            if any(feature.startswith("evm-audit-") for feature in features):
                errors.append(f"{prefix}: domain names must not be routable features")
            if isinstance(predicate, dict):
                expected_features = sorted({feature for key in PREDICATE_KEYS for feature in predicate.get(key, [])})
                if features != expected_features:
                    errors.append(f"{prefix}: features must equal the predicate feature union")

        provenance = check.get("provenance")
        if not isinstance(provenance, list) or not provenance:
            errors.append(f"{prefix}: provenance must be a non-empty list")
        else:
            for p_index, entry in enumerate(provenance, 1):
                if not isinstance(entry, dict) or not entry.get("label") or not entry.get("locator"):
                    errors.append(f"{prefix}.provenance[{p_index}]: label and locator are required")
                    continue
                if entry.get("source_key") not in source_catalog_keys:
                    errors.append(f"{prefix}.provenance[{p_index}]: unknown source tag {entry.get('source_key')!r}")
                url = entry.get("url")
                if url is not None and (not isinstance(url, str) or not URL_VALUE_RE.match(url)):
                    errors.append(f"{prefix}.provenance[{p_index}]: invalid URL {url!r}")
                if entry.get("kind") == "official" and not url:
                    errors.append(f"{prefix}.provenance[{p_index}]: official provenance requires a URL")
                if entry.get("kind") not in {"official", "secondary", "legacy"}:
                    errors.append(f"{prefix}.provenance[{p_index}]: unknown provenance kind {entry.get('kind')!r}")
                for source_id in SOURCE_ID_RE.findall(str(entry.get("label"))):
                    previous = source_ids.get(source_id)
                    if previous and previous != canonical_id:
                        errors.append(f"{prefix}: source ID {source_id} also appears in {previous}")
                    source_ids[source_id] = canonical_id

        verification = check.get("verification")
        if not isinstance(verification, dict) or verification.get("status") not in VERIFICATION_STATUSES or not verification.get("basis"):
            errors.append(f"{prefix}: verification must contain a valid status and basis")

        freshness = check.get("freshness")
        if freshness not in FRESHNESS_CLASSES:
            errors.append(f"{prefix}: freshness must be one of {sorted(FRESHNESS_CLASSES)}")
        verified_at = check.get("verified_at")
        if verified_at is not None:
            if not isinstance(verified_at, str):
                errors.append(f"{prefix}: verified_at must be an ISO date or null")
            else:
                try:
                    parsed_verified_at = date.fromisoformat(verified_at)
                    if parsed_verified_at > date.today():
                        errors.append(f"{prefix}: verified_at cannot be in the future")
                except ValueError:
                    errors.append(f"{prefix}: verified_at must be an ISO date or null")

        aliases = check.get("aliases")
        if not isinstance(aliases, list) or not aliases:
            errors.append(f"{prefix}: aliases must be a non-empty list")
        else:
            for alias in aliases:
                if not isinstance(alias, dict) or not isinstance(alias.get("path"), str) or not isinstance(alias.get("line"), int) or not alias.get("title"):
                    errors.append(f"{prefix}: malformed alias {alias!r}")
                    continue
                alias_key = (alias["path"], alias["line"])
                if alias_key in alias_keys:
                    errors.append(f"{prefix}: duplicate legacy alias {alias_key}")
                alias_keys.add(alias_key)
                for source_id in alias.get("source_ids", []):
                    if not SOURCE_ID_RE.fullmatch(source_id):
                        errors.append(f"{prefix}: malformed source ID in alias {source_id!r}")
                    previous = source_ids.get(source_id)
                    if previous and previous != canonical_id:
                        errors.append(f"{prefix}: source ID {source_id} also appears in {previous}")
                    source_ids[source_id] = canonical_id
                    if not any(source_id in str(entry.get("label", "")) for entry in provenance if isinstance(entry, dict)):
                        errors.append(f"{prefix}: source ID {source_id} has no provenance entry")

        if not isinstance(check.get("related"), list):
            errors.append(f"{prefix}: related must be a list")

    for check in checks:
        for related in check.get("related", []):
            if related not in ids:
                errors.append(f"{path}: {check.get('canonical_id')} references unknown related ID {related}")
    for decision in registry.get("dedup_decisions", {}).get("reviewed_candidates", []):
        if decision.get("canonical_id") not in ids:
            errors.append(f"{path}: dedup decision references unknown canonical ID {decision.get('canonical_id')}")
    missing_domains = sorted(valid_domains - {domain for check in checks for domain in check.get("domains", [])})
    if missing_domains:
        errors.append(f"{path}: no checks routed to domains {missing_domains}")
    return errors


def validate_generated_registry(root: Path, registry: dict[str, object]) -> list[str]:
    errors: list[str] = []
    generated_errors = check_outputs(registry, root)
    errors.extend(generated_errors)
    expected: dict[str, int] = {}
    for check in registry.get("checks", []):  # type: ignore[union-attr]
        expected[check["canonical_id"]] = len(check.get("domains", []))
    actual: dict[str, int] = {}
    for path in sorted(root.glob("evm-audit-*/references/checklist.md")):
        items, parse_errors, _ = parse_checklist(path)
        errors.extend(parse_errors)
        for item in items:
            match = CANONICAL_ID_RE.search(item.title)
            if not match:
                errors.append(f"{item.ref}: missing canonical ID")
                continue
            canonical_id = match.group(1)
            actual[canonical_id] = actual.get(canonical_id, 0) + 1
    if actual != expected:
        errors.append(f"generated checklist coverage differs from registry (expected={expected}, actual={actual})")
    return errors


def validate_review_ledger_text(text: str, expected_ids: set[str] | None = None) -> list[str]:
    """Validate the machine-checkable shape of a per-check review ledger."""
    errors: list[str] = []
    records: list[tuple[str, dict[str, str], int]] = []
    current: tuple[str, dict[str, str], int] | None = None
    for line_number, line in enumerate(text.splitlines(), 1):
        heading = LEDGER_HEADING_RE.match(line)
        if heading:
            if current:
                records.append(current)
            current = (heading.group(1), {}, line_number)
            continue
        if current:
            field = LEDGER_FIELD_RE.match(line)
            if field:
                current[1][field.group(1)] = field.group(2).strip()
    if current:
        records.append(current)
    if not records:
        return ["review ledger contains no records"]

    seen: set[str] = set()
    common = {"Review stage", "Routing basis", "Status", "Applicability", "Evidence"}
    deep = {"Code path", "Preconditions", "Exploitability", "Impact", "PoC / Invariant violation"}
    for canonical_id, fields, line_number in records:
        if canonical_id in seen:
            errors.append(f"ledger:{line_number}: duplicate record {canonical_id}")
        seen.add(canonical_id)
        missing_common = sorted(common - set(fields))
        if missing_common:
            errors.append(f"ledger:{line_number}: {canonical_id} missing fields {missing_common}")
            continue
        stage = fields["Review stage"]
        status = fields["Status"]
        if stage not in LEDGER_STAGES:
            errors.append(f"ledger:{line_number}: {canonical_id} has invalid stage {stage!r}")
        if status not in LEDGER_STATUSES:
            errors.append(f"ledger:{line_number}: {canonical_id} has invalid status {status!r}")
        if status == "SUSPICIOUS" and any(key.lower() == "severity" for key in fields):
            errors.append(f"ledger:{line_number}: {canonical_id} assigns severity to SUSPICIOUS")
        if stage in {"DEEP_REVIEW", "PROOF"} and status in {"REVIEWED_SAFE", "SUSPICIOUS", "CONFIRMED"}:
            missing_deep = sorted(deep - set(fields))
            if missing_deep:
                errors.append(f"ledger:{line_number}: {canonical_id} missing deep-review fields {missing_deep}")
        if status == "CONFIRMED":
            unresolved = [key for key in deep if fields.get(key, "").startswith("UNRESOLVED")]
            if unresolved:
                errors.append(f"ledger:{line_number}: {canonical_id} is CONFIRMED with unresolved fields {unresolved}")
            if not fields.get("Code path") or not fields.get("Preconditions") or not fields.get("Impact") or not fields.get("PoC / Invariant violation"):
                errors.append(f"ledger:{line_number}: {canonical_id} CONFIRMED lacks concrete path, preconditions, impact, or proof")
    if expected_ids is not None:
        missing = sorted(expected_ids - seen)
        unknown = sorted(seen - expected_ids)
        if missing:
            errors.append(f"review ledger missing canonical IDs: {missing}")
        if unknown:
            errors.append(f"review ledger has unknown canonical IDs: {unknown}")
    return errors


def _ledger_ids(text: str) -> list[str]:
    return [match.group(1) for line in text.splitlines() if (match := LEDGER_HEADING_RE.match(line))]


def validate_routing_manifest(root: Path, manifest_path: Path, ledger_paths: list[Path] | None = None) -> list[str]:
    """Validate routing coverage and, when supplied, selected-ledger coverage."""

    errors: list[str] = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"{manifest_path}: cannot parse routing manifest: {error}"]
    if not isinstance(manifest, dict):
        return [f"{manifest_path}: routing manifest root must be an object"]
    if manifest.get("schema_version") != ROUTING_MANIFEST_VERSION:
        errors.append(f"{manifest_path}: unsupported routing manifest schema_version {manifest.get('schema_version')!r}")
    if manifest.get("stage") != "FAST_FILTER":
        errors.append(f"{manifest_path}: stage must be FAST_FILTER")

    audit = manifest.get("audit_context")
    audit_fields = {
        "selector_version",
        "registry_sha256",
        "knowledge_commit",
        "knowledge_dirty",
        "target_commit",
        "chain_id",
        "fork_block",
        "compiler_version",
        "audit_timestamp",
    }
    if not isinstance(audit, dict):
        errors.append(f"{manifest_path}: audit_context must be an object")
        audit = {}
    else:
        missing_audit = sorted(audit_fields - set(audit))
        if missing_audit:
            errors.append(f"{manifest_path}: audit_context missing fields {missing_audit}")
        registry_digest = audit.get("registry_sha256")
        if not isinstance(registry_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", registry_digest):
            errors.append(f"{manifest_path}: audit_context.registry_sha256 must be a lowercase SHA-256")
        timestamp = audit.get("audit_timestamp")
        if not isinstance(timestamp, str):
            errors.append(f"{manifest_path}: audit_context.audit_timestamp must be an ISO-8601 string")
        else:
            try:
                datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"{manifest_path}: audit_context.audit_timestamp must be an ISO-8601 string")
        for integer_field in ("chain_id", "fork_block"):
            value = audit.get(integer_field)
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                errors.append(f"{manifest_path}: audit_context.{integer_field} must be a non-negative integer or null")

    feature_path = root / "data" / "features.json"
    try:
        feature_data = json.loads(feature_path.read_text(encoding="utf-8"))
        feature_names, _ = feature_vocabulary(feature_data)
        raw_feature_map = manifest.get("feature_map", {})
        # Accept the early direct-map shape while emitting the explicit
        # schema-wrapped form from the current selector.
        if isinstance(raw_feature_map, dict) and "features" not in raw_feature_map:
            raw_feature_map = {"schema_version": 1, "features": raw_feature_map}
        feature_map = normalize_feature_map(raw_feature_map, feature_names)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        errors.append(f"{manifest_path}: invalid feature_map: {error}")
        feature_names = set()
        feature_map = {}
    if "features" in manifest and manifest.get("features") != feature_map:
        errors.append(f"{manifest_path}: features must mirror feature_map.features")

    try:
        registry = normalize_registry(load_registry(root / "data" / "canonical-checks.json"))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        return errors + [f"{manifest_path}: cannot load canonical registry: {error}"]
    if audit.get("registry_sha256") != registry_sha256(registry):
        errors.append(f"{manifest_path}: audit_context.registry_sha256 does not match the current canonical registry")
    checks = {check["canonical_id"]: check for check in registry.get("checks", [])}
    scope = manifest.get("scope")
    if not isinstance(scope, dict):
        errors.append(f"{manifest_path}: scope must be an object")
        scope = {}
    domains = scope.get("domains")
    if domains is not None and (not isinstance(domains, list) or any(not isinstance(domain, str) for domain in domains)):
        errors.append(f"{manifest_path}: scope.domains must be a string list or null")
        domains = None
    elif domains == []:
        errors.append(f"{manifest_path}: scope.domains cannot be empty")
    candidate_ids = {
        canonical_id
        for canonical_id, check in checks.items()
        if domains is None or set(check.get("domains", [])) & set(domains)
    }
    if scope.get("candidate_count") != len(candidate_ids):
        errors.append(f"{manifest_path}: scope.candidate_count does not match registry scope")

    selected = manifest.get("selected")
    filtered = manifest.get("filtered")
    if not isinstance(selected, list) or not isinstance(filtered, list):
        errors.append(f"{manifest_path}: selected and filtered must be lists")
        selected = selected if isinstance(selected, list) else []
        filtered = filtered if isinstance(filtered, list) else []
    selected_ids = [entry.get("canonical_id") for entry in selected if isinstance(entry, dict) and isinstance(entry.get("canonical_id"), str)]
    filtered_ids = [entry.get("canonical_id") for entry in filtered if isinstance(entry, dict) and isinstance(entry.get("canonical_id"), str)]
    route_fields = {
        "canonical_id",
        "title",
        "domains",
        "owner_domain",
        "freshness",
        "verified_at",
        "predicate",
        "predicate_source",
        "predicate_evaluation",
        "evaluation",
        "matched_features",
        "unknown_features",
        "basis",
    }
    for bucket_name, bucket in (("selected", selected), ("filtered", filtered)):
        for index, entry in enumerate(bucket, 1):
            if not isinstance(entry, dict):
                errors.append(f"{manifest_path}:{bucket_name}[{index}] must be an object")
            else:
                missing_fields = sorted(route_fields - set(entry))
                if missing_fields:
                    errors.append(f"{manifest_path}:{bucket_name}[{index}] missing fields {missing_fields}")
                elif not isinstance(entry.get("canonical_id"), str):
                    errors.append(f"{manifest_path}:{bucket_name}[{index}] canonical_id must be a string")
    if len(selected_ids) != len(set(selected_ids)):
        errors.append(f"{manifest_path}: duplicate selected canonical IDs")
    if len(filtered_ids) != len(set(filtered_ids)):
        errors.append(f"{manifest_path}: duplicate filtered canonical IDs")
    selected_set = set(selected_ids)
    filtered_set = set(filtered_ids)
    unknown_ids = sorted((selected_set | filtered_set) - set(checks))
    if unknown_ids:
        errors.append(f"{manifest_path}: unknown canonical IDs {unknown_ids}")
    if selected_set & filtered_set:
        errors.append(f"{manifest_path}: IDs appear in both selected and filtered: {sorted(selected_set & filtered_set)}")
    if selected_set | filtered_set != candidate_ids:
        errors.append(
            f"{manifest_path}: routing coverage differs (missing={sorted(candidate_ids - (selected_set | filtered_set))}, "
            f"extra={sorted((selected_set | filtered_set) - candidate_ids)})"
        )
    if manifest.get("selected_count") != len(selected) or manifest.get("filtered_count") != len(filtered):
        errors.append(f"{manifest_path}: selected_count/filtered_count do not match entries")
    filtered_out = manifest.get("filtered_out")
    if filtered_out is not None and filtered_out != filtered_ids:
        errors.append(f"{manifest_path}: filtered_out must match filtered canonical IDs")

    for entry in [item for item in selected + filtered if isinstance(item, dict) and item.get("canonical_id") in checks]:
        canonical_id = entry["canonical_id"]
        try:
            expected = evaluate_check(checks[canonical_id], feature_map, feature_names)
        except ValueError as error:
            errors.append(f"{manifest_path}: cannot evaluate {canonical_id}: {error}")
            continue
        if entry.get("evaluation") != expected["result"]:
            errors.append(f"{manifest_path}: {canonical_id} has stale evaluation {entry.get('evaluation')!r}")
        if entry.get("predicate_evaluation") != expected["predicate_result"]:
            errors.append(f"{manifest_path}: {canonical_id} has stale predicate_evaluation")
        if entry.get("predicate_source") != expected["predicate_source"]:
            errors.append(f"{manifest_path}: {canonical_id} has stale predicate_source")
        if entry.get("freshness") != checks[canonical_id].get("freshness") or entry.get("verified_at") != checks[canonical_id].get("verified_at"):
            errors.append(f"{manifest_path}: {canonical_id} has stale freshness metadata")
        if entry.get("predicate") != expected["predicate"]:
            errors.append(f"{manifest_path}: {canonical_id} has stale predicate")
        if entry.get("matched_features") != expected["matched_features"] or entry.get("unknown_features") != expected["unknown_features"]:
            errors.append(f"{manifest_path}: {canonical_id} has stale feature matches")
        expected_owner = checks[canonical_id].get("primary_domain")
        if domains and expected_owner not in domains:
            expected_owner = next((domain for domain in domains if domain in checks[canonical_id].get("domains", [])), expected_owner)
        if entry.get("owner_domain") != expected_owner:
            errors.append(f"{manifest_path}: {canonical_id} has owner_domain {entry.get('owner_domain')!r}, expected {expected_owner!r}")
        if (canonical_id in selected_set) != (expected["result"] != "FALSE"):
            errors.append(f"{manifest_path}: {canonical_id} is in the wrong routing bucket")

    selected_checks = manifest.get("selected_checks")
    if selected_checks is not None:
        if not isinstance(selected_checks, list):
            errors.append(f"{manifest_path}: selected_checks must be a list")
        else:
            body_ids = [entry.get("canonical_id") for entry in selected_checks if isinstance(entry, dict)]
            if set(body_ids) != selected_set or len(body_ids) != len(set(body_ids)):
                errors.append(f"{manifest_path}: selected_checks IDs must exactly match selected IDs")

    if ledger_paths:
        seen_ledger: set[str] = set()
        owner_by_id = {
            entry["canonical_id"]: entry.get("owner_domain")
            for entry in selected
            if isinstance(entry, dict) and isinstance(entry.get("canonical_id"), str)
        }
        for ledger_path in ledger_paths:
            try:
                ledger_text = ledger_path.read_text(encoding="utf-8")
            except OSError as error:
                errors.append(f"{ledger_path}: cannot read review ledger: {error}")
                continue
            for canonical_id in _ledger_ids(ledger_text):
                if canonical_id in seen_ledger:
                    errors.append(f"{ledger_path}: duplicate selected ledger record across ledgers: {canonical_id}")
                seen_ledger.add(canonical_id)
                if canonical_id in filtered_set:
                    errors.append(f"{ledger_path}: filtered ID must not have a ledger record: {canonical_id}")
                elif canonical_id not in selected_set:
                    errors.append(f"{ledger_path}: ledger contains non-selected/unknown ID: {canonical_id}")
                else:
                    expected_name = f"review-{owner_by_id[canonical_id]}.md"
                    if ledger_path.name != expected_name:
                        errors.append(
                            f"{ledger_path}: {canonical_id} belongs in {expected_name} for owner_domain={owner_by_id[canonical_id]}"
                        )
        missing = sorted(selected_set - seen_ledger)
        if missing:
            errors.append(f"{manifest_path}: selected IDs missing from review ledgers: {missing}")
    return errors


def validate_knowledge_claims(root: Path, registry: dict[str, Any] | None = None) -> list[str]:
    """Require evidence-backed regression claims for high-confidence checks."""

    path = root / "tests" / "knowledge" / "claims.json"
    if not path.exists():
        return [f"missing knowledge claims: {path}"]
    errors: list[str] = []
    try:
        claims_data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"{path}: cannot parse JSON: {error}"]
    if not isinstance(claims_data, dict) or claims_data.get("schema_version") != CLAIMS_SCHEMA_VERSION:
        errors.append(f"{path}: schema_version must be {CLAIMS_SCHEMA_VERSION}")
    claims = claims_data.get("claims") if isinstance(claims_data, dict) else None
    if not isinstance(claims, list):
        return errors + [f"{path}: claims must be a list"]
    if registry is None:
        try:
            registry = normalize_registry(load_registry(root / "data" / "canonical-checks.json"))
        except (OSError, json.JSONDecodeError, ValueError) as error:
            return errors + [f"{path}: cannot load registry: {error}"]
    checks = {check.get("canonical_id"): check for check in registry.get("checks", [])}
    target_ids = {
        canonical_id
        for canonical_id, check in checks.items()
        if check.get("type") == "normative" or (check.get("type") == "semantic" and check.get("confidence") == "high")
    }
    seen: set[str] = set()
    for index, claim in enumerate(claims, 1):
        prefix = f"{path}:claims[{index}]"
        if not isinstance(claim, dict):
            errors.append(f"{prefix}: claim must be an object")
            continue
        canonical_id = claim.get("canonical_id")
        if canonical_id in seen:
            errors.append(f"{prefix}: duplicate canonical_id {canonical_id}")
        seen.add(canonical_id)
        if canonical_id not in checks:
            errors.append(f"{prefix}: unknown canonical_id {canonical_id!r}")
        evidence = claim.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{prefix}: evidence must be a non-empty list")
        else:
            truth_kinds: set[str] = set()
            for evidence_index, item in enumerate(evidence, 1):
                if not isinstance(item, dict) or item.get("kind") not in CLAIM_EVIDENCE_KINDS:
                    errors.append(
                        f"{prefix}.evidence[{evidence_index}]: kind must be official, executable, or text-regression"
                    )
                    continue
                if item["kind"] in {"official", "executable"}:
                    truth_kinds.add(item["kind"])
                if item["kind"] == "official":
                    if not isinstance(item.get("url"), str) or not item["url"].startswith("https://") or not URL_VALUE_RE.match(item["url"]):
                        errors.append(f"{prefix}.evidence[{evidence_index}]: official evidence needs an HTTPS URL")
                    if not item.get("locator"):
                        errors.append(f"{prefix}.evidence[{evidence_index}]: official evidence needs a locator")
                    elif canonical_id in checks:
                        official_urls = {
                            source.get("url")
                            for source in checks[canonical_id].get("provenance", [])
                            if isinstance(source, dict) and source.get("kind") == "official"
                        }
                        if item.get("url") not in official_urls:
                            errors.append(f"{prefix}.evidence[{evidence_index}]: URL is not recorded as official provenance for {canonical_id}")
                elif not isinstance(item.get("test"), str) or not item["test"].strip():
                    errors.append(f"{prefix}.evidence[{evidence_index}]: {item['kind']} evidence needs a test identifier")
                elif "::" in item["test"]:
                    path_part, *identifier_parts = item["test"].split("::")
                    test_path = root / path_part
                    if item["kind"] == "executable" and "test_knowledge_claims_and_forbidden_regressions" in item["test"]:
                        errors.append(
                            f"{prefix}.evidence[{evidence_index}]: text-only regression test cannot be executable evidence"
                        )
                    if not test_path.exists():
                        errors.append(f"{prefix}.evidence[{evidence_index}]: test file does not exist: {test_path}")
                    elif item["kind"] == "executable" and test_path.suffix == ".sol":
                        test_name = identifier_parts[-1] if identifier_parts else ""
                        source_text = test_path.read_text(encoding="utf-8")
                        if not test_name.startswith("test") or not re.search(rf"\bfunction\s+{re.escape(test_name)}\s*\(", source_text):
                            errors.append(
                                f"{prefix}.evidence[{evidence_index}]: Solidity executable test identifier does not exist: {test_name!r}"
                            )
            if not truth_kinds:
                errors.append(f"{prefix}: text-regression evidence cannot establish factual correctness")
        for field in ("required_terms", "forbidden_terms"):
            values = claim.get(field)
            if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
                errors.append(f"{prefix}: {field} must be a string list")
    missing = sorted(target_ids - seen)
    supplemental_ids = {
        claim.get("canonical_id")
        for claim in claims
        if isinstance(claim, dict) and claim.get("supplemental") is True
    }
    extra = sorted(seen - target_ids - supplemental_ids)
    if missing:
        errors.append(f"{path}: missing high-confidence claims for {missing}")
    if extra:
        errors.append(f"{path}: non-target claims must set supplemental=true: {extra}")
    return errors


def relative_link_errors(root: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(root.rglob("*.md")):
        if ".git" in path.parts:
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for raw_target in LINK_RE.findall(line):
                target = raw_target.strip().strip("<>").split("#", 1)[0].split("?", 1)[0]
                if not target or target.startswith(("http://", "https://", "mailto:")):
                    continue
                target_path = (path.parent / target).resolve()
                if not target_path.exists():
                    errors.append(f"{path}:{line_number}: broken relative link: {raw_target}")
    return errors


def external_link_errors(root: Path) -> list[str]:
    """Optionally check source URL liveness without making it a default CI gate."""
    urls: set[str] = set()
    for path in sorted(root.rglob("*.md")):
        if ".git" in path.parts:
            continue
        urls.update(LINK_RE.findall(path.read_text(encoding="utf-8")))
    registry_path = root / "data" / "canonical-checks.json"
    if registry_path.exists():
        try:
            registry = load_registry(registry_path)
            for source in registry.get("source_catalog", {}).values():
                if isinstance(source, dict) and source.get("url"):
                    urls.add(str(source["url"]))
            for check in registry.get("checks", []):
                for source in check.get("provenance", []):
                    if isinstance(source, dict) and source.get("url"):
                        urls.add(str(source["url"]))
        except (OSError, json.JSONDecodeError):
            pass

    errors: list[str] = []
    for url in sorted(url for url in urls if url.startswith(("http://", "https://"))):
        try:
            request = Request(url, method="HEAD", headers={"User-Agent": "evm-audit-skills-validator/1"})
            with urlopen(request, timeout=8) as response:
                if response.status >= 400:
                    errors.append(f"external source URL returned {response.status}: {url}")
        except HTTPError as error:
            if error.code in {405, 403}:
                try:
                    request = Request(url, headers={"Range": "bytes=0-64", "User-Agent": "evm-audit-skills-validator/1"})
                    with urlopen(request, timeout=8) as response:
                        if response.status >= 400:
                            errors.append(f"external source URL returned {response.status}: {url}")
                except (HTTPError, URLError, TimeoutError) as fallback_error:
                    errors.append(f"external source URL unavailable: {url} ({fallback_error})")
            else:
                errors.append(f"external source URL returned {error.code}: {url}")
        except (URLError, TimeoutError) as error:
            errors.append(f"external source URL unavailable: {url} ({error})")
    return errors


def validate_counts(root: Path, counts: dict[str, int]) -> list[str]:
    errors: list[str] = []
    runtime_total = sum(counts.values())
    registry_path = root / "data" / "canonical-checks.json"
    canonical_total = len(load_registry(registry_path).get("checks", [])) if registry_path.exists() else 0

    readme = root / "README.md"
    readme_text = readme.read_text(encoding="utf-8")
    readme_canonical_match = README_CANONICAL_RE.search(readme_text)
    if not readme_canonical_match:
        errors.append("README.md: missing canonical-check count")
    elif int(readme_canonical_match.group(1).replace(",", "")) != canonical_total:
        errors.append(
            f"README.md: canonical count {readme_canonical_match.group(1)} does not match registry total {canonical_total}"
        )
    readme_runtime_match = README_RUNTIME_RE.search(readme_text)
    if not readme_runtime_match:
        errors.append("README.md: missing generated-runtime count")
    elif int(readme_runtime_match.group(1).replace(",", "")) != runtime_total:
        errors.append(
            f"README.md: runtime count {readme_runtime_match.group(1)} does not match generated total {runtime_total}"
        )

    master = root / "evm-audit-master" / "SKILL.md"
    master_text = master.read_text(encoding="utf-8")
    master_counts: dict[str, int] = {}
    for line in master_text.splitlines():
        match = MASTER_ROW_RE.match(line)
        if match:
            master_counts[match.group(1)] = int(match.group(2))

    if master_counts != counts:
        missing = sorted(set(counts) - set(master_counts))
        extra = sorted(set(master_counts) - set(counts))
        changed = sorted(
            domain
            for domain in set(counts) & set(master_counts)
            if counts[domain] != master_counts[domain]
        )
        errors.append(
            "evm-audit-master/SKILL.md: table counts differ "
            f"(missing={missing}, extra={extra}, changed={changed})"
        )

    master_canonical_match = MASTER_CANONICAL_RE.search(master_text)
    if not master_canonical_match:
        errors.append("evm-audit-master/SKILL.md: missing canonical total")
    elif int(master_canonical_match.group(1).replace(",", "")) != canonical_total:
        errors.append(
            "evm-audit-master/SKILL.md: canonical total "
            f"{master_canonical_match.group(1)} does not match registry total {canonical_total}"
        )
    master_runtime_match = MASTER_RUNTIME_RE.search(master_text)
    if not master_runtime_match:
        errors.append("evm-audit-master/SKILL.md: missing generated-runtime total")
    elif int(master_runtime_match.group(1).replace(",", "")) != runtime_total:
        errors.append(
            "evm-audit-master/SKILL.md: runtime total "
            f"{master_runtime_match.group(1)} does not match generated total {runtime_total}"
        )

    return errors


def validate_review_record(root: Path, strict: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    path = root / "evm-audit-master" / "references" / "checklist-semantic-dedup-review.md"
    if not path.exists():
        return [f"missing review record: {path}"], warnings

    groups: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = REVIEW_ROW_RE.match(line)
        if not match:
            continue
        group, decision = match.groups()
        if group in groups:
            errors.append(f"{path}:{line_number}: duplicate review group {group}")
        groups[group] = decision
        if decision == "PENDING_USER_CONFIRMATION":
            warnings.append(f"pending cross-domain decision: {group}")

    if strict and any(decision == "PENDING_USER_CONFIRMATION" for decision in groups.values()):
        errors.append("semantic-dedup review still has pending cross-domain decisions")
    return errors, warnings


def semantic_candidates(items: list[Item], limit: int) -> list[str]:
    candidates: list[tuple[float, Item, Item]] = []
    for index, left in enumerate(items):
        left_normalized = normalize_title(left.title)
        left_tokens = title_tokens(left.title)
        left_id = CANONICAL_ID_RE.search(left.title)
        for right in items[index + 1 :]:
            if left.path == right.path:
                continue
            right_id = CANONICAL_ID_RE.search(right.title)
            if left_id and right_id and left_id.group(1) == right_id.group(1):
                continue
            right_normalized = normalize_title(right.title)
            right_tokens = title_tokens(right.title)
            exact = left_normalized == right_normalized
            token_similarity = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
            sequence_similarity = SequenceMatcher(None, left_normalized, right_normalized).ratio()
            if exact or sequence_similarity >= 0.82 or token_similarity >= 0.72:
                score = 1.0 if exact else max(sequence_similarity, token_similarity)
                candidates.append((score, left, right))

    candidates.sort(key=lambda candidate: (-candidate[0], candidate[1].ref, candidate[2].ref))
    output: list[str] = []
    for score, left, right in candidates[:limit]:
        label = "exact-title" if score == 1.0 else f"similarity={score:.2f}"
        output.append(
            f"[semantic-candidate] {label}: {left.ref} [{left.title}] <-> "
            f"{right.ref} [{right.title}]"
        )
    if len(candidates) > limit:
        output.append(f"[semantic-candidate] {len(candidates) - limit} additional candidates suppressed")
    return output


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--strict", action="store_true", help="fail if review decisions are pending")
    parser.add_argument(
        "--candidates",
        action="store_true",
        help="print cross-domain semantic similarity candidates",
    )
    parser.add_argument(
        "--check-external-links",
        action="store_true",
        help="perform network liveness checks for external source URLs",
    )
    parser.add_argument(
        "--review-ledger",
        action="append",
        type=Path,
        default=[],
        help="validate one or more run-specific review ledger files",
    )
    parser.add_argument(
        "--routing-manifest",
        action="append",
        type=Path,
        default=[],
        help="validate one or more machine routing manifests and their selected-ledger coverage",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()

    errors: list[str] = []
    warnings: list[str] = []
    all_items: list[Item] = []
    counts: dict[str, int] = {}
    source_occurrences: dict[str, list[str]] = {}

    checklist_paths = sorted(root.glob("evm-audit-*/references/checklist.md"))
    if len(checklist_paths) != 19:
        errors.append(f"expected 19 domain checklists, found {len(checklist_paths)}")

    errors.extend(validate_registry(root))
    registry_path = root / "data" / "canonical-checks.json"
    if registry_path.exists():
        try:
            normalized_registry = normalize_registry(load_registry(registry_path))
            errors.extend(validate_generated_registry(root, normalized_registry))
            errors.extend(validate_knowledge_claims(root, normalized_registry))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{registry_path}: cannot load generated coverage: {error}")

    model_files = sorted(
        path for domain in root.glob("evm-audit-*")
        for path in (domain / "references").glob("*.md")
        if path.name in {"known.md", "partial.md", "novel.md"}
    )
    if model_files:
        errors.append("model-specific references remain in runtime directories: " + ", ".join(str(path) for path in model_files))

    for path in checklist_paths:
        items, parse_errors, source_ids = parse_checklist(path)
        errors.extend(parse_errors)
        all_items.extend(items)
        domain = path.parts[-3]
        counts[domain] = len(items)
        normalized_titles: dict[str, Item] = {}
        for item in items:
            key = normalize_title(item.title)
            previous = normalized_titles.get(key)
            if previous:
                errors.append(
                    f"{path}:{item.line}: duplicate normalized title with {previous.ref}: {item.title}"
                )
            else:
                normalized_titles[key] = item
        for source_id, occurrence_count in source_ids.items():
            source_occurrences.setdefault(source_id, []).extend([str(path)] * occurrence_count)

    for source_id, locations in sorted(source_occurrences.items()):
        if len(locations) > 1:
            errors.append(f"duplicate structured source ID {source_id}: {', '.join(locations)}")

    if (root / "attack-vectors.md").exists():
        errors.append("central attack-vectors.md must not be used as a runtime source")

    errors.extend(relative_link_errors(root))
    if args.check_external_links:
        errors.extend(external_link_errors(root))
    for ledger_path in args.review_ledger:
        try:
            errors.extend(validate_review_ledger_text(ledger_path.read_text(encoding="utf-8")))
        except OSError as error:
            errors.append(f"{ledger_path}: cannot read review ledger: {error}")
    for manifest_path in args.routing_manifest:
        errors.extend(validate_routing_manifest(root, manifest_path.resolve(), args.review_ledger))
    errors.extend(validate_counts(root, counts))
    review_errors, review_warnings = validate_review_record(root, args.strict)
    errors.extend(review_errors)
    warnings.extend(review_warnings)

    if args.candidates:
        warnings.extend(semantic_candidates(all_items, limit=120))
    else:
        exact_candidates = [line for line in semantic_candidates(all_items, limit=120) if "exact-title" in line]
        warnings.extend(exact_candidates)

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)

    print(f"checklists={len(checklist_paths)} items={sum(counts.values())} errors={len(errors)} warnings={len(warnings)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
