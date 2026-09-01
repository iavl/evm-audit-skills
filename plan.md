# plan.md — Re-audit hardening plan for `evm-audit-skills-standalone`

## Audit baseline

This plan was prepared against:

- Repository: `iavl/evm-audit-skills-standalone`
- Branch: `main`
- Audited commit: `22482731f1c641cb3f9189bf857aac1f7979e000`
- Commit message: `Improve audit pipeline correctness and validation`
- Previous reviewed baseline: `6074455d850fefecbe3fdaa94044738e76d7547a`

Read and obey the repository-root `AGENTS.md` before modifying anything.

Do **not** re-implement previous hardening that already exists. The latest commit materially fixed earlier issues:

- real Slither IR adapters are used by `code-index`;
- state writes are separated from local writes;
- path-qualified function identities and bounded graph traversal exist;
- runtime Markdown is body-hash checked;
- out-of-build-root compilation inputs fail closed;
- invalid optional `code-index` no longer blocks authoritative state;
- ledger locking has POSIX and Windows implementations;
- ledger appends flush and `fsync`;
- report synthesis happens before final outputs are replaced;
- real Slither integration tests exist.

The work below addresses newly discovered bugs and remaining integrity/maintainability gaps.

---

# 0. Implementation policy

Use this priority order:

1. P1 audit-state correctness.
2. P1 code-index integrity.
3. Current failing CI.
4. P2 artifact/query correctness.
5. P3 benchmark/CI/maintainability improvements.

For every behavioral bug:

1. add a regression test that fails on current code;
2. implement the smallest safe fix;
3. run focused tests;
4. run the full validation suite;
5. only then refactor.

Do not weaken schemas, evidence requirements, routing recall, or stage gates merely to make tests pass.

Do not perform a broad rewrite of `audit_run.py`, `review_ledger.py`, `code_context.py`, or routing in the same commit as a correctness fix.

---

# P1.1 — Close the direct-PROOF review lifecycle bypass

## Severity

**P1 — audit-state integrity**

## Problem

The current validator enforces revision numbering, strong evidence for `CONFIRMED`, and transition checks for later records. However, the transition check is only meaningful when a previous record exists.

A first review record can therefore currently be shaped as:

```json
{
  "revision": 1,
  "review_stage": "PROOF",
  "status": "REVIEWED_SAFE"
}
```

and can pass if all other required fields are supplied.

Likewise revision 1 can be:

```json
{
  "revision": 1,
  "review_stage": "PROOF",
  "status": "CONFIRMED"
}
```

when strong proof evidence is supplied.

This allows a hand-crafted ledger to skip the required Deep Review event. The controller normally reaches Proof only after a Deep `SUSPICIOUS` record, but authoritative completion is derived from persisted artifacts. Therefore validation must independently enforce the lifecycle.

This is especially important for `PROOF/REVIEWED_SAFE`, because otherwise a candidate may become clean without ever recording a Deep Review event.

## Target files

- `scripts/review_ledger.py`
- `schemas/review-record.schema.json` if useful
- `tests/test_runtime.py`
- `tests/test_audit_run.py`
- review-contract docs only if lifecycle wording needs clarification

## Required lifecycle

### First revision

A first review event for a canonical ID MUST satisfy:

```text
revision == 1
review_stage == DEEP_REVIEW
status ∈ {
  NOT_APPLICABLE,
  REVIEWED_SAFE,
  SUSPICIOUS
}
```

`CONFIRMED` MUST NOT be possible as the first revision.

### Follow-up revision

A revision greater than 1 MUST:

- immediately follow a previous `SUSPICIOUS`;
- use `review_stage=PROOF`;
- have contiguous revision numbering;
- resolve to one of:
   - `REVIEWED_SAFE`
   - `SUSPICIOUS`
   - `CONFIRMED`

Keep `NOT_APPLICABLE` invalid as a Proof-stage resolution unless an explicit evidence-safe policy is introduced later.

### Confirmed

`CONFIRMED` MUST imply:

- `review_stage=PROOF`;
- revision >= 2;
- previous revision exists;
- previous status is `SUSPICIOUS`;
- all existing strong-proof requirements remain satisfied.

