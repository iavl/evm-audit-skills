#!/usr/bin/env python3
"""Regression checks for shared model-facing limits."""

from __future__ import annotations

import unittest

from evm_audit_runtime.limits import MAX_CODE_CONTEXT_EDGES, MAX_CODE_CONTEXT_NODES, MAX_SCREEN_GATE_LENGTH
from evm_audit_runtime.code_index import lookup


class LimitTests(unittest.TestCase):
    def test_code_context_default_is_the_shared_cap(self) -> None:
        self.assertEqual(lookup.__kwdefaults__["max_nodes"], MAX_CODE_CONTEXT_NODES)
        self.assertEqual(lookup.__kwdefaults__["max_edges"], MAX_CODE_CONTEXT_EDGES)

    def test_screen_gate_limit_is_positive(self) -> None:
        self.assertGreater(MAX_SCREEN_GATE_LENGTH, 0)


if __name__ == "__main__":
    unittest.main()
