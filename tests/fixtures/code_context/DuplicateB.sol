pragma solidity ^0.8.0;

contract Duplicate {
    function same(uint256 value) external pure returns (uint256) {
        return value + 1;
    }
}
