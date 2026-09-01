"""Domain configuration validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any


ABSENCE_EVIDENCE = {"scope", "inheritance", "interface", "dependency", "deployment"}
REQUIRED_FIELDS = {
    "id", "name", "checklist_title", "description", "surface_features", "related_domains",
    "always_screen", "required_context", "review_requirements", "trusted_absence_policy",
}
OPTIONAL_FIELDS = {"dependency_presence_sufficient"}


def validate_domain_configs(
    root: Path,
    configs: dict[str, dict[str, Any]],
    feature_names: set[str],
) -> list[str]:
    errors: list[str] = []
    valid_domains = set(configs)
    for domain, config in configs.items():
        prefix = f"{root / 'domains'}:{domain}"
        if set(config) - REQUIRED_FIELDS - OPTIONAL_FIELDS or not REQUIRED_FIELDS <= set(config):
            errors.append(f"{prefix}: fields must include {sorted(REQUIRED_FIELDS)}")
        if not all(isinstance(config.get(field), str) and config[field].strip() for field in ("id", "name", "checklist_title", "description")):
            errors.append(f"{prefix}: id/name/checklist_title/description must be non-empty strings")
        if not isinstance(config.get("surface_features"), list) or not config["surface_features"]:
            errors.append(f"{prefix}: surface_features must be a non-empty list")
        if not isinstance(config.get("related_domains"), list):
            errors.append(f"{prefix}: related_domains must be a list")
        if not isinstance(config.get("always_screen"), bool):
            errors.append(f"{prefix}: always_screen must be boolean")
        if "dependency_presence_sufficient" in config and not isinstance(config["dependency_presence_sufficient"], bool):
            errors.append(f"{prefix}: dependency_presence_sufficient must be boolean")
        required_context = config.get("required_context")
        if not isinstance(required_context, list) or not required_context:
            errors.append(f"{prefix}: required_context must be a non-empty list")
        else:
            keys: set[str] = set()
            for value in required_context:
                if not isinstance(value, dict) or set(value) != {"key", "required", "description"} or not isinstance(value.get("key"), str) or not value["key"] or not isinstance(value.get("required"), bool) or not isinstance(value.get("description"), str) or not value["description"]:
                    errors.append(f"{prefix}: malformed required_context entry {value!r}")
                    continue
                if value["key"] in keys:
                    errors.append(f"{prefix}: duplicate required_context key {value['key']}")
                keys.add(value["key"])
        if not isinstance(config.get("review_requirements"), list) or not config["review_requirements"] or any(not isinstance(value, str) or not value.strip() for value in config["review_requirements"]):
            errors.append(f"{prefix}: review_requirements must be a non-empty string list")
        policy = config.get("trusted_absence_policy")
        if not isinstance(policy, dict) or set(policy) != {"requires_complete_scope", "allowed_evidence"} or policy.get("requires_complete_scope") is not True:
            errors.append(f"{prefix}: trusted_absence_policy must require complete scope")
        elif not isinstance(policy.get("allowed_evidence"), list) or not policy["allowed_evidence"] or any(kind not in ABSENCE_EVIDENCE for kind in policy["allowed_evidence"]):
            errors.append(f"{prefix}: trusted_absence_policy.allowed_evidence is invalid")
        if not (root / "skills" / domain / "SKILL.md").exists():
            errors.append(f"{prefix}: missing skill directory")
        unknown_features = sorted(set(config.get("surface_features", [])) - feature_names)
        unknown_related = sorted(set(config.get("related_domains", [])) - valid_domains)
        if unknown_features:
            errors.append(f"{prefix}: unknown surface features {unknown_features}")
        if unknown_related:
            errors.append(f"{prefix}: unknown related domains {unknown_related}")
        if domain in config.get("related_domains", []):
            errors.append(f"{prefix}: domain cannot relate to itself")
    return errors
