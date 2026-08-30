// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

contract EIP6780LifecycleTarget {
    function destroy() external {
        selfdestruct(payable(msg.sender));
    }
}

contract EIP6780LifecycleFactory {
    address public target;

    function deploy2(bytes32 salt) external returns (address deployed) {
        bytes memory initCode = type(EIP6780LifecycleTarget).creationCode;
        assembly {
            deployed := create2(0, add(initCode, 0x20), mload(initCode), salt)
        }
        require(deployed != address(0), "CREATE2_FAILED");
        target = deployed;
    }
}
