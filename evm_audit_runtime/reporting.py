"""Pure report-admission decisions."""

from __future__ import annotations

SEVERITY_ORDER = {"Informational": 0, "Low": 1, "Medium": 2, "High": 3, "Critical": 4}


def issue_candidate(severity: str | None) -> bool:
    return severity is not None and SEVERITY_ORDER[severity] >= SEVERITY_ORDER["Medium"]
