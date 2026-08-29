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
from difflib import SequenceMatcher
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from generate_checklists import DOMAIN_CODES, check_outputs, load_registry, normalize_registry
except ImportError:  # pragma: no cover - supports importing this file from another cwd
    from scripts.generate_checklists import DOMAIN_CODES, check_outputs, load_registry, normalize_registry


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
    "provenance",
    "related",
    "aliases",
    "verification",
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
            feature_names = set(feature_data.get("features", {}))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{feature_path}: cannot parse JSON: {error}")
            feature_names = set()

    try:
        registry = normalize_registry(load_registry(path))
    except (OSError, json.JSONDecodeError) as error:
        return errors + [f"{path}: cannot parse JSON: {error}"]
    if registry.get("schema_version") != 1:
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
        for field in ("trigger", "detection", "false_positive_gates", "proof", "features"):
            value = check.get(field)
            if not isinstance(value, list) or not value or any(not isinstance(part, str) or not part.strip() for part in value):
                errors.append(f"{prefix}: {field} must be a non-empty string list")
        unknown_features = sorted(set(check.get("features", [])) - feature_names)
        if unknown_features:
            errors.append(f"{prefix}: unknown features {unknown_features}")

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
            errors.extend(validate_generated_registry(root, normalize_registry(load_registry(registry_path))))
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
