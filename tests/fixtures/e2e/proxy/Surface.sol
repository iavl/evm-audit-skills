// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract UpgradeableProxySurface {
    address public implementation;

    function forward(address target, bytes calldata data) external returns (bool, bytes memory) {
        return target.delegatecall(data);
    }

    fallback() external payable {
        address target = implementation;
        assembly {
            calldatacopy(0, 0, calldatasize())
            let ok := delegatecall(gas(), target, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch ok
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }
}
