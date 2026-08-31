"""Generated checklist coverage validation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    from generate_checklists import check_outputs
except ImportError:  # pragma: no cover
    from scripts.generate_checklists import check_outputs


CANONICAL_ID_RE = re.compile(r"\[([A-Z0-9]+(?:-[A-Z0-9]+)+-\d{3})\]")
ITEM_RE = re.compile(r"^- \[ \] \*\*(.*?)\*\*")


def validate_generated_registry(root: Path, registry: dict[str, Any]) -> list[str]:
    errors = check_outputs(registry, root)
    expected = {
        check["canonical_id"]: len(check.get("domains", []))
        for check in registry.get("checks", [])
    }
    actual: dict[str, int] = {}
    for path in sorted(root.glob("skills/evm-audit-*/references/checklist.md")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.startswith("- [ ]"):
                continue
            item = ITEM_RE.match(line)
            if not item:
                errors.append(f"{path}:{line_number}: malformed checklist item")
                continue
            match = CANONICAL_ID_RE.search(item.group(1))
            if match:
                actual[match.group(1)] = actual.get(match.group(1), 0) + 1
            else:
                errors.append(f"{path}:{line_number}: missing canonical ID")
    if actual != expected:
        errors.append(f"generated checklist coverage differs from registry (expected={expected}, actual={actual})")
    return errors
