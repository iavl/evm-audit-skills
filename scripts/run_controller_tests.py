#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.run_test_suite import run_controller


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--shard",
        choices=("lifecycle", "reporting", "reporting-publication", "reporting-authoring"),
    )
    raise SystemExit(run_controller(parser.parse_args().shard))
