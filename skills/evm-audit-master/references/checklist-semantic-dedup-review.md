# Runtime Checklist Semantic Deduplication Review

This is the repository-level review record for semantic deduplication of the
canonical registry and its 19 generated domain views. It is audit metadata,
not a runtime checklist. Source provenance remains attached to the canonical
JSON item; source-level provenance maps do not imply that all runtime prose is
unique.

## Decision Rules

- `MERGED`: one runtime item remains because the candidates have the same root
  cause, detection condition, and security consequence. The canonical item
  contains the useful detail and all relevant provenance.
- `KEEP_DISTINCT`: the candidates share vocabulary but differ in actor,
  precondition, execution path, impact, or required verification. The titles or
  descriptions must make that boundary explicit.
- `PENDING_USER_CONFIRMATION`: candidates cross domain boundaries and are not
  changed by this pass. They require an explicit choice before any move or
  global merge.

The canonical item is normally the earlier topical entry. Expanded and Phase 3
sections remain as organizational boundaries, but contain only additional
runtime checks after this review.

## Same-File Merges Applied

| Group | Canonical runtime coverage | Merged or removed aliases |
|---|---|---|
| GEN-01 | `general / External Calls & Low-Level Interactions / msg.value persistence` | multicall/batch persistence; delegatecall persistence; expanded loop/multicall row; RareSkills payable-multicall row |
| GEN-02 | `general / External Calls & Low-Level Interactions / Call to non-existent address returns true` | expanded non-existent-address row |
| GEN-03 | `general / General Solidity Footguns / Deleting a struct doesn't delete its nested mappings` | RareSkills dynamic-type deletion row |
| GEN-04 | `general / Code Structure Issues / Withdraw should undo ALL deposit state changes` | expanded code-asymmetry row |
| GEN-05 | `general / Reentrancy / Reentrancy guard must precede modifiers that can yield control` | expanded `NoReentrant` ordering row |
| GEN-06 | `general / Merkle Tree Pitfalls / Merkle claim beneficiary must be bound to the payout` | RareSkills sender-binding/front-running row; encoding ambiguity is tracked separately as `EVM-GEN-109` |
| GEN-07 | `general / Force-Feeding Attacks` | broad expanded force-feeding summary reduced to the existing selfdestruct, CREATE2, and coinbase mechanism checks |
| LEN-01 | `lending / Liquidation Mechanics / Cannot repay loan = permanent bad debt` | impossible repayment condition; Dacian permanently-reverting repay row |
| LEN-02 | `lending / Liquidation Mechanics / Single borrower can't be liquidated` | Dacian single-borrower edge-case row |
| LEN-03 | `lending / Liquidation Mechanics / Liquidation before grace period` | repayment-resumption grace-period row |
| LEN-04 | `lending / Auction Liquidations / Partial collateral auction math` | expanded partial-auction math row |
| LEN-05 | `lending / Auction Liquidations / Interrupted bid funds not returned` | expanded interrupted-auction refund row |
| LEN-06 | `lending / CDP-Specific / Closed vault storage not cleaned` | expanded closed-CDP storage row |
| LEN-07 | `lending / CDP-Specific / Stablecoin collateral arbitrage across assets` | expanded stablecoin collateral-swapping row |
| LEN-08 | `lending / CDP-Specific / Interest accrual ordering around close and liquidation` | expanded interest-timing row |
| LEN-09 | `lending / AAVE/Compound Integration / High utilization blocks withdrawal` | expanded high-utilization integration row |
| LEN-10 | `lending / AAVE/Compound Integration / AAVE siloed asset prohibition` | expanded siloed-asset row |
| LEN-11 | `lending / AAVE/Compound Integration / AAVE isolated-asset debt cap can block borrowing` | expanded isolated-cap row |
| LEN-12 | `lending / AAVE/Compound Integration / Paused AAVE/Compound market blocks integration` | expanded paused-market row |
| LEN-13 | `lending / AAVE/Compound Integration / Deprecated AAVE/Compound pool can strand funds` | expanded deprecated-pool row |
| LEN-14 | `lending / LP Token Collateral / Multiple pool types for same pair` | expanded fee-tier row |
| LEN-15 | `lending / Earn/Yield-Bearing Collateral / Pegged asset collateral depeg risk` | expanded earn-token depeg row |
| AMM-01 | `amm / General AMM / Signed integer balance updates` | expanded signed-integer overflow row |
| AMM-02 | `amm / Slippage Protection / Hardcoded slippage` | expanded hardcoded-slippage row |
| AMM-03 | `amm / Slippage Protection / On-chain slippage calculation is manipulable` | expanded on-chain quote row; Dacian Quoter row |
| AMM-04 | `amm / Slippage Protection / No expiration deadline` | Dacian deadline row |
| AMM-05 | `amm / Slippage Protection / Missing refunds after swaps` | expanded refund row |
| AMM-06 | `amm / Uniswap V4 Hooks / Hook permissions derived from address bits` | expanded low-bit permissions row; upgradeable-permission rows |
| AMM-07 | `amm / Uniswap V4 Hooks / BeforeSwapDelta sign confusion` | expanded sign-convention row |
| AMM-08 | `amm / Uniswap V4 Hooks / Unsettled deltas revert unlock()` | expanded unsettled-delta row |
| AMM-09 | `amm / Uniswap V4 Hooks / Async hooks steal custody` | expanded async-custody row |
| AMM-10 | `amm / Uniswap V4 Hooks / Missing access control on hook functions` | expanded `onlyPoolManager` row |
| AMM-11 | `amm / AMM Integration / Callback function must verify caller is the pool` | expanded callback-validation row |
| AMM-12 | `amm / AMM Integration / Don't use pool.swap() directly` | expanded direct-pool row |
| AMM-13 | `amm / AMM Integration / AMM pool token0/token1 order differs by chain` | expanded token-order row |
| AMM-14 | `amm / TWAMM / Rebasing token balance changes during long-term swaps` | expanded TWAMM-rebasing row |
| AMM-15 | `amm / TWAMM / Hardcoded DEX pool fees prevent optimal routing` | Dacian hardcoded-Uniswap-fee row |
| STK-01 | `staking / rETH / rETH burn() reverts if RocketDepositPool is empty` | expanded rETH burn row |
| STK-02 | `staking / rETH / rETH/ETH rate CAN decrease` | expanded rETH slashing-rate row |
| STK-03 | `staking / rETH / Consensus attack on RPL nodes` | expanded RPL consensus row |
| STK-04 | `staking / cbETH / cbETH has full blacklisting` | expanded cbETH blacklist row |
| STK-05 | `staking / cbETH / cbETH/ETH rate changeable by oracle` | expanded `onlyOracle` rate row; redundant cbETH decrease row |
| STK-06 | `staking / sfrxETH / sfrxETH can temporarily detach from frxETH` | expanded sfrxETH detachment row |
| STK-07 | `staking / LSD Protocol Design / WithdrawCredentials front-running` | expanded validator-deposit row |
| STK-08 | `staking / LSD Protocol Design / DepositContract.deposit() gas limit` | expanded accumulated-ETH gas row |
| STK-09 | `staking / LSD Protocol Design / Validator array iteration gas` | expanded validator-iteration row |
| STK-10 | `staking / LSD Protocol Design / Slashing penalty exceeds operator balance` | expanded operator-slashing row |
| STK-11 | `staking / Staking Lock Mechanisms / Staking for others reduces lock time` | expanded lock-time row |
| VLT-01 | `erc4626 / Compliance Requirements / convertToAssets/convertToShares caller independence` | expanded caller-independence row |
| VLT-02 | `erc4626 / Compliance Requirements / convertToAssets/convertToShares idealized math` | expanded no-slippage row |
| VLT-03 | `erc4626 / Compliance Requirements / totalAssets includes yield and fees` | expanded totalAssets row |
| VLT-04 | `erc4626 / Share Price Manipulation / Direct token transfer inflates share price` | expanded direct-transfer row |
| VLT-05 | `erc4626 / Vault Math Edge Cases / 1 wei remaining` | expanded one-wei row |
| VLT-06 | `erc4626 / Vault Math Edge Cases / zero shares or assets` | expanded zero-state row |
| VLT-07 | `erc4626 / Inheritance Issues / Override all needed functions` | expanded dependent-override row |
| ASM-01 | `assembly / CREATE2 Metamorphic Contracts / CREATE2 + selfdestruct` | expanded metamorphic and mutable-bytecode rows |
| ASM-02 | `assembly / EXTCODESIZE / Contract-code checks return zero during construction` | Solidity `address.code.length` row; expanded EXTCODESIZE row |
| ASM-03 | `assembly / Inline Assembly Math / Division by zero returns 0 in Yul` | expanded Yul division row |
| ASM-04 | `assembly / Inline Assembly Math / No overflow/underflow protection in assembly` | expanded assembly-arithmetic and Dacian overflow rows |
| ASM-05 | `assembly / Memory & Calldata / Free memory pointer and allocation integrity` | expanded free-memory-pointer row |
| ASM-06 | `assembly / Low-Level Calls / call() to non-existent contract returns success` | expanded assembly non-existent-call row |
| PRO-01 | `proxies / UUPS Proxy / Implementation must disable initializers` | RareSkills uninitialized-implementation row |
| PRO-02 | `proxies / UUPS Proxy / No selfdestruct or untrusted delegatecall` | expanded implementation-destruction row; RareSkills UUPS selfdestruct row |
| PRO-03 | `proxies / UUPS Proxy / Immutable variables lost on upgrade` | expanded immutable row |
| PRO-04 | `proxies / UUPS Proxy / Storage layout compatibility` | expanded storage-collision row |
| PRO-05 | `proxies / Initialization / No constructor state` | expanded constructor row |
| PRO-06 | `proxies / Initialization / Use upgradeable inherited contracts` | expanded non-upgradeable-base row |
| PRO-07 | `proxies / Initialization / Deployer must call initialize atomically` | expanded initialize-after-deployment row |
| PRO-08 | `proxies / Transparent Proxy / Function selector clashing` | expanded selector-clashing row |
| PRO-09 | `proxies / Metamorphic Contracts / CREATE2 + selfdestruct` | expanded metamorphic-rug row |
| ORC-01 | `oracles / Answer Bounds / minAnswer/maxAnswer circuit breakers` | expanded flash-crash bound row; Cyfrin min/max row |
| ORC-02 | `oracles / Chainlink Price Feeds / Price = 0 not handled` | Oracle Price Zero Edge Case row |
| ORC-03 | `oracles / L2 Sequencer / L2 sequencer downtime leaves stale prices` | expanded sequencer row |
| ORC-04 | `oracles / Feed Configuration / Feed decimal precision varies` | expanded feed-decimal row; AMPL decimal row; lending setup conversion row |
| ORC-05 | `oracles / Feed Configuration / Deprecated or hardcoded feeds` | expanded hardcoded-feed row |
| ORC-06 | `oracles / Spot Price Manipulation / NEVER use spot reserves` | Sigma Prime spot-manipulation row |
| ORC-07 | `oracles / Price Peg Assumptions / Hardcoded price peg assumptions` | WBTC, stETH, USDC, and expanded WBTC-depeg rows |
| ORC-08 | `oracles / Chainlink Deep Dive / Oracle price update front-running/backrunning` | stablecoin oracle-front-running row |
| CHN-01 | `chain-specific / Arbitrum / block.number returns L1 block number` | expanded Arbitrum block-number row |
| CHN-02 | `chain-specific / zkSync / msg.sender == tx.origin is not an EOA proof` | expanded L2 tx.origin row |
| CHN-03 | `chain-specific / BNB Chain / Precompile addresses differ across chains` | expanded precompile row |
| CHN-04 | `chain-specific / General L2 / PUSH0 support varies by chain` | expanded PUSH0 row |
| MAT-01 | `precision-math / Division Before Multiplication / Hidden division-before-multiplication` | Dacian hidden-ordering row |
| MAT-02 | `precision-math / Rounding Direction / Protocol-favoring rounding rule` | expanded rounding-direction row; Dacian fee-rounding row |
| MAT-03 | `precision-math / Integer Overflow / Overflow in unchecked blocks` | expanded unchecked-validation row |
| MAT-04 | `precision-math / Integer Overflow / Downcast overflow` | Dacian pre-downcast-invariant row |
| MAT-05 | `precision-math / Integer Overflow / Negative-to-unsigned cast` | expanded negative-cast row |
| SIG-01 | `signatures / Cross-Chain Replay / Missing chain ID` | expanded cross-chain replay row; UserOperation chain-ID row |
| SIG-02 | `signatures / Cross-Chain Replay / Missing msg.sender binding` | expanded wrong-person row |
| SIG-03 | `signatures / Replay / Nonce-less signatures` | Dacian KYC/privilege replay row |
| SIG-04 | `signatures / ecrecover / Invalid ecrecover can return address(0)` | expanded zero-address and Dacian ecrecover rows |
| SIG-05 | `signatures / ecrecover / Signature malleability` | expanded raw-ecrecover and Dacian dual-signature rows |
| SIG-06 | `signatures / ecrecover / abi.encodePacked collision` | expanded dynamic-type collision row |
| SIG-07 | `signatures / EIP-712 / DOMAIN_SEPARATOR cached` | expanded cached-domain row |
| SIG-08 | `signatures / EIP-712 / Missing expiration` | Dacian lifetime-license row |
| BRG-01 | `bridges / Bridge Fundamentals / Signed bridge messages bind all execution-affecting fields` | expanded signed-values row |
| BRG-02 | `bridges / Bridge Fundamentals / Used bridge signatures must be invalidated` | expanded signature-invalidation row |
| BRG-03 | `bridges / Bridge Fundamentals / Bridge chain identifiers cannot be spoofed` | expanded chain-identifier row |
| GOV-01 | `governance / Proposal Execution / Fake proposals via CREATE/CREATE2 substitution` | expanded fake-proposal row |
| TOK-01 | `erc20 / Decimal Quirks / Decimals vary across chains` | expanded USDC/USDT decimal row |

