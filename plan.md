# PLAN — EVM Audit Skills Hardening, Correctness, and Maintainability

Repository: `iavl/evm-audit-skills-standalone`  
Baseline reviewed: `main` at `6074455d850fefecbe3fdaa94044738e76d7547a`  
Primary goal: fix correctness/integrity bugs without weakening the repository's conservative, fail-closed audit semantics.

---

## 0. Execution rules for Codex

Implement this plan in priority order. Do not perform a broad refactor before the P1 correctness items and their regression tests are green.

### Security invariants that MUST NOT change

Preserve all of the following behavior:

- `UNKNOWN != ABSENT`.
- Incomplete compilation must never establish trusted absence.
- Inferred predicate falsehood must not become a trusted filter.
- Screen may only produce `CANDIDATE` or `NOT_APPLICABLE_CONFIRMED`.
- Deep Review must consume only Screen candidates.
- `SUSPICIOUS` must require a later `PROOF` event.
- Only `CONFIRMED` findings may enter the final report.
- A `CONFIRMED` record must remain proof-gated and require strong evidence.
- Routing, review, source, compilation, and registry lineage must remain snapshot-bound.
- Generated Markdown is a view; machine-readable JSON/JSONL remains authoritative.
- `data/canonical-checks.json` remains the authoritative checklist knowledge source.
- Do not edit generated per-domain checklist Markdown by hand when the generator is the source of truth.
- The code index is a navigation hint only; source code is authoritative.
- Do not trade recall for token savings.

### General implementation rules

- Prefer pure helpers in `evm_audit_runtime/` for reusable logic, but keep CLI compatibility.
- Keep Python 3.12 compatibility.
- Keep `requirements-runtime.lock` fully pinned.
- All new JSON shapes must be schema-validated.
- All generated run artifacts that can affect model behavior must be written atomically.
- Every bug fix below must include a regression test that fails before the fix and passes after it.
- Run the complete existing suite after every P1 phase.
- Avoid unrelated formatting churn in `data/canonical-checks.json` and generated checklist files.
- If a schema/version bump is necessary, document compatibility behavior explicitly.

---

# P1 — Correctness and audit-integrity fixes

## P1.1 Fix real Slither call-graph extraction in `code-index`

### Problem

`scripts/code_context.py::build_code_index()` currently treats several Slither APIs as if they directly returned `Function` objects.

The pinned Slither API (`slither-analyzer==0.11.6`) does not have that shape:

- `Function.internal_calls` contains `InternalCall` IR objects.
- `Function.high_level_calls` contains `(Contract, HighLevelCall)` tuples.
- `Function.library_calls` contains `LibraryCall` IR objects.
- `Function.low_level_calls` contains `LowLevelCall` IR objects.

The current `_name(value)` path therefore cannot reliably resolve the real callee for internal/high-level/library calls. The synthetic unit test currently constructs an already-correct index and only tests `lookup()`, so it does not detect the generator bug.

This is security-relevant because the Master Skill explicitly asks the model to use the code index for targeted source loading and caller/callee expansion. A broken graph can hide a reachable path from the model.

### Target files

- `scripts/code_context.py`
- `schemas/code-index.schema.json` only if required
- `tests/test_plan_hardening.py` or preferably a new focused `tests/test_code_context.py`
- `tests/fixtures/...` for real Solidity call-graph fixtures
- `skills/evm-audit-master/SKILL.md` only if behavior/documentation changes
- `docs/recon-and-routing.md`
- `docs/audit-runtime.md` if artifact semantics change

### Required implementation

1. Add explicit Slither adapters instead of calling `_name()` on arbitrary objects.

   Implement helpers with narrow responsibilities, for example:

   - `_function_identity(function, scope_root, build_root, audit_files) -> str`
   - `_resolve_internal_call(ir) -> Function | None`
   - `_resolve_high_level_call(item) -> tuple[Function | None, metadata]`
   - `_resolve_library_call(ir) -> Function | None`
   - `_describe_low_level_call(ir) -> metadata`
   - `_source_location(value_or_ir, ...)`