Do not weaken the current evidence gate.

## Implementation guidance

Prefer one explicit lifecycle validator rather than scattered checks.

JSON Schema can keep local record constraints such as:

```text
CONFIRMED -> review_stage=PROOF
```

but history-dependent rules must be enforced in Python.

## Required regression tests

Add tests proving:

1. revision 1 + `DEEP_REVIEW/REVIEWED_SAFE` is valid.
2. revision 1 + `DEEP_REVIEW/NOT_APPLICABLE` is valid with required absence evidence.
3. revision 1 + `DEEP_REVIEW/SUSPICIOUS` is valid.
4. revision 1 + `PROOF/REVIEWED_SAFE` is rejected.
5. revision 1 + `PROOF/SUSPICIOUS` is rejected.
6. revision 1 + `PROOF/CONFIRMED` is rejected even with strong evidence.
7. `DEEP_REVIEW/SUSPICIOUS -> PROOF/REVIEWED_SAFE` is valid.
8. `DEEP_REVIEW/SUSPICIOUS -> PROOF/SUSPICIOUS -> PROOF/CONFIRMED` is valid.
9. `DEEP_REVIEW/REVIEWED_SAFE -> PROOF/*` remains rejected.
10. `DEEP_REVIEW/NOT_APPLICABLE -> PROOF/*` remains rejected.
11. a hand-crafted direct-Proof ledger cannot make `validate_run()` return `COMPLETE_CLEAN`.
12. a hand-crafted direct-Proof ledger cannot make `validate_run()` return `COMPLETE_WITH_FINDINGS`.

Add at least one controller/state-level regression, not only `validate_record()` unit tests.

## Acceptance criteria

No audit reaches a complete state unless every Deep candidate has an explicit revision-1 Deep Review event.

---

# P1.2 — Cryptographically bind the optional `code-index` to authoritative Recon/routing state

## Severity

**P1 — model-navigation integrity**

## Problem

`recon/code-index.json` is non-authoritative, but the Master Skill tells the model to inspect it first and use it to target source loading and caller/callee expansion.

Current validation checks its schema plus embedded:

```text
source_digest
compilation_input_digest
```

Those values identify source/compilation inputs, not the actual generated index body.

A modified index can preserve both digests while changing:

- call edges;
- source ranges;
- function mappings;
- storage-write locations;

and still be classified as `CURRENT`.

Because the token-efficient audit workflow intentionally uses this index to decide which source ranges to load, silent corruption can misdirect reachable-path investigation.

## Design requirement

Treat the index as:

```text
non-authoritative but integrity-bound
```

Corruption must disable navigation, not invalidate an otherwise valid authoritative audit snapshot.

## Recommended design

Bind a deterministic digest of the generated code index into an authoritative Recon artifact.

Preferred shape:

```json
"recon_context": {
  "...": "...",
  "navigation_artifacts": {
    "code_index": {
      "schema_version": 2,
      "sha256": "<64 hex>"
    }
  }
}
```

or another clearly versioned equivalent.

The digest must flow into the routing snapshot through Feature Map / audit-context lineage.

### Digest rules

- Hash exact serialized bytes or one documented canonical JSON encoding consistently.
- Do not trust a sidecar that can be changed together with the index without authoritative binding.
- Avoid circular hashing.
- Represent a missing optional index explicitly.
- Standalone Recon without `--code-index-out` must remain supported.

## Controller behavior

`_optional_code_index_status()` should distinguish at least:

```text
ABSENT
CURRENT
UNAVAILABLE
```

Optionally add:

```text
TAMPERED
```

If the body digest does not match authoritative lineage:

- `available=false`;
- never consume the index;
- warn clearly;
- do not change a valid authoritative audit into `INVALID_SNAPSHOT` solely because this optional artifact is corrupt.

## Likely target files

- `scripts/recon.py`
- `scripts/code_context.py`
- `scripts/audit_run.py`
- `scripts/select_checks.py`
- `scripts/audit_artifacts.py`
- relevant Feature Map / audit-context / manifest schemas
- `evm_audit_runtime/versions.py` only if a schema must bump
- `tests/test_audit_run.py`
- `tests/test_code_context.py`
- docs

