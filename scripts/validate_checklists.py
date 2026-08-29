#!/usr/bin/env python3
"""Validate EVM audit checklist structure and report semantic dedup candidates.

The validator deliberately does not decide semantic equivalence. It fails only
on deterministic repository invariants and reports cross-file similarity for
human review.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path


ITEM_RE = re.compile(r"^- \[ \] \*\*(.*?)\*\*")
SOURCE_ID_RE = re.compile(r"\b(?:SAS-AV-\d{3}|DROZER-[A-Z0-9-]+|AUDITMOS-[A-Z0-9-]+)\b")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
MASTER_ROW_RE = re.compile(
    r"^\|\s*\d+\s*\|\s*\*\*(evm-audit-[^*]+)\*\*.*\|\s*(\d+)\s*\|\s*$"
)
README_TOTAL_RE = re.compile(r"(\d[\d,]*)\s+individual checks")
MASTER_TOTAL_RE = re.compile(r"Total:\s+(\d[\d,]*)\s+checklist items")
REVIEW_ROW_RE = re.compile(
    r"^\|\s*([A-Z]+-\d+)\s*\|.*\|\s*(MERGED|MERGE|KEEP_DISTINCT|PENDING_USER_CONFIRMATION)\s*\|\s*$"
)

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


def validate_counts(root: Path, counts: dict[str, int]) -> list[str]:
    errors: list[str] = []
    total = sum(counts.values())

    readme = root / "README.md"
    readme_match = README_TOTAL_RE.search(readme.read_text(encoding="utf-8"))
    if not readme_match:
        errors.append("README.md: missing individual-check count")
    elif int(readme_match.group(1).replace(",", "")) != total:
        errors.append(
            f"README.md: count {readme_match.group(1)} does not match runtime total {total}"
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

    master_total_match = MASTER_TOTAL_RE.search(master_text)
    if not master_total_match:
        errors.append("evm-audit-master/SKILL.md: missing total count")
    elif int(master_total_match.group(1).replace(",", "")) != total:
        errors.append(
            "evm-audit-master/SKILL.md: total "
            f"{master_total_match.group(1)} does not match runtime total {total}"
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
        for right in items[index + 1 :]:
            if left.path == right.path:
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
