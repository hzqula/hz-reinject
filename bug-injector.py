#!/usr/bin/env python3
"""
SolidiFI-Compliant Reentrancy Bug Injector
Methodology: Systematic Injection into All Candidate State Variables
"""

import os
import re
import json
from typing import List, Dict, Tuple

class ReentrancyInjector:
    def __init__(self, contract_path: str, output_dir: str = "injected-contracts"):
        self.contract_path = contract_path
        self.output_dir = output_dir
        self.contract_name = os.path.basename(contract_path).replace('.sol', '')
        
        with open(contract_path, 'r', encoding='utf-8') as f:
            self.source_code = f.read()
        
        self.main_contract_name = self._detect_contract_name()
        
        # [SOLIDIFI UPDATE] Detect ALL candidates, not just the first one
        self.balance_mappings = self._detect_all_balance_mappings()
        self.total_deposit_vars = self._detect_all_uint_vars()
        
        self.injection_log = []
    
    def _detect_contract_name(self) -> str:
        match = re.search(r'contract\s+(\w+)', self.source_code)
        return match.group(1) if match else self.contract_name
    
    def _detect_all_balance_mappings(self) -> List[str]:
        """Find ALL mappings that look like balances"""
        mappings = []
        # Pattern: mapping(address => uint...) name;
        pattern = r'mapping\s*\(\s*address\s*=>\s*u?int\d*\s*\)\s*(?:public|private|internal)?\s+(\w+)'
        matches = re.finditer(pattern, self.source_code)
        for match in matches:
            name = match.group(1)
            # Filter out non-balance looking names if needed, or keep all for "Exhaustive" approach
            mappings.append(name)
        
        if not mappings:
            print("[WARN] No mappings found. Using default 'balances'.")
            return ['balances']
        
        print(f"[INFO] Detected {len(mappings)} potential balance mappings: {mappings}")
        return mappings
    
    def _detect_all_uint_vars(self) -> List[str]:
        """Find ALL uint variables (candidates for total supply/deposits)"""
        uints = []
        # Pattern: uint256 name;
        pattern = r'uint(?:256)?\s+(?:public|private|internal)?\s+(\w+)\s*;'
        matches = re.finditer(pattern, self.source_code)
        
        # Helper to blacklist constants or irrelevant vars
        blacklist = ['deadline', 'start', 'end', 'period', 'version']
        
        for match in matches:
            name = match.group(1)
            if not any(b in name.lower() for b in blacklist):
                uints.append(name)
        
        # Prioritize 'total' vars, but keep others for SolidiFI exhaustiveness
        if not uints:
            print("[WARN] No uint variables found. Using default 'totalDeposits'.")
            return ['totalDeposits']
            
        print(f"[INFO] Detected {len(uints)} state variables: {uints}")
        return uints

    def _get_bug_variants(self, target_mapping: str, target_total: str) -> List[Dict]:
        """Generate bug variants for a SPECIFIC mapping/total pair"""
        variants = []
        
        # NOTE: Using simplified variants without 'total -= amount' to trigger Oracle Failure (Accounting Bug)
        
        # Variant 1: Classic
        variants.append({
            'name': 'classic_call',
            'code': f'''
    // [SolidiFI] Injected Bug: Classic Reentrancy on {{ {target_mapping} }}
    function withdraw_vulnerable_{target_mapping}(uint256 _amount) public {{
        require({target_mapping}[msg.sender] >= _amount, "Insufficient balance");
        (bool success, ) = msg.sender.call{{value: _amount}}("");
        require(success, "Transfer failed");
        {target_mapping}[msg.sender] -= _amount;
        // BUG: {target_total} NOT updated -> Oracle Violation
    }}
    
    function echidna_detect_{target_mapping}_classic() public view returns (bool) {{
        return address(this).balance >= {target_total};
    }}
'''
        })
        
        # Variant 2: Send
        variants.append({
            'name': 'send',
            'constructor': '    constructor() payable {} \n    receive() external payable {}',
            'code': f'''
    // [SolidiFI] Injected Bug: Send Reentrancy on {{ {target_mapping} }}
    function withdraw_send_{target_mapping}(uint256 _amount) public {{
        require({target_mapping}[msg.sender] >= _amount, "Insufficient balance");
        bool success = payable(msg.sender).send(_amount);
        require(success, "Send failed");
        {target_mapping}[msg.sender] -= _amount;
    }}
    
    function echidna_detect_{target_mapping}_send() public view returns (bool) {{
        return address(this).balance >= {target_total};
    }}
'''
        })
        
        # Variant 3: Transfer
        variants.append({
            'name': 'transfer',
            'constructor': '    constructor() payable {} \n    receive() external payable {}',
            'code': f'''
    // [SolidiFI] Injected Bug: Transfer Reentrancy on {{ {target_mapping} }}
    function withdraw_transfer_{target_mapping}() public {{
        uint256 amount = {target_mapping}[msg.sender];
        require(amount > 0, "No balance");
        payable(msg.sender).transfer(amount);
        {target_mapping}[msg.sender] = 0;
    }}
    
    function echidna_detect_{target_mapping}_transfer() public view returns (bool) {{
        return address(this).balance >= {target_total};
    }}
'''
        })

        # Variant 4: DelegateCall
        variants.append({
            'name': 'delegatecall',
            'constructor': '    constructor() payable {} \n    receive() external payable {}',
            'code': f'''
    // [SolidiFI] Injected Bug: DelegateCall on {{ {target_mapping} }}
    address public externalContract_{target_mapping};
    function setExternal_{target_mapping}(address _contract) public {{ externalContract_{target_mapping} = _contract; }}
    
    function withdraw_delegate_{target_mapping}(uint256 _amount) public {{
        require({target_mapping}[msg.sender] >= _amount);
        (bool success,) = msg.sender.call{{value: _amount}}("");
        require(success);
        {target_mapping}[msg.sender] -= _amount;
    }}

    function echidna_detect_{target_mapping}_delegate() public view returns (bool) {{
        return address(this).balance >= {target_total};
    }}
'''
        })
        
        return variants
    
    def _find_contract_end_from_lines(self, lines: List[str]) -> int:
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip().startswith('}'): return i
        return len(lines) - 1

    def _find_or_create_constructor(self, lines: list) -> tuple:
        for i, line in enumerate(lines):
            if 'constructor' in line: return (True, i)
        for i, line in enumerate(lines):
            if 'contract ' in line: return (False, i + 1)
        return (False, 0)
    
    def inject_all(self) -> List[str]:
        os.makedirs(self.output_dir, exist_ok=True)
        output_files = []
        
        # [SOLIDIFI CORE] Loop through ALL combinations of Mapping + Uint
        # This creates the "Exhaustive" nature of SolidiFI
        for mapping_var in self.balance_mappings:
            
            # Smart Selection: Find the uint most likely associated with this mapping
            # (Simplification: Just pick 'totalDeposits' if it exists, or the first one)
            # Ideally SolidiFI uses Data Flow Analysis, we use Heuristic Matching
            target_uint = 'totalDeposits' if 'totalDeposits' in self.total_deposit_vars else self.total_deposit_vars[0]
            
            bug_variants = self._get_bug_variants(mapping_var, target_uint)
            
            for i, variant in enumerate(bug_variants):
                try:
                    lines = self.source_code.split('\n')
                    
                    if 'constructor' in variant:
                        has_cons, pos = self._find_or_create_constructor(lines)
                        if not has_cons: lines.insert(pos, variant['constructor'])
                    
                    inject_pos = self._find_contract_end_from_lines(lines)
                    lines.insert(inject_pos, variant['code'])
                    
                    injected_code = '\n'.join(lines)
                    
                    # Naming convention: Contract_MappingName_BugType
                    file_suffix = f"{mapping_var}_{variant['name']}"
                    new_contract_name = f"{self.main_contract_name}_Inj_{file_suffix}"
                    injected_code = re.sub(
                        r'contract\s+' + re.escape(self.main_contract_name) + r'\b',
                        f'contract {new_contract_name}',
                        injected_code, count=1
                    )
                    
                    fname = f"{self.contract_name}_{file_suffix}.sol"
                    fpath = os.path.join(self.output_dir, fname)
                    
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(injected_code)
                    
                    output_files.append(fpath)
                    self.injection_log.append({'file': fname, 'target': mapping_var, 'bug': variant['name']})
                    print(f"  ✓ Generated: {fname}")
                    
                except Exception as e:
                    print(f"[ERROR] Failed {variant['name']}: {e}")
        
        self._save_log()
        return output_files
    
    def _save_log(self):
        log_path = os.path.join(self.output_dir, f"{self.contract_name}_injection_log.json")
        with open(log_path, 'w') as f: json.dump(self.injection_log, f, indent=2)

def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 bug-injector.py <contract.sol> [output_dir]")
        sys.exit(1)
    
    injector = ReentrancyInjector(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "injected-contracts")
    injector.inject_all()

if __name__ == "__main__":
    main()