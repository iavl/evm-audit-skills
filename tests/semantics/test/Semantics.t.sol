// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

contract Returner {
    function word() external pure returns (uint256) {
        return 0xBEEF;
    }

    fallback() external {
        assembly {
            return(0, calldatasize())
        }
    }
}

contract GasConsumer {
    function consume() external pure returns (uint256 result) {
        for (uint256 i; i < 1_000; ++i) {
            result += i;
        }
    }
}

contract ZeroBalanceCreate {
    function attemptCreateWithValue() external returns (address deployed) {
        assembly {
            deployed := create(1, 0, 0)
        }
    }
}

contract DelegateTarget {
    function record() external payable {
        assembly {
            sstore(0, caller())
            sstore(1, callvalue())
        }
    }

    function recordTransient() external {
        assembly {
            tstore(0xA11CE, 0xBEEF)
        }
    }
}

contract UnsafeAbiReader {
    function readsTrailingCalldata() external pure returns (uint256 value) {
        assembly {
            value := calldataload(4)
        }
    }

    function readsDynamicHead(bytes calldata) external pure returns (uint256 value) {
        assembly {
            value := calldataload(4)
        }
    }
}

contract ReentrantCallback {
    ReentrancyVictim public victim;
    bool private entered;

    function setVictim(ReentrancyVictim target) external {
        victim = target;
    }

    function callback() external {
        if (!entered) {
            entered = true;
            victim.enter();
        }
    }
}

contract ReentrancyVictim {
    ReentrantCallback public immutable callbackTarget;
    uint256 public completed;

    constructor(ReentrantCallback target) {
        callbackTarget = target;
    }

    function enter() external {
        callbackTarget.callback();
        ++completed;
    }
}

contract InheritanceA {
    function resolved() public pure virtual returns (uint256) {
        return 1;
    }
}

contract InheritanceB {
    function resolved() public pure virtual returns (uint256) {
        return 2;
    }
}

contract InheritanceAB is InheritanceA, InheritanceB {
    function resolved() public pure override(InheritanceA, InheritanceB) returns (uint256) {
        return super.resolved();
    }
}

contract InheritanceBA is InheritanceB, InheritanceA {
    function resolved() public pure override(InheritanceB, InheritanceA) returns (uint256) {
        return super.resolved();
    }
}

