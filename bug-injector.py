#!/usr/bin/env python3
"""
Fixed Reentrancy Bug Injector - Oracle Violation Version
Change: Removed totalDeposits update to force invariant violation on withdraw
"""

import os
import re
import json
import subprocess
from typing import List, Dict

class ReentrancyInjector:
    def __init__(self, contract_path: str, output_dir: str = "injected-contracts"):
        self.contract_path = contract_path
        self.output_dir = output_dir
        self.contract_name = os.path.basename(contract_path).replace('.sol', '')
        
        with open(contract_path, 'r', encoding='utf-8') as f:
            self.source_code = f.read()
        
        self.main_contract_name = self._detect_contract_name()
        self.balance_mapping = self._detect_balance_mapping()
        self.total_deposits_var = self._detect_total_deposits()
        
        self.injection_log = []
    
    def _detect_contract_name(self) -> str:
        match = re.search(r'contract\s+(\w+)', self.source_code)
        return match.group(1) if match else self.contract_name
    
    def _detect_balance_mapping(self) -> str:
        patterns = [
            r'mapping\s*\(\s*address\s*=>\s*uint256\s*\)\s*(?:public|private|internal)?\s+(\w+)',
            r'mapping\s*\(\s*address\s*=>\s*uint\s*\)\s*(?:public|private|internal)?\s+(\w+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, self.source_code)
            if match:
                print(f"[INFO] Detected balance mapping: {match.group(1)}")
                return match.group(1)
        print("[WARN] No balance mapping found, will use 'balances'")
        return 'balances'
    
    def _detect_total_deposits(self) -> str:
        match = re.search(r'uint256\s+(?:public\s+)?(\w*[Tt]otal\w*)', self.source_code)
        if match:
            print(f"[INFO] Detected total deposits variable: {match.group(1)}")
            return match.group(1)
        print("[WARN] No total deposits variable found, will use 'totalDeposits'")
        return 'totalDeposits'
    
    def _get_bug_variants(self) -> List[Dict]:
        # NOTE: We intentionally REMOVED the totalDeposits update logic 
        # to ensure the solvency oracle (balance >= totalDeposits) fails when money leaves.
        variants = []
        
        # Variant 1: Classic
        variants.append({
            'name': 'classic_call_reentrancy',
            'description': 'Classic call.value() with CEI violation',
            'code': f'''
    // ========== INJECTED BUG: Classic Reentrancy ==========
    function withdraw_vulnerable(uint256 _amount) public {{
        require({self.balance_mapping}[msg.sender] >= _amount, "Insufficient balance");
        (bool success, ) = msg.sender.call{{value: _amount}}("");
        require(success, "Transfer failed");
        {self.balance_mapping}[msg.sender] -= _amount;
        // BUG: Missing {self.total_deposits_var} update causes invariant violation!
    }}
    
    function echidna_no_reentrancy_classic() public view returns (bool) {{
        return address(this).balance >= {self.total_deposits_var};
    }}
'''
        })
        
        # Variant 2: Send
        variants.append({
            'name': 'send_reentrancy',
            'description': 'Send-based reentrancy',
            'constructor': '    constructor() payable {} \n    receive() external payable {}',
            'code': f'''
    // ========== INJECTED BUG: Send Reentrancy ==========
    function withdraw_send(uint256 _amount) public {{
        require({self.balance_mapping}[msg.sender] >= _amount, "Insufficient balance");
        bool success = payable(msg.sender).send(_amount);
        require(success, "Send failed");
        {self.balance_mapping}[msg.sender] -= _amount;
        // BUG: Missing {self.total_deposits_var} update
    }}
    
    function echidna_no_reentrancy_send() public view returns (bool) {{
        return address(this).balance >= {self.total_deposits_var};
    }}
'''
        })
        
        # Variant 3: Transfer
        variants.append({
            'name': 'transfer_reentrancy',
            'description': 'Transfer-based reentrancy',
            'constructor': '    constructor() payable {} \n    receive() external payable {}',
            'code': f'''
    // ========== INJECTED BUG: Transfer Reentrancy ==========
    function withdraw_transfer() public {{
        uint256 amount = {self.balance_mapping}[msg.sender];
        require(amount > 0, "No balance");
        payable(msg.sender).transfer(amount);
        {self.balance_mapping}[msg.sender] = 0;
        // BUG: Missing {self.total_deposits_var} update
    }}
    
    function echidna_no_reentrancy_transfer() public view returns (bool) {{
        return address(this).balance >= {self.total_deposits_var};
    }}
'''
        })
        
        # Variant 4: Cross-function
        variants.append({
            'name': 'cross_function_reentrancy',
            'description': 'Cross-function reentrancy',
            'constructor': '    constructor() payable {} \n    receive() external payable {}',
            'code': f'''
    // ========== INJECTED BUG: Cross-Function Reentrancy ==========
    uint256 public pendingRewards;
    
    function addRewards() public payable {{
        pendingRewards += msg.value;
    }}
    
    function withdraw_partial(uint256 _amount) public {{
        require({self.balance_mapping}[msg.sender] >= _amount, "Insufficient balance");
        (bool success,) = msg.sender.call{{value: _amount}}("");
        require(success);
        {self.balance_mapping}[msg.sender] -= _amount;
        // BUG: Missing {self.total_deposits_var} update
    }}
    
    function claimReward() public {{
        require({self.balance_mapping}[msg.sender] > 0, "Must have balance");
        uint256 reward = pendingRewards / 100;
        (bool success,) = msg.sender.call{{value: reward}}("");
        require(success);
        pendingRewards -= reward;
    }}
    
    function echidna_no_reentrancy_cross() public view returns (bool) {{
        return address(this).balance >= ({self.total_deposits_var} + pendingRewards);
    }}
'''
        })
        
        # Variant 5: Delegatecall
        variants.append({
            'name': 'delegatecall_reentrancy',
            'description': 'Delegatecall-based reentrancy',
            'constructor': '    constructor() payable {} \n    receive() external payable {}',
            'code': f'''
    // ========== INJECTED BUG: Delegatecall Reentrancy ==========
    address public externalContract;
    
    function setExternalContract(address _contract) public {{
        externalContract = _contract;
    }}
    
    function execute_external(bytes memory _data) public {{
        require({self.balance_mapping}[msg.sender] > 0, "No balance");
        (bool success,) = externalContract.delegatecall(_data);
        require(success, "Delegatecall failed");
    }}
    
    function withdraw_after_execute(uint256 _amount) public {{
        require({self.balance_mapping}[msg.sender] >= _amount);
        (bool success,) = msg.sender.call{{value: _amount}}("");
        require(success);
        {self.balance_mapping}[msg.sender] -= _amount;
        // BUG: Missing {self.total_deposits_var} update
    }}
    
    function echidna_no_reentrancy_delegatecall() public view returns (bool) {{
        return address(this).balance >= {self.total_deposits_var};
    }}
'''
        })
        
        print(f"[INFO] Generated {len(variants)} bug variants")
        return variants
    
    # Helper method to find contract end from current LINES list
    def _find_contract_end_from_lines(self, lines: List[str]) -> int:
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if line.startswith('}') or line == '}':
                return i
        return len(lines) - 1

    def _find_or_create_constructor(self, lines: list) -> tuple:
        for i, line in enumerate(lines):
            if 'constructor(' in line or 'constructor (' in line:
                return (True, i)
        for i, line in enumerate(lines):
            if 'function ' in line and 'public' in line:
                return (False, i)
        for i, line in enumerate(lines):
            if 'contract ' in line and '{' in line:
                return (False, i + 1)
        return (False, 0)
    
    def inject_all(self) -> List[str]:
        os.makedirs(self.output_dir, exist_ok=True)
        bug_variants = self._get_bug_variants()
        output_files = []
        
        for i, variant in enumerate(bug_variants):
            try:
                lines = self.source_code.split('\n')
                
                if 'constructor' in variant:
                    has_constructor, constructor_pos = self._find_or_create_constructor(lines)
                    if not has_constructor:
                        lines.insert(constructor_pos, variant['constructor'])
                        print(f"  [+] Injected payable constructor at line {constructor_pos}")
                
                inject_pos = self._find_contract_end_from_lines(lines)
                lines.insert(inject_pos, variant['code'])
                
                injected_code = '\n'.join(lines)
                
                new_contract_name = f"{self.main_contract_name}_Injected_V{i+1}"
                injected_code = re.sub(
                    r'contract\s+' + re.escape(self.main_contract_name) + r'\b',
                    f'contract {new_contract_name}',
                    injected_code,
                    count=1
                )
                
                output_filename = f"{self.contract_name}_{variant['name']}.sol"
                output_path = os.path.join(self.output_dir, output_filename)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(injected_code)
                output_files.append(output_path)
                self.injection_log.append({
                    'file': output_filename,
                    'variant': i + 1,
                    'bug_type': variant['name'],
                    'location': f'Line {inject_pos}'
                })
                print(f"  ✓ Generated: {output_filename}")
                
            except Exception as e:
                print(f"[ERROR] Failed to inject variant {i}: {e}")
        
        self._save_log()
        return output_files
    
    def _save_log(self):
        log_path = os.path.join(self.output_dir, f"{self.contract_name}_injection_log.json")
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump({'injections': self.injection_log}, f, indent=2)
        print(f"[INFO] Injection log saved: {log_path}")

def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 bug-injector.py <contract.sol> [output_dir]")
        sys.exit(1)
    
    contract_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "injected-contracts"
    
    if not os.path.exists(contract_path):
        print(f"[ERROR] Contract not found: {contract_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("SolidiFI-Inspired Reentrancy Bug Injector (Fixed & Oracle-Violation)")
    print("=" * 60)
    
    injector = ReentrancyInjector(contract_path, output_dir)
    injector.inject_all()
    print(f"\n✓ Generated contracts in: {output_dir}/")

if __name__ == "__main__":
    main()