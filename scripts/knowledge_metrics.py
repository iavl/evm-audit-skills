#!/usr/bin/env python3
"""Emit canonical knowledge metrics globally and per Domain."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from audit_artifacts import registry_sha256, validate_schema
except ImportError:  # pragma: no cover
    from scripts.audit_artifacts import registry_sha256, validate_schema


ROOT = Path(__file__).resolve().parents[1]


def _evidence_by_check(claims: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        claim["canonical_id"]: claim.get("evidence", [])
        for claim in claims
        if isinstance(claim, dict) and isinstance(claim.get("canonical_id"), str)
    }


def _metrics(checks: list[dict[str, Any]], claims: list[dict[str, Any]]) -> dict[str, Any]:
    specific_fp = [check for check in checks if check["fp_policy"] == "specific"]
    specific_proof = [check for check in checks if check["proof_policy"] == "specific"]
    evidence = [item for claim in claims for item in claim.get("evidence", [])]
    return {
        "canonical_checks": len(checks),
        "global_fp_count": len(checks) - len(specific_fp),
        "specific_fp_count": len(specific_fp),
        "global_proof_count": len(checks) - len(specific_proof),
        "specific_proof_count": len(specific_proof),
        "specific_fp_coverage": round(len(specific_fp) / len(checks), 4) if checks else 0,
        "specific_proof_coverage": round(len(specific_proof) / len(checks), 4) if checks else 0,
        "generic_boilerplate_count": sum(
            any("Verify the guard, invariant" in item for item in check["false_positive_gates"])
            or any("Trace a reachable path, satisfy the preconditions" in item for item in check["proof"])
            for check in checks
        ),
        "official_evidence_count": sum(item.get("kind") == "official" for item in evidence),
        "executable_evidence_count": sum(item.get("kind") == "executable" for item in evidence),
        "curated_predicate_count": sum(check.get("predicate_source") == "curated" for check in checks),
        "routing_verified_count": sum(bool(check.get("routing_verification")) for check in checks),
        "versioned_verified_count": sum(bool(check.get("freshness") == "versioned" and check.get("verified_at")) for check in checks),
        "time_sensitive_verified_count": sum(bool(check.get("freshness") == "time-sensitive" and check.get("verified_at")) for check in checks),
    }


def metrics(registry: dict[str, Any], claims: list[dict[str, Any]]) -> dict[str, Any]:
    checks = registry["checks"]
    by_claim = _evidence_by_check(claims)
    domains = sorted({domain for check in checks for domain in check.get("domains", [])})
    per_domain: dict[str, dict[str, Any]] = {}
    for domain in domains:
        domain_checks = [check for check in checks if domain in check.get("domains", [])]
        domain_claims = [claim for claim in claims if claim.get("canonical_id") in {check["canonical_id"] for check in domain_checks}]
        domain_metric = _metrics(domain_checks, domain_claims)
        domain_metric["shared_checks"] = sum(len(check.get("domains", [])) > 1 for check in domain_checks)
        domain_metric["checks_with_claim_evidence"] = sum(bool(by_claim.get(check["canonical_id"])) for check in domain_checks)
        per_domain[domain] = domain_metric
    return {
        "schema_version": 1,
        **_metrics(checks, claims),
        "registry_sha256": registry_sha256(registry),
        "per_domain": per_domain,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    registry = json.loads((root / "data/canonical-checks.json").read_text(encoding="utf-8"))
    claims = json.loads((root / "tests/knowledge/claims.json").read_text(encoding="utf-8"))["claims"]
    value = metrics(registry, claims)
    validate_schema(root, "knowledge-metrics.schema.json", value)
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