2. For `InternalCall`:
   - resolve the callee through `ir.function` when it is a concrete Solidity function;
   - do not convert `SolidityCall` or dynamic/unresolved calls into fake function IDs.

3. For `high_level_calls`:
   - unpack `(target_contract, ir)`;
   - inspect `ir.function`;
   - handle public state-variable getters and unresolved call targets safely;
   - never assume `ir.function` is always a `Function`.

4. For `LibraryCall`:
   - resolve `ir.function` when available;
   - avoid double-counting a library call through both `high_level_calls` and `library_calls`.

5. For low-level calls:
   - preserve the call as an edge/event with a precise `kind` such as `call`, `delegatecall`, `staticcall`, or `callcode`;
   - only create a graph callee edge when a concrete function can actually be resolved;
   - otherwise retain a target-expression descriptor rather than fabricating a callable function ID.

6. Correct `storage_writes` semantics:
   - use Slither's `state_variables_written`, not `variables_written`;
   - local-variable assignments must not appear in the top-level `storage_writes` collection;
   - if the per-function `writes` field intentionally contains all writes, rename it or add separate `state_reads` / `state_writes` fields so the artifact is unambiguous.

7. Record the actual call/write source location:
   - do not assign every call/write to the containing function's first line;
   - use the IR/node source mapping whenever possible;
   - fall back to the function location only when the IR location is genuinely unavailable, and mark that fallback if the schema supports it.

8. Ensure all code-index collections are deterministically ordered.

### Stable identity / collision requirement

Current keys such as `ContractName.function(...)` can collide when two source units contain the same contract name/signature.

Do not silently overwrite entries.

Implement one of these safe approaches:

- Preferred: path-qualified stable IDs, e.g. `src/A.sol::Vault.deposit(uint256)`.
- Alternative: an explicit stable `function_id` derived from normalized source path + canonical function name.

Requirements:

- user-facing display names may remain short;
- internal graph edges must use collision-safe IDs;
- `lookup()` must support exact stable IDs and a short-name search that returns an ambiguity error when more than one match exists;
- never choose one ambiguous function silently.

If changing the index format, either:
- bump the code-index schema version and make old indexes explicitly unsupported for navigation; or
- add backward-compatible optional fields without weakening collision detection.

Because the code index is non-authoritative, an old/invalid index must be ignored/rejected as a navigation hint rather than making a valid audit state appear clean.

### Regression tests

Add a REAL Slither-backed integration fixture and invoke `build_code_index()`, not only `lookup()` on a hand-written dictionary.

Fixture must include at least:

- external entry function -> internal helper;
- internal helper -> another internal function;
- contract A -> high-level call into contract B;
- library call;
- low-level call;
- delegatecall if practical;
- state-variable write;
- local-variable write;
- modifier;
- inheritance;
- overloaded function;
- two same-name contracts/functions in different source files if Solidity fixture layout permits it.

Assertions:

- expected internal edge exists;
- expected high-level edge exists;
- library call is represented once;
- unresolved low-level call is represented but is not fabricated as a concrete callee;
- local-variable write is absent from `storage_writes`;
- real state-variable write is present;
- call/write line numbers point to the call/write site rather than the function declaration line where Slither provides the mapping;
- ambiguous short-name lookup fails with a clear error;
- caller/callee expansion returns the correct functions.

### Acceptance criteria

- New real-Slither integration test fails on the old implementation.
- `python3 -m unittest discover -s tests -v` passes.
- `python3 scripts/benchmark_routing.py` passes.
- `python3 scripts/generate_checklists.py --check` passes.
- `python3 scripts/validate_checklists.py --strict` passes.
- No existing routing or review state is silently changed by the code-index fix.

---

