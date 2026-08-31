// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract GovernorSurface {
    mapping(uint256 => uint256) public proposalVotes;

    function proposal(uint256 id) external view returns (uint256) {
        return proposalVotes[id];
    }

    function castVote(uint256 id, uint256 weight) external {
        proposalVotes[id] += weight;
    }
}