## Near-Matches Kept Distinct

These groups were reviewed by the same semantic pass but remain separate
because their proof obligations are different.

| Group | Kept-distinct items | Boundary |
|---|---|---|
| KEEP-01 | chain-specific Arbitrum `block.number` vs OP Stack `block.number` | They document opposite chain semantics and require different deployment checks. |
| KEEP-02 | lending no-partial-liquidation-for-whales vs repeated-liquidation-of-one-position | One concerns capital/transaction capacity; the other concerns idempotency and replay of a closed position. |
| KEEP-03 | ERC4626 conversion rounding vs caller-independent conversion | One is a rounding-direction invariant; the other is an ERC4626 view-function purity/composability invariant. |
| KEEP-04 | flash-loan governance quorum manipulation vs flash-loan AMM/TWAP manipulation | The capital source is shared, but voting snapshots and oracle price horizons have different attack proofs. |
| KEEP-05 | general cross-contract reentrancy vs SAS-AV cross-function reentrancy | The former crosses contract boundaries and shared state; the latter stays within one contract's function set. |
| KEEP-06 | AMM hook attachment to multiple pools vs hook state isolation across pools | One validates the allowed PoolKey; the other prevents state collision when multiple PoolKeys are allowed. |

## Cross-Domain Decisions

No cross-domain candidate is merged automatically. Each row below records the
human decision for whether the domain-local contexts are retained or one
canonical runtime item is used.

