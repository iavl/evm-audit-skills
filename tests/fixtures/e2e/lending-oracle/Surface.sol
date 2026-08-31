// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface OracleSurface {
    function latestRoundData() external view returns (uint80, int256, uint256, uint256, uint80);
}

contract LendingOracleSurface {
    OracleSurface public oracle;

    function borrow(uint256 collateral) external view returns (uint256) {
        oracle.latestRoundData();
        return collateral;
    }

    function liquidate(address borrower) external {
        borrower;
    }
}
