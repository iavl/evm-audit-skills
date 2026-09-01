pragma solidity ^0.8.0;

import "./MathLib.sol";
import "./Service.sol";
import * as DuplicateA from "./DuplicateA.sol";
import * as DuplicateB from "./DuplicateB.sol";

contract Base {
    uint256 public inherited;

    modifier auth() {
        _modifierHelper();
        _;
    }

    function _modifierHelper() internal {
        inherited = inherited + 1;
    }
}

contract Main is Base {
    uint256 public value;
    Service public target;

    function entry(uint256 amount) external auth returns (uint256) {
        uint256 local = amount + 1;
        value = local;
        _helper(amount);
        uint256 result = target.ping(amount);
        uint256 remote = target.number();
        uint256 bumped = MathLib.bump(amount);
        (bool delegated, ) = address(target).delegatecall(abi.encodeWithSignature("ping(uint256)", amount));
        (bool called, ) = address(target).call(abi.encodeWithSignature("ping(uint256)", amount));
        require(delegated || called);
        return result + remote + bumped + local;
    }

    function _helper(uint256 amount) internal returns (uint256) {
        value = amount;
        return _callee(amount);
    }

    function _callee(uint256 amount) internal pure returns (uint256) {
        uint256 local = amount * 2;
        return local;
    }

    function overloaded(uint256 amount) external pure returns (uint256) {
        return amount;
    }

    function overloaded(address account) external pure returns (address) {
        return account;
    }
}