## P1.2 Cryptographically bind runtime Markdown body to its `.meta.json`

### Problem

`audit_run.py::_runtime_view_current()` currently considers a Deep/Proof runtime view current when:

- the Markdown file exists;
- the sidecar exists;
- the sidecar JSON exactly equals the expected metadata.

It does NOT verify that the Markdown body itself still matches the sidecar.

Therefore a modified, truncated, or partially rewritten model-facing runtime Markdown file can be reused as "current" as long as the old sidecar remains unchanged.

This weakens the repository's artifact-integrity guarantees and can feed stale/tampered instructions/checks to the audit model.

### Target files

- `scripts/render_runtime.py`
- `scripts/audit_run.py`
- `scripts/audit_artifacts.py` if a shared file-hash helper is added
- optional new `schemas/runtime-metadata.schema.json`
- `tests/test_hardening.py`
- `tests/test_audit_run.py`
- `docs/audit-runtime.md`

### Required implementation

1. Add a SHA-256 digest of the exact UTF-8 runtime Markdown body to the sidecar.
   Suggested field:
   - `runtime_sha256`

2. Split sidecar metadata conceptually into:
   - immutable expected identity fields;
   - rendered-body digest.

3. Update runtime generation flow:
   - render Markdown into memory;
   - compute SHA-256 of exact bytes;
   - atomically write Markdown;
   - atomically write sidecar containing identity + `runtime_sha256`.

4. Update `_runtime_view_current()`:
   - parse sidecar;
   - verify all expected identity fields;
   - verify `runtime_sha256`;
   - hash the actual Markdown bytes and compare;
   - return false on any mismatch or parse/read error.

5. Use the existing atomic artifact helpers instead of raw `Path.write_text()` for runtime Markdown and sidecar writes.

6. Apply the same integrity pattern to Screen runtime if the controller ever reuses it based on metadata. At minimum ensure Screen writes are atomic.

### Regression tests

- Generate a Deep runtime view.
- Modify only the `.md`; leave `.meta.json` unchanged.
- Call controller `next` again.
- Assert the runtime view is regenerated and the tampered body is not reused.

Also test:

- corrupt/truncate `.md`;
- corrupt `.meta.json`;
- change only `runtime_sha256`;
- interrupted-write style state where old sidecar exists with a different body;
- unchanged body + unchanged identity is reused.

### Acceptance criteria

- A model-facing runtime file can never be reused solely because identity metadata matches.
- The body hash is checked every time a cached runtime view is reused.
- Existing fail-closed state semantics remain unchanged.

---

## P1.3 Do not silently fall back when the real compilation closure escapes `build_root`

### Problem

`scripts/recon.py::compilation_unit_paths()` returns `None` if ANY file in Slither's actual compilation closure resolves outside `build_root`.

`build_feature_map()` then passes `compilation_files=None` to `compilation_digests()`.

That triggers the conservative "scan all Solidity under build_root" fallback.

This fallback is over-broad inside the root but, critically, it omits the compiled dependency that was outside the root. An external/sibling/remapped/symlinked compiled source can therefore change without changing `compilation_input_digest`.

That violates the intended stale-artifact lineage guarantee.

### Target files

- `scripts/recon.py`
- `scripts/scope_context.py`
- `tests/test_plan_hardening.py` or a new `tests/test_compilation_lineage.py`
- `docs/recon-and-routing.md`
- `docs/audit-runtime.md`

### Required implementation

Distinguish these states:

1. **Closure available and fully representable**
   - hash exactly the Slither compilation closure.

2. **Closure API unavailable**
   - allow the existing conservative build-root fallback, but record that fallback mode explicitly in Recon quality/provenance.

3. **Closure contains a compiled source outside build_root**
   - DO NOT silently convert this into state (2).

For the first safe implementation, fail closed with a clear error such as:

`compiled source is outside build_root; choose a build_root that contains the complete compilation closure: <path>`

