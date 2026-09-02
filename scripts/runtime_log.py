"""Small stderr-only progress helpers for the audit runtime."""

from __future__ import annotations

import sys

from evm_audit_runtime.controller_state import STAGE_PROGRESS, progress_metadata


_WIDTH = 46
_quiet = False
_verbose = False


def configure(*, quiet: bool = False, verbose: bool = False) -> None:
    global _quiet, _verbose
    _quiet = quiet
    _verbose = verbose


def _emit(message: str, *, force: bool = False) -> None:
    if not force and _quiet:
        return
    print(message, file=sys.stderr)


def stage(name: str, *, step: int | None = None, total: int | None = None, detail: str | None = None) -> None:
    stage_name = name
    metadata = progress_metadata(stage_name)
    name = metadata["label"]
    banner_name = name.upper()
    step = metadata["step"]
    total = metadata["total"]
    _emit(f"+{'-' * _WIDTH}+")
    _emit(f"|{f'EVM AUDIT :: {banner_name}':^{_WIDTH}}|")
    _emit(f"+{'-' * _WIDTH}+")
    if step is not None:
        progress = f"[{step}/{total}]" if total is not None else f"[{step}]"
        info(f"{progress} {name}")
        substage = STAGE_PROGRESS[stage_name].get("substage")
        if _verbose and substage:
            info(f"{progress} {name} · {substage}")
    if detail:
        info(detail)


def info(message: str) -> None:
    _emit(f"  - {message}")


def success(message: str) -> None:
    _emit(f"  + {message}")


def warning(message: str) -> None:
    _emit(f"  ! {message}")


def verbose(message: str) -> None:
    if _verbose:
        _emit(f"    {message}")


def error(message: object) -> None:
    """Errors remain visible even when progress is quiet."""
    _emit(f"ERROR: {message}", force=True)
