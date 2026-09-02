# Environment Trust

`chain_id` maps to a known family and allowed execution environments. Conflicting
values hard-fail. Facts are `UNKNOWN`, `DECLARED`, `OBSERVED`, or `CONFIRMED`;
CLI values default to `DECLARED`, and only `environment_facts.trust=CONFIRMED`
may filter a check. Unknown or declared facts keep it selected.
`fork_block` is reproducibility metadata, never a hardfork oracle. Project
Analysis may mark a complete compiler result `CONFIRMED` when it carries
evidence.