If you choose to support external closure files instead, all external inputs MUST receive a stable normalized identity and their bytes MUST be included in the compilation digest. Do not hash only the path.

### Symlink requirement

Resolve symlinks before deciding whether a file is inside `build_root`.

A source that appears lexically inside the root but resolves outside must be handled as an external compiled input.

### Recon provenance

Add enough metadata to distinguish:

- `EXACT_COMPILATION_CLOSURE`
- `CONSERVATIVE_BUILD_ROOT_FALLBACK`

The fallback must not be presented as exact closure provenance.

### Regression tests

Add tests for:

- exact in-root closure;
- unrelated uncompiled Solidity file does not change the exact closure digest;
- compiled sibling source outside build root fails closed;
- symlink inside build root pointing to external Solidity fails closed or is explicitly external-hashed;
- changing an actual compiled dependency changes `compilation_input_digest`;
- changing a noncompiled unrelated file does not change the exact closure digest.

### Acceptance criteria

There is no path where Recon observes an out-of-root compiled file and then produces a compilation digest that excludes its bytes.

---

## P1.4 Make review-ledger concurrency portable and crash-safe

### Problem

`review_ledger.py` uses `fcntl.flock()` when available.

On Windows, `fcntl` is unavailable and `_ledger_lock()` currently becomes a no-op.

That means multiple agents/processes can race on:

- reading the current revision;
- calculating the next revision;
- creating the checkpoint;
- appending JSONL records.

The repository explicitly allows parallel Domain work when supported, so the ledger layer must not silently lose its serialization guarantees on a supported Python platform.

### Target files

- `scripts/review_ledger.py`
- preferably a small shared locking helper under `evm_audit_runtime/`
- `requirements-runtime.lock` only if a small lock dependency is intentionally introduced
- `tests/test_review_ledger_concurrency.py`
- `.github/workflows/validate.yml`
- docs describing concurrency guarantees

### Required implementation

Implement a portable cross-process lock.

Preferred order:

1. a small internal abstraction using:
   - `fcntl` on POSIX;
   - `msvcrt` or another reliable built-in mechanism on Windows;

OR

2. use a well-maintained pinned cross-platform locking dependency if the built-in implementation becomes error-prone.

Correctness is more important than read concurrency. It is acceptable for Windows reads to use an exclusive lock if necessary.

### Append durability

While holding the writer lock:

- compute the next revision;
- validate the transition;
- serialize complete line(s);
- append checkpoint + first record as one logical write operation when creating a new ledger;
- flush and `fsync()` before releasing the lock.

Do not rewrite the entire append-only ledger during a normal append.

### Regression tests

Use multiple processes, not only threads.

Test:

1. concurrent appends of different canonical IDs into one ledger;
2. race where two processes both attempt the first revision for the same ID;
3. concurrent reader while writer appends;
4. resulting file is parseable JSONL;
5. no lost records;
6. no duplicate revision is accepted;
7. every completed ledger passes `validate_records()`.

Create a lightweight Windows CI job for the ledger tests if full Slither-on-Windows CI is undesirable.

### Acceptance criteria

- No platform silently falls back to "unlocked".
- Racing writes either serialize correctly or one writer fails cleanly.
- JSONL remains append-only and valid after concurrency tests.

---

# P2 — Reliability, precision, and developer-experience improvements

## P2.1 Make final report regeneration transactional

### Problem

`report_run()` deletes:

- `AUDIT-REPORT.md`
- `issue-candidates.json`

before `_load_run()`, audit-state validation, reporting-input validation, and synthesis have successfully completed.

A bad report invocation or malformed severity/finding-details input can therefore destroy a previously valid deliverable before the new one exists.

### Target files

- `scripts/audit_run.py`
- `scripts/synthesize_report.py` only if needed
- `tests/test_reporting.py`
- `tests/test_hardening.py`

### Required implementation

