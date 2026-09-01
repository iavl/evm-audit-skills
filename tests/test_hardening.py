"""Regression tests for artifact lineage and false-clean boundaries."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_artifacts import canonical_sha256, check_body_hash, derive_review_snapshot_id
from scripts.audit_run import _ensure_reporting_templates
from scripts.render_runtime import domain_context_template, domain_resolution_template, screen_results_template
from scripts.review_ledger import append
from scripts.scope_context import compilation_digests, resolve_build_root, scope_inventory
from scripts.synthesize_report import main as synthesize_main, synthesize
from scripts.validate_audit_run import validate_run

from helpers import ROOT, build_manifest


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class HardeningTests(unittest.TestCase):
    def context(self, manifest: dict, resolution: dict | None = None) -> dict:
        value = domain_context_template(manifest, resolution)
        for requirements in value["domains"].values():
            for item in requirements.values():
                item.update(
                    status="KNOWN",
                    value="fixture",
                    evidence=[{"kind": "scope", "location": "fixture", "reason": "known context"}],
                )
        return value

    def screen(self, manifest: dict, resolution: dict | None = None, *, candidate: bool) -> tuple[dict, str]:
        value = screen_results_template(manifest, resolution)
        candidate_id = value["results"][0]["canonical_id"]
        evidence = [
            {"kind": "scope", "location": "fixture", "reason": "complete scope"},
            {"kind": "source", "location": "fixture", "reason": "screen disposition"},
        ]
        for item in value["results"]:
            if candidate and item["canonical_id"] == candidate_id:
                continue
            item.update(result="NOT_APPLICABLE_CONFIRMED", scope_complete=True, evidence=evidence)
        return value, candidate_id

    def review_record(self, registry: dict, manifest: dict, canonical_id: str, *, confirmed: bool = False) -> dict:
        route = next(item for item in manifest["selected"] if item["canonical_id"] == canonical_id)
        check = next(item for item in registry["checks"] if item["canonical_id"] == canonical_id)
        value = {
            "record_type": "review",
            "schema_version": 6,
            "canonical_id": canonical_id,
            "owner_domain": route["owner_domain"],
            "check_body_hash": check_body_hash(check),
            "review_stage": "PROOF" if confirmed else "DEEP_REVIEW",
            "status": "CONFIRMED" if confirmed else "REVIEWED_SAFE",
            "applicability": "APPLICABLE - fixture",
            "code_path": "fixture entry",
            "preconditions": "fixture state",
            "exploitability": "fixture path is reachable",
            "impact": "fixture impact" if confirmed else "none",
            "proof": "deterministic fixture trace",
            "evidence": [{"kind": "trace", "location": "fixture", "reason": "deterministic trace"}],
        }
        if not confirmed:
            value["preserved_invariant"] = "fixture invariant holds"
        return value

    @staticmethod
    def context_artifact(manifest: dict) -> dict:
        return {**manifest["audit_context"], "routing_snapshot_id": manifest["routing_snapshot_id"]}

    def test_context_and_screen_mutations_stale_existing_review(self) -> None:
        registry, _, _, manifest = build_manifest()
        domain_context = self.context(manifest)
        screen, candidate_id = self.screen(manifest, candidate=True)
        context = self.context_artifact(manifest)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "review.jsonl"
            append(
                ledger,
                manifest,
                self.review_record(registry, manifest, candidate_id),
                registry,
                {candidate_id},
                domain_context=domain_context,
                screen_results=screen,
            )
            clean = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            self.assertEqual(clean["status"], "COMPLETE_CLEAN")

            first_domain = next(iter(domain_context["domains"]))
            first_key = next(iter(domain_context["domains"][first_domain]))
            domain_context["domains"][first_domain][first_key]["value"] = "changed context"
            stale_context = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            self.assertEqual(stale_context["status"], "INCOMPLETE_REVIEW")
            self.assertTrue(any("review_snapshot_id" in reason for reason in stale_context["reasons"]))

            domain_context = self.context(manifest)
            screen["results"][1]["evidence"][1]["reason"] = "changed screen evidence"
            stale_screen = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            self.assertEqual(stale_screen["status"], "INCOMPLETE_REVIEW")
            self.assertTrue(any("review_snapshot_id" in reason for reason in stale_screen["reasons"]))

    def test_review_snapshot_preserves_ordered_values_and_normalizes_set_like_results(self) -> None:
        _, _, _, manifest = build_manifest()
        domain_context = self.context(manifest)
        screen, _ = self.screen(manifest, candidate=False)
        domain = next(iter(domain_context["domains"]))
        key = next(iter(domain_context["domains"][domain]))
        domain_context["domains"][domain][key]["value"] = ["chainlink", "twap"]
        first = derive_review_snapshot_id(ROOT, manifest, None, domain_context, screen)

        reversed_context = json.loads(json.dumps(domain_context))
        reversed_context["domains"][domain][key]["value"] = ["twap", "chainlink"]
        self.assertNotEqual(
            first,
            derive_review_snapshot_id(ROOT, manifest, None, reversed_context, screen),
        )

        permuted_screen = json.loads(json.dumps(screen))
        permuted_screen["results"].reverse()
        for item in permuted_screen["results"]:
            item["evidence"].reverse()
        self.assertEqual(
            first,
            derive_review_snapshot_id(ROOT, manifest, None, domain_context, permuted_screen),
        )
        self.assertEqual(
            canonical_sha256({"a": 1, "b": 2}),
            canonical_sha256({"b": 2, "a": 1}),
        )

    def test_ordered_domain_context_mutation_stales_existing_review(self) -> None:
        registry, _, _, manifest = build_manifest()
        domain_context = self.context(manifest)
        screen, candidate_id = self.screen(manifest, candidate=True)
        domain = next(iter(domain_context["domains"]))
        key = next(iter(domain_context["domains"][domain]))
        domain_context["domains"][domain][key]["value"] = ["A", "B"]
        context = self.context_artifact(manifest)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "review.jsonl"
            append(
                ledger,
                manifest,
                self.review_record(registry, manifest, candidate_id),
                registry,
                {candidate_id},
                domain_context=domain_context,
                screen_results=screen,
            )
            clean = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            self.assertEqual(clean["status"], "COMPLETE_CLEAN")

            domain_context["domains"][domain][key]["value"] = ["B", "A"]
            stale = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            self.assertNotEqual(clean["review_snapshot_id"], stale["review_snapshot_id"])
            self.assertEqual(stale["status"], "INCOMPLETE_REVIEW")
            self.assertTrue(any("review_snapshot_id" in reason for reason in stale["reasons"]))

    def test_domain_resolution_mutation_stales_existing_review(self) -> None:
        registry, _, _, manifest = build_manifest(domains=None)
        resolution = domain_resolution_template(manifest)
        for item in resolution["domains"].values():
            item.update(
                status="ABSENT_CONFIRMED",
                scope_complete=True,
                evidence=[{"kind": "scope", "location": "fixture", "reason": "complete scope"}],
            )
        domain_context = self.context(manifest, resolution)
        screen, candidate_id = self.screen(manifest, resolution, candidate=True)
        context = self.context_artifact(manifest)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "review.jsonl"
            append(
                ledger,
                manifest,
                self.review_record(registry, manifest, candidate_id),
                registry,
                {candidate_id},
                resolution,
                domain_context=domain_context,
                screen_results=screen,
            )
            self.assertEqual(
                validate_run(ROOT, manifest, registry, screen, resolution, domain_context, context, [ledger])["status"],
                "COMPLETE_CLEAN",
            )
            resolution["domains"][next(iter(resolution["domains"]))]["evidence"][0]["reason"] = "changed resolution evidence"
            stale = validate_run(ROOT, manifest, registry, screen, resolution, domain_context, context, [ledger])
            self.assertEqual(stale["status"], "INCOMPLETE_REVIEW")

    def test_required_context_not_applicable_requires_trusted_complete_scope(self) -> None:
        _, _, _, manifest = build_manifest()
        context = self.context(manifest)
        domain = next(iter(context["domains"]))
        key = next(iter(context["domains"][domain]))
        context["domains"][domain][key] = {
            "status": "NOT_APPLICABLE",
            "scope_complete": True,
            "evidence": [{"kind": "manual", "location": "fixture", "reason": "manual assertion"}],
        }
        from scripts.audit_artifacts import validate_domain_context

        with self.assertRaisesRegex(ValueError, "exclusion dimension"):
            validate_domain_context(ROOT, manifest, context)
        context["domains"][domain][key]["scope_complete"] = False
        with self.assertRaises(ValueError):
            validate_domain_context(ROOT, manifest, context)
        context["domains"][domain][key] = {
            "status": "NOT_APPLICABLE",
            "scope_complete": True,
            "evidence": [
                {"kind": "scope", "location": "fixture", "reason": "complete scope"},
                {"kind": "dependency", "location": "fixture", "reason": "required component absent"},
            ],
        }
        self.assertEqual(validate_domain_context(ROOT, manifest, context), set())
        context["domains"][domain][key] = {"status": "UNKNOWN", "evidence": []}
        with self.assertRaisesRegex(ValueError, "remains UNKNOWN"):
            validate_domain_context(ROOT, manifest, context, require_complete=True)

    def test_single_file_compilation_scope_and_lib_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "src/Target.sol"
            dependency = root / "src/Dependency.sol"
            internal_lib = root / "src/lib/Foo.sol"
            external_lib = root / "lib/openzeppelin/Foo.sol"
            first_party_lib = root / "lib/MyProtocol.sol"
            for path in (target, dependency, internal_lib, external_lib, first_party_lib):
                path.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('pragma solidity ^0.8.24; import "./Dependency.sol"; contract Target is Dependency {}', encoding="utf-8")
            dependency.write_text("pragma solidity ^0.8.24; contract Dependency {}", encoding="utf-8")
            internal_lib.write_text("pragma solidity ^0.8.24; contract Foo {}", encoding="utf-8")
            external_lib.write_text("pragma solidity ^0.8.24; contract OpenZeppelinFoo {}", encoding="utf-8")
            first_party_lib.write_text("pragma solidity ^0.8.24; contract MyProtocol {}", encoding="utf-8")
            (root / "foundry.toml").write_text('[profile.default]\nsrc = "src"\n', encoding="utf-8")

            included, excluded = scope_inventory(root)
            self.assertIn("src/lib/Foo.sol", included)
            self.assertIn("lib/MyProtocol.sol", excluded)
            included, _ = scope_inventory(root, include_patterns=("lib/MyProtocol.sol",))
            self.assertIn("lib/MyProtocol.sol", included)
            self.assertNotIn("lib/openzeppelin/Foo.sol", included)

            files, _ = scope_inventory(target)
            before = compilation_digests(target, files, "0.8.24", build_root=root)
            target.write_text('pragma solidity ^0.8.24; import "./Dependency.sol"; contract Target is Dependency { uint256 changed; }', encoding="utf-8")
            after_target = compilation_digests(target, files, "0.8.24", build_root=root)
            self.assertNotEqual(before["audit_source_digest"], after_target["audit_source_digest"])
            self.assertNotEqual(before["compilation_input_digest"], after_target["compilation_input_digest"])
            target.write_text('pragma solidity ^0.8.24; import "./Dependency.sol"; contract Target is Dependency {}', encoding="utf-8")
            dependency.write_text("pragma solidity ^0.8.24; contract Dependency { uint256 changed; }", encoding="utf-8")
            after_dependency = compilation_digests(target, files, "0.8.24", build_root=root)
            self.assertEqual(before["audit_source_digest"], after_dependency["audit_source_digest"])
            self.assertNotEqual(before["compilation_input_digest"], after_dependency["compilation_input_digest"])
            (root / "foundry.toml").write_text('[profile.default]\nsrc = "contracts"\n', encoding="utf-8")
            after_config = compilation_digests(target, files, "0.8.24", build_root=root)
            self.assertNotEqual(after_dependency["compilation_input_digest"], after_config["compilation_input_digest"])

    def test_directory_scope_discovers_nearest_project_build_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            source = project / "src"
            dependency = project / "lib/Dependency.sol"
            for path in (source / "Vault.sol", source / "Helper.sol", dependency):
                path.parent.mkdir(parents=True, exist_ok=True)
            (project / "foundry.toml").write_text('[profile.default]\nsrc = "src"\n', encoding="utf-8")
            (project / "remappings.txt").write_text("dep/=lib/\n", encoding="utf-8")
            (source / "Vault.sol").write_text("pragma solidity ^0.8.24; contract Vault {}", encoding="utf-8")
            (source / "Helper.sol").write_text("pragma solidity ^0.8.24; contract Helper {}", encoding="utf-8")
            dependency.write_text("pragma solidity ^0.8.24; contract Dependency {}", encoding="utf-8")

            self.assertEqual(resolve_build_root(source), project.resolve())
            files, _ = scope_inventory(source)
            before = compilation_digests(source, files, "0.8.24")
            (project / "foundry.toml").write_text('[profile.default]\nsrc = "contracts"\n', encoding="utf-8")
            after_config = compilation_digests(source, files, "0.8.24")
            self.assertNotEqual(before["compilation_input_digest"], after_config["compilation_input_digest"])
            dependency.write_text("pragma solidity ^0.8.24; contract Dependency { uint256 changed; }", encoding="utf-8")
            after_dependency = compilation_digests(source, files, "0.8.24")
            self.assertNotEqual(after_config["compilation_input_digest"], after_dependency["compilation_input_digest"])

            repo = root / "repo"
            protocol = repo / "packages/protocol"
            (repo / "package.json").parent.mkdir(parents=True, exist_ok=True)
            (repo / "package.json").write_text("{}", encoding="utf-8")
            (protocol / "foundry.toml").parent.mkdir(parents=True, exist_ok=True)
            (protocol / "foundry.toml").write_text("[profile.default]\n", encoding="utf-8")
            nested_source = protocol / "src"
            nested_source.mkdir()
            self.assertEqual(resolve_build_root(nested_source), protocol.resolve())

            override = root
            self.assertEqual(resolve_build_root(source, override), override.resolve())
            outside = root / "outside"
            outside.mkdir()
            with self.assertRaisesRegex(ValueError, "inside build root"):
                resolve_build_root(source, outside)

    def test_reporting_templates_refresh_and_preserve_completed_artifacts(self) -> None:
        _, _, _, manifest = build_manifest()
        candidate_id = manifest["selected"][0]["canonical_id"]
        second_candidate_id = manifest["selected"][1]["canonical_id"]
        digest_one = "1" * 64
        digest_two = "2" * 64
        state_one = {"review_state_digest": digest_one, "coverage": {"confirmed": [candidate_id]}}
        state_two = {"review_state_digest": digest_two, "coverage": {"confirmed": [candidate_id]}}
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            first = _ensure_reporting_templates(manifest, state_one, run_dir)
            self.assertEqual(first["template_status"], {"severity": "GENERATED_TEMPLATE", "finding_details": "GENERATED_TEMPLATE"})
            severity_path = run_dir / "reviews/severity-decisions.json"
            details_path = run_dir / "reviews/finding-details.json"
            original = severity_path.read_text(encoding="utf-8")
            self.assertEqual(json.loads(original)["review_state_digest"], digest_one)
            self.assertEqual(json.loads(original)["artifact_state"], "TEMPLATE")

            unchanged = _ensure_reporting_templates(manifest, state_one, run_dir)
            self.assertEqual(unchanged["template_status"]["severity"], "CURRENT_TEMPLATE")
            self.assertEqual(severity_path.read_text(encoding="utf-8"), original)

            refreshed = _ensure_reporting_templates(manifest, state_two, run_dir)
            self.assertEqual(refreshed["template_status"]["severity"], "REGENERATED_STALE_TEMPLATE")
            self.assertEqual(json.loads(severity_path.read_text(encoding="utf-8"))["review_state_digest"], digest_two)

            changed_set = _ensure_reporting_templates(
                manifest,
                {"review_state_digest": digest_two, "coverage": {"confirmed": [candidate_id, second_candidate_id]}},
                run_dir,
            )
            self.assertEqual(changed_set["template_status"]["severity"], "REGENERATED_STALE_TEMPLATE")
            self.assertEqual(
                set(json.loads(severity_path.read_text(encoding="utf-8"))["decisions"]),
                {candidate_id, second_candidate_id},
            )
            _ensure_reporting_templates(manifest, state_two, run_dir)

            completed_severity = json.loads(severity_path.read_text(encoding="utf-8"))
            completed_severity["artifact_state"] = "COMPLETED"
            completed_severity["decisions"][candidate_id] = {
                "severity": "High",
                "rationale": "completed rationale",
                "dimensions": {dimension: "completed" for dimension in (
                    "impact", "exploitability", "privileges", "capital_required", "repeatability",
                    "user_interaction", "loss_bound", "protocol_exposure", "recoverability",
                )},
            }
            completed_severity["review_state_digest"] = digest_one
            severity_path.write_text(json.dumps(completed_severity) + "\n", encoding="utf-8")
            completed_details = json.loads(details_path.read_text(encoding="utf-8"))
            completed_details["artifact_state"] = "COMPLETED"
            completed_details["review_state_digest"] = digest_one
            completed_details["findings"][0].update(description="completed description", recommendation="completed fix")
            details_path.write_text(json.dumps(completed_details) + "\n", encoding="utf-8")

            archived = _ensure_reporting_templates(manifest, state_two, run_dir)
            self.assertEqual(archived["template_status"]["severity"], "ARCHIVED_STALE_ARTIFACT")
            self.assertEqual(archived["template_status"]["finding_details"], "ARCHIVED_STALE_ARTIFACT")
            self.assertIn("completed rationale", Path(archived["archived_templates"]["severity"]).read_text(encoding="utf-8"))
            self.assertEqual(json.loads(severity_path.read_text(encoding="utf-8"))["artifact_state"], "TEMPLATE")

    def test_review_state_digest_rejects_stale_reporting_inputs(self) -> None:
        registry, _, _, manifest = build_manifest()
        domain_context = self.context(manifest)
        screen, candidate_id = self.screen(manifest, candidate=True)
        context = self.context_artifact(manifest)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "review.jsonl"
            append(
                ledger,
                manifest,
                self.review_record(registry, manifest, candidate_id, confirmed=True),
                registry,
                {candidate_id},
                domain_context=domain_context,
                screen_results=screen,
            )
            state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            digest = state["review_state_digest"]
            identity = {
                "schema_version": 2,
                "routing_snapshot_id": manifest["routing_snapshot_id"],
                "review_state_digest": digest,
                **{key: manifest["audit_context"][key] for key in ("registry_sha256", "source_digest", "compilation_input_digest")},
            }
            severity = {
                **identity,
                "decisions": {
                    candidate_id: {
                        "severity": "High",
                        "rationale": "proof-bound fixture impact",
                        "dimensions": {key: "fixture" for key in ("impact", "exploitability", "privileges", "capital_required", "repeatability", "user_interaction", "loss_bound", "protocol_exposure", "recoverability")},
                    }
                },
            }
            details = {**identity, "findings": [{"canonical_id": candidate_id, "location": "Fixture.sol:1", "description": "fixture", "recommendation": "fix"}]}
            synthesize(ROOT, manifest, registry, state, [ledger], severity, finding_details=details, screen_results=screen, domain_context=domain_context, context=context)

            records = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            records[-1]["proof"] = "changed current proof"
            ledger.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in records), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "mismatched review_state_digest"):
                synthesize(ROOT, manifest, registry, state, [ledger], severity, finding_details=details, screen_results=screen, domain_context=domain_context, context=context)

    def test_registry_mutation_invalidates_current_state(self) -> None:
        registry, _, _, manifest = build_manifest()
        domain_context = self.context(manifest)
        screen, _ = self.screen(manifest, candidate=False)
        changed_registry = json.loads(json.dumps(registry))
        changed_registry["checks"][0]["title"] += " changed"
        state = validate_run(
            ROOT,
            manifest,
            changed_registry,
            screen,
            None,
            domain_context,
            self.context_artifact(manifest),
            [],
        )
        self.assertEqual(state["status"], "INVALID_SNAPSHOT")
        self.assertTrue(any("registry" in reason for reason in state["reasons"]))

    def test_severity_and_details_mutation_rewrites_final_report(self) -> None:
        registry, _, _, manifest = build_manifest()
        domain_context = self.context(manifest)
        screen, candidate_id = self.screen(manifest, candidate=True)
        context = self.context_artifact(manifest)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path, context_path = root / "manifest.json", root / "context.json"
            domain_context_path, screen_path = root / "domain-context.json", root / "screen-results.json"
            state_path, ledger = root / "audit-state.json", root / "review.jsonl"
            severity_path, details_path = root / "severity.json", root / "details.json"
            report_path, issues_path = root / "AUDIT-REPORT.md", root / "issue-candidates.json"
            for path, value in ((manifest_path, manifest), (context_path, context), (domain_context_path, domain_context), (screen_path, screen)):
                write_json(path, value)
            append(
                ledger,
                manifest,
                self.review_record(registry, manifest, candidate_id, confirmed=True),
                registry,
                {candidate_id},
                domain_context=domain_context,
                screen_results=screen,
            )
            state = validate_run(ROOT, manifest, registry, screen, None, domain_context, context, [ledger])
            write_json(state_path, state)
            identity = {
                "schema_version": 2,
                "routing_snapshot_id": manifest["routing_snapshot_id"],
                "review_state_digest": state["review_state_digest"],
                **{key: manifest["audit_context"][key] for key in ("registry_sha256", "source_digest", "compilation_input_digest")},
            }
            severity = {**identity, "decisions": {candidate_id: {"severity": "High", "rationale": "first", "dimensions": {key: "first" for key in ("impact", "exploitability", "privileges", "capital_required", "repeatability", "user_interaction", "loss_bound", "protocol_exposure", "recoverability")}}}}
            details = {**identity, "findings": [{"canonical_id": candidate_id, "location": "Fixture.sol:1", "description": "first description", "recommendation": "first fix"}]}
            write_json(severity_path, severity)
            write_json(details_path, details)
            command = [
                "--manifest", str(manifest_path), "--audit-state", str(state_path), "--context", str(context_path),
                "--domain-context", str(domain_context_path), "--screen-results", str(screen_path), "--ledger", str(ledger),
                "--severity-decisions", str(severity_path), "--finding-details", str(details_path),
                "--output", str(report_path), "--issue-candidates-out", str(issues_path),
            ]
            self.assertEqual(synthesize_main(command), 0)
            severity["decisions"][candidate_id]["severity"] = "Medium"
            details["findings"][0]["description"] = "updated description"
            write_json(severity_path, severity)
            write_json(details_path, details)
            self.assertEqual(synthesize_main(command), 0)
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("**Severity:** Medium", report)
            self.assertIn("updated description", report)

    def test_failed_direct_synthesis_removes_stale_final_outputs(self) -> None:
        registry, _, _, manifest = build_manifest()
        domain_context = self.context(manifest)
        screen, candidate_id = self.screen(manifest, candidate=False)
        context = self.context_artifact(manifest)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            context_path = root / "context.json"
            domain_context_path = root / "domain-context.json"
            screen_path = root / "screen-results.json"
            state_path = root / "audit-state.json"
            report_path = root / "AUDIT-REPORT.md"
            issues_path = root / "issue-candidates.json"
            for path, value in ((manifest_path, manifest), (context_path, context), (domain_context_path, domain_context), (screen_path, screen)):
                write_json(path, value)
            write_json(state_path, validate_run(ROOT, manifest, registry, screen, None, domain_context, context, []))
            self.assertEqual(
                synthesize_main([
                    "--manifest", str(manifest_path), "--audit-state", str(state_path), "--context", str(context_path),
                    "--domain-context", str(domain_context_path), "--screen-results", str(screen_path),
                    "--output", str(report_path), "--issue-candidates-out", str(issues_path),
                ]),
                0,
            )
            self.assertIn("COMPLETE_CLEAN", report_path.read_text(encoding="utf-8"))

            screen, candidate_id = self.screen(manifest, candidate=True)
            write_json(screen_path, screen)
            ledger = root / "review.jsonl"
            append(
                ledger,
                manifest,
                self.review_record(registry, manifest, candidate_id, confirmed=True),
                registry,
                {candidate_id},
                domain_context=domain_context,
                screen_results=screen,
            )
            self.assertEqual(
                synthesize_main([
                    "--manifest", str(manifest_path), "--audit-state", str(state_path), "--context", str(context_path),
                    "--domain-context", str(domain_context_path), "--screen-results", str(screen_path), "--ledger", str(ledger),
                    "--output", str(report_path), "--issue-candidates-out", str(issues_path),
                ]),
                1,
            )
            self.assertFalse(report_path.exists())
            self.assertFalse(issues_path.exists())


if __name__ == "__main__":
    unittest.main()
