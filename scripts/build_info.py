#!/usr/bin/env python3
"""Emit reproducible tool and knowledge provenance for an audit artifact."""
from __future__ import annotations
import json
import hashlib
import platform
import subprocess
from pathlib import Path

def version(command: list[str]) -> str | None:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    lines = result.stdout.strip().splitlines()
    return next((line.strip() for line in lines if "Version:" in line), lines[0].strip())

def main() -> int:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip() or None
    lock = Path(__file__).resolve().parents[1] / "requirements-runtime.lock"
    lock_digest = hashlib.sha256(lock.read_bytes()).hexdigest() if lock.exists() else None
    print(json.dumps({"python": platform.python_version(), "slither": version(["slither", "--version"]), "solc": version(["solc", "--version"]), "foundry": version(["forge", "--version"]), "knowledge_commit": commit, "requirements_lock_sha256": lock_digest}, sort_keys=True))
    return 0

if __name__ == "__main__": raise SystemExit(main())