- Do all validation and report synthesis in memory first.
- Only after successful synthesis, atomically replace:
  - `AUDIT-REPORT.md`
  - `issue-candidates.json`
- Treat both as one logical output generation step.
- If the new report cannot be generated, leave the previous files untouched OR explicitly archive them as stale with lineage metadata. Do not silently delete them first.
- Never present an old report as current if its bound review state no longer matches; if needed add a small report metadata sidecar or stale archive naming.

### Regression tests

- Start with a valid generated report.
- Re-run report with malformed reporting input.
- Assert command fails.
- Assert the previous report is not partially replaced/deleted.
- Then run with valid input and assert both outputs are atomically replaced.

---

## P2.2 Improve code-context traversal without exploding model context

### Goal

The Master Skill says to expand callers/callees when reachability is uncertain. Current lookup is one hop and loses useful edge semantics.

### Target files

- `scripts/code_context.py`
- `skills/evm-audit-master/SKILL.md`
- tests

### Required implementation

Add bounded graph traversal:

- `--depth N`, default `1`;
- `--max-nodes N`, conservative default such as `25`;
- cycle detection;
- deterministic BFS/DFS order;
- explicit truncation flag if max-nodes is hit.

Return:

- selected functions;
- source ranges;
- caller edges;
- callee edges;
- unresolved external/low-level edges;
- truncation metadata.

Do not automatically dump source code into the index output. Keep it a navigation structure.

### Acceptance criteria

- A two-hop internal reachability fixture can be expanded with `--depth 2`.
- Cycles terminate.
- A large graph is capped deterministically.
- The Master Skill continues to require source verification.

---

## P2.3 Normalize code-index paths and remove host-specific absolute-path leakage

### Problem

For dependencies outside the audit-scope directory, `_location()` may store absolute machine paths.

For single-file audit scopes it can reduce dependency paths to only `basename`, which can collide.

### Required implementation

Normalize index locations relative to `build_root` whenever possible.

Use an explicit namespace for locations that cannot be represented relative to the build root, for example:

- `build://src/Vault.sol`
- `external://<stable-id>/Dependency.sol`

Do not use basename-only identity for dependency files.

Do not use host absolute paths as graph identity.

If an absolute path must be shown for diagnostics, keep it outside the deterministic identity and never hash it into a portable artifact identity unless that behavior is intentional and documented.

### Tests

- same basename in two different directories;
- dependency file outside audit root but inside build root;
- no accidental function/contract overwrite;
- deterministic index across equivalent repository locations where intended.

---

## P2.4 Move optional code-index failure out of authoritative audit-state semantics

### Goal

The code index is documented as a navigation hint, not authoritative security evidence.

### Required implementation

Review `_load_run()` behavior.

Currently, if `recon/code-index.json` exists and validation fails, loading the run raises.

Refine this behavior so that:

- authoritative lineage failures still fail closed;
- an invalid optional navigation index cannot be consumed;
- but the audit's authoritative routing/review state is not falsely reclassified as secure/clean because of it;
- controller output clearly reports that code-index navigation is unavailable/stale and must not be used.

Recommended behavior:

- validate index before exposing it to the model;
- if invalid, mark it unusable and require regeneration for navigation;
- keep audit-state derivation independent from the optional hint.

Add tests for stale/invalid code index with otherwise valid routing/review artifacts.

---

## P2.5 Strengthen normal CI around the gaps found in this review

The latest `Validate checklist corpus` workflow is green, so new tests must specifically cover the missing behaviors rather than duplicating existing checks.

### Update `.github/workflows/validate.yml`

Normal PR CI should include:

- real Slither-backed code-index generation test;
- runtime Markdown body-integrity/tamper test;
- compilation-closure external-path lineage test;
- report transactionality test;
- concurrency unit/integration tests appropriate for Linux;
- a lightweight Windows ledger-lock job.

Keep the existing:

- generated checklist check;
- strict registry/provenance validation;
- routing regression benchmark;
- full unittest discovery;
- whitespace check.

