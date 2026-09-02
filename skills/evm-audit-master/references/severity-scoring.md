# Confirmed Finding Severity Model

Severity is assigned during synthesis, after the `CONFIRMED` evidence gate has
passed. A checklist `type`, `confidence`, or source label never determines
severity by itself.

## Required dimensions

For every confirmed finding, record an evidence-backed value and rationale for:

- **Impact** — loss of funds, insolvency, authorization failure, availability, accounting, or no security impact.
- **Exploitability** — permissionless, conditional, privileged, or unreachable after review.
- **Privileges** — attacker, ordinary user, approved operator, governance, or owner.
- **Capital required** — none, low, material, or greater than extractable value.
- **Repeatability** — one-shot, repeatable, or state-consuming.
- **User interaction** — none, predictable transaction ordering, victim action, or trusted operator action.
- **Loss bound** — bounded amount, affected position, protocol liquidity, or unbounded/insolvency risk.
- **Protocol exposure** — isolated component, affected users, market, or whole protocol.
- **Recoverability** — automatic, admin-remediable, delayed, or irreversible.

Use the constrained enum values in
`<suite-root>/schemas/severity-decisions.schema.json` (for example
`fund_loss`, `permissionless`, `repeatable`, and `whole_protocol`), not free-form
sentences. Include the code path, calculation, test, or deployment fact in the
rationale supporting each value.

## Synthesis mapping

| Severity | Minimum confirmed consequence and reachability |
|---|---|
| **Critical** | Direct third-party or protocol-wide fund loss/insolvency with no meaningful precondition, or a permissionless path that can drain the exposed system. |
| **High** | Material fund loss, protocol insolvency, or permanent DoS reachable under concrete conditions such as a vulnerable configuration, capital requirement, or timing window. |
| **Medium** | Bounded loss, incorrect accounting, degraded availability, trust-model violation, or owner/privileged loss that does not meet the High threshold. |
| **Low** | Confirmed latent defect or best-practice failure without direct material fund loss or meaningful availability impact. |
| **Info** | Confirmed behavior or documentation/configuration concern with no security impact. |

When dimensions disagree, explain the limiting factor instead of averaging away
the impact. Keep unresolved economic assumptions as `SUSPICIOUS`; do not assign a
severity until they are established.

## PoC threshold

Severity is assigned only after strong proof confirms the finding. The runnable
PoC gate is then applied to reporting:

| Final severity | Runnable PoC required for final publication? |
|---|---:|
| Info | No |
| Low | No |
| Medium | No |
| High | Yes |
| Critical | Yes |

Do not generate a PoC for a confirmed sub-High finding merely to satisfy
reporting. Create a reproduction when it is genuinely necessary to establish
correctness, not because the reporting policy requires it.
