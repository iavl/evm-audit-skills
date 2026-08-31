<!-- GENERATED FILE: source is ../../../data/canonical-checks.json; do not edit by hand. -->
# Assembly & Opcode Security Checklist

Each entry has a stable canonical ID, a type/confidence label, and an explicit evidence path. Shared entries are deduplicated by canonical ID.
Global FP/proof obligations live in the Review Contract; only check-specific gates and proofs are repeated below.

## CREATE / CREATE2

- [ ] **[EVM-ASM-001] CREATE2 and SELFDESTRUCT redeployment is fork- and transaction-dependent** _(semantic; high)_: After EIP-6780, SELFDESTRUCT in an existing contract transfers its balance but does not delete code or storage. Code deletion and subsequent redeployment remain possible only for a contract created in the same transaction, so CREATE2 plus SELFDESTRUCT is not a general metamorphic upgrade primitive.
  - **Trigger:** A protocol assumes a CREATE2 address can be destroyed and later redeployed with different code.
  - **Risk:** A protocol that relies on code replacement may be unsafe only on pre-EIP-6780 chains or same-transaction-created paths; verify the target fork and lifecycle.
  - **Detection:** Check the target chain fork, whether the contract was created in the same transaction, and whether the design relies on post-deployment code replacement.
  - **Specific FP:** The deployment chain implements EIP-6780 and no same-transaction-created contract can reach the replacement path.
  - **Specific proof:** Build the exact create, SELFDESTRUCT, and redeployment transaction sequence for the declared fork and observe code/storage at each step.
  - **Provenance:** mixbytes CREATE2; [EIP-6780 SELFDESTRUCT](https://eips.ethereum.org/EIPS/eip-6780)

- [ ] **[EVM-ASM-002] CREATE2 address lifecycle depends on EIP-6780 and transaction context** _(semantic; high)_: Before deployment a CREATE2 address has no code or storage. After deployment it has code and storage. On a post-EIP-6780 chain, SELFDESTRUCT of an existing contract leaves code and storage in place; deletion semantics are retained only when the contract was created in the same transaction.
  - **Trigger:** Code relies on a CREATE2 address changing between deployed, destroyed, and redeployed states.
  - **Risk:** Treating an address as permanently empty or redeployable without checking the fork and creation transaction can invalidate identity and code-integrity assumptions.
  - **Detection:** Model the address state before deployment, after deployment, after SELFDESTRUCT, and in the next transaction under the target fork.
  - **Specific FP:** The implementation verifies code and storage state at the point of use and documents the target chain fork.
  - **Specific proof:** Execute or statically prove the lifecycle for both an existing contract and a same-transaction-created contract.
  - **Provenance:** mixbytes CREATE2; [EIP-6780 SELFDESTRUCT](https://eips.ethereum.org/EIPS/eip-6780)

- [ ] **[EVM-ASM-003] CREATE2 address collision attack** _(exploit-pattern; medium)_: With ~2^80 work (birthday attack), an attacker can find a CREATE2 salt that produces the same address as an existing contract. At current compute costs, this is expensive but feasible for high-value targets (~$10B+). Look for: high-value contracts that don't verify code hash. [mixbytes CREATE2]
  - **Provenance:** mixbytes CREATE2

- [ ] **[EVM-ASM-004] CREATE inside CREATE2 does not guarantee metamorphic child replacement** _(semantic; high)_: A CREATE2 factory's child nonce and address assumptions must be evaluated together with the chain's SELFDESTRUCT rules. After EIP-6780, an existing factory cannot generally be destroyed and redeployed to reset its child-creation state.
  - **Trigger:** A CREATE2-deployed factory uses CREATE for children and the design relies on factory redeployment or nonce reset.
  - **Risk:** Assuming a factory or child can be replaced at the same address can break code identity and deployment invariants when the assumed lifecycle is unavailable.
  - **Detection:** Trace factory creation, child nonce/address derivation, SELFDESTRUCT, and any attempted redeployment on the target fork.
  - **Specific FP:** The design does not rely on post-EIP-6780 metamorphic replacement, or it proves the same-transaction creation path.
  - **Specific proof:** Reproduce the complete lifecycle and compare the observed child code/address with the assumed deployment model.
  - **Provenance:** mixbytes CREATE2; [EIP-6780 SELFDESTRUCT](https://eips.ethereum.org/EIPS/eip-6780)

- [ ] **[EVM-ASM-005] One-time code verification may not establish ongoing code identity** _(semantic; high)_: A code-hash check made at registration proves only the state observed at that time. Ongoing identity requires verifying the code at each security-sensitive use and accounting for proxy upgrades, same-transaction creation/destruction, and the target chain's SELFDESTRUCT rules.
  - **Trigger:** A trusted address is registered once and later used without rechecking code identity.
  - **Risk:** Trusting a stale code check can route calls or assets to code that no longer satisfies the intended identity invariant.
  - **Detection:** Trace upgrades, code replacement, proxy implementation changes, and the exact use-time code check.
  - **Specific FP:** The address is immutable and the deployment model proves code cannot change, or use-time code identity is checked.
  - **Specific proof:** Provide a lifecycle trace showing whether the registered code hash can differ from the code used by the protected operation.
  - **Provenance:** mixbytes CREATE2; [EIP-6780 SELFDESTRUCT](https://eips.ethereum.org/EIPS/eip-6780)
  - **Notes:** ### EXTCODESIZE / isContract Bypass

- [ ] **[EVM-ASM-006] Contract-code checks return zero during construction** _(exploit-pattern; medium)_: While a contract's constructor is executing, `extcodesize(address(this)) == 0` and `address(this).code.length == 0`. Any check like `require(!isContract(msg.sender))` can be bypassed by calling from a constructor. Look for: `isContract()`, `Address.isContract()`, `extcodesize`, or `address.code.length` used as access control. [mixbytes CREATE2, SWC-112, beirao G-14]
  - **Provenance:** mixbytes CREATE2, SWC-112, beirao G-14

- [ ] **[EVM-ASM-007] Pre-deployed CREATE2 address has no code** _(exploit-pattern; medium)_: Before deployment, a CREATE2 address is just a number — no code exists there. `extcodesize == 0`, `codehash == 0`. If you whitelist this address and later check `isContract()`, it fails until deployed. Look for: address whitelisting before actual deployment. [mixbytes CREATE2]
  - **Provenance:** mixbytes CREATE2

- [ ] **[EVM-ASM-008] `extcodecopy` after SELFDESTRUCT depends on fork and creation lifecycle** _(semantic; high)_: On post-EIP-6780 chains, SELFDESTRUCT of an existing contract does not remove its code, so extcodecopy does not generally become empty in the next transaction. Empty-code behavior remains relevant for a contract created and destroyed in the same transaction and for pre-EIP-6780 forks.
  - **Trigger:** The implementation copies or checks code after a target may execute SELFDESTRUCT.
  - **Risk:** Code-integrity checks that assume every SELFDESTRUCT empties code can accept or reject the wrong target state.
  - **Detection:** Identify the target chain fork and whether the target was created in the same transaction as SELFDESTRUCT; inspect both same-transaction and later reads.
  - **Specific FP:** The code-state assertion matches the target fork and creation lifecycle, and identity is checked at use time.
  - **Specific proof:** Run a fork-appropriate trace of extcodesize/extcodecopy before and after SELFDESTRUCT and compare it with the invariant.
  - **Provenance:** mixbytes CREATE2; [EIP-6780 SELFDESTRUCT](https://eips.ethereum.org/EIPS/eip-6780)

## Inline Assembly Math

- [ ] **[EVM-ASM-009] Division by zero returns 0 in Yul** _(semantic; high)_: `div(x, 0)`, `sdiv(x, 0)`, and `mod(x, 0)` all return 0 in assembly instead of reverting like Solidity. This silently produces wrong results. Look for: any `div`, `sdiv`, `mod`, or `smod` in assembly without a prior zero check on the denominator. [beirao M-12, SWC-101]
  - **Provenance:** beirao M-12, SWC-101

- [ ] **[EVM-ASM-010] No overflow/underflow protection in assembly** _(semantic; high)_: Assembly `add`, `sub`, and `mul` silently wrap on overflow/underflow. Unlike Solidity ≥0.8 checked math, assembly never reverts; width-specific values such as `uint128` can also overflow after a 256-bit check. Look for: arithmetic in `assembly { }` blocks with user-influenced values or narrowing after assembly. [beirao M-10, Dacian — Inline Assembly Vulnerabilities]
  - **Provenance:** beirao M-10, Dacian — Inline Assembly Vulnerabilities

- [ ] **[EVM-ASM-011] `shr` and `shl` with shift ≥ 256 returns 0** _(exploit-pattern; medium)_: Unlike some languages where shifting by >= bit-width is undefined, EVM returns 0. This is usually correct but can be surprising. Look for: shift amounts derived from user input. [SWC-101]
  - **Provenance:** SWC-101

- [ ] **[EVM-ASM-012] `signextend` misunderstanding** _(exploit-pattern; medium)_: `signextend(b, x)` extends the sign bit from byte `b` of `x`. Off-by-one on `b` (0-indexed from the least significant byte) produces wildly wrong results. Look for: `signextend` usage, verify `b` parameter is correct for the intended type width. [SWC-101]
  - **Provenance:** SWC-101

## Memory & Calldata in Assembly

- [ ] **[EVM-ASM-013] Memory expansion gas cost is quadratic** _(exploit-pattern; medium)_: Memory cost = `3 * words + words² / 512`. A single `mstore` at offset `2^32` costs ~32 billion gas. Any user-controlled memory offset is a gas bomb. Look for: `mstore(userOffset, ...)` or `mload(userOffset)` where offset isn't bounded. [SWC-101]
  - **Provenance:** SWC-101

- [ ] **[EVM-ASM-014] Free memory pointer and allocation integrity** _(semantic; high)_: If assembly overwrites `mload(0x40)`, writes below the free memory pointer without reserving space, or fails to advance the pointer, later Solidity operations can overwrite or read the wrong memory. Look for: assembly blocks that modify memory at `0x40` or below the current pointer without restoring or explicitly allocating it. [SWC-101, Tamjid C13]
  - **Provenance:** SWC-101, Tamjid C13

- [ ] **[EVM-ASM-015] Returndata buffer reuse** _(semantic; high)_: After an external call, `returndatasize` and `returndatacopy` reflect the LAST call's return data. A subsequent assembly block may read stale returndata from a previous call. Look for: `returndatacopy` without checking which call's data it references. [SWC-101]
  - **Provenance:** SWC-101

- [ ] **[EVM-ASM-016] `calldataload` beyond calldata returns 0** _(exploit-pattern; medium)_: Reading past `calldatasize()` returns zero-padded data. This can mask missing parameters. Look for: `calldataload` without bounds checking against `calldatasize`. [SWC-101]
  - **Provenance:** SWC-101

## Storage Writes

- [ ] **[EVM-ASM-017] User-controlled `sstore` slot enables arbitrary state corruption** _(exploit-pattern; medium)_: If an input influences the storage slot or the slot computation without a fixed, reviewed namespace, an attacker can overwrite ownership, balances, configuration, or accounting state. Look for: `sstore(userInput, value)`, user-controlled slot offsets, or hash-based slots whose namespace is not fixed by the protocol. [SWC-124]
  - **Provenance:** SWC-124

## Transient Storage — EIP-1153

- [ ] **[EVM-ASM-018] Transient storage slot collision across modules** _(semantic; high)_: Transient slots share a namespace for the active storage context. Reusing a slot between unrelated locks, callbacks, or accounting values—especially across `delegatecall`—lets one component overwrite another's state. Look for: generic numeric `tstore` slots or modules without namespaced transient keys. [EIP-1153](https://eips.ethereum.org/EIPS/eip-1153)
  - **Provenance:** [https://eips.ethereum.org/EIPS/eip-1153](https://eips.ethereum.org/EIPS/eip-1153); EIP-1153

- [ ] **[EVM-ASM-019] `delegatecall` exposes the caller's transient storage** _(semantic; high)_: Code reached through `delegatecall` executes with the caller's storage context, including EIP-1153 transient slots. Untrusted or insufficiently isolated delegatees can read or overwrite transient locks and in-flight accounting. Look for: `delegatecall` into code that uses `tload`/`tstore` without a reviewed slot contract. [EIP-1153](https://eips.ethereum.org/EIPS/eip-1153)
  - **Provenance:** [https://eips.ethereum.org/EIPS/eip-1153](https://eips.ethereum.org/EIPS/eip-1153); EIP-1153

- [ ] **[EVM-ASM-020] Transient storage lacks type/domain safety** _(exploit-pattern; medium)_: `tload` returns an untyped 256-bit word; reusing a slot for values with different widths or meanings can turn stale flags, amounts, or addresses into valid-looking state. Look for: the same transient slot used by multiple value types, missing masks/range checks, or transient keys not namespaced by module and purpose. [EIP-1153](https://eips.ethereum.org/EIPS/eip-1153)
  - **Provenance:** [https://eips.ethereum.org/EIPS/eip-1153](https://eips.ethereum.org/EIPS/eip-1153); EIP-1153

## Low-Level Calls

- [ ] **[EVM-ASM-021] `call()` to non-existent contract returns success** _(semantic; high)_: A low-level `call` to an address with no code returns `success = true` with empty returndata; reading stale memory as the return value can make this look valid. Solmate's `SafeTransferLib` has this vulnerability when code existence is not checked. Look for: `.call()`/`staticcall` without checking target code and return size, or potentially-empty addresses passed to SafeTransferLib. [beirao G-08, SWC-101, Dacian — Inline Assembly Vulnerabilities]
  - **Provenance:** beirao G-08, SWC-101, Dacian — Inline Assembly Vulnerabilities

- [ ] **[EVM-ASM-022] `delegatecall` preserves `msg.sender` and `msg.value`** _(semantic; high)_: Inside a `delegatecall`, `msg.sender` is the ORIGINAL caller, not the calling contract. `msg.value` is also preserved (the same ETH can be "spent" multiple times via delegatecall loops). Look for: `delegatecall` in functions that check `msg.value` for payment. [SWC-112]
  - **Provenance:** SWC-112

- [ ] **[EVM-ASM-023] Return bomb attack** _(semantic; high)_: A malicious contract can return enormous data (e.g., 1MB). If the caller copies all return data to memory (`returndatacopy(0, 0, returndatasize())`), the memory expansion cost can DoS the caller. Fix: limit returndata copy size. Look for: unbounded `returndatacopy` or Solidity `abi.decode` on untrusted external call returns. [beirao G-13]
  - **Provenance:** beirao G-13

- [ ] **[EVM-ASM-024] Gas forwarding with 63/64 rule (EIP-150)** _(exploit-pattern; medium)_: A `call` forwards at most 63/64 of remaining gas. With ~350K gas remaining, a nested call gets ~344K, leaving ~6K for the caller to finish execution. This can cause the outer call to succeed but the inner call to fail. Look for: nested calls where gas remaining after the inner call is critical. [SWC-126]
  - **Provenance:** SWC-126

## Compiler & EVM Version Quirks

- [ ] **[EVM-ASM-025] `PUSH0` availability depends on compiler target and chain fork** _(semantic; high)_: PUSH0 is an EVM instruction introduced by Shanghai. A compiler version alone does not determine whether deployed bytecode contains it: inspect the compiler EVM target and verify that the destination chain supports the instruction.
  - **Trigger:** Deployment uses compiler output that may contain PUSH0 and targets a non-mainnet or older fork.
  - **Risk:** Deploying bytecode containing PUSH0 to a chain or fork without support can fail at deployment or execution.
  - **Detection:** Inspect compiler version and evmVersion, disassemble the artifact for PUSH0, and compare the target chain fork's opcode support.
  - **Specific FP:** The artifact targets a fork with PUSH0 support, or compilation explicitly targets a compatible earlier EVM version.
  - **Specific proof:** Compile the declared artifact, identify PUSH0 bytes, and deploy or execute against the declared chain fork.
  - **Provenance:** multichain-auditor; multichain-auditor, beirao MC-03; [EIP-3855 PUSH0](https://eips.ethereum.org/EIPS/eip-3855)

- [ ] **[EVM-ASM-026] `type(uint8).max` = 255, not 256** _(exploit-pattern; medium)_: Off-by-one when using type max values. `type(uint8).max + 1` overflows. Look for: loop counters or array indices using `type(uintN).max` as upper bound without careful comparison. [SWC-101]
  - **Provenance:** SWC-101

- [ ] **[EVM-ASM-027] Dirty upper bits in assembly** _(semantic; high)_: When loading from storage or calldata in assembly, upper bits may contain garbage from previous operations. Always mask with `and(value, 0xff)` for uint8, `and(value, 0xffff)` for uint16, etc. Look for: assembly reads that assume clean upper bits without masking. [SWC-101]
  - **Provenance:** SWC-101

## Precompile Interactions

- [ ] **[EVM-ASM-028] ecrecover (0x01) gas cost varies by input** _(exploit-pattern; medium)_: Invalid inputs cause full gas consumption. If ecrecover is called in a loop with potentially-invalid data, gas exhaustion occurs. Look for: ecrecover calls with unbounded loop over user data. [SWC-113]
  - **Provenance:** SWC-113

- [ ] **[EVM-ASM-029] modexp (0x05) gas cost can be enormous** _(exploit-pattern; medium)_: Modular exponentiation precompile gas depends on exponent size. User-supplied exponents can cause massive gas consumption. Look for: modexp calls with user-controlled exponent length. [SWC-113]
  - **Provenance:** SWC-113

- [ ] **[EVM-ASM-030] Precompile address range differs by chain** _(exploit-pattern; medium)_: Addresses 0x01-0x09 are precompiles on mainnet. Other chains add custom precompiles at different addresses. Calling a non-existent precompile returns success with empty data. Look for: hardcoded precompile addresses in multi-chain deployments. [multichain-auditor]
  - **Provenance:** multichain-auditor

## CREATE/CREATE2 Deep Dive (Expanded from MixBytes)

- [ ] **[EVM-ASM-031] CREATE nonce dependency — reorg vulnerability** _(exploit-pattern; medium)_: With CREATE, the deployed address depends on the sender's nonce. A chain reorg can change the nonce, causing the contract to deploy at a different address. Users who sent funds to the pre-computed address lose them. Look for: address precomputation using CREATE (nonce-dependent) without reorg protection. [beirao G-19, MixBytes CREATE2]
  - **Provenance:** beirao G-19, MixBytes CREATE2

## Inline Assembly Pitfalls (Expanded)

- [ ] **[EVM-ASM-032] `chainid()` and `extcodesize()` available without assembly since Solidity 0.8** _(semantic; high)_: Using assembly for `chainid` or `extcodesize` is unnecessary in modern Solidity and adds audit complexity. `block.chainid` and `address.code.length` work natively. Look for: assembly blocks used for operations available as Solidity builtins. [Tamjid C37]
  - **Provenance:** Tamjid C37
  - **Notes:** ---

## Dacian — Solidity Inline Assembly Vulnerabilities (Phase 3)

- [ ] **[EVM-ASM-033] Memory corruption from external call overwriting assembly-stored variables** _(semantic; high)_: Manual assembly stores values at NFMA (0x80, 0xa0...) but doesn't update the free memory pointer (0x40). When a subsequent external call occurs, Solidity reads stale FMPA, overwrites stored variables with call setup data and return values. Fix: `mstore(0x40, dataPtr)` after assembly allocations before any external call. [Source: Dacian — Inline Assembly Vulnerabilities, OpenZeppelin Scroll Phase 1]
  - **Provenance:** Source: Dacian — Inline Assembly Vulnerabilities, OpenZeppelin Scroll Phase 1

- [ ] **[EVM-ASM-034] Assuming unchanged free memory pointer between assembly blocks** _(semantic; high)_: Normal Solidity code between assembly blocks updates FMPA. If the final assembly block reads FMPA assuming it still points to where inputs were stored, it will hash wrong memory regions (possibly empty). Fix: save start pointer in a variable, don't rely on FMPA in later blocks. [Source: Dacian — Inline Assembly Vulnerabilities]
  - **Provenance:** Source: Dacian — Inline Assembly Vulnerabilities

- [ ] **[EVM-ASM-035] Memory corruption from insufficient allocation (off-by-32)** _(semantic; high)_: If `init()` allocates `capacity` bytes but `write()` expects `capacity + 32` (for length prefix), writes overflow into adjacent memory variables. The ENS Buffer library had this: writing "A" corrupted `foo.length` stored immediately after the buffer. [Source: Dacian — Inline Assembly Vulnerabilities, ConsenSys ENS Audit]
  - **Provenance:** Source: Dacian — Inline Assembly Vulnerabilities, ConsenSys ENS Audit

- [ ] **[EVM-ASM-036] uint128 overflow evades detection because assembly uses 256-bit words** _(semantic; high)_: For `uint128` parameters, `add(type(uint128).max, 1)` in assembly returns a 256-bit value that's > input (passing the `lt` check), but when returned as `uint128` it silently overflows to 0. Fix: use `addmod` with N=type(uint128).max, or add Solidity-level `require()` after the assembly block. [Source: Dacian — Inline Assembly Vulnerabilities, Trail of Bits Primitive Hyper]
  - **Provenance:** Source: Dacian — Inline Assembly Vulnerabilities, Trail of Bits Primitive Hyper

## Supplemental Attack Vectors (SAS-AV)

- [ ] **[EVM-ASM-037] CREATE / CREATE2 Deployment Failure Silently Returns Zero** _(semantic; high)_: Assembly `create(v, offset, size)` or `create2(v, offset, size, salt)` returns `address(0)` on failure but code does not check for zero.
  - **Specific FP:** Immediate check: `if iszero(addr) { revert(0, 0) }` after create/create2. Address validated downstream.
  - **Provenance:** [SAS-AV-014](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-102

- [ ] **[EVM-ASM-038] Hardcoded Calldataload Offset Bypass via Non-Canonical ABI Encoding** _(semantic; high)_: Assembly reads a field at hardcoded calldata offset assuming standard ABI layout. Attacker crafts non-canonical encoding so a different value sits at the expected position.
  - **Specific FP:** Field decoded via `abi.decode()`. No hardcoded `calldataload` offsets. `calldatasize() >= expected` validated.
  - **Provenance:** [SAS-AV-017](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-166

- [ ] **[EVM-ASM-039] Unsafe ABI Decoding of Untrusted Calldata** _(semantic; high)_: Raw `abi.decode(data, (...))` called on user-supplied or cross-contract calldata without length or schema validation. Truncated, malformed, or oversized payloads cause unexpected reverts, type confusion, or silent misinterpretation of parameters. In assembly-based decoders, out-of-bounds reads return zero.
  - **Specific FP:** `data.length >= expectedMinLength` checked before decoding. `try/catch` wrapping untrusted decode. Assembly decoders validate bounds. Only trusted internal calldata decoded without checks.
  - **Provenance:** [SAS-AV-021](https://github.com/sanbir/solidity-auditor-skills)
  - **Source detail:** `sanbir/solidity-auditor-skills` AV-216
