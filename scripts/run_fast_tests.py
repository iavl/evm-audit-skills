#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.run_test_suite import run_fast


if __name__ == "__main__":
    raise SystemExit(run_fast())
