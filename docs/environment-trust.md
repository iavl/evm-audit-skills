# Environment Trust

`chain_id` maps to a known family and allowed execution environments. Conflicting
values hard-fail. Recon compiler evidence and a CLI compiler version must agree.
Only `environment_facts.status=CONFIRMED` may filter a check; unknown facts keep
it selected. `fork_block` is reproducibility metadata, never a hardfork oracle.
