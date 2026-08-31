// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IERC20Surface {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

contract ERC20Surface {
    IERC20Surface public token;

    function deposit(uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
    }
}