Do not bump unrelated schema versions.

## Required tests

1. generate a valid index and confirm `CURRENT`;
2. modify one call edge while keeping source/compilation digests unchanged -> navigation becomes unavailable/tampered;
3. modify only a source range -> same;
4. modify only a storage-write record -> same;
5. authoritative audit status remains derived from authoritative artifacts;
6. deleting the optional index produces `ABSENT`, not `INVALID_SNAPSHOT`;
7. regenerating the same index produces a stable digest.

## Acceptance criteria

No changed `code-index.json` body is accepted as `CURRENT` unless it matches the digest bound into authoritative Recon/routing lineage.

---

# P1.3 — Add full relational validation for `code-index`

## Severity

**P1/P2 — navigation correctness**

## Problem

The schema validates object shapes, but `validate_code_index()` currently checks only a small number of relationships.

A schema-valid but internally inconsistent index can pass validation.

Concrete failure path:

1. `functions` contains function `F`;
2. `source_ranges` lacks `F`;
3. `validate_code_index()` accepts the index;
4. `lookup()` builds `source_ranges[F]` using `.get()` and returns `None`;
5. `code-context-query.schema.json` requires a range object;
6. the query fails only later.

The controller can therefore label an index `CURRENT` even when it cannot produce a schema-valid query.

## Required relational invariants

At minimum:

```text
set(functions) == set(source_ranges)
set(functions) == set(modifiers)
set(contracts) == set(inheritance)
```

For every function:

- `function.function_id == map key`;
- `function.contract_id` exists;
- function `file/start_line/end_line` matches `source_ranges[function_id]`;
- `start_line <= end_line`.

For inheritance:

- every key is a known contract;
- every base reference is a known contract.

For call events:

- every `caller` is a known function;
- concrete function targets reference known functions;
- unresolved targets are distinguishable from concrete targets.

For storage writes:

- every `function` is known;
- location fields are valid.

For per-function call lists:

- every concrete internal/external function reference exists;
- list/event relationships are deterministic and internally consistent.

## Recommended future schema cleanup

The current string `target` field mixes:

- real function IDs;
- Solidity built-ins;
- unresolved high-level calls;
- low-level descriptors.

A future schema should prefer explicit typing, for example:

```json
{
  "kind": "delegatecall",
  "resolution": "UNRESOLVED",
  "target_function_id": null,
  "target_descriptor": "..."
}
```

versus:

```json
{
  "kind": "internal",
  "resolution": "FUNCTION",
  "target_function_id": "build://...::Contract.fn(uint256)"
}
```

If this migration makes the P1 patch large, first fix relational validation around v2, then migrate typed edges separately.

## Target files

- `scripts/code_context.py`
- `evm_audit_runtime/code_index.py`
- `schemas/code-index.schema.json`
- `schemas/code-context-query.schema.json`
- `tests/test_code_context.py`

## Required tests

Create schema-valid-but-relationally-invalid cases for:

- missing source range;
- extra source range;
- missing modifier key;
- missing inheritance key;
- nonexistent contract ID;
- unknown concrete callee;
- unknown event caller;
- unknown storage-write function;
- mismatched source range.

All must fail in `validate_code_index()` before `lookup()`.

Also assert every accepted index can produce a schema-valid query for every indexed function using:

```text
depth=0
depth=1
include_callers only
include_callees only
include both
```

---

# P1.4 — Repair the currently failing Windows CI job without masking ledger coverage

## Severity

**P1 CI correctness**

## Current state

At audited commit `22482731f1c641cb3f9189bf857aac1f7979e000`, the latest `Validate checklist corpus` workflow completed with failure.

Jobs:

```text
generated-and-registry: PASS
python-tests (Ubuntu): PASS
whitespace: PASS
windows-ledger: FAIL
```

The actual Windows multiprocessing ledger serialization test passed.

The failing test is:

```text
test_routing_manifest_rejects_invalid_shape
```