Do not move heavy weekly EIP-6780 / Foundry quality work into every PR unless runtime cost is acceptable.

---

## P2.6 Add targeted type/API guards around third-party analyzer integration

### Goal

Prevent another Slither API shape mismatch.

### Required implementation

Do not attempt a repo-wide type-checking migration in the same PR.

Instead:

- isolate Slither object-shape handling inside a small adapter layer;
- annotate adapter inputs/outputs where practical;
- add runtime `isinstance`/shape validation around:
  - `InternalCall`;
  - `HighLevelCall`;
  - `LibraryCall`;
  - `LowLevelCall`;
  - concrete `Function`;
  - state-variable getter cases;
- fail with a clear diagnostic when a new Slither version produces an unsupported shape;
- include the detected Slither version in the diagnostic.

Consider a small compatibility test that asserts assumptions against the pinned Slither version.

---

# P3 — Maintainability improvements after correctness is stable

## P3.1 Reduce giant-script coupling

The following scripts currently contain both CLI orchestration and substantial domain logic:

- `scripts/audit_run.py`
- `scripts/select_checks.py`
- `scripts/validate_checklists.py`
- `scripts/review_ledger.py`
- `scripts/render_runtime.py`

Do this only after P1/P2 tests are green.

### Refactor direction

Move pure logic incrementally into `evm_audit_runtime/`, for example:

- `evm_audit_runtime/artifacts.py`
- `evm_audit_runtime/code_index.py`
- `evm_audit_runtime/review.py`
- `evm_audit_runtime/controller_state.py`
- `evm_audit_runtime/environment.py`

Keep `scripts/*.py` as thin backward-compatible CLI adapters.

Do not rename public CLI flags during this refactor.

### Acceptance criteria

- existing CLI commands retain behavior;
- test fixtures do not need mass rewrites;
- imports no longer rely on repeated try/except script-vs-package fallbacks for newly extracted code.

---

## P3.2 Centralize artifact/schema version constants

Versions are currently spread across code and schemas, e.g. routing v7, review-record v7, feature-map v4, code-index v1.

Create one small version module or a validation table.

Add a test that ensures:

- code constant;
- schema `$id` / `const`;
- docs where machine-parsed;
- generated artifact version

do not drift.

Do not make the runtime dynamically trust a schema version merely because a file claims it. Supported versions must remain explicit.

---

## P3.3 Centralize runtime rendering limits

The renderer and validators currently contain their own compactness constraints such as Screen gate lengths.

Create shared constants for model-facing limits where the same semantic limit is enforced in multiple places.

Examples:

- max Screen gate length;
- code-context max default nodes;
- optional max proof-context fields if introduced.

Add tests so validator and renderer cannot drift.

---

## P3.4 Expand benchmark coverage for audit recall, not just byte size

Keep the current token/byte-efficiency benchmark, but add regression fixtures that measure correctness.

At minimum maintain fixtures for:

- access control;
- proxy/upgradeability;
- external call / delegatecall;
- oracle;
- ERC4626;
- lending/liquidation;
- precision math;
- governance;
- chain/fork-specific semantics;
- dependency-only feature presence;
- incomplete compilation.

For every fixture define expected:

- selected Domains;
- deferred Domains;
- filtered Domains;
- must-include canonical checks;
- checks that may safely filter;
- no known false-negative cases.

A routing optimization must fail CI if it reduces expected recall, even if runtime bytes decrease.

---

# P3 — Skill/prompt quality improvements

## P3.5 Keep global safety rules centralized; keep Domain Skills domain-specific

The current architecture is already moving in the correct direction: the global reachable-path / proof-gating contract is centralized in the Master reference instead of being copied into every generated check.

Preserve that pattern.

Review Domain Skills for duplicated generic instructions and remove only duplicates that are already guaranteed by the Master contract.

