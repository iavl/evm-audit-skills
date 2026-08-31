# Knowledge Evidence

Knowledge evidence determines what a checklist claim can establish. Normative
claims require official evidence. Semantic claims require official or
executable evidence. Versioned and time-sensitive claims require official
evidence plus `verified_at`; text-regression evidence cannot establish factual
correctness.

## Evidence classes

- `official` supports normative or version-sensitive claims with an EIP,
  standard, protocol specification, or other authoritative source.
- `executable` supports behavior that is demonstrated by a deterministic test,
  invariant, or other runnable proof.
- `text-regression` protects wording and generated-view stability. It can catch
  accidental text changes but cannot establish factual correctness by itself.

## Verification and freshness

Versioned and time-sensitive knowledge carries `verified_at` metadata. A source
that cannot currently be fetched is not silently treated as disproved;
scheduled health checks report broken or stale sources and preserve temporary
network failures as `UNKNOWN`.

## Evidence for feature absence

Feature evidence is typed with `kind`, `location`, and `reason`. Absence is
accepted only when the feature's `absence_policy` allows that evidence kind.
Incomplete compilation, missing scope, or unsupported evidence does not prove
absence.

## Related maintenance checks

The scheduled knowledge-health workflow reports stale or unverified entries,
broken official sources, and semantic-test regressions in one deduplicated
issue. Run the repository validation described in the
[`Development Guide`](../development/README.md) when changing knowledge or its
generated views.
