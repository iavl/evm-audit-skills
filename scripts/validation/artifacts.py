"""Schema-file validation."""

from __future__ import annotations

import json
from pathlib import Path


def validate_artifact_schemas(root: Path) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return ["schemas: jsonschema is required; install requirements-runtime.txt"]
    errors: list[str] = []
    for path in sorted((root / "schemas").glob("*.schema.json")):
        try:
            Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, ValueError) as error:
            errors.append(f"{path}: invalid Draft 2020-12 schema: {error}")
    return errors