The traceback is a Windows `PermissionError` caused by opening a `NamedTemporaryFile` and then reopening that same file path while the original handle is still open.

This is a test portability bug, not evidence that the new Windows ledger lock itself failed.

## Required fix

Replace the test with a cross-platform-safe pattern.

Preferred:

```python
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "manifest.json"
    path.write_text(...)
    validate_manifest(... load_json(path) ...)
```

Alternative:

- use `NamedTemporaryFile(delete=False)`;
- close it before reopening;
- guarantee cleanup.

Prefer `TemporaryDirectory`.

## Do not

- skip the test on Windows;
- catch and ignore `PermissionError`;
- disable the Windows job;
- weaken locking.

## CI structure improvement

The job is named `windows-ledger` but executes all of `test_runtime.py`.

After portability is fixed, either:

### Option A

Move OS-specific lock tests to:

```text
tests/test_ledger_locking.py
```

and have `windows-ledger` run that file.

### Option B

Keep all runtime tests on Windows but rename the job to `windows-runtime`.

Choose intentionally.

## Acceptance criteria

- Windows multiprocessing locking remains green.
- The temporary-file test becomes portable.
- No Windows skip is added for ledger correctness.
- Entire GitHub workflow becomes green.

---

# P2.1 — Make `code_context.lookup()` output semantics match include flags

## Problem

Graph expansion uses:

```text
include_callers
include_callees
depth
max_nodes
```

to select function nodes.

But returned `caller_edges` and `callee_edges` are assembled independently and may reference functions not included in the returned `functions` map, including when expansion is disabled or `depth=0`.

That makes the compact query artifact ambiguous.

## Required design

Choose and document one semantic model.

Recommended:

### Selected-subgraph fields

```text
functions
source_ranges
caller_edges
callee_edges
```

contain only nodes/edges admitted by requested expansion.

### Boundary information

If boundary edges are useful, expose an explicit field:

```text
boundary_edges
```

or:

```text
unexpanded_edges
```

Do not overload `caller_edges` / `callee_edges`.

### Flag behavior

- `include_callers=false` -> no expanded caller edges in `caller_edges`;
- `include_callees=false` -> no expanded callee edges in `callee_edges`;
- `depth=0` -> selected function only, with boundary information separate if retained;
- unresolved edges emitted by selected callers may remain visible because they are reachability uncertainty, but document this explicitly.

## Target files

- `evm_audit_runtime/code_index.py`
- `schemas/code-context-query.schema.json`
- `scripts/code_context.py`
- `tests/test_code_context.py`
- `docs/recon-and-routing.md`

## Tests

Cover exact functions and edges for:

- neither flag;
- callers only;
- callees only;
- both;
- depth 0;
- depth 1;
- depth 2;
- cycle;
- truncation;
- unresolved edge.

---

# P2.2 — Make final report + issue-candidates a verifiable output bundle

## Problem

`report_run()` now correctly synthesizes before replacing previous outputs, which fixes the earlier destructive behavior.

But final outputs are still committed independently:

```text
AUDIT-REPORT.md
issue-candidates.json
```

Each write is individually atomic, but the pair is not.

Possible failure:

1. synthesis succeeds;
2. new report is installed;
3. issue-candidates write fails;
4. run now contains a new report plus old/missing issue candidates.

## Required design

Introduce a report-bundle commit identity.

Recommended metadata:

```json
{
  "routing_snapshot_id": "...",
  "review_state_digest": "...",
  "report_sha256": "...",
  "issue_candidates_sha256": "..."
}
```

Commit sequence:

1. synthesize both in memory;
2. validate both;
3. write body files safely;
4. install body files;
5. write/install metadata commit marker **last**.

Consumers treat the bundle as current only when:

- metadata identity matches current audit state;
- both body hashes match.

Do not claim filesystem multi-file atomicity. The final metadata marker is the consistency boundary.

## Target files

- `scripts/audit_run.py`
- `scripts/synthesize_report.py`
- `scripts/audit_artifacts.py`
- report metadata schema
- `tests/test_audit_run.py`
- `docs/audit-runtime.md`

