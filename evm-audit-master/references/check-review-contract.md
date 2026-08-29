# Per-Check Review Contract

This contract defines the audit-run review ledger. The canonical domain checklists remain unchanged and remain the runtime source of truth. Statuses belong only to the run-specific ledger under `audits/<repo>-<date>/`.

## Review Pipeline

Every selected checklist item follows this order:

```text
Checklist item
      ↓
Applicability check
      ↓
NOT_APPLICABLE or APPLICABLE
      ↓
Code path identification
      ↓
Preconditions
      ↓
Exploitability
      ↓
Impact
      ↓
PoC / invariant violation
      ↓
One terminal status
```

`APPLICABLE` is a branch in the analysis, not a fifth status. Do not skip from recognizing a pattern to confirming a finding.

## Terminal Statuses

| Status | Meaning | Required evidence | Final report |
|---|---|---|---|
| `NOT_APPLICABLE` | The checklist item's applicability predicate is absent from the in-scope system. | Concrete scope/code evidence showing why the item cannot apply. | Never a finding. |
| `REVIEWED_SAFE` | The item applies, but all relevant paths preserve the required guard or invariant. | Relevant path coverage plus the guard, invariant, or verified false-positive condition. | Never a finding. |
| `SUSPICIOUS` | A plausible concern remains, but at least one path, precondition, exploitability, impact, or proof step is unresolved. | Exact concern, explored path, and the missing proof step. No severity. | Internal ledger only. |
| `CONFIRMED` | The security-relevant defect is reachable and proven. | Complete path, preconditions, exploitability, concrete impact, and a runnable PoC or deterministic invariant violation. | Eligible for synthesis and reporting. |

Every record must end with exactly one of these four statuses. There is no emitted `UNREVIEWED` or `IN_PROGRESS` status. A `SUSPICIOUS` record may be resolved to `REVIEWED_SAFE` or `CONFIRMED` only after the missing evidence is supplied.

## Record Identity and Format

Use the existing source identifier when a checklist item has one, including `SAS-AV-*`, `DROZER-*`, and `AUDITMOS-*`. For an item without a source identifier, use `<domain>/<section>/<exact-title>`. If the exact title repeats within a section, append a one-based occurrence index. Do not renumber or mechanically rewrite the canonical checklists.

Each selected skill writes one `review-<skill>.md` ledger. Preserve checklist order and write exactly one record per checklist item:

```markdown
### <check-ref> — <title>
- **Status**: NOT_APPLICABLE | REVIEWED_SAFE | SUSPICIOUS | CONFIRMED
- **Applicability**: APPLICABLE — ... | NOT_APPLICABLE — ...
- **Code path**: ...
- **Preconditions**: ...
- **Exploitability**: ...
- **Impact**: ...
- **PoC / Invariant violation**: ...
- **Evidence**: file:line, test name, trace, calculation, or explicit scope basis
```

Do not leave fields blank. Use an explicit `N/A — reason` or `UNRESOLVED — missing ...` where a field does not support the selected status.

## State-Specific Gates

### `NOT_APPLICABLE`

- Set `Applicability` to `NOT_APPLICABLE` and state the concrete absence of the relevant surface.
- Cite the source inventory, inheritance/proxy map, interface usage, or other code evidence.
- “I did not find it quickly,” an unfamiliar dependency, or an inability to run a test is not enough. Use `SUSPICIOUS` when applicability is uncertain.
- Set the remaining analytical fields to explicit `N/A — not applicable` values.

### `REVIEWED_SAFE`

- Set `Applicability` to `APPLICABLE`.
- Identify every relevant entry-to-operation path, including inherited, proxy, delegatecall, callback, and alternate state-transition paths where applicable.
- Name the guard, invariant, or verified false-positive condition that blocks the suspected failure.
- A checklist `FP` note is a hypothesis to verify, not automatic proof of safety.

### `SUSPICIOUS`

- Set `Applicability` to `APPLICABLE` and record the uncertainty when the relevant surface cannot yet be excluded. Do not introduce a third applicability value.
- Record the exact code path and what was observed.
- State which proof obligation is missing: reachability, precondition, exploitability, impact, or PoC/invariant evidence.
- Do not assign severity, call it a finding, file an issue, or promote it because the pattern resembles a known vulnerability.
- If the required PoC cannot run because the environment or dependency is unavailable, retain `SUSPICIOUS` and record that limitation.

### `CONFIRMED`

All of the following must be concrete and supported:

1. A reachable code path from an allowed or attacker-controlled entry point.
2. Preconditions that can actually be satisfied in the declared deployment/threat model.
3. An exploitability argument showing who performs which actions and in what order.
4. A specific impact on funds, accounting, authorization, availability, or another stated security invariant.
5. Either a runnable PoC/transaction trace with observed results, or a deterministic invariant violation with a complete path and state relation.

