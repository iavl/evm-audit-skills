// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract BridgeSurface {
    event MessageSent(uint256 destinationChain, bytes payload);

    function bridge(uint256 destinationChain, bytes calldata payload) external {
        emit MessageSent(destinationChain, payload);
    }

    function sendMessage(bytes calldata payload) external {
        emit MessageSent(0, payload);
    }
}
