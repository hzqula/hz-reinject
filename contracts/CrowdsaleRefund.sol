// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract CrowdsaleRefund {
    mapping(address => uint256) public balances;
    uint256 public targetAmount = 100 ether;

    function contribute() public payable {
        balances[msg.sender] += msg.value;
    }

    // Fungsi Refund (Aman)
    function claimRefund() public {
        // Hanya boleh refund jika total belum mencapai target
        require(address(this).balance < targetAmount, "Target reached, no refunds");
        
        uint256 amount = balances[msg.sender];
        require(amount > 0, "No contribution");

        // [SECURE PATTERN] 
        balances[msg.sender] = 0;

        // Transfer
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Refund failed");
    }
}