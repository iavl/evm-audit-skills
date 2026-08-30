# Runtime Per-Check Review Contract

Review exactly the canonical IDs assigned to the Domain in the routing-v4
manifest. Filtered IDs remain manifest-only. Each selected ID gets one record
in `reviews/review-<owner-domain>.md`.

## Terminal statuses

- `NOT_APPLICABLE`: concrete scope/code evidence proves the selected check cannot apply.
- `REVIEWED_SAFE`: every relevant reachable path preserves the required guard or invariant.
- `SUSPICIOUS`: a plausible concern remains but reachability, preconditions, exploitability, impact, or proof is unresolved. Never assign severity.
- `CONFIRMED`: the defect has a reachable path, satisfiable preconditions, concrete exploitability and impact, plus a runnable PoC/trace or deterministic invariant violation.

Use exactly one terminal status. Pattern similarity, an unavailable test, or one
safe path cannot establish `REVIEWED_SAFE` or `CONFIRMED`.

## Record

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

For `NOT_APPLICABLE`, cite the complete scope/inheritance/dependency evidence.
For `REVIEWED_SAFE`, cover alternate, inherited, proxy, callback, and
delegatecall paths where relevant. For `SUSPICIOUS`, identify the missing proof
step. Only `CONFIRMED` records enter synthesis or receive severity.

Reject synthesis when any selected ID is missing, duplicated, malformed, or
non-terminal. If suspicious records remain, use report status
`COMPLETE_WITH_UNRESOLVED_REVIEW` and do not call the audit clean. The final
report contains only `CONFIRMED` findings.
