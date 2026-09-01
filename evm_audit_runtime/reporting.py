"""Pure report-admission decisions."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

SEVERITY_ORDER = {"Info": 0, "Low": 1, "Medium": 2, "High": 3, "Critical": 4}


def issue_candidate(severity: str | None) -> bool:
    return severity is not None and SEVERITY_ORDER[severity] >= SEVERITY_ORDER["Medium"]


def derive_issue_candidates(
    confirmed_ids: Iterable[str],
    severity_decisions: Mapping[str, Mapping[str, str]],
) -> list[dict[str, str]]:
    """Return the exact filing projection for the current confirmed findings."""
    confirmed = set(confirmed_ids)
    decision_ids = set(severity_decisions)
    if decision_ids != confirmed:
        raise ValueError(
            "severity decision IDs do not match confirmed IDs: "
            f"missing={sorted(confirmed - decision_ids)} extra={sorted(decision_ids - confirmed)}"
        )
    candidates: list[dict[str, str]] = []
    for canonical_id in sorted(confirmed):
        decision = severity_decisions[canonical_id]
        if not isinstance(decision, Mapping):
            raise ValueError(f"invalid severity decision for {canonical_id}")
        severity = decision.get("severity")
        if severity not in SEVERITY_ORDER:
            raise ValueError(f"invalid severity for {canonical_id}: {severity!r}")
        if issue_candidate(severity):
            candidates.append({"canonical_id": canonical_id, "severity": severity})
    return candidates
