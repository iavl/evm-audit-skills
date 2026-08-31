#!/usr/bin/env python3
"""Tests for canonical-to-generated checklist rendering."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.generate_checklists import load_domains, write_outputs

from helpers import ROOT


class GenerationTests(unittest.TestCase):
    def test_generated_markdown_is_current(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/generate_checklists.py", "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_generator_is_a_pure_renderer(self) -> None:
        registry_path = ROOT / "data/canonical-checks.json"
        before = hashlib.sha256(registry_path.read_bytes()).hexdigest()
        result = subprocess.run(
            [sys.executable, "scripts/generate_checklists.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(before, hashlib.sha256(registry_path.read_bytes()).hexdigest())

    def test_domain_configuration_drives_generated_skills(self) -> None:
        domains = load_domains(ROOT)
        skill_paths = sorted((ROOT / "skills").glob("evm-audit-*/SKILL.md"))
        self.assertEqual(
            {path.parent.name for path in skill_paths},
            set(domains) | {"evm-audit-master"},
        )
        checklist_paths = sorted((ROOT / "skills").glob("evm-audit-*/references/checklist.md"))
        self.assertEqual({path.parent.parent.name for path in checklist_paths}, set(domains))
        for domain in domains:
            skill = (ROOT / "skills" / domain / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn(f"--domain {domain}", skill)
        for path in skill_paths:
            name = next(line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("name: "))
            self.assertEqual(path.parent.name, name.removeprefix("name: "))

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "domains").mkdir()
            (root / "domains/example.json").write_text(
                json.dumps(
                    {
                        "id": "evm-audit-example",
                        "name": "Example",
                        "checklist_title": "Example Checklist",
                        "description": "Example domain.",
                        "surface_features": ["uses-example"],
                        "related_domains": [],
                        "always_screen": False,
                        "screening_terms": ["example"],
                        "required_context": [
                            {"key": "example_context", "required": True, "description": "example context"}
                        ],
                        "review_requirements": ["example review"],
                        "trusted_absence_policy": {
                            "requires_complete_scope": True,
                            "allowed_evidence": ["scope"],
                        },
                    }
                ),
                encoding="utf-8",
            )
            write_outputs({"checks": []}, root)
            self.assertTrue((root / "skills/evm-audit-example/SKILL.md").exists())
            self.assertTrue((root / "skills/evm-audit-example/references/checklist.md").exists())


if __name__ == "__main__":
    unittest.main()