| Group | Candidate runtime items | Why the boundary needs a human decision | Decision |
|---|---|---|---|
| X-01 | general `Call to non-existent address`; assembly `call() to non-existent contract`; erc20 Solmate SafeTransferLib check | Same EVM behavior, but assembly return-data safety and ERC20-library integration may require different audit evidence. | KEEP_DISTINCT |
| X-02 | general returndata bombing; assembly Return bomb; DOS Returndata bombing | Same gas-griefing primitive, but the runtime owner could be general, assembly, or DOS depending on whether the suite requires domain-local evidence. | KEEP_DISTINCT |
| X-03 | general `try/catch` insufficient gas; DOS `try/catch` insufficient gas | Exact same title and source behavior across two runtime skills. Canonical: general / External Calls & Low-Level Interactions. | MERGED |
| X-04 | general `EVM-GEN-021` beneficiary binding; governance `EVM-GOV-026` beneficiary binding | Generic claim binding and governance-specific claim flows retain distinct agent-facing contexts while linking to the shared general invariant. | KEEP_DISTINCT |
| X-05 | flashloans `Flash-loan voting`; governance `Flash loan voting` | Same governance attack family, but the flash-loan skill emphasizes capital composition while governance emphasizes snapshot/quorum rules. | KEEP_DISTINCT |
| X-06 | general `msg.value` persistence; assembly delegatecall preserves `msg.value`; ERC-4337 UserOperation value paths | Same value-preservation primitive, but delegatecall and account-abstraction execution have distinct trust boundaries. | KEEP_DISTINCT |
| X-07 | general force-feeding; chain-specific native-yield balance drift; ERC4626 direct-donation/share-price checks | All involve unexpected balances, but native ETH force-send, automatic yield, and ERC4626 donation accounting have different assets and invariants. | KEEP_DISTINCT |
| X-08 | general ERC721 callbacks; erc721 safe-transfer callbacks; lending liquidation callback | Same callback/reentrancy mechanism, but lending adds liquidation-health ordering and NFT adds standard-specific callback coverage. | KEEP_DISTINCT |
| X-09 | general pause/liquidation risk; DOS pause-related liquidation; lending liquidation pause/grace period; ERC721 pausable collateral | Same pause asymmetry family with different protocol impacts and recovery requirements. | KEEP_DISTINCT |
| X-10 | oracle spot reserves; AMM pool reserves; lending LP collateral reserves | Same manipulable reserve source, but oracle, swap execution, and collateral valuation are different consumers and may need separate checks. | KEEP_DISTINCT |
| X-11 | flashloans spot/TWAP manipulation; oracle spot/TWAP manipulation; lending oracle extraction model | Same capital source can feed three different economic proofs; merge policy changes which checklist owns the `C_manipulation > V_extractable_borrow` context. | KEEP_DISTINCT |
| X-12 | precision/oracle/erc20/erc4626 decimal mismatch checks | Same dimensional risk, but feed decimals, token decimals, vault shares, and cross-chain token behavior require different paths and false-positive gates. | KEEP_DISTINCT |
| X-13 | AMM slippage; ERC4626 withdrawal slippage; lending liquidation slippage | Same protection concept but different final-value and settlement boundaries. | KEEP_DISTINCT |
| X-14 | assembly/proxies/general CREATE2 and selfdestruct checks | Same opcode family, but implementation destruction, metamorphic deployment, and ordinary contract balance/code assumptions have different assets and lifecycle states. | KEEP_DISTINCT |

