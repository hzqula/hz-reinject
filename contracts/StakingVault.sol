// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract StakingVault {
    mapping(address => uint256) public balances;
    
    // [INSTRUMENTASI MANUAL]
    uint256 public totalDeposits;

    function stake() public payable {
        require(msg.value > 0, "Cannot stake 0");
        balances[msg.sender] += msg.value;
        totalDeposits += msg.value;
    }

    // Fungsi Unstake Semua (Aman)
    function unstakeAll() public {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "Nothing to unstake");

        // [SECURE PATTERN]
        balances[msg.sender] = 0;
        totalDeposits -= amount;

        // Transfer
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
    }

    // [ORACLE]
    function echidna_test_solvency() public view returns (bool) {
        return address(this).balance >= totalDeposits;
    }
}