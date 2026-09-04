#!/usr/bin/env python3
"""Run one explicit unittest layer with timing and a coarse budget warning."""

from __future__ import annotations

import os
import sys
import time
import unittest
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
SCRIPT_DIR = str(ROOT / "scripts")
sys.path[:] = [path for path in sys.path if path != SCRIPT_DIR]
for path in (str(TESTS), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from scripts.test_timing import TimingRunner, run as run_timed_discovery


RUNTIME_CONTROLLER_TESTS = frozenset(
    {
        "test_runtime.RuntimeTests.test_checkpoint_cli_has_no_cross_snapshot_option",
        "test_runtime.RuntimeTests.test_selector_has_no_domain_context_option",
        "test_runtime.RuntimeTests.test_selector_single_snapshot_writes_manifest_and_runtime",
    }
)

PLATFORM_TESTS = frozenset(
    {
        "test_audit_run.AuditRunTests.test_concurrent_report_publications_leave_pointer_and_convenience_copies_consistent",
        "test_audit_run.AuditRunTests.test_report_lock_does_not_silently_disable_on_windows",
        "test_audit_run.AuditRunTests.test_report_lock_is_cross_process",
        "test_runtime.RuntimeTests.test_ledger_does_not_silently_disable_locking",
        "test_runtime.RuntimeTests.test_multiprocess_ledger_writes_are_serialized_and_durable",
    }
)

FAST_MODULES = (
    "test_generation",
    "test_knowledge",
    "test_limits",
    "test_plan_hardening",
    "test_reporting",
    "test_routing",
    "test_runtime",
    "test_versions",
)

CONTROLLER_MODULES = (
    "test_audit_run",
    "test_codex_model_profile",
    "test_hardening",
    "test_lifecycle",
    "test_observability",
    "test_poc_verification",
    "test_runtime",
)
CONTROLLER_REPORTING_MODULES = ("test_audit_run", "test_hardening")
CONTROLLER_LIFECYCLE_MODULES = (
    "test_codex_model_profile",
    "test_lifecycle",
    "test_observability",
    "test_poc_verification",
    "test_repository_trust",
    "test_review_ledger_commit",
    "test_runtime",
)

SLITHER_MODULES = (
    "test_code_context",
    "test_compilation_lineage",
    "test_packaging",
    "test_recon",
)

PLATFORM_MODULES = ("test_audit_run", "test_runtime")


def _tests(suite: unittest.TestSuite) -> Iterable[unittest.case.TestCase]:
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from _tests(test)
        else:
            yield test


def _load(
    modules: Iterable[str],
    *,
    include: frozenset[str] | None = None,
    exclude: frozenset[str] = frozenset(),
) -> unittest.TestSuite:
    loader = unittest.defaultTestLoader
    selected = unittest.TestSuite()
    for module in modules:
        for test in _tests(loader.loadTestsFromName(module)):
            test_id = test.id()
            if include is not None and test_id not in include:
                continue
            if test_id in exclude:
                continue
            selected.addTest(test)
    if selected.countTestCases() == 0:
        raise SystemExit("test layer selected no tests")
    return selected


def _runtime_fast_tests() -> frozenset[str]:
    return frozenset(
        test.id()
        for test in _tests(_load(("test_runtime",)))
        if test.id() not in RUNTIME_CONTROLLER_TESTS | PLATFORM_TESTS
    )


def _write_summary(name: str, result: object, elapsed: float, budget: float | None) -> None:
    timings = sorted(getattr(result, "timings", []), key=lambda item: item["seconds"], reverse=True)
    lines = [f"{name}: {getattr(result, 'testsRun', 0)} tests in {elapsed:.3f}s"]
    lines.append("slowest 10:")
    lines.extend(f"- {item['seconds']:.3f}s {item['test']}" for item in timings[:10])
    if budget is not None and elapsed > budget:
        lines.append(f"WARNING: {name} exceeded the {budget:.0f}s budget")
    output = "\n".join(lines)
    print(output)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as summary:
            summary.write(f"## {name}\n\n{output}\n")


def run_suite(
    name: str,
    modules: Iterable[str],
    *,
    include: frozenset[str] | None = None,
    exclude: frozenset[str] = frozenset(),
    budget: float | None = None,
) -> int:
    suite = _load(modules, include=include, exclude=exclude)
    started = time.perf_counter()
    result = TimingRunner(stream=sys.stderr, verbosity=1).run(suite)
    _write_summary(name, result, time.perf_counter() - started, budget)
    return 0 if result.wasSuccessful() else 1


def run_fast() -> int:
    return run_suite(
        "fast-unit",
        FAST_MODULES,
        exclude=RUNTIME_CONTROLLER_TESTS | PLATFORM_TESTS,
        budget=45,
    )


def run_controller(shard: str | None = None) -> int:
    if shard == "reporting":
        modules = CONTROLLER_REPORTING_MODULES
    elif shard == "lifecycle":
        modules = CONTROLLER_LIFECYCLE_MODULES
    else:
        modules = CONTROLLER_MODULES
    return run_suite(
        f"controller-{shard or 'integration'}",
        modules,
        include=None,
        exclude=_runtime_fast_tests() | PLATFORM_TESTS,
        budget=180,
    )


def run_slither() -> int:
    return run_suite("slither-integration", SLITHER_MODULES, budget=180)


def run_platform() -> int:
    return run_suite("platform-concurrency", PLATFORM_MODULES, include=PLATFORM_TESTS, budget=180)


def run_all() -> int:
    return run_timed_discovery()
