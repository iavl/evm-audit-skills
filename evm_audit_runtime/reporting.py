"""Pure report-admission decisions."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

SEVERITY_ORDER = {"Info": 0, "Low": 1, "Medium": 2, "High": 3, "Critical": 4}
POC_REQUIRED_MIN_SEVERITY = "High"


def _severity_rank(severity: str) -> int:
    try:
        return SEVERITY_ORDER[severity]
    except KeyError as error:
        raise ValueError(f"unknown severity: {severity!r}") from error


def poc_required(severity: str | None) -> bool:
    """Return whether a confirmed finding needs runnable PoC evidence to report."""
    return severity is not None and _severity_rank(severity) >= _severity_rank(POC_REQUIRED_MIN_SEVERITY)


def _decision_map(value: Mapping[str, Mapping[str, str]]) -> Mapping[str, Mapping[str, str]]:
    nested = value.get("decisions") if isinstance(value, Mapping) else None
    if nested is not None:
        if not isinstance(nested, Mapping):
            raise ValueError("severity decisions must contain a decisions object")
        return nested
    return value


def derive_poc_required_ids(
    confirmed_ids: Iterable[str],
    severity_decisions: Mapping[str, Mapping[str, str]],
) -> list[str]:
    """Return the deterministic High/Critical projection of confirmed findings."""
    confirmed = set(confirmed_ids)
    decisions = _decision_map(severity_decisions)
    decision_ids = set(decisions)
    if decision_ids != confirmed:
        raise ValueError(
            "severity decision IDs do not match confirmed IDs: "
            f"missing={sorted(confirmed - decision_ids)} extra={sorted(decision_ids - confirmed)}"
        )
    required: list[str] = []
    for canonical_id in sorted(confirmed):
        decision = decisions[canonical_id]
        if not isinstance(decision, Mapping):
            raise ValueError(f"invalid severity decision for {canonical_id}")
        severity = decision.get("severity")
        if severity not in SEVERITY_ORDER:
            raise ValueError(f"invalid severity for {canonical_id}: {severity!r}")
        if poc_required(severity):
            required.append(canonical_id)
    return required


def issue_candidate(severity: str | None) -> bool:
    return severity is not None and _severity_rank(severity) >= SEVERITY_ORDER["Medium"]


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
