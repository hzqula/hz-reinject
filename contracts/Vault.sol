// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Vault {
    mapping(address => uint) public balances;

    uint public totalDeposits; 

    function deposit() public payable {
        balances[msg.sender] += msg.value;
        totalDeposits += msg.value;
    }

    function withdraw(uint _amount) public {
        require(balances[msg.sender] >= _amount);

        balances[msg.sender] -= _amount;
        totalDeposits -= _amount; 

        (bool success, ) = msg.sender.call{value: _amount}("");
        require(success);
    }

    // --- ORACLE ---
    function echidna_test_solvency() public view returns (bool) {
        return address(this).balance >= totalDeposits;
    }
}