Do NOT remove domain-specific requirements such as:

- oracle freshness/scaling/sequencer checks;
- ERC4626 preview/rounding/donation checks;
- chain-specific opcode/system-contract semantics;
- lending liquidation/economic checks.

Acceptance criterion:

- Domain Skill context becomes smaller without losing a domain-specific security instruction.

---

# P4 — Documentation and operator clarity

## P4.1 Document authoritative vs non-authoritative artifacts

Create a compact table in `docs/audit-runtime.md`:

| Artifact | Authoritative? | Snapshot bound? | Can affect clean completion? | Regenerable? |
|---|---:|---:|---:|---:|
| feature-map | yes | source/compilation | yes | yes |
| routing manifest | yes | routing snapshot | yes | yes |
| code-index | no, navigation hint | source/compilation | no | yes |
| domain-resolution | yes | routing | yes | yes |
| domain-context | yes | routing | yes | yes |
| screen-results | yes | routing | yes | yes |
| review JSONL | yes | review snapshot | yes | append-only |
| runtime Markdown | no, generated view | body + snapshot | no direct state authority | yes |
| severity/finding details | reporting input | review-state digest | report only | yes |
| final report | deliverable | review/report lineage | n/a | yes |

Make sure implementation matches the documentation.

---

# Suggested implementation sequence

Use separate commits/PR-sized steps where practical.

## Commit 1 — Code-index correctness

- Fix Slither IR adapters.
- Fix storage-write semantics.
- Add path-safe function identity.
- Add real Slither integration fixture/tests.
- Keep lookup backward-compatible where possible.

## Commit 2 — Runtime view integrity

- Add `runtime_sha256`.
- Atomic runtime writes.
- Body verification before cache reuse.
- Tamper/interrupted-write regression tests.

## Commit 3 — Compilation lineage hardening

- Distinguish exact closure vs fallback.
- Fail closed on out-of-build-root compiled inputs or explicitly hash them.
- Add symlink/external dependency tests.

## Commit 4 — Ledger concurrency

- Portable locking.
- durable append.
- multiprocessing tests.
- lightweight Windows CI.

## Commit 5 — Report transactionality

- Synthesize/validate before replacing outputs.
- atomic paired output writes.
- failure-preserves-previous-output tests.

## Commit 6 — Bounded code-context traversal + docs

- depth/max-node traversal.
- unresolved edge metadata.
- Master Skill guidance update.
- artifact authority table.

## Commit 7 — Maintainability refactor

- only after all prior tests are green;
- extract pure runtime helpers;
- centralize versions/limits;
- preserve CLI API.

---

# Mandatory validation commands before completion

Run all applicable commands from repository root:

```bash
python3 -m pip install -r requirements-runtime.lock

python3 scripts/generate_checklists.py --check
python3 scripts/validate_checklists.py --strict
python3 scripts/benchmark_routing.py

python3 -m unittest discover -s tests -v

git diff --check
```

If Foundry is available, also run the heavy checks that are normally scheduled:

```bash
python3 scripts/benchmark_routing.py --e2e

bash tests/semantics/test_eip6780_differential.sh paris
bash tests/semantics/test_eip6780_differential.sh cancun

python3 scripts/knowledge_metrics.py --output /tmp/knowledge-metrics.json
```

Do not mark the work complete if any pre-existing test becomes skipped merely to make CI green.

---

# Required final Codex report

When implementation is complete, return a Markdown summary containing:

1. exact commits/files changed;
2. each plan item completed / deferred;
3. root cause of every fixed bug;
4. regression test added for each bug;
5. any schema/version migration;
6. backward-compatibility notes for existing `audits/*` runs;
7. full test commands executed and results;
8. any remaining known risks;
9. whether generated checklist files changed and why;
10. whether routing recall/benchmark results changed.

Do not claim the code-index call graph is authoritative security evidence. It remains a navigation optimization whose output must be verified against Solidity source.
