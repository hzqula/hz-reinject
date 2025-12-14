#!/usr/bin/env python3
"""
Fixed Reentrancy Bug Injector
Simplified approach: inject lengkap di akhir contract saja
"""

import os
import re
import json
import subprocess
from typing import List, Dict

class SimpleReentrancyInjector:
    """
    Simplified injector: inject semua bug variants di akhir contract
    """
    
    def __init__(self, contract_path: str, output_dir: str = "injected-contracts"):
        self.contract_path = contract_path
        self.output_dir = output_dir
        self.contract_name = os.path.basename(contract_path).replace('.sol', '')
        
        # Baca source code
        with open(contract_path, 'r', encoding='utf-8') as f:
            self.source_code = f.read()
        
        # Detect contract name
        self.main_contract_name = self._detect_contract_name()
        
        # Detect balance mappings
        self.balance_mappings = self._detect_balance_mappings()
        
        self.injection_log = []
    
    def _detect_contract_name(self) -> str:
        """Extract main contract name"""
        match = re.search(r'contract\s+(\w+)', self.source_code)
        return match.group(1) if match else self.contract_name
    
    def _detect_balance_mappings(self) -> List[str]:
        """Detect balance mappings"""
        mappings = []
        pattern = r'mapping\s*\(\s*address\s*=>\s*u?int\d*\s*\)\s*(?:public|private|internal)?\s+(\w+)'
        
        for match in re.finditer(pattern, self.source_code):
            mappings.append(match.group(1))
        
        if not mappings:
            mappings = ['balances']
        
        print(f"[INFO] Detected mappings: {mappings}")
        return mappings
    
    def _get_bug_variants(self) -> List[str]:
        """
        Generate SEMUA variasi bug reentrancy
        Setiap bug variant = 1 complete contract
        """
        variants = []
        
        # Variant 1: Classic call.value reentrancy
        variants.append(f'''
    // ========== INJECTED REENTRANCY BUG: VARIANT 1 ==========
    // Classic call.value() reentrancy
    mapping(address => uint256) public balances_reentrancy;
    uint256 public totalDeposits_reentrancy;
    
    function deposit_reentrancy() public payable {{
        require(msg.value > 0, "Must deposit something");
        balances_reentrancy[msg.sender] += msg.value;
        totalDeposits_reentrancy += msg.value;
    }}
    
    function withdraw_reentrancy(uint256 _amount) public {{
        require(balances_reentrancy[msg.sender] >= _amount, "Insufficient balance");
        
        // VULNERABLE: External call BEFORE state update
        (bool success, ) = msg.sender.call{{value: _amount}}("");
        require(success, "Transfer failed");
        
        // State update AFTER call (reentrancy vulnerable!)
        balances_reentrancy[msg.sender] -= _amount;
        totalDeposits_reentrancy -= _amount;
    }}
    
    // Echidna property test
    function echidna_test_balance() public view returns (bool) {{
        return address(this).balance >= totalDeposits_reentrancy;
    }}
''')
        
        # Variant 2: Send-based reentrancy
        variants.append(f'''
    // ========== INJECTED REENTRANCY BUG: VARIANT 2 ==========
    // Send-based reentrancy
    mapping(address => uint256) public userBalance_send;
    uint256 public totalBalance_send;
    
    function addBalance_send() public payable {{
        require(msg.value > 0);
        userBalance_send[msg.sender] += msg.value;
        totalBalance_send += msg.value;
    }}
    
    function withdrawBalance_send(uint256 _amount) public {{
        require(userBalance_send[msg.sender] >= _amount);
        
        // VULNERABLE: Send before state update
        require(payable(msg.sender).send(_amount), "Send failed");
        userBalance_send[msg.sender] -= _amount;
        totalBalance_send -= _amount;
    }}
    
    function echidna_test_send() public view returns (bool) {{
        return address(this).balance >= totalBalance_send;
    }}
''')
        
        # Variant 3: Transfer-based
        variants.append(f'''
    // ========== INJECTED REENTRANCY BUG: VARIANT 3 ==========
    // Transfer-based reentrancy
    mapping(address => uint256) public rewards_transfer;
    uint256 public totalRewards_transfer;
    
    function addReward_transfer() public payable {{
        rewards_transfer[msg.sender] += msg.value;
        totalRewards_transfer += msg.value;
    }}
    
    function claimReward_transfer() public {{
        uint256 reward = rewards_transfer[msg.sender];
        require(reward > 0, "No reward");
        
        // VULNERABLE: Transfer before zeroing balance
        payable(msg.sender).transfer(reward);
        rewards_transfer[msg.sender] = 0;
        totalRewards_transfer -= reward;
    }}
    
    function echidna_test_transfer() public view returns (bool) {{
        return address(this).balance >= totalRewards_transfer;
    }}
''')
        
        # Variant 4: Cross-function reentrancy
        variants.append(f'''
    // ========== INJECTED REENTRANCY BUG: VARIANT 4 ==========
    // Cross-function reentrancy
    mapping(address => uint256) public stakes_cross;
    uint256 public totalStakes_cross;
    uint256 public rewardPool_cross;
    
    function stake_cross() public payable {{
        stakes_cross[msg.sender] += msg.value;
        totalStakes_cross += msg.value;
    }}
    
    function addRewardPool_cross() public payable {{
        rewardPool_cross += msg.value;
    }}
    
    function unstake_cross() public {{
        uint256 amount = stakes_cross[msg.sender];
        require(amount > 0, "No stake");
        
        // VULNERABLE: External call affects shared state
        (bool success,) = msg.sender.call{{value: amount}}("");
        require(success);
        
        stakes_cross[msg.sender] = 0;
        totalStakes_cross -= amount;
    }}
    
    function claimReward_cross() public {{
        require(stakes_cross[msg.sender] > 0, "Must have stake");
        uint256 reward = rewardPool_cross / 10; // 10% of pool
        
        (bool success,) = msg.sender.call{{value: reward}}("");
        require(success);
        
        rewardPool_cross -= reward;
    }}
    
    function echidna_test_cross() public view returns (bool) {{
        return address(this).balance >= (totalStakes_cross + rewardPool_cross);
    }}
''')
        
        # Variant 5: Withdraw pattern
        variants.append(f'''
    // ========== INJECTED REENTRANCY BUG: VARIANT 5 ==========
    // Withdraw pattern reentrancy
    mapping(address => uint256) public pendingWithdrawals;
    uint256 public totalPending;
    
    function deposit_withdraw() public payable {{
        pendingWithdrawals[msg.sender] += msg.value;
        totalPending += msg.value;
    }}
    
    function withdraw_pattern() public {{
        uint256 amount = pendingWithdrawals[msg.sender];
        require(amount > 0, "Nothing to withdraw");
        
        // VULNERABLE: Pay before reset
        (bool success,) = msg.sender.call{{value: amount}}("");
        require(success, "Transfer failed");
        
        pendingWithdrawals[msg.sender] = 0;
        totalPending -= amount;
    }}
    
    function echidna_test_withdraw() public view returns (bool) {{
        return address(this).balance >= totalPending;
    }}
''')
        
        print(f"[INFO] Generated {len(variants)} bug variants")
        return variants
    
    def _find_contract_end(self) -> int:
        """
        Temukan posisi sebelum closing brace terakhir dari contract
        """
        lines = self.source_code.split('\n')
        
        # Cari baris terakhir yang punya }
        for i in range(len(lines) - 1, -1, -1):
            if '}' in lines[i] and not lines[i].strip().startswith('//'):
                return i
        
        return len(lines) - 1
    
    def inject_all(self) -> List[str]:
        """
        Inject SEMUA variants ke contracts terpisah
        """
        os.makedirs(self.output_dir, exist_ok=True)
        
        bug_variants = self._get_bug_variants()
        output_files = []
        
        for i, bug_code in enumerate(bug_variants):
            try:
                # Split source ke lines
                lines = self.source_code.split('\n')
                
                # Temukan posisi inject (sebelum closing brace)
                inject_pos = self._find_contract_end()
                
                # Insert bug code
                lines.insert(inject_pos, bug_code)
                
                # Join kembali
                injected_code = '\n'.join(lines)
                
                # Rename contract
                new_contract_name = f"{self.main_contract_name}_Injected"
                injected_code = re.sub(
                    r'contract\s+' + re.escape(self.main_contract_name) + r'\b',
                    f'contract {new_contract_name}',
                    injected_code,
                    count=1
                )
                
                # Save to file
                output_filename = f"{self.contract_name}_variant_{i+1}.sol"
                output_path = os.path.join(self.output_dir, output_filename)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(injected_code)
                
                output_files.append(output_path)
                
                self.injection_log.append({
                    'file': output_filename,
                    'variant': i + 1,
                    'bug_type': f'Reentrancy Variant {i+1}',
                    'location': f'Line {inject_pos}',
                    'description': self._get_variant_description(i)
                })
                
            except Exception as e:
                print(f"[ERROR] Failed to inject variant {i}: {e}")
        
        print(f"\n[SUCCESS] Generated {len(output_files)} vulnerable contracts")
        
        # Save log
        self._save_log()
        
        return output_files
    
    def _get_variant_description(self, variant_idx: int) -> str:
        """Get description for each variant"""
        descriptions = [
            "Classic call.value() reentrancy with CEI violation",
            "Send-based reentrancy with state update after send()",
            "Transfer-based reentrancy with balance zeroing after transfer()",
            "Cross-function reentrancy with shared state",
            "Withdraw pattern reentrancy"
        ]
        return descriptions[variant_idx] if variant_idx < len(descriptions) else "Unknown"
    
    def _save_log(self):
        """Save injection log"""
        log_path = os.path.join(self.output_dir, f"{self.contract_name}_injection_log.json")
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump({
                'original_contract': self.contract_name,
                'main_contract_name': self.main_contract_name,
                'total_variants': len(self.injection_log),
                'balance_mappings_detected': self.balance_mappings,
                'injections': self.injection_log
            }, f, indent=2)
        
        print(f"[INFO] Injection log saved: {log_path}")


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 fixed_reentrancy_injector.py <contract.sol> [output_dir]")
        sys.exit(1)
    
    contract_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "injected-contracts"
    
    if not os.path.exists(contract_path):
        print(f"[ERROR] Contract not found: {contract_path}")
        sys.exit(1)
    
    print("=" * 70)
    print("Fixed Reentrancy Bug Injector")
    print("Simplified & Robust Approach")
    print("=" * 70)
    
    injector = SimpleReentrancyInjector(contract_path, output_dir)
    output_files = injector.inject_all()
    
    print(f"\n✓ Generated {len(output_files)} contracts")
    print(f"✓ Output: {output_dir}/")
    print("\nNext: python3 verify_contracts.py injected-contracts/")


if __name__ == "__main__":
    main()