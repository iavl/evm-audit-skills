// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IERC4626Surface {
    function deposit(uint256 assets, address receiver) external returns (uint256);
}

contract ERC4626Surface {
    IERC4626Surface public vault;

    function depositToVault(uint256 assets) external {
        vault.deposit(assets, msg.sender);
    }
}