## Required tests

Fault-inject:

- report write failure;
- issue-candidates write failure;
- metadata write failure;
- report body tamper;
- issue-candidates tamper;
- stale `review_state_digest`.

No mismatched bundle may be reported as current.

---

# P2.3 — Make audit initialization recoverable after Recon/Routing failure

## Problem

`init_run()` writes run-scoped artifacts such as the model profile before initialization fully succeeds, while also refusing to initialize a non-empty run directory.

A Recon or Routing failure can therefore leave a partial run that cannot simply be retried with the same `init`.

## Preferred solution

Make initialization transactional at run-directory level:

1. verify final `run_dir` is absent/empty;
2. create a sibling temporary run directory;
3. write profile, Recon, code-index and routing outputs there;
4. validate initialized state;
5. rename temporary directory to final `run_dir`.

If cross-platform directory rename semantics make this undesirable, use a narrow explicit initialization marker such as:

```text
.init-incomplete
```

with a safe retry policy.

Never automatically delete arbitrary user files.

## Required tests

- Recon failure leaves no apparently valid initialized run.
- Routing failure is recoverable.
- Retrying the same desired run succeeds safely.
- Existing unrelated user content is never deleted.

---

# P2.4 — Harden compilation dependency digest diagnostics

## Problem

`_submodule_commits()` invokes:

```text
git -C <root> ls-files -s -- <dependency roots>
```

with `check=False`, then hashes matching gitlink lines.

If Git fails unexpectedly, it silently produces an empty submodule-commit set.

For a project that uses Git submodules as Solidity dependencies, unexpected Git failure should not be indistinguishable from “there are no submodule gitlinks”.

## Required behavior

Distinguish:

1. build root is not a Git worktree -> explicit deterministic no-gitlink state;
2. Git worktree and command succeeds -> hash gitlinks;
3. Git worktree but command fails -> actionable error or explicit degraded provenance.

Do not silently map case 3 to case 1.

## Tests

- non-Git build root;
- Git repo without submodules;
- Git repo with a gitlink/submodule entry;
- mocked Git command failure.

No network access in tests.

---

# P3.1 — Fix routing benchmark assertion semantics

## Problem

`benchmark_routing.py::_assert_fixture()` currently combines:

```text
must_not_filter_domains
must_not_select_domains
```

into one `forbidden` set and then rejects a Domain if it is either filtered or selected.

This makes both fields effectively mean:

```text
Domain must be deferred
```

despite their names expressing different invariants.

It can incorrectly reject a conservative change that moves a Domain from Deferred to Selected.

## Required semantics

Implement literally:

```text
must_not_filter_domains:
    fail only if Domain is FILTERED

must_not_select_domains:
    fail only if Domain is SELECTED

must_select_domains:
    fail unless Domain is SELECTED
```

If a fixture requires exactly Deferred, encode both negative constraints or use:

```text
expected_deferred_domains
```

Likewise confirm check-level fields retain literal meaning.

## Target files

- `scripts/benchmark_routing.py`
- benchmark schema/fixtures as required
- focused unit tests around `_assert_fixture`

## Required tests

```text
must_not_filter_domain may be selected
must_not_select_domain may be filtered
deferred-only requires both constraints or exact expected bucket
```

## Acceptance criteria

The benchmark distinguishes false-negative filtering from conservative over-selection.

---

# P3.2 — Remove duplicated expensive tests from Ubuntu CI

## Problem

Current `python-tests` runs focused hardening suites:

```text
test_code_context.py
test_compilation_lineage.py
test_hardening.py
test_runtime.py
```

and then immediately runs:

```bash
python3 -m unittest discover -s tests -v
```

which executes those same tests again.

This doubles expensive work, including real Slither tests.

## Recommended options

### Option A — simplest

Remove the focused step and keep full discovery.

### Option B — parallel fast-fail job

Run focused hardening regressions in a separate parallel job and full discovery separately.

Do not run focused + full serially in the same job.

Keep all security-critical PR coverage.

---

# P3.3 — Improve schema strictness and reduce duplicate code-index shape definitions

