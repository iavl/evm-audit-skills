"""Small stderr-only progress helpers for the audit runtime."""

from __future__ import annotations

import sys


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
    _emit(f"+{'-' * _WIDTH}+")
    _emit(f"|{f'EVM AUDIT :: {name}':^{_WIDTH}}|")
    _emit(f"+{'-' * _WIDTH}+")
    if step is not None:
        progress = f"[{step}/{total}]" if total is not None else f"[{step}]"
        info(f"{progress} {detail or ''}".rstrip())
    elif detail:
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
