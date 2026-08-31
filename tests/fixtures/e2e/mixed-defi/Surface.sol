// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface MixedToken {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

interface IERC4626Mixed {
    function deposit(uint256 assets, address receiver) external returns (uint256);
}

interface MixedOracle {
    function latestRoundData() external view returns (uint80, int256, uint256, uint256, uint80);
}

contract MixedDefiSurface {
    MixedToken public token;
    IERC4626Mixed public vault;
    MixedOracle public oracle;

    function swap(uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
        vault.deposit(amount, msg.sender);
        oracle.latestRoundData();
    }

    function borrow(uint256 amount) external {
        amount;
    }

    function stake(uint256 amount) external {
        amount;
    }
}
