// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

interface IERC4626 is IERC20 {
    function deposit(uint256 assets, address receiver) external returns (uint256);
}

interface AggregatorV3Interface {
    function latestRoundData() external view returns (uint80, int256, uint256, uint256, uint80);
}

abstract contract ERC1967Proxy {}
abstract contract EIP712 {}

library MerkleProof {
    function verify(bytes32[] memory, bytes32, bytes32) internal pure returns (bool) {
        return true;
    }
}

contract ReconFixture is ERC1967Proxy, EIP712 {
    IERC20 public token;
    IERC4626 public vault;
    AggregatorV3Interface public oracle;

    constructor(IERC20 token_, IERC4626 vault_, AggregatorV3Interface oracle_) payable {
        token = token_;
        vault = vault_;
        oracle = oracle_;
    }

    function multicall(bytes[] calldata calls) external payable returns (bytes[] memory results) {
        results = new bytes[](calls.length);
        for (uint256 i; i < calls.length; ++i) {
            (bool success, bytes memory result) = address(this).delegatecall(calls[i]);
            require(success);
            results[i] = result;
        }
    }

    function useSurface(bytes32[] calldata proof, bytes32 root, bytes32 leaf) external payable {
        token.transferFrom(msg.sender, address(this), msg.value);
        oracle.latestRoundData();
        MerkleProof.verify(proof, root, leaf);
        assembly {
            pop(create2(0, 0, 0, 0))
        }
    }

    function onERC721Received(address, address, uint256, bytes calldata) external pure returns (bytes4) {
        return this.onERC721Received.selector;
    }
}
