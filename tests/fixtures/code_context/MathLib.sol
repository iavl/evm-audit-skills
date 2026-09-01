pragma solidity ^0.8.0;

library MathLib {
    function bump(uint256 value) external pure returns (uint256) {
        return value + 1;
    }
}
