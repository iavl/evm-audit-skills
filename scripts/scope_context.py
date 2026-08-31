#!/usr/bin/env python3
"""Deterministic Solidity audit-scope inventory and digest helpers."""

from __future__ import annotations

import hashlib
import subprocess
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
BUILD_CONFIG_NAMES = {"foundry.toml", "remappings.txt", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"}
DEPENDENCY_LOCK_NAMES = {"forge.lock", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"}
DEPENDENCY_METADATA_NAMES = DEPENDENCY_LOCK_NAMES | {".gitmodules"}
DEPENDENCY_ROOTS = {"lib", "node_modules"}
NON_SOURCE_PARTS = {".git", "artifacts", "build", "cache", "deployments", "fizz_data", "out", "venv"}


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


def _dependency_sources(root: Path) -> list[Path]:
    sources: list[Path] = []
    for dependency_root in sorted(DEPENDENCY_ROOTS):
        base = root / dependency_root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.sol")):
            relative_parts = path.relative_to(root).parts
            if not any(part in NON_SOURCE_PARTS for part in relative_parts):
                sources.append(path)
    return sources


def _compilation_digest(
    audit: str,
    dependency: str,
    build: str,
    compiler_version: str | None,
) -> str:
    values = (audit, dependency, build, compiler_version or "")
    return hashlib.sha256(b"\0".join(value.encode("utf-8") for value in values)).hexdigest()


def _submodule_commits(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-s", "--", "lib", "node_modules"],
        capture_output=True,
        text=True,
        check=False,
    )
    return "\n".join(line.strip() for line in result.stdout.splitlines() if line.startswith("160000 "))


def compilation_digests(root: Path, source_files: Iterable[str], compiler_version: str | None = None) -> dict[str, str]:
    """Fingerprint audit and resolved compilation inputs separately."""
    if root.is_file():
        audit = source_digest(root, source_files)
        empty = hashlib.sha256(b"").hexdigest()
        return {
            "audit_source_digest": audit,
            "dependency_digest": empty,
            "build_config_digest": empty,
            "compilation_input_digest": _compilation_digest(audit, empty, empty, compiler_version),
        }
    configs = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and (path.name in BUILD_CONFIG_NAMES or path.name in {".gitmodules"} or path.name.startswith("hardhat.config."))
        and not any(part in DEPENDENCY_ROOTS for part in path.relative_to(root).parts)
        and not _excluded(path.relative_to(root).as_posix(), ())
    ]
    dependencies = [
        path for path in configs if path.name in DEPENDENCY_METADATA_NAMES
    ] + _dependency_sources(root)
    build_configs = [path for path in configs if path.name not in DEPENDENCY_METADATA_NAMES]
    audit = source_digest(root, source_files)
    dependency_files = _digest_files(root, sorted(set(dependencies)))
    dependency = hashlib.sha256((dependency_files + "\0" + _submodule_commits(root)).encode("utf-8")).hexdigest()
    build = _digest_files(root, build_configs)
    compilation = _compilation_digest(audit, dependency, build, compiler_version)
    return {"audit_source_digest": audit, "dependency_digest": dependency, "build_config_digest": build, "compilation_input_digest": compilation}
