# Runtime Per-Check Review Contract

Review only IDs promoted from Screen to Deep in the immutable routing-v7 manifest.
Filtered and Deferred IDs remain manifest-visible. Each deep-review record is
append-only JSONL at `reviews/review-<owner-domain>.jsonl`; Markdown is a generated view.

Global review contract: verify every reachable path before `REVIEWED_SAFE`.
Use `CONFIRMED` only with reachable preconditions, concrete impact, and a
runnable PoC/trace or deterministic invariant violation.

## Terminal statuses

- `NOT_APPLICABLE`: concrete scope/code evidence proves the selected check cannot apply.
- `REVIEWED_SAFE`: every relevant reachable path preserves the required guard or invariant.
- `SUSPICIOUS`: a plausible concern remains but reachability, preconditions, exploitability, impact, or proof is unresolved. Never assign severity.
- `CONFIRMED`: the defect has a reachable path, satisfiable preconditions, concrete exploitability and impact, plus a runnable PoC/trace or deterministic invariant violation.

Use exactly one terminal status. `LIKELY_SAFE` is not a status. Pattern similarity, an unavailable test, or one
safe path cannot establish `REVIEWED_SAFE` or `CONFIRMED`.

## Record

The authoritative JSON object includes `routing_snapshot_id`,
`registry_sha256`, `source_digest`, `compilation_input_digest`, `owner_domain`,
`check_body_hash`, `revision`, `review_stage`, `status`, all review fields, and typed
`evidence` entries (`kind`, `location`, `reason`). It uses review-record schema
v5 and must match the one routing snapshot that owns the ledger. A follow-up
revision may resolve only a prior `SUSPICIOUS` event and must use `PROOF`.
`CONFIRMED` records require `PROOF` stage and strong test, trace, invariant, or
calculation evidence.

```markdown
### <canonical-id> — <title>
- **Review stage**: DEEP_REVIEW | PROOF
- **Routing basis**: matched features and environment evidence
- **Status**: NOT_APPLICABLE | REVIEWED_SAFE | SUSPICIOUS | CONFIRMED
- **Applicability**: APPLICABLE — ... | NOT_APPLICABLE — ...
- **Code path**: entry point → affected operation
- **Preconditions**: caller, state, timing, balances, roles, and deployment facts
- **Exploitability**: concrete actor actions, or the guard that blocks them
- **Impact**: concrete consequence, or N/A with the preserved invariant
- **PoC / Invariant violation**: named runnable proof, deterministic invariant, or UNRESOLVED
- **Evidence**: file:line, test, trace, calculation, or scope inventory
```

For `NOT_APPLICABLE`, set complete scope evidence and cite the relevant exclusion
dimension; irrelevant evidence kinds are not required.
For `REVIEWED_SAFE`, cover alternate, inherited, proxy, callback, and
delegatecall paths where relevant. For `SUSPICIOUS`, identify the missing proof
step. Only `CONFIRMED` records enter synthesis or receive severity.

Reject synthesis when any selected Deep ID is missing, malformed, non-terminal,
or has an invalid revision history. Deferred Domains require
`INCOMPLETE_DOMAIN_ROUTING`; unknown required context requires
`INCOMPLETE_CONTEXT`; suspicious records require `INCOMPLETE_REVIEW`. Only
`COMPLETE_CLEAN` is clean, and final findings contain only `CONFIRMED` records.
