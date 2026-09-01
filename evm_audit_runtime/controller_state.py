"""Pure controller stage metadata shared by the audit CLI and tests."""

from __future__ import annotations

from typing import Any


TOTAL_STAGES = 7
STAGE_PROGRESS: dict[str, dict[str, Any]] = {
    "RECON": {"step": 1, "label": "RECON"},
    "ROUTING": {"step": 2, "label": "ROUTING"},
    "DOMAIN_RESOLUTION": {"step": 3, "label": "DOMAIN RESOLUTION"},
    "DOMAIN_CONTEXT": {"step": 3, "label": "DOMAIN CONTEXT"},
    "SCREEN": {"step": 4, "label": "SCREEN"},
    "DEEP_REVIEW": {"step": 5, "label": "DEEP REVIEW"},
    "PROOF": {"step": 6, "label": "PROOF"},
    "REPORT": {"step": 7, "label": "REPORT"},
}


def progress_metadata(stage_name: str, *, summary: str | None = None) -> dict[str, Any]:
    try:
        metadata = STAGE_PROGRESS[stage_name]
    except KeyError as exc:
        raise ValueError(f"unknown audit stage: {stage_name}") from exc
    return {
        "step": metadata["step"],
        "total": TOTAL_STAGES,
        "label": metadata["label"],
        "summary": summary or f"{metadata['label']} stage",
    }


def display_stage(name: str) -> str:
    return progress_metadata(name)["label"] if name in STAGE_PROGRESS else name.replace("_", " ")
