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
    "out",
    "venv",
}
BUILD_CONFIG_NAMES = {
    "foundry.toml",
    "forge.lock",
    "remappings.txt",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
}
DEPENDENCY_LOCK_NAMES = {"forge.lock", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"}
DEPENDENCY_METADATA_NAMES = DEPENDENCY_LOCK_NAMES | {".gitmodules"}
DEFAULT_DEPENDENCY_ROOTS = {"lib", "node_modules"}
DEPENDENCY_ROOTS = DEFAULT_DEPENDENCY_ROOTS
NON_SOURCE_PARTS = DEFAULT_EXCLUDED_PARTS | {"build"}


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


def _matches(path: Path, patterns: Iterable[str]) -> bool:
    return any(path.match(pattern) for pattern in patterns)


def _excluded(
    relative: str,
    patterns: Iterable[str],
    include_patterns: Iterable[str] = (),
    dependency_roots: Iterable[str] = DEFAULT_DEPENDENCY_ROOTS,
) -> bool:
    path = Path(relative)
    if any(part in DEFAULT_EXCLUDED_PARTS for part in path.parts):
        return True
    if _matches(path, patterns):
        return True
    roots = set(dependency_roots)
    return bool(path.parts and path.parts[0] in roots and not _matches(path, include_patterns))


def scope_inventory(
    root: Path,
    exclusions: Iterable[str] = (),
    include_patterns: Iterable[str] = (),
    dependency_roots: Iterable[str] = DEFAULT_DEPENDENCY_ROOTS,
) -> tuple[list[str], list[str]]:
    patterns = tuple(sorted({pattern.strip() for pattern in exclusions if pattern.strip()}))
    includes = tuple(sorted({pattern.strip() for pattern in include_patterns if pattern.strip()}))
    dependency_roots = tuple(sorted({root.strip() for root in dependency_roots if root.strip()}))
    if root.is_file():
        if root.suffix != ".sol":
            raise ValueError(f"audit scope file must be Solidity: {root}")
        relative = root.name
        if _excluded(relative, patterns, includes, dependency_roots):
            raise ValueError(f"audit scope excludes its only Solidity file: {root}")
        return [relative], []

    included: list[str] = []
    excluded: list[str] = []
    for path in sorted(root.rglob("*.sol")):
        relative = path.relative_to(root).as_posix()
        (excluded if _excluded(relative, patterns, includes, dependency_roots) else included).append(relative)
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


def _compilation_sources(root: Path) -> list[Path]:
    return [
        path
        for path in sorted(root.rglob("*.sol"))
        if not any(part in NON_SOURCE_PARTS for part in path.relative_to(root).parts)
    ]


def _selected_compilation_sources(root: Path, compilation_files: Iterable[str]) -> list[Path]:
    selected: list[Path] = []
    for relative in sorted(set(compilation_files)):
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError as error:
            raise ValueError(f"compilation file is outside build root: {relative}") from error
        if path.suffix != ".sol" or not path.is_file():
            raise ValueError(f"compilation file is not an existing Solidity file: {relative}")
        selected.append(path)
    return selected


def _build_configs(root: Path, dependency_roots: Iterable[str]) -> list[Path]:
    roots = set(dependency_roots)
    return [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and (path.name in BUILD_CONFIG_NAMES or path.name == ".gitmodules" or path.name.startswith("hardhat.config."))
        and not any(part in NON_SOURCE_PARTS for part in path.relative_to(root).parts)
        and (not path.relative_to(root).parts or path.relative_to(root).parts[0] not in roots)
    ]


def _compilation_digest(
    audit: str,
    dependency: str,
    build: str,
    compiler_version: str | None,
    compiler_versions: Iterable[str] | None = None,
) -> str:
    versions = sorted(set(compiler_versions or (() if compiler_version is None else (compiler_version,))))
    values = (audit, dependency, build, "\0".join(versions))
    return hashlib.sha256(b"\0".join(value.encode("utf-8") for value in values)).hexdigest()


def _submodule_commits(root: Path, dependency_roots: Iterable[str]) -> str:
    try:
        probe = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        raise ValueError("cannot inspect Git dependency lineage: git executable is unavailable") from error
    if probe.returncode != 0 or probe.stdout.strip().lower() != "true":
        return "NO_GIT_WORKTREE"
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-s", "--", *sorted(dependency_roots)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        raise ValueError("cannot inspect Git dependency lineage: git executable is unavailable") from error
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or f"exit={result.returncode}"
        raise ValueError(f"cannot inspect Git submodule entries under build root {root}: {detail}")
    gitlinks = sorted(line.strip() for line in result.stdout.splitlines() if line.startswith("160000 "))
    return "\n".join(gitlinks) if gitlinks else "NO_GITLINKS"


def resolve_build_root(target: Path, build_root: Path | None = None) -> Path:
    """Resolve the compilation project independently from the audit scope."""
    target = target.resolve()
    if build_root is not None:
        resolved = build_root.resolve()
        if not resolved.is_dir():
            raise ValueError(f"build root must be a directory: {resolved}")
        try:
            target.relative_to(resolved)
        except ValueError as error:
            raise ValueError("audit root must be inside build root") from error
        return resolved
    start = target if target.is_dir() else target.parent
    for candidate in (start, *start.parents):
        if (
            (candidate / "foundry.toml").is_file()
            or (candidate / "package.json").is_file()
            or (candidate / "remappings.txt").is_file()
            or any(candidate.glob("hardhat.config.*"))
        ):
            return candidate
    # No marker means the scope itself (or a standalone file's parent) is the conservative fallback.
    return start


def compilation_digests(
    root: Path,
    source_files: Iterable[str],
    compiler_version: str | None = None,
    *,
    build_root: Path | None = None,
    dependency_roots: Iterable[str] = DEFAULT_DEPENDENCY_ROOTS,
    compilation_files: Iterable[str] | None = None,
    compiler_versions: Iterable[str] | None = None,
) -> dict[str, str]:
    """Fingerprint audit scope and the complete selected compilation context separately."""
    source_files = tuple(source_files)
    audit_root = root.resolve()
    compilation_root = resolve_build_root(audit_root, build_root)
    try:
        audit_root.relative_to(compilation_root)
    except ValueError as error:
        raise ValueError("audit root must be inside build root") from error
    audit = source_digest(audit_root, source_files)
    compilation_sources = (
        _selected_compilation_sources(compilation_root, compilation_files)
        if compilation_files is not None
        else _compilation_sources(compilation_root)
    )
    audit_paths = {
        (audit_root if audit_root.is_file() else audit_root / relative).resolve()
        for relative in source_files
    }
    dependency_sources = [path for path in compilation_sources if path.resolve() not in audit_paths]
    configs = _build_configs(compilation_root, dependency_roots)
    dependencies = [path for path in configs if path.name in DEPENDENCY_METADATA_NAMES] + dependency_sources
    dependency_files = _digest_files(compilation_root, sorted(set(dependencies)))
    dependency = hashlib.sha256((dependency_files + "\0" + _submodule_commits(compilation_root, dependency_roots)).encode("utf-8")).hexdigest()
    build_configs = [path for path in configs if path.name not in DEPENDENCY_METADATA_NAMES]
    build = _digest_files(compilation_root, build_configs)
    if compiler_versions is None and compiler_version is not None:
        compiler_versions = (compiler_version,)
    compilation = _compilation_digest(audit, dependency, build, compiler_version, compiler_versions)
    return {"audit_source_digest": audit, "dependency_digest": dependency, "build_config_digest": build, "compilation_input_digest": compilation}
