"""Explicit supported artifact and schema versions."""

from __future__ import annotations


SCHEMA_VERSIONS = {
    "audit-context": 1,
    "audit-state": 2,
    "benchmark-routing-fixture": 1,
    "code-context-query": 5,
    "code-context-benchmark": 2,
    "code-index": 2,
    "codex-model-profile": 1,
    "domain-context": 3,
    "domain-resolution": 2,
    "environment-context": 1,
    "feature-detectors": 1,
    "feature-map": 4,
    "finding-details": 2,
    "issue-candidates": 2,
    "knowledge-metrics": 1,
    "poc-evidence": 1,
    "poc-verification": 1,
    "review-record": 7,
    "routing-manifest": 7,
    "report-bundle": 3,
    "report-current": 3,
    "repository-trust": 1,
    "runtime-metadata": 1,
    "screen-results": 2,
    "severity-decisions": 2,
}

AUDIT_STATE_VERSION = SCHEMA_VERSIONS["audit-state"]
BENCHMARK_ROUTING_FIXTURE_VERSION = SCHEMA_VERSIONS["benchmark-routing-fixture"]
CODE_CONTEXT_QUERY_VERSION = SCHEMA_VERSIONS["code-context-query"]
CODE_CONTEXT_BENCHMARK_VERSION = SCHEMA_VERSIONS["code-context-benchmark"]
CODE_INDEX_VERSION = SCHEMA_VERSIONS["code-index"]
CODEX_MODEL_PROFILE_VERSION = SCHEMA_VERSIONS["codex-model-profile"]
DOMAIN_CONTEXT_VERSION = SCHEMA_VERSIONS["domain-context"]
DOMAIN_RESOLUTION_VERSION = SCHEMA_VERSIONS["domain-resolution"]
ENVIRONMENT_CONTEXT_VERSION = SCHEMA_VERSIONS["environment-context"]
FEATURE_MAP_VERSION = SCHEMA_VERSIONS["feature-map"]
FINDING_DETAILS_VERSION = SCHEMA_VERSIONS["finding-details"]
ISSUE_CANDIDATES_VERSION = SCHEMA_VERSIONS["issue-candidates"]
KNOWLEDGE_METRICS_VERSION = SCHEMA_VERSIONS["knowledge-metrics"]
POC_EVIDENCE_VERSION = SCHEMA_VERSIONS["poc-evidence"]
POC_VERIFICATION_VERSION = SCHEMA_VERSIONS["poc-verification"]
REVIEW_RECORD_VERSION = SCHEMA_VERSIONS["review-record"]
ROUTING_MANIFEST_VERSION = SCHEMA_VERSIONS["routing-manifest"]
REPORT_BUNDLE_VERSION = SCHEMA_VERSIONS["report-bundle"]
REPORT_CURRENT_VERSION = SCHEMA_VERSIONS["report-current"]
REPOSITORY_TRUST_VERSION = SCHEMA_VERSIONS["repository-trust"]
RUNTIME_METADATA_VERSION = SCHEMA_VERSIONS["runtime-metadata"]
SCREEN_RESULTS_VERSION = SCHEMA_VERSIONS["screen-results"]
SEVERITY_DECISIONS_VERSION = SCHEMA_VERSIONS["severity-decisions"]
CANONICAL_CHECKS_VERSION = 5
CANONICAL_HISTORY_VERSION = 1
CLAIMS_VERSION = 3
FEATURE_REGISTRY_VERSION = 2
KNOWLEDGE_HEALTH_VERSION = 1
REPORTING_VERSION = SEVERITY_DECISIONS_VERSION
