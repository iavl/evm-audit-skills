# evm-audit-access-control — PARTIAL

*Generated: 2026-02-28 | Items: 1*

⚠️  The general class is established, but protocol, version, or formula details require focused review.

- [ ] **Whitelist bypass via proxy tokens**: If a protocol whitelists specific addresses but doesn't check for proxy/alias addresses, users can bypass restrictions using alternate token addresses. Look for: address-based whitelists that don't account for proxy patterns. [beirao A-04]
