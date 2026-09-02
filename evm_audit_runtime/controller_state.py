"""Pure controller stage metadata shared by the audit CLI and tests."""

from __future__ import annotations

from typing import Any


# Retain the legacy seven-stage constant for compatibility; progress output
# uses the six public phases below.
TOTAL_STAGES = 7
TOTAL_DISPLAY_PHASES = 6
STAGE_PROGRESS: dict[str, dict[str, Any]] = {
    "RECON": {"step": 1, "label": "Project Analysis", "substage": "Recon"},
    "ROUTING": {"step": 1, "label": "Project Analysis", "substage": "Routing"},
    "DOMAIN_RESOLUTION": {"step": 2, "label": "Context Analysis", "substage": "Domain Resolution"},
    "DOMAIN_CONTEXT": {"step": 2, "label": "Context Analysis", "substage": "Domain Context"},
    "SCREEN": {"step": 3, "label": "Initial Review"},
    "DEEP_REVIEW": {"step": 4, "label": "Deep Audit"},
    "PROOF": {"step": 5, "label": "Vulnerability Validation"},
    "REPORT": {"step": 6, "label": "Final Report"},
}


def progress_metadata(stage_name: str, *, summary: str | None = None) -> dict[str, Any]:
    try:
        metadata = STAGE_PROGRESS[stage_name]
    except KeyError as exc:
        raise ValueError(f"unknown audit stage: {stage_name}") from exc
    return {
        "step": metadata["step"],
        "total": TOTAL_DISPLAY_PHASES,
        "label": metadata["label"],
        "summary": summary or f"{metadata['label']} stage",
    }


def display_stage(name: str) -> str:
    return progress_metadata(name)["label"]
