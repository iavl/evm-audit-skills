#!/usr/bin/env python3
"""Render runtime Markdown views from the canonical JSON registry.

The generator is deliberately knowledge-free: it never repairs, infers, or
rewrites canonical records. Historical transformations live under
``development/migrations`` and normal maintenance edits ``data/canonical-checks.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "canonical-checks.json"


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_registry(registry: dict[str, Any]) -> dict[str, Any]:
    """Compatibility helper retained for callers; canonical data is untouched."""

    return registry


def load_domains(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    domains: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "domains").glob("*.json")):
        if path.name == "domain.schema.json":
            continue
        domain = json.loads(path.read_text(encoding="utf-8"))
        if domain["id"] in domains:
            raise ValueError(f"duplicate domain id: {domain['id']}")
        domains[domain["id"]] = domain
    return domains


def one_line(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(str(part).strip() for part in value if str(part).strip())
    return str(value).strip()


def render_provenance(item: dict[str, Any]) -> str:
    rendered: list[str] = []
    for entry in item.get("provenance", []):
        label = entry.get("label", "unknown source")
        url = entry.get("url")
        rendered.append(f"[{label}]({url})" if url else str(label))
    return "; ".join(dict.fromkeys(rendered)) or "Canonical registry entry"


def render_full_item(item: dict[str, Any]) -> list[str]:
    metadata = f"_({item['type']}; {item['confidence']})_"
    description = one_line(item["description"])
    lines = [f"- [ ] **[{item['canonical_id']}] {item['title']}** {metadata}: {description}"]
    seen = {description}
    for label, field in (
        ("Trigger", "trigger"),
        ("Risk", "risk"),
        ("Detection", "detection"),
        ("Specific FP", "false_positive_gates"),
        ("Specific proof", "proof"),
    ):
        if field == "false_positive_gates" and item.get("fp_policy") != "specific":
            continue
        if field == "proof" and item.get("proof_policy") != "specific":
            continue
        value = one_line(item[field])
        if value and value not in seen:
            lines.append(f"  - **{label}:** {value}")
            seen.add(value)
    lines.append(f"  - **Provenance:** {render_provenance(item)}")
    if item.get("related"):
        lines.append(f"  - **Related:** {', '.join(item['related'])}")
    if item.get("origin_notes"):
        lines.append(f"  - **Source detail:** {one_line(item['origin_notes'])}")
    if item.get("notes"):
        lines.append(f"  - **Notes:** {one_line(item['notes'])}")
    return lines


def render_alias(item: dict[str, Any]) -> list[str]:
    return [
        f"- [ ] **[{item['canonical_id']}] {item['title']}**: Shared canonical check; "
        f"apply the primary definition and evidence requirements for `{item['primary_domain']}`."
    ]


def render_domain(registry: dict[str, Any], config: dict[str, Any]) -> str:
    domain = config["id"]
    items = [item for item in registry["checks"] if domain in item.get("domains", [])]
    sections = list(dict.fromkeys(item.get("section", "Uncategorized") for item in items))
    output = [
        "<!-- GENERATED FILE: source is ../../../data/canonical-checks.json; do not edit by hand. -->",
        f"# {config['checklist_title']}",
        "",
        "Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.",
        "Global FP/proof obligations live in the Review Contract; only check-specific gates and proofs are repeated below.",
        "",
    ]
    for section in sections:
        output.extend([f"## {section}", ""])
        for item in items:
            if item.get("section") != section:
                continue
            output.extend(render_full_item(item) if item.get("primary_domain") == domain else render_alias(item))
            output.append("")
    return "\n".join(output).rstrip() + "\n"


def render_skill(config: dict[str, Any]) -> str:
    domain = config["id"]
    related = ", ".join(f"`{value}`" for value in config["related_domains"]) or "none"
    required_context = "\n".join(f"- `{value['key']}`: {value['description']}" for value in config["required_context"])
    review_requirements = "\n".join(f"- {value}" for value in config["review_requirements"])
    return f"""---
name: {domain}
description: {config['description']} Consume routed selected-check bodies at runtime.
---
# {config['name']}

## Runtime Modes

Resolve `<suite-root>` as the nearest ancestor containing `data/`, `domains/`, and `scripts/`. It is the repository root, not the `skills/` directory.

### Standalone

When invoked directly, create `audits/<repo>-<UTC timestamp>/` with `recon/`, `routing/`, `runtime/`, and `reviews/`, then run the shared pipeline for `{domain}` once:

1. `python3 <suite-root>/scripts/recon.py <target> --audit-root <target-root> --output <run-dir>/recon/feature-map.json`
2. `python3 <suite-root>/scripts/select_checks.py --feature-map <run-dir>/recon/feature-map.json --target-root <target-root> --domain {domain} --manifest-out <run-dir>/routing/manifest.json --context-out <run-dir>/context.json --environment-out <run-dir>/routing/environment-context.json`
3. `python3 <suite-root>/scripts/render_runtime.py --manifest <run-dir>/routing/manifest.json --profile screen --owner-domain {domain} --output <run-dir>/runtime/screen-{domain}.md --domain-resolution-out <run-dir>/reviews/domain-resolution.json`
4. Resolve `domain-resolution.json`; then rerun Screen with `--domain-resolution <run-dir>/reviews/domain-resolution.json --screen-results-out <run-dir>/reviews/screen-results.json --output <run-dir>/runtime/screen-{domain}.md`.
5. Classify every Screen card as `NOT_APPLICABLE_CONFIRMED` or `CANDIDATE`; uncertainty is always `CANDIDATE` and Screen never filters.
6. `python3 <suite-root>/scripts/render_runtime.py --manifest <run-dir>/routing/manifest.json --profile deep --domain-resolution <run-dir>/reviews/domain-resolution.json --screen-results <run-dir>/reviews/screen-results.json --owner-domain {domain} --output <run-dir>/runtime/deep-{domain}.md`
7. Write one JSONL record per candidate with `review_ledger.py`, then derive `audit-state.json` with `validate_audit_run.py`.

### Orchestrated

When Master supplies `context.json`, the immutable routing manifest, Screen results, and `screen-{domain}.md`, consume those artifacts directly. Never rerun Recon or Selector in orchestrated mode.

## Required Context

{required_context}

Deferred Domain absence may be marked `ABSENT_CONFIRMED` only with complete
scope evidence accepted by this Domain's trusted-absence policy.

## Domain Review Requirements

{review_requirements}

Do not load `<suite-root>/data/canonical-checks.json` or the full generated checklist into model context. Apply the tri-state predicate router before deep review. Pattern matches are candidates, not findings. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and runnable PoC or deterministic invariant evidence.
Apply `<suite-root>/skills/evm-audit-master/references/check-review-contract.runtime.md` to every Deep review record.

Related domains (advisory only; never auto-expand direct scope): {related}.

## Maintenance View
- `references/checklist.md` is generated for maintenance and compatibility.
"""


def render_domain_catalog(registry: dict[str, Any], domains: dict[str, dict[str, Any]]) -> str:
    lines = [
        "<!-- GENERATED FILE: source is domains/*.json and data/canonical-checks.json; do not edit by hand. -->",
        "# Domain Catalog",
        "",
        "| Domain | Purpose | Surface features | Related domains | Runtime entries |",
        "|---|---|---|---|---:|",
    ]
    for domain, config in domains.items():
        count = sum(domain in check.get("domains", []) for check in registry["checks"])
        features = ", ".join(f"`{value}`" for value in config["surface_features"])
        related = ", ".join(f"`{value}`" for value in config["related_domains"]) or "—"
        lines.append(f"| `{domain}` | {config['description']} | {features} | {related} | {count} |")
    return "\n".join(lines) + "\n"


def generated_outputs(registry: dict[str, Any], root: Path) -> dict[Path, str]:
    domains = load_domains(root)
    outputs: dict[Path, str] = {}
    for domain, config in domains.items():
        outputs[root / "skills" / domain / "references" / "checklist.md"] = render_domain(registry, config)
        outputs[root / "skills" / domain / "SKILL.md"] = render_skill(config)
    outputs[root / "skills" / "evm-audit-master" / "references" / "domains.md"] = render_domain_catalog(registry, domains)
    return outputs


def write_outputs(registry: dict[str, Any], root: Path) -> None:
    for path, content in generated_outputs(registry, root).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def check_outputs(registry: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    for path, expected in generated_outputs(registry, root).items():
        if not path.exists():
            errors.append(f"missing generated file: {path}")
        elif path.read_text(encoding="utf-8") != expected:
            errors.append(f"generated file is stale: {path}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true", help="verify generated Markdown without writing files")
    args = parser.parse_args(argv)
    root = args.root.resolve()

    try:
        registry = load_registry(root / "data" / "canonical-checks.json")
        errors = check_outputs(registry, root)
        if args.check:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            print(f"canonical_checks={len(registry.get('checks', []))} generated_errors={len(errors)}")
            return 1 if errors else 0
        write_outputs(registry, root)
        print(f"canonical_checks={len(registry.get('checks', []))} generated={len(load_domains(root))}")
        return 0
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