`code-index.schema.json` and `code-context-query.schema.json` duplicate function/range/edge definitions.

This creates drift risk. Some object definitions also have less consistent `additionalProperties` behavior than strict function objects.

After P1/P2 are green, choose one low-risk approach:

- shared schema `$defs` references;
- generated schema fragments from one source;
- or tests that assert shared shape equivalence.

Do not loosen schemas.

---

# P3.4 — Incrementally move pure logic out of oversized CLI modules

Only after correctness work is green.

Good extraction candidates:

```text
review lifecycle transition logic
code-index relational validation
report-bundle identity
recon provenance/digest policy
```

Move reusable pure logic into `evm_audit_runtime/`.

Keep CLI flags and external behavior stable.

Do not do a repository-wide restructure.

---

# P3.5 — Add explicit artifact-authority documentation

Update `docs/audit-runtime.md` with a compact table like:

| Artifact | Authoritative? | Integrity binding | Failure behavior |
|---|---|---|---|
| Feature Map | yes for Recon snapshot | routing/input lineage | fail closed |
| Routing manifest | yes | `routing_snapshot_id` | invalid snapshot |
| Domain resolution | yes | routing identity | block downstream |
| Domain context | yes | routing/review identity | block downstream |
| Screen results | yes | review inputs | block downstream |
| Review JSONL | yes | checkpoint + review snapshot/state digest | block completion |
| runtime Markdown | no | sidecar + body SHA | regenerate |
| code-index | no | authoritative index digest after P1.2 | disable navigation |
| final report bundle | derived | report metadata after P2.2 | stale/incomplete |

Document explicitly:

```text
non-authoritative != integrity-unchecked
```

---

# 1. Current CI state that must be fixed

At audited commit `22482731f1c641cb3f9189bf857aac1f7979e000`:

```text
generated-and-registry: PASS
python-tests (Ubuntu): PASS
whitespace: PASS
windows-ledger: FAIL
```

Windows failure is caused by the POSIX-style open `NamedTemporaryFile` test pattern, not by the multiprocessing ledger locking test.

After P1.4, push and require the actual GitHub workflow to be fully green.

Do not report only local test success.

---

# 2. Minimum new regression tests

## Review lifecycle

```text
test_revision_one_must_be_deep_review
test_direct_proof_reviewed_safe_cannot_complete_clean
test_direct_proof_confirmed_cannot_complete_with_findings
test_proof_requires_previous_suspicious
```

## Code-index integrity

```text
test_code_index_body_tamper_disables_navigation
test_code_index_requires_source_range_for_every_function
test_code_index_rejects_unknown_call_event_caller
test_code_index_rejects_unknown_storage_write_function
test_code_index_rejects_relationally_inconsistent_maps
```

## Query semantics

```text
test_lookup_depth_zero_returns_only_root_subgraph
test_lookup_honors_include_callers
test_lookup_honors_include_callees
test_lookup_boundary_edges_are_explicit
```

## Report bundle

```text
test_report_bundle_rejects_mixed_generation_outputs
test_report_bundle_detects_report_tamper
test_report_bundle_detects_issue_candidate_tamper
```

## Benchmark DSL

```text
test_must_not_filter_domain_may_be_selected
test_must_not_select_domain_may_be_filtered
test_deferred_only_requires_both_or_exact_expected_bucket
```

---

# 3. Suggested commit sequence

## Commit 1 — `Enforce review stage lifecycle`

Implement P1.1 only.

## Commit 2 — `Bind and validate code index integrity`

Implement P1.2 + P1.3.

If schema versions change, include exact migrations/tests.

## Commit 3 — `Fix Windows runtime CI portability`

Implement P1.4.

Optionally isolate ledger-specific Windows tests.

## Commit 4 — `Clarify bounded code context query semantics`

Implement P2.1.

## Commit 5 — `Bind final report output bundle`

Implement P2.2.

## Commit 6 — `Harden init and compilation provenance`

Implement P2.3 + P2.4 if small; otherwise split.

## Commit 7 — `Correct routing benchmark semantics and streamline CI`

Implement P3.1 + P3.2.

