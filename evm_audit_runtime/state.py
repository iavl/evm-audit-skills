"""Unambiguous audit-state semantics."""

from __future__ import annotations

COMPLETE_STATES = {"COMPLETE_CLEAN", "COMPLETE_WITH_FINDINGS"}


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
