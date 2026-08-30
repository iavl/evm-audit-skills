#!/usr/bin/env python3
"""Emit reproducible tool and knowledge provenance for an audit artifact."""
from __future__ import annotations
import json
import platform
import subprocess

def version(command: list[str]) -> str | None:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return result.stdout.strip().splitlines()[0] if result.returncode == 0 and result.stdout.strip() else None

def main() -> int:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip() or None
    print(json.dumps({"python": platform.python_version(), "slither": version(["slither", "--version"]), "solc": version(["solc", "--version"]), "foundry": version(["forge", "--version"]), "knowledge_commit": commit}, sort_keys=True))
    return 0

if __name__ == "__main__": raise SystemExit(main())
