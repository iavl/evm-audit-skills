#!/usr/bin/env bash
set -euo pipefail

hardfork="${1:-}"
case "$hardfork" in
  paris|cancun) ;;
  *) echo "usage: $0 paris|cancun" >&2; exit 2 ;;
esac

port="$((18545 + RANDOM % 1000))"
private_key="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
rpc_url="http://127.0.0.1:${port}"
tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/eip6780.XXXXXX")"
anvil_pid=""
cleanup() {
  if [[ -n "$anvil_pid" ]]; then kill "$anvil_pid" 2>/dev/null || true; fi
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

anvil --hardfork "$hardfork" --port "$port" --silent >"$tmp_dir/anvil.log" 2>&1 &
anvil_pid=$!
for _ in {1..50}; do
  if cast block-number --rpc-url "$rpc_url" >/dev/null 2>&1; then break; fi
  sleep 0.1
done
cast block-number --rpc-url "$rpc_url" >/dev/null

FOUNDRY_EVM_VERSION="$hardfork" forge build --root tests/semantics-eip6780 >/dev/null
factory="$(FOUNDRY_EVM_VERSION="$hardfork" forge create --root tests/semantics-eip6780 --rpc-url "$rpc_url" --private-key "$private_key" --broadcast --json src/EIP6780Lifecycle.sol:EIP6780LifecycleFactory | jq -r '.deployedTo')"
[[ "$factory" != "null" && -n "$factory" ]]
salt="0x$(printf '%064d' 6780)"
cast send "$factory" "deploy2(bytes32)" "$salt" --rpc-url "$rpc_url" --private-key "$private_key" >/dev/null
target="$(cast call "$factory" "target()(address)" --rpc-url "$rpc_url")"
cast send "$target" "destroy()" --rpc-url "$rpc_url" --private-key "$private_key" >/dev/null
code_after="$(cast code "$target" --rpc-url "$rpc_url")"

if [[ "$hardfork" == "paris" ]]; then
  [[ "$code_after" == "0x" ]]
  cast send "$factory" "deploy2(bytes32)" "$salt" --rpc-url "$rpc_url" --private-key "$private_key" >/dev/null
else
  [[ "$code_after" != "0x" ]]
  if cast send "$factory" "deploy2(bytes32)" "$salt" --rpc-url "$rpc_url" --private-key "$private_key" >/dev/null 2>&1; then
    echo "Cancun unexpectedly allowed CREATE2 redeployment" >&2
    exit 1
  fi
fi

echo "EIP-6780 ${hardfork}: independent deploy → SELFDESTRUCT → code check → CREATE2 redeploy passed"