contract SemanticsTest {
    address private storedSender;
    uint256 private storedValue;

    function testYulDivisionByZeroReturnsZero() external pure {
        uint256 quotient;
        uint256 signedQuotient;
        uint256 remainder;
        assembly {
            quotient := div(7, 0)
            signedQuotient := sdiv(7, 0)
            remainder := mod(7, 0)
        }
        require(quotient == 0 && signedQuotient == 0 && remainder == 0, "Yul zero divisor semantics changed");
    }

    function testYulArithmeticWrapsAt256Bits() external pure {
        uint256 wrapped;
        uint256 widerThanUint128;
        assembly {
            wrapped := add(not(0), 1)
            widerThanUint128 := add(0xffffffffffffffffffffffffffffffff, 1)
        }
        require(wrapped == 0, "Yul add should wrap modulo 2**256");
        require(widerThanUint128 == 1 << 128, "assembly operates on 256-bit words");
        require(uint128(widerThanUint128) == 0, "narrowing must truncate explicitly");
    }

    function testFreeMemoryPointerIsNotAdvancedByMstore() external pure {
        uint256 beforePointer;
        uint256 afterPointer;
        uint256 observed;
        assembly {
            beforePointer := mload(0x40)
            mstore(beforePointer, 0xCAFE)
            afterPointer := mload(0x40)
            observed := mload(beforePointer)
        }
        require(beforePointer == afterPointer, "mstore must not allocate memory implicitly");
        require(observed == 0xCAFE, "memory write not observed");
    }

    function testExternalCallWritesToCallerSelectedMemory() external {
        Returner target = new Returner();
        uint256 observed;
        bool success;
        assembly {
            let pointer := mload(0x40)
            mstore(pointer, 0xCAFE)
            mstore(0, shl(224, 0x2f64d386))
            success := call(gas(), target, 0, 0, 4, pointer, 32)
            observed := mload(pointer)
        }
        require(success && observed == 0xBEEF, "call output must overwrite the selected buffer");
    }

    function testReturndataBufferIsReplacedAfterEachCall() external {
        Returner target = new Returner();
        uint256 firstSize;
        uint256 secondSize;
        assembly {
            mstore(0, shl(224, 0x2f64d386))
            pop(call(gas(), target, 0, 0, 4, 0, 0))
            firstSize := returndatasize()
            pop(call(gas(), 0x000000000000000000000000000000000000dEaD, 0, 0, 0, 0, 0))
            secondSize := returndatasize()
        }
        require(firstSize == 32 && secondSize == 0, "returndata must describe only the latest call");
    }

    function testTransientStorageIsSharedThroughDelegatecall() external {
        DelegateTarget target = new DelegateTarget();
        (bool success,) = address(target).delegatecall(abi.encodeCall(DelegateTarget.recordTransient, ()));
        require(success, "delegatecall failed");
        uint256 observed;
        assembly {
            observed := tload(0xA11CE)
        }
        require(observed == 0xBEEF, "delegatecall must use the caller transient-storage context");
    }

    function testCallToNoCodeReturnsSuccessWithEmptyData() external {
        address noCode = address(0x000000000000000000000000000000000000dEaD);
        require(noCode.code.length == 0, "fixture unexpectedly has code");
        (bool success, bytes memory data) = noCode.call(hex"12345678");
        require(success && data.length == 0, "CALL to an empty account should succeed with empty returndata");
    }

    function delegateAndRecord(address target) external payable {
        require(msg.sender == address(this), "relay must be self-called by the test");
        (bool success,) = target.delegatecall(abi.encodeCall(DelegateTarget.record, ()));
        require(success, "delegatecall failed");
    }

    function testDelegatecallPreservesSenderAndValue() external {
        DelegateTarget target = new DelegateTarget();
        (bool success,) = address(this).call{value: 7}(abi.encodeCall(this.delegateAndRecord, (address(target))));
        require(success, "self-call failed");
        require(storedSender == address(this), "delegatecall changed msg.sender");
        require(storedValue == 7, "delegatecall changed msg.value");
    }

    function testReturndataCanBeArbitrarilyLarge() external {
        Returner target = new Returner();
        bytes memory payload = new bytes(8_192);
        (bool success, bytes memory data) = address(target).call(payload);
        require(success && data.length == payload.length, "caller copied attacker-sized returndata");
    }

    function testNarrowAssemblyValueCanCarryDirtyUpperBits() external pure {
        uint8 narrowed;
        uint256 raw;
        assembly {
            narrowed := not(0)
            raw := narrowed
        }
        require(raw == type(uint256).max, "assembly assignment unexpectedly cleaned upper bits");
        require(narrowed == type(uint8).max, "high-level use must observe the narrowed value");
    }

    function testChainidAndCodeLengthHaveHighLevelSyntax() external view {
        require(block.chainid != 0, "chainid unavailable");
        require(address(0xBEEF).code.length == 0, "code.length unavailable");
    }

    function testCreateFailureReturnsZeroInYul() external {
        ZeroBalanceCreate helper = new ZeroBalanceCreate();
        require(address(helper).balance == 0, "fixture must have zero balance");
        require(helper.attemptCreateWithValue() == address(0), "CREATE failure must return address(0)");
    }

    function testAssemblyCanReadNonCanonicalTrailingCalldata() external {
        UnsafeAbiReader target = new UnsafeAbiReader();
        bytes memory callData = abi.encodePacked(target.readsTrailingCalldata.selector, uint256(42));
        (bool success, bytes memory result) = address(target).call(callData);
        require(success && abi.decode(result, (uint256)) == 42, "trailing calldata was not observable");
    }

    function testHardcodedCalldataOffsetReadsDynamicHead() external {
        UnsafeAbiReader target = new UnsafeAbiReader();
        bytes memory actual = abi.encodePacked(uint256(99));
        require(target.readsDynamicHead(actual) == 32, "offset 4 should contain the dynamic ABI head, not data");
    }

    function testFixedGasCallCanFailWhileFullGasSucceeds() external {
        GasConsumer target = new GasConsumer();
        (bool limited,) = address(target).call{gas: 1_000}(abi.encodeCall(GasConsumer.consume, ()));
        (bool full,) = address(target).call(abi.encodeCall(GasConsumer.consume, ()));
        require(!limited && full, "fixed gas should be observable as a liveness constraint");
    }

    function testCrossContractReentrancyOccursBeforeAccounting() external {
        ReentrantCallback callbackTarget = new ReentrantCallback();
        ReentrancyVictim victim = new ReentrancyVictim(callbackTarget);
        callbackTarget.setVictim(victim);
        victim.enter();
        require(victim.completed() == 2, "callback did not reenter before accounting");
    }

    function testC3InheritanceOrderChangesSuperResolution() external {
        require(new InheritanceAB().resolved() == 2, "right-most base should resolve first");
        require(new InheritanceBA().resolved() == 1, "base order should change resolution");
    }

    function testExpressionWidthAndDowncastSemantics() external pure {
        uint8 a = 200;
        uint8 b = 100;
        uint8 wrapped;
        unchecked {
            wrapped = a + b;
        }
        require(wrapped == 44, "uint8 expression should not upcast to uint256");
        require(uint8(uint256(300)) == 44, "explicit downcast should truncate instead of reverting");
    }

    function testSignedToUnsignedConversionPreservesTwosComplementBits() external pure {
        int256 negative = -1;
        require(uint256(negative) == type(uint256).max, "signed conversion should preserve the bit pattern");
    }

    function testERC4626CanonicalRoundingDirections() external pure {
        uint256 supply = 3;
        uint256 assets = 2;
        require(5 * supply / assets == 7, "deposit and convertToShares round down");
        require((8 * assets + supply - 1) / supply == 6, "mint rounds assets up");
        require((5 * supply + assets - 1) / assets == 8, "withdraw rounds shares up");
        require(8 * assets / supply == 5, "redeem and convertToAssets round down");
    }

    function testIntegerDivisionRoundsTowardZero() external pure {
        require(uint256(1) / 2 == 0, "small integer division should truncate to zero");
    }
}
