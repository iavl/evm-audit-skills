#!/usr/bin/env python3
"""Deterministic Solidity audit-scope inventory and digest helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable


DEFAULT_EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "artifacts",
    "build",
    "cache",
    "deployments",
    "fizz_data",
    "lib",
    "node_modules",
    "out",
    "venv",
}
BUILD_CONFIG_NAMES = {"foundry.toml", "remappings.txt", "forge.lock", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"}


def find_suite_root(start_path: Path) -> Path:
    """Find the suite root from a script or nested Skill path."""
    start = start_path.resolve()
    candidate = start if start.is_dir() else start.parent
    for root in (candidate, *candidate.parents):
        if all((root / name).is_dir() for name in ("data", "domains", "scripts")):
            return root
    raise ValueError(f"cannot find EVM audit suite root from {start_path}")


def resolve_scope_root(target: Path, audit_root: Path | None = None) -> Path:
    root = (audit_root or target).resolve()
    if not root.exists():
        raise ValueError(f"audit scope does not exist: {root}")
    return root


def relative_scope_path(root: Path, path: Path) -> str | None:
    path = path.resolve()
    if root.is_file():
        return root.name if path == root else None
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return None


def _excluded(relative: str, patterns: Iterable[str]) -> bool:
    path = Path(relative)
    if any(part in DEFAULT_EXCLUDED_PARTS for part in path.parts):
        return True
    return any(path.match(pattern) for pattern in patterns)


def scope_inventory(root: Path, exclusions: Iterable[str] = ()) -> tuple[list[str], list[str]]:
    patterns = tuple(sorted({pattern.strip() for pattern in exclusions if pattern.strip()}))
    if root.is_file():
        if root.suffix != ".sol":
            raise ValueError(f"audit scope file must be Solidity: {root}")
        relative = root.name
        if _excluded(relative, patterns):
            raise ValueError(f"audit scope excludes its only Solidity file: {root}")
        return [relative], []

    included: list[str] = []
    excluded: list[str] = []
    for path in sorted(root.rglob("*.sol")):
        relative = path.relative_to(root).as_posix()
        (excluded if _excluded(relative, patterns) else included).append(relative)
    if not included:
        raise ValueError(f"audit scope contains no Solidity files: {root}")
    return included, excluded


def source_digest(root: Path, files: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for relative in sorted(files):
        path = root if root.is_file() else root / relative
        data = path.read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(data)).encode("ascii"))
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
    return digest.hexdigest()


def _digest_files(root: Path, files: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(set(files)):
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        digest.update(relative.encode("utf-8") + b"\0" + data + b"\0")
    return digest.hexdigest()


def compilation_digests(root: Path, source_files: Iterable[str], compiler_version: str | None = None) -> dict[str, str]:
    """Fingerprint declared compilation inputs; this is not compiled-bytecode identity."""
    if root.is_file():
        return {
            "audit_source_digest": source_digest(root, source_files),
            "dependency_digest": hashlib.sha256(b"").hexdigest(),
            "build_config_digest": hashlib.sha256(b"").hexdigest(),
            "compilation_input_digest": hashlib.sha256((source_digest(root, source_files) + (compiler_version or "")).encode()).hexdigest(),
        }
    configs = [path for path in root.rglob("*") if path.is_file() and (path.name in BUILD_CONFIG_NAMES or path.name.startswith("hardhat.config.")) and not _excluded(path.relative_to(root).as_posix(), ())]
    dependencies = [path for path in configs if path.name in {"forge.lock", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"}]
    build_configs = [path for path in configs if path not in dependencies]
    audit = source_digest(root, source_files)
    dependency = _digest_files(root, dependencies)
    build = _digest_files(root, build_configs)
    compilation = hashlib.sha256((audit + dependency + build + (compiler_version or "")).encode()).hexdigest()
    return {"audit_source_digest": audit, "dependency_digest": dependency, "build_config_digest": build, "compilation_input_digest": compilation}
