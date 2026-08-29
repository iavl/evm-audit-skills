---
name: evm-audit-erc721
description: EVM smart contract audit checklist for ERC721/ERC1155 tokens. Covers weird NFT behaviors, dual-standard tokens, wrapped/legacy collections, permit issues, fractionalization, pausability, blacklists, and upgradeable NFTs. Use when auditing protocols that interact with arbitrary ERC721/ERC1155 tokens. Load references/checklist.md for the full checklist.
---

# ERC721/ERC1155 Audit Skill

## Overview
Non-obvious security edge cases for protocols interacting with ERC721 and ERC1155 tokens. Based on real-world token behaviors that have caused exploits.

## Audit Contract
When this skill is invoked directly or via the master skill:
1. Read `../evm-audit-master/references/check-review-contract.md` and use the canonical IDs from `../data/canonical-checks.json`.
2. Pattern matches are candidates, not findings; apply the feature filter before deep review.
3. Do not report a finding without a reachable path, exploitable preconditions, concrete impact, and PoC or deterministic invariant evidence.

## Reference Files
- **references/checklist.md** — Full audit checklist, load this when auditing NFT-related protocols
