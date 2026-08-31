"""Deterministic post-resolution routing decisions."""

from __future__ import annotations

from typing import Any


def effective_owner_domain(route: dict[str, Any], active_domains: set[str]) -> str | None:
    """Return the stable owner for a route after Domain resolution."""
    active = sorted(set(route.get("domains", [])) & active_domains)
    if not active:
        return None
    owner = route.get("owner_domain")
    return owner if owner in active else active[0]


def resolved_routes(
    manifest: dict[str, Any],
    domain_resolution: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Resolve active routes and effective owners without mutating the manifest."""
    selected_domains = {entry["domain"] for entry in manifest.get("selected_domains", [])}
    deferred_domains = {entry["domain"] for entry in manifest.get("deferred_domains", [])}
    active_domains = set(selected_domains)
    if domain_resolution is not None:
        active_domains |= {
            domain
            for domain, resolution in domain_resolution.get("domains", {}).items()
            if domain in deferred_domains
            and isinstance(resolution, dict)
            and resolution.get("status") == "PRESENT"
        }

    routes: list[dict[str, Any]] = []
    for bucket in ("selected", "deferred"):
        for route in manifest.get(bucket, []):
            owner = effective_owner_domain(route, active_domains)
            if owner is not None:
                routes.append({**route, "owner_domain": owner})
    return routes
