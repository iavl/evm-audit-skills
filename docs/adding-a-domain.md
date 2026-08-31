# Adding a Domain

Add one `domains/<name>.json` with `surface_features`, related Domains,
`required_context`, `review_requirements`, and a `trusted_absence_policy` that
requires complete scope evidence, plus the matching `skills/<name>/` Skill
folder.
Do not copy checklist knowledge into the Skill. Run the generator to render its
runtime checklist and wrapper. Required context is snapshotted in the routing
manifest and resolved later in `domain-context.json`; it must not be evaluated
by Selector.