## Commit 8 — `Reduce schema/runtime duplication`

Implement selected P3.3–P3.5 after all correctness tests are green.

---

# 4. Mandatory validation

Install pinned dependencies:

```bash
python3 -m pip install -r requirements-runtime.lock
```

Generated corpus and provenance:

```bash
python3 scripts/generate_checklists.py --check
python3 scripts/validate_checklists.py --strict
```

Routing benchmark:

```bash
python3 scripts/benchmark_routing.py
```

Focused tests:

```bash
python3 -m unittest discover -s tests -p 'test_runtime.py' -v
python3 -m unittest discover -s tests -p 'test_audit_run.py' -v
python3 -m unittest discover -s tests -p 'test_code_context.py' -v
python3 -m unittest discover -s tests -p 'test_compilation_lineage.py' -v
```

Full suite:

```bash
python3 -m unittest discover -s tests -v
git diff --check
```

Where Foundry is available:

```bash
python3 scripts/benchmark_routing.py --e2e
bash tests/semantics/test_eip6780_differential.sh paris
bash tests/semantics/test_eip6780_differential.sh cancun
python3 scripts/knowledge_metrics.py --output /tmp/knowledge-metrics.json
```

Finally push and verify GitHub Actions.

Required final state:

```text
generated-and-registry = success
python-tests = success
Windows ledger/runtime = success
whitespace = success
```

---

# 5. Security invariants to re-check after every commit

```text
UNKNOWN != ABSENT
```

```text
incomplete compilation cannot prove absence
```

```text
Screen cannot produce REVIEWED_SAFE or CONFIRMED
```

```text
Deep Review cannot be skipped for a candidate
```

```text
CONFIRMED requires prior SUSPICIOUS + Proof
```

```text
SUSPICIOUS cannot enter final severity/reporting
```

```text
only complete authoritative state can produce COMPLETE_CLEAN
```

```text
optional code-index corruption disables navigation but does not fabricate
authoritative audit invalidity
```

```text
runtime Markdown remains derived and body-hash verified
```

```text
routing recall is not reduced to save context/tokens
```

---

# 6. Explicit non-goals

Do not:

- replace deterministic routing with an LLM router;
- turn code-index into authoritative reachability evidence;
- allow missing code-index to block an otherwise valid audit;
- weaken proof evidence to simplify lifecycle validation;
- add a database;
- rewrite the canonical knowledge corpus as part of these fixes;
- change default Codex stage/model recommendations unless separately requested;
- add unrelated CI matrices;
- perform a large directory restructure;
- optimize candidate count at the cost of routing recall.

---

# 7. Completion report Codex must provide

When finished, return:

## Implemented

For every item:

```text
P1.1: DONE / PARTIAL / NOT DONE
P1.2: ...
...
```

## Root causes

Explain the actual root cause of every fixed bug.

## Files changed

Group by plan item.

## Schema changes

For each bump:

- old version;
- new version;
- compatibility behavior;
- migration impact.

## Tests added

List exact regression test names.

## Commands run

List commands actually executed.

## Results

Include:

- full unit tests;
- routing benchmark;
- registry/provenance validation;
- whitespace;
- heavy/e2e checks if run;
- GitHub Actions status.

## Remaining risks

Explicitly list deferred items.

Do not claim a P1 item complete without a regression test.

---

# 8. Definition of done

This plan is complete only when:

1. revision-1 Proof records cannot bypass Deep Review;
2. `CONFIRMED` requires an actual preceding `SUSPICIOUS`;
3. a modified code-index body cannot remain `CURRENT`;
4. every accepted code index is relationally consistent and can produce schema-valid queries;
5. code-context flags have explicit tested output semantics;
6. Windows CI is green without skipping ledger correctness;
7. final report outputs have a verifiable generation boundary;
8. routing benchmark field semantics are no longer conflated;
9. duplicated CI work is reduced without removing critical coverage;
10. the full required validation suite is green.

If scope must be reduced, finish P1.1–P1.4 first and leave P2/P3 explicitly documented as follow-up. Correctness takes priority over refactoring.
