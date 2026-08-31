<!-- GENERATED FILE: source is domains/*.json and data/canonical-checks.json; do not edit by hand. -->
# Domain Catalog

| Domain | Purpose | Surface features | Related domains | Runtime entries |
|---|---|---|---|---:|
| `evm-audit-access-control` | Security review for ownership, roles, authorization, governance, and privileged operations. | `uses-access-control` | `evm-audit-general` | 21 |
| `evm-audit-defi-amm` | Security review for AMMs, DEXs, swap routers, liquidity pools, and hooks. | `uses-amm` | `evm-audit-precision-math`, `evm-audit-erc20`, `evm-audit-oracles` | 66 |
| `evm-audit-assembly` | Security review for inline assembly, Yul, CREATE2, low-level calls, and EVM opcodes. | `uses-assembly`, `uses-create2`, `uses-low-level-call` | `evm-audit-general`, `evm-audit-chain-specific` | 39 |
| `evm-audit-bridges` | Security review for cross-chain bridges, messaging, relayers, and adapters. | `uses-bridge` | `evm-audit-signatures`, `evm-audit-chain-specific` | 58 |
| `evm-audit-chain-specific` | Security review for non-mainnet EVM deployments and chain-specific execution assumptions. | `uses-chain-specific` | `evm-audit-oracles`, `evm-audit-assembly` | 39 |
| `evm-audit-dos` | Security review for denial-of-service, gas griefing, unbounded work, and revert propagation. | `uses-dynamic-loop` | `evm-audit-general` | 18 |
| `evm-audit-erc20` | Security review for contracts that implement or integrate ERC20-compatible tokens. | `uses-erc20` | `evm-audit-general`, `evm-audit-precision-math` | 40 |
| `evm-audit-erc4337` | Security review for ERC4337 wallets, paymasters, bundlers, and account-abstraction infrastructure. | `uses-erc4337` | `evm-audit-signatures`, `evm-audit-access-control` | 40 |
| `evm-audit-erc4626` | Security review for ERC4626 vaults and vault integrations. | `uses-erc4626` | `evm-audit-precision-math`, `evm-audit-erc20` | 53 |
| `evm-audit-erc721` | Security review for ERC721, ERC1155, NFT implementations, and NFT integrations. | `uses-erc721` | `evm-audit-general`, `evm-audit-access-control` | 39 |
| `evm-audit-flashloans` | Security review for flash loans, flash minting, and atomic economic attacks. | `uses-flash-loan` | `evm-audit-governance`, `evm-audit-oracles`, `evm-audit-defi-amm` | 14 |
| `evm-audit-general` | General Solidity and EVM security review for every smart contract. | `uses-general` | `evm-audit-precision-math` | 109 |
| `evm-audit-governance` | Security review for governance, voting, proposals, timelocks, and treasury control. | `uses-governance` | `evm-audit-access-control`, `evm-audit-flashloans` | 54 |
| `evm-audit-defi-lending` | Security review for lending, borrowing, collateral, liquidation, and CDP protocols. | `uses-lending` | `evm-audit-precision-math`, `evm-audit-erc20`, `evm-audit-oracles` | 88 |
| `evm-audit-oracles` | Security review for price feeds, TWAPs, VRF, and external data inputs. | `uses-oracle` | `evm-audit-chain-specific`, `evm-audit-precision-math` | 48 |
| `evm-audit-precision-math` | Precision, rounding, fixed-point math, conversion, and arithmetic security review for EVM contracts. | `uses-math` | `evm-audit-general` | 36 |
| `evm-audit-proxies` | Security review for proxies, upgrade mechanisms, initializers, and storage layouts. | `uses-proxy` | `evm-audit-access-control`, `evm-audit-assembly` | 32 |
| `evm-audit-signatures` | Security review for signatures, permits, EIP-712, and meta-transactions. | `uses-signature` | `evm-audit-access-control`, `evm-audit-chain-specific` | 21 |
| `evm-audit-defi-staking` | Security review for staking, liquid staking, restaking, rewards, and yield aggregation. | `uses-staking` | `evm-audit-precision-math`, `evm-audit-erc20` | 57 |
