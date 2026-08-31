# evm-audit-skills

---

## What This Is

Each skill is a structured, sourced checklist of **non-obvious** security vulnerabilities for a specific domain. The canonical JSON registry keeps one stable attack hypothesis per root cause while generated Markdown views remain easy for audit runtimes to consume.

**869 canonical checks and 872 generated runtime entries across the 19 domain skills plus the master index.**

---

## Skills

Start with `evm-audit-master`. Domain definitions and relationships live in
`domains/*.json`; the generated [domain catalog](evm-audit-master/references/domains.md)
lists every independently invokable domain skill and its current runtime count.

## Repository Sources and Lineage

The table distinguishes repositories whose checklist content was merged from repositories used only as references or for coverage comparison.

| Repository | Relationship to this suite | Scope / revision |
|---|---|---|
| [austintgriffith/evm-audit-skills](https://github.com/austintgriffith/evm-audit-skills) | Base repository / current fork parent | Original 20-skill structure and initial checklists |
| [OpenZeppelin Contracts ERC4626 guide](https://docs.openzeppelin.com/contracts/5.x/erc4626) | Official implementation reference | Fee-aware asset/share conversion context |
| [sanbir/solidity-auditor-skills](https://github.com/sanbir/solidity-auditor-skills) | Merged and adapted | 166 source-level deduplicated `SAS-AV` checks; commit `b864c2ee3b2f63c4361a5064084ce1e99dcf7444`; MIT |
| [gdroz3r/drozer-lite](https://github.com/gdroz3r/drozer-lite) | Merged and adapted | 177 EVM checks; commit `fcc489d7eb14208bedcb6290b7b8ca5af6058539`; MIT |
| [auditmos/skills](https://github.com/auditmos/skills) | Merged and adapted | 116 attack-vector patterns; commit `c9583babb0ce189d9f39a05caf94b5a5da655010`; MIT |
| [devdacian/ai-auditor-primers](https://github.com/devdacian/ai-auditor-primers) | Reference only | Primer patterns cross-referenced and integrated selectively; no full repository copied |
| [d-xo/weird-erc20](https://github.com/d-xo/weird-erc20) | Reference only | Non-standard ERC20 behavior catalog |
| [juancito-dev/multichain-auditor](https://github.com/juancito-dev/multichain-auditor) | Reference only | Cross-chain deployment and EVM-chain pitfalls; formerly recorded as `0xJuancito/multichain-auditor` |
| [tamjidahmed0/smart-contract-audit-checklist](https://github.com/tamjidahmed0/smart-contract-audit-checklist) | Reference only (historical) | Practical Solidity footguns from the recorded source checklist; the original repository was unavailable when rechecked |
| [nascentxyz/simple-security-toolkit](https://github.com/nascentxyz/simple-security-toolkit) | Reference only | DeFi security and audit-readiness guidance |
| [SmartContractSecurity/SWC-registry](https://github.com/SmartContractSecurity/SWC-registry) | Reference only | Archived weakness taxonomy used for legacy `SWC-*` provenance |
| [alt-research2/SolidityGuard](https://github.com/alt-research2/SolidityGuard) | Coverage comparison only | No text, code, identifiers, or directory structure imported |

The three rows marked “Merged and adapted” represent external repository content incorporated into the runtime checklists; the base row records the original lineage. The SolidityGuard comparison used commit `35645e8ba76cdacbeec40f347c758de2077e2ecd`; resulting gap checks were independently written from public EIP, SWC, and ERC-4337 references.

External source integration is preserved as provenance, not counted as separate attack vectors. Edit [`data/canonical-checks.json`](data/canonical-checks.json) for security knowledge or `domains/*.json` for domain metadata, then run `python3 scripts/generate_checklists.py` to update the generated checklists, Skill wrappers, and domain catalog. Semantic merges require the same root cause, trigger, proof obligation, and impact; otherwise related contextual checks remain distinct.

---

## How To Use

### Run an audit

Just provide the workflow with a contract:

```
audit this contract and file issues: https://github.com/owner/repo/blob/main/contracts/MyContract.sol
```

The workflow will:
1. Load `evm-audit-master` and build a source, dependency, chain, and evidence-backed feature map.
2. Use Slither-backed reconnaissance and `data/features.json` to emit one immutable routing-v6 manifest; only curated predicates proven false are filtered.
3. Render Screen from the manifest, classify only `NOT_APPLICABLE_CONFIRMED` or `CANDIDATE`, resolve Deferred Domains, then render Deep from candidates only.
4. Write exactly one JSONL Deep/proof record per candidate; filtered IDs remain only in the machine manifest.
5. Independently derive `audit-state.json`; synthesize only `CONFIRMED` records into a final `AUDIT-REPORT.md` and assign severity there.
6. File GitHub issues only for confirmed Medium+ findings when explicitly in scope.

### Runtime-neutral execution

If the runtime supports sub-agents:

- Parallelize independent domain reviews.
- Respect the runtime's concurrency limits.
- Reuse the reconnaissance/source context; do not duplicate source ingestion.
- Use the strongest appropriate available reasoning model.

If sub-agents are unavailable:

- Execute domains sequentially.

### Canonical source and validation

The editable source is [`data/canonical-checks.json`](data/canonical-checks.json).
The generator is a pure renderer and never repairs or overrides registry
knowledge; one-time schema/knowledge transformations live in
[`scripts/migrations/`](scripts/migrations/). The checked-in migrations have
already been applied; ordinary maintenance edits the registry or domain config
and renders without a migration step.
The pinned Python runtime roots are listed in
[`requirements-runtime.txt`](requirements-runtime.txt), with the resolved
snapshot in [`requirements-runtime.lock`](requirements-runtime.lock); CI uses
Python 3.12 and the pinned compiler in [`solc-version.txt`](solc-version.txt).
It is a machine database and should not be loaded into model context. Feature
definitions live in [`data/features.json`](data/features.json); the input shape
is documented in [`data/feature-map.schema.json`](data/feature-map.schema.json).
A v4 reconnaissance feature map uses `PRESENT`, `ABSENT_CONFIRMED`, or
`UNKNOWN`, and carries a scope-bound `recon_context` with the analyzed files,
compilation completeness, tool versions, and source digest. Non-v4 maps are
rejected. Evidence for confirmed states is typed with `kind`, `location`, and
`reason`; absence is accepted only when the feature's `absence_policy` allows
the evidence kind.

Each canonical check stores an explicit `all_of`/`any_of`/`none_of` predicate.
Historically keyword-derived predicates are marked `inferred`; hand-reviewed
combinations are marked `curated`. A `FALSE` result can filter only a curated
predicate. An inferred `FALSE` is downgraded to `UNKNOWN` and remains selected,
so keyword inference can improve recall but cannot prove non-applicability.

Build the initial feature map from Slither's AST/IR, then supplement remaining
`UNKNOWN` features from deployment evidence:

```bash
python3 scripts/recon.py <target-project-or-solidity-file> --audit-root <target-repo> \
  --output recon-features.json
```

```bash
python3 scripts/select_checks.py --feature-map recon-features.json --target-root <target-repo> \
  --chain-id <id> --chain-family <family> --execution-environment <environment> \
  --fork-block <block> --compiler-version <version> --evm-fork <fork> \
  --manifest-out routing/manifest.json --context-out context.json \
  --environment-out routing/environment-context.json \
  --format json
```

The v6 manifest records selected, Deferred, and filtered Domain/check stages;
registry, source, dependency, build-config, and compilation fingerprints; and
evidence-backed environment facts. `fork_block` is reproducibility metadata,
not hardfork inference. Render the runtime views and conservative artifact
templates with:

```bash
python3 scripts/render_runtime.py --manifest routing/manifest.json --profile screen \
  --output runtime/screen.md --screen-results-out reviews/screen-results.json \
  --domain-resolution-out reviews/domain-resolution.json
python3 scripts/render_runtime.py --manifest routing/manifest.json --profile deep \
  --screen-results reviews/screen-results.json --output runtime/deep.md
```

Screen contains only ID/title/trigger/detection; only `CANDIDATE` cards reach
Deep. Resolve Deferred Domains and rerun Screen with `--domain-resolution`
before Deep when a Deferred Domain is `PRESENT`. `LIKELY_SAFE` is not a valid
state.

Regenerate and validate the runtime views with:

```bash
python3 scripts/generate_checklists.py --check
python3 scripts/validate_checklists.py --strict
python3 -m unittest discover -s tests -v
forge test --root tests/semantics -vv
python3 scripts/validate_audit_run.py --manifest routing/manifest.json \
  --screen-results reviews/screen-results.json \
  --domain-resolution reviews/domain-resolution.json \
  --ledger reviews/review-<owner-domain>.jsonl \
  --output audit-state.json
python3 scripts/knowledge_metrics.py
```

Knowledge claims distinguish `official`, genuinely `executable`, and
`text-regression` evidence. Text regression protects wording but cannot by
itself establish factual correctness. Versioned and time-sensitive checks carry
`verified_at` metadata; the scheduled knowledge-health workflow reports stale
or unverified entries, broken official sources, and semantic-test regressions in
one deduplicated issue.

Third-party license text lives in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). It does not declare a
license for independently authored repository content; that content is
licensed by [`LICENSE`](LICENSE).

### Installation layout

This repository is a suite, not a collection of independently installable
domain folders. Keep the shared `data/`, `scripts/`, and
`evm-audit-master/` siblings together under one installed suite directory; any
top-level discovery symlinks must resolve back into that directory. The
packaging smoke test exercises this layout without modifying the user's
installed skills.

Model-specific `known/partial/novel` snapshots are retained only under
`benchmarks/model-knowledge/`; they are not runtime inputs.

### The audit pipeline

```
Contract URL/path
      │
      ▼
  RECON + FEATURE MAP
      │
      ▼
  IMMUTABLE ROUTING (v6 manifest: selected + deferred + filtered IDs)
      │
      ▼
  SCREEN → CANDIDATE-ONLY DEEP REVIEW (parallel when supported; sequential otherwise)
  ├── candidate domain → review-<skill>.jsonl
  └── filtered IDs remain machine-readable in routing-manifest.json
      │
      ▼
  PROOF (PoC / invariant) → CONFIRMED candidates
      │
      ▼
  SYNTHESIS (validate coverage, deduplicate, score severity)
      │
      ▼
  AUDIT-REPORT.md + GitHub Issues
```

---

## Review Ledger and Confirmed Finding Format

Each candidate canonical ID receives one JSONL review record. Filtered IDs are kept in
the routing manifest and do not generate per-check Markdown records. Deep/proof
candidates include snapshot/hash identity, applicability, code path, preconditions, exploitability,
impact, PoC/invariant evidence, and exactly one of `NOT_APPLICABLE`,
`REVIEWED_SAFE`, `SUSPICIOUS`, or `CONFIRMED`. Use the compact runtime contract
at [`evm-audit-master/references/check-review-contract.runtime.md`](evm-audit-master/references/check-review-contract.runtime.md);
the full contract remains available for maintenance.

Only `CONFIRMED` records may become findings. Confirmed findings use this format:

```
## [X-N] Title
**Status**: CONFIRMED
**Checklist reference**: `<canonical-id>`
**Legacy/source references**: `<source IDs or aliases from canonical registry>`
**Severity**: Critical / High / Medium / Low / Info
**Category**: [skill name]
**Location**: `functionName()` or file:line
**Applicability**: APPLICABLE — why the checklist item applies
**Code path**: Exact reachable path
**Preconditions**: Concrete conditions
**Exploitability**: How the conditions are satisfied
**Impact**: Concrete consequence
**Proof of Concept / Invariant Violation**: Runnable proof or deterministic invariant violation
**Description**: What the issue is and why it matters.
**Recommendation**: Concrete fix with code snippet.
```

Severity is assigned only after confirmation using the dimensions and mapping in [`evm-audit-master/references/severity-scoring.md`](evm-audit-master/references/severity-scoring.md). Checklist type and confidence never determine severity.

`NOT_APPLICABLE`, `REVIEWED_SAFE`, and `SUSPICIOUS` records never appear as findings in `AUDIT-REPORT.md`. If all records have terminal statuses but suspicious items remain, the report must disclose unresolved review status and must not claim the audit is clean.

---
