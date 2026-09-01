pragma solidity ^0.8.0;

contract Service {
    uint256 public number;

    function ping(uint256 value) external pure returns (uint256) {
        return value;
    }
}
