#!/usr/bin/env python3
"""Print a stable quality baseline for the canonical knowledge registry."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    registry = json.loads((ROOT / "data/canonical-checks.json").read_text(encoding="utf-8"))
    claims = json.loads((ROOT / "tests/knowledge/claims.json").read_text(encoding="utf-8"))["claims"]
    checks = registry["checks"]
    specific_fp = [check for check in checks if check["fp_policy"] == "specific"]
    specific_proof = [check for check in checks if check["proof_policy"] == "specific"]
    evidence = [item for claim in claims for item in claim.get("evidence", [])]
    metrics = {
        "canonical_checks": len(checks),
        "global_fp_count": len(checks) - len(specific_fp),
        "specific_fp_count": len(specific_fp),
        "global_proof_count": len(checks) - len(specific_proof),
        "specific_proof_count": len(specific_proof),
        "specific_fp_coverage": round(len(specific_fp) / len(checks), 4),
        "specific_proof_coverage": round(len(specific_proof) / len(checks), 4),
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
    print(json.dumps(metrics, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
