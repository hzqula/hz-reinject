// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SimpleBank {
    mapping(address => uint256) public balances;
    
    // [INSTRUMENTASI MANUAL]
    uint256 public totalDeposits;

    function deposit() public payable {
        balances[msg.sender] += msg.value;
        totalDeposits += msg.value;
    }

    function withdraw(uint256 _amount) public {
        require(balances[msg.sender] >= _amount, "Insufficient funds");

        // [SECURE PATTERN] Effects (Update State) DULU
        balances[msg.sender] -= _amount;
        totalDeposits -= _amount;

        // [INTERACTION] Transfer BELAKANGAN
        (bool success, ) = msg.sender.call{value: _amount}("");
        require(success, "Transfer failed");
    }

    // [ORACLE]
    function echidna_test_solvency() public view returns (bool) {
        return address(this).balance >= totalDeposits;
    }
}