## Completion State

The same-file pass is complete for the groups listed above. All cross-domain
groups are now classified: X-03 is merged into the general canonical item and
the remaining groups are intentionally kept distinct. The three exact-title
legacy candidates are represented by explicit shared canonical IDs or
cross-domain retention, not unreviewed candidates.

## Canonical Registry Decisions

The following corrections are represented as one stable canonical item with
legacy aliases; source identifiers remain provenance only.

| Canonical ID | Covered legacy items | Decision |
|---|---|---|
| `EVM-TYPE-001` | Precision negative-to-unsigned cast; General assigning a negative value to uint | Merge: same explicit conversion semantics and proof obligation. |
| `EVM-TIME-001` | Precision time-literal claim; General regular time-expression claim | Merge: same literal typing and narrowing-conversion proof obligation. |
| `ERC4626-ROUND-001` | `convertTo*`, `previewDeposit`, `previewMint`, `previewWithdraw`, `previewRedeem`, and broad vault-favoring rounding rows | Merge: one EIP-4626 normative rounding table; all six legacy rows are aliases. |
| `EVM-ASM-025` | Assembly and chain-specific PUSH0 support checks | Merge: one compiler-target/fork opcode rule with both runtime contexts. |

The canonical registry is the source of truth for future decisions. A candidate
may be merged only when its root cause, trigger, proof obligation, and impact
match; contextual differences remain separate and use `related` IDs.

Merkle claimant binding and Merkle leaf encoding are intentionally separate:
`EVM-GEN-021` covers beneficiary redirection, while `EVM-GEN-109` covers
ambiguous or non-domain-separated leaf construction.