Code pattern matching, a hypothetical “could,” a severity label, or a recommendation alone cannot produce `CONFIRMED`.

Accepted proof includes a named Foundry/Hardhat test and result, a reproducible transaction sequence and state delta, or a static proof of a violated invariant that does not depend on an unverified assumption. If proof depends on unavailable fork state, deployment configuration, or external behavior, keep the record `SUSPICIOUS` until that dependency is established.

## D/FP Handling

Checklist `D` sections identify candidate detection conditions. They do not establish reachability, impact, or exploitability. `FP` sections describe possible false-positive gates. Verify each `FP` condition against the actual implementation and all relevant paths before assigning `REVIEWED_SAFE`.

Reject these shortcuts:

| Shortcut | Correct disposition |
|---|---|
| “The code resembles a known vulnerable pattern.” | Candidate only; trace the path and prove the consequences. |
| “The function was not found in one file.” | Search inheritance, proxy, callbacks, and dependencies; otherwise remain unresolved. |
| “The test or fork was unavailable.” | `SUSPICIOUS`, not `CONFIRMED`. |
| “One path has a guard.” | Check every reachable alternate path before `REVIEWED_SAFE`. |
| “The issue sounds severe.” | Severity comes after the confirmation gate. |

## Minimal Disposition Examples

Pattern absent from scope:

```markdown
### general/no-proxy-upgrade-path — Proxy upgrade authorization
- **Status**: NOT_APPLICABLE
- **Applicability**: NOT_APPLICABLE — source inventory contains no proxy, upgrade entry point, or delegatecall path.
- **Code path**: N/A — not applicable
- **Preconditions**: N/A — not applicable
- **Exploitability**: N/A — not applicable
- **Impact**: N/A — not applicable
- **PoC / Invariant violation**: N/A — not applicable
- **Evidence**: source inventory and inheritance/proxy map reviewed.
```

Pattern applies but the invariant holds:

```markdown
### precision-math/rounding/deposit-rounding — Deposit conversion rounding
- **Status**: REVIEWED_SAFE
- **Applicability**: APPLICABLE — deposit converts assets to shares.
- **Code path**: deposit() → _convertToShares() → mulDiv(..., Rounding.Down)
- **Preconditions**: Any supported deposit amount.
- **Exploitability**: Blocked because deposits round in the protocol-favoring direction.
- **Impact**: N/A — required rounding invariant is preserved.
- **PoC / Invariant violation**: Invariant holds: minted shares never exceed the exact asset/share conversion.
- **Evidence**: source path and focused rounding tests reviewed.
```

Pattern exists but proof is incomplete:

```markdown
### lending/oracle/spot-price — Spot price used for collateral
- **Status**: SUSPICIOUS
- **Applicability**: APPLICABLE — collateral valuation reads the pool spot price.
- **Code path**: borrow() → _healthFactor() → pool.getReserves()
- **Preconditions**: Attacker needs sufficient liquidity and a borrowable market.
- **Exploitability**: UNRESOLVED — executable manipulation cost and available borrow liquidity were not established.
- **Impact**: UNRESOLVED — extractable value is not quantified.
- **PoC / Invariant violation**: UNRESOLVED — no executable fork test or economic bound yet.
- **Evidence**: price read is confirmed; liquidity and cap data are missing.
```

Reachable defect with proof:

```markdown
### erc20/transfer-accounting — Fee-on-transfer amount mismatch
- **Status**: CONFIRMED
- **Applicability**: APPLICABLE — the protocol accepts an arbitrary fee-on-transfer token.
- **Code path**: deposit() → token.transferFrom() → credits[msg.sender] = amount
- **Preconditions**: Token burns a fee and the caller deposits through deposit().
- **Exploitability**: Caller deposits amount A while the contract receives less than A; credited balance can be withdrawn against unreceived tokens.
- **Impact**: Protocol insolvency or loss to other depositors.
- **PoC / Invariant violation**: Foundry test demonstrates received amount < credited amount and a later withdrawal exceeds actual token balance.
- **Evidence**: named test, trace, and balance delta.
```

## Synthesis Admission Gate

1. Enumerate the expected items from every selected canonical checklist.
2. Reject ledgers with missing, duplicate, unknown, malformed, or non-terminal records. Mark the audit `INCOMPLETE` and do not write a final report.
3. Consider only records whose exact status is `CONFIRMED` for finding deduplication and report generation.
4. Preserve all relevant checklist references and evidence when merging duplicate confirmed records.
5. Map cross-domain candidates to existing records, or create `review-integration.md` and apply this contract to the new record.
6. If suspicious records remain after complete coverage, the report may be emitted with report-level status `COMPLETE_WITH_UNRESOLVED_REVIEW`, but it must not claim the audit is clean or vulnerability-free and must not include suspicious details as findings.
7. If no confirmed records remain, report only that no confirmed findings were established within the reviewed scope.
