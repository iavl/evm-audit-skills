#!/usr/bin/env python3
"""Run the unittest discovery suite and report per-test timing."""

from __future__ import annotations

import argparse
import json
import sys
import time
import unittest
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = str(ROOT / "scripts")
sys.path[:] = [path for path in sys.path if path != SCRIPT_DIR]
for path in (str(ROOT / "tests"), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)


class TimingResult(unittest.TextTestResult):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.timings: list[dict[str, Any]] = []
        self._started: dict[int, float] = {}

    def startTest(self, test: unittest.case.TestCase) -> None:
        self._started[id(test)] = time.perf_counter()
        super().startTest(test)

    def stopTest(self, test: unittest.case.TestCase) -> None:
        started = self._started.pop(id(test), time.perf_counter())
        test_id = test.id()
        module = test_id.split(".", 1)[0]
        self.timings.append(
            {"test": test_id, "module": module, "seconds": time.perf_counter() - started}
        )
        super().stopTest(test)


class TimingRunner(unittest.TextTestRunner):
    resultclass = TimingResult


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=int, default=20, help="number of slowest tests to print")
    parser.add_argument("--json", type=Path, help="write timing data to this JSON path")
    return parser.parse_args()


def run() -> int:
    args = parse_args()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    started = time.perf_counter()
    result = TimingRunner(stream=sys.stderr, verbosity=1).run(suite)
    elapsed = time.perf_counter() - started

    module_totals: dict[str, float] = defaultdict(float)
    for timing in result.timings:
        module_totals[timing["module"]] += timing["seconds"]
    slowest = sorted(result.timings, key=lambda item: item["seconds"], reverse=True)
    payload = {
        "tests_run": result.testsRun,
        "elapsed_seconds": elapsed,
        "tests": result.timings,
        "module_totals": dict(sorted(module_totals.items(), key=lambda item: -item[1])),
        "slowest": slowest[: max(args.top, 0)],
        "failures": [test.id() for test, _ in result.failures],
        "errors": [test.id() for test, _ in result.errors],
    }
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"tests: {result.testsRun}")
    print(f"elapsed: {elapsed:.3f}s")
    print("slowest tests:")
    for timing in slowest[: max(args.top, 0)]:
        print(f"  {timing['seconds']:.3f}s {timing['test']}")
    print("module totals:")
    for module, seconds in sorted(module_totals.items(), key=lambda item: -item[1]):
        print(f"  {seconds:.3f}s {module}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(run())
