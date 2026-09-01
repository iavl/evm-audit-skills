#!/usr/bin/env python3
"""Keep supported artifact versions aligned with their schemas and emitters."""

from __future__ import annotations

import json
import re
import unittest

from helpers import ROOT, build_manifest, review_inputs, synthetic_feature_map
from scripts.render_runtime import runtime_metadata
from scripts.review_ledger import checkpoint
from evm_audit_runtime.versions import SCHEMA_VERSIONS


class VersionTests(unittest.TestCase):
    def test_schema_ids_and_declared_constants_do_not_drift(self) -> None:
        for path in sorted((ROOT / "schemas").glob("*.schema.json")):
            schema = json.loads(path.read_text(encoding="utf-8"))
            match = re.fullmatch(r"urn:evm-audit-skills:([^:]+):v(\d+)", schema["$id"])
            self.assertIsNotNone(match, path.name)
            name, version = match.groups()
            with self.subTest(schema=path.name):
                self.assertEqual(SCHEMA_VERSIONS[name], int(version))
                declared = schema.get("properties", {}).get("schema_version", {}).get("const")
                if declared is not None:
                    self.assertEqual(declared, SCHEMA_VERSIONS[name])

    def test_emitters_use_current_versions(self) -> None:
        registry, _, _, manifest = build_manifest()
        screen, domain_context, snapshot = review_inputs(manifest)
        self.assertEqual(synthetic_feature_map()["schema_version"], SCHEMA_VERSIONS["feature-map"])
        self.assertEqual(manifest["schema_version"], SCHEMA_VERSIONS["routing-manifest"])
        self.assertEqual(checkpoint(manifest, snapshot)["schema_version"], SCHEMA_VERSIONS["review-record"])
        metadata = runtime_metadata(manifest, "deep", [screen["results"][0]["canonical_id"]], None, snapshot, "0" * 64)
        self.assertEqual(metadata["schema_version"], SCHEMA_VERSIONS["runtime-metadata"])
        self.assertEqual(domain_context["schema_version"], SCHEMA_VERSIONS["domain-context"])


if __name__ == "__main__":
    unittest.main()
