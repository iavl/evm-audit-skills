"""Feature and Recon-detector registry validation."""

from __future__ import annotations

import json
from pathlib import Path

try:
    from recon import load_detector_config
except ImportError:  # pragma: no cover
    from scripts.recon import load_detector_config


def validate_detector_registry(root: Path, feature_names: set[str]) -> list[str]:
    path = root / "data" / "feature-detectors.json"
    if not path.exists():
        return [f"missing feature detector registry: {path}"]
    try:
        load_detector_config(root, feature_names)
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as error:
        return [f"{path}: invalid detector registry: {error}"]
    return []
