"""Unambiguous audit-state semantics."""

from __future__ import annotations

from typing import Any

COMPLETE_STATES = {"COMPLETE_CLEAN", "COMPLETE_WITH_FINDINGS"}


def review_lifecycle_errors(previous: dict[str, Any] | None, current: dict[str, Any]) -> list[str]:
    if previous is None:
        errors: list[str] = []
        if current.get("review_stage") != "DEEP_REVIEW":
            errors.append(
                f"{current.get('canonical_id')}: first review revision must use review_stage=DEEP_REVIEW"
            )
        if current.get("status") not in {"NOT_APPLICABLE", "REVIEWED_SAFE", "SUSPICIOUS"}:
            errors.append(
                f"{current.get('canonical_id')}: first review status {current.get('status')} is not a valid Deep resolution"
            )
        return errors
    if previous.get("status") != "SUSPICIOUS":
        return [
            f"{current.get('canonical_id')}: revision {current.get('revision')} cannot follow "
            f"{previous.get('status')}"
        ]
    errors = []
    if current.get("review_stage") != "PROOF":
        errors.append(f"{current.get('canonical_id')}: follow-up review must use review_stage=PROOF")
    if current.get("status") not in {"REVIEWED_SAFE", "SUSPICIOUS", "CONFIRMED"}:
        errors.append(
            f"{current.get('canonical_id')}: follow-up status {current.get('status')} is not a valid proof resolution"
        )
    return errors


def derive_status(
    *,
    invalid: bool,
    coverage: bool,
    domain: bool,
    context: bool,
    review: bool,
    confirmed: bool,
) -> str:
    if invalid:
        return "INVALID_SNAPSHOT"
    if coverage:
        return "INCOMPLETE_COVERAGE"
    if domain:
        return "INCOMPLETE_DOMAIN_ROUTING"
    if context:
        return "INCOMPLETE_CONTEXT"
    if review:
        return "INCOMPLETE_REVIEW"
    return "COMPLETE_WITH_FINDINGS" if confirmed else "COMPLETE_CLEAN"
