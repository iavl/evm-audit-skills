"""Codex-only execution policy for audit stages."""

from __future__ import annotations

from copy import deepcopy
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evm_audit_runtime.versions import CODEX_MODEL_PROFILE_VERSION

try:
    from audit_artifacts import atomic_write_json
except ImportError:  # pragma: no cover
    from scripts.audit_artifacts import atomic_write_json


STAGES = (
    "RECON",
    "ROUTING",
    "DOMAIN_RESOLUTION",
    "DOMAIN_CONTEXT",
    "SCREEN",
    "DEEP_REVIEW",
    "PROOF",
    "REPORT",
)
CODEX_MODELS = ("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol")
REASONING_EFFORTS = ("none", "low", "medium", "high", "xhigh", "max")


DEFAULT_CODEX_MODEL_PROFILE: dict[str, Any] = {
    "schema_version": CODEX_MODEL_PROFILE_VERSION,
    "provider": "codex",
    "profile_name": "default-balanced-audit",
    "stages": {
        "RECON": {"model": "gpt-5.6-luna", "reasoning_effort": "max"},
        "ROUTING": {"model": "gpt-5.6-luna", "reasoning_effort": "max"},
        "DOMAIN_RESOLUTION": {"model": "gpt-5.6-terra", "reasoning_effort": "medium"},
        "DOMAIN_CONTEXT": {"model": "gpt-5.6-terra", "reasoning_effort": "medium"},
        "SCREEN": {"model": "gpt-5.6-terra", "reasoning_effort": "high"},
        "DEEP_REVIEW": {"model": "gpt-5.6-sol", "reasoning_effort": "high"},
        "PROOF": {"model": "gpt-5.6-sol", "reasoning_effort": "max"},
        "REPORT": {"model": "gpt-5.6-terra", "reasoning_effort": "medium"},
    },
}


def default_profile() -> dict[str, Any]:
    return deepcopy(DEFAULT_CODEX_MODEL_PROFILE)


def validate_profile(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("Codex model profile must be an object")
    if set(value) != {"schema_version", "provider", "profile_name", "stages"}:
        raise ValueError("Codex model profile has unexpected or missing fields")
    if isinstance(value["schema_version"], bool) or value["schema_version"] != CODEX_MODEL_PROFILE_VERSION:
        raise ValueError(f"Codex model profile schema_version must be {CODEX_MODEL_PROFILE_VERSION}")
    if value["provider"] != "codex":
        raise ValueError("Codex model profile provider must be codex")
    if not isinstance(value["profile_name"], str) or not value["profile_name"].strip():
        raise ValueError("Codex model profile profile_name must be non-empty")
    stages = value["stages"]
    if not isinstance(stages, dict) or set(stages) != set(STAGES):
        raise ValueError(f"Codex model profile stages must be exactly {', '.join(STAGES)}")
    for stage in STAGES:
        entry = stages[stage]
        if not isinstance(entry, dict) or set(entry) != {"model", "reasoning_effort"}:
            raise ValueError(f"Codex model profile {stage} must contain model and reasoning_effort")
        if entry["model"] not in CODEX_MODELS:
            raise ValueError(f"{stage}: unsupported Codex model {entry['model']!r}")
        if entry["reasoning_effort"] not in REASONING_EFFORTS:
            raise ValueError(f"{stage}: invalid reasoning effort {entry['reasoning_effort']!r}")


def load_profile(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc.msg}") from exc
    validate_profile(value)
    return value


def write_profile(path: Path, profile: dict[str, Any]) -> dict[str, Any]:
    validate_profile(profile)
    atomic_write_json(path, profile)
    return profile


def write_default_profile(path: Path) -> dict[str, Any]:
    return write_profile(path, default_profile())


def global_profile_path() -> Path:
    return Path.home() / ".codex" / "evm-audit-model-profile.json"


def load_global_profile(path: Path | None = None) -> dict[str, Any] | None:
    path = path or global_profile_path()
    return load_profile(path) if path.exists() else None


def init_global_profile(path: Path | None = None) -> dict[str, Any]:
    path = path or global_profile_path()
    if path.exists():
        raise ValueError(f"refusing to overwrite existing global Codex profile: {path}")
    return write_default_profile(path)


def stage_model(profile: dict[str, Any], stage: str) -> dict[str, str]:
    validate_profile(profile)
    if stage not in STAGES:
        raise ValueError(f"unknown Codex audit stage: {stage}")
    return dict(profile["stages"][stage])


def compact_summary(profile: dict[str, Any]) -> str:
    validate_profile(profile)
    return "\n".join(
        f"{stage:<20} {profile['stages'][stage]['model']:<15} {profile['stages'][stage]['reasoning_effort']}"
        for stage in STAGES
    )
