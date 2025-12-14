#!/usr/bin/env python3
"""
Contract Verification Script
Verifies that all injected contracts can be compiled
"""

import os
import subprocess
from pathlib import Path
from typing import List, Tuple

def verify_contract(contract_path: str) -> Tuple[bool, str]:
    """
    Verify single contract can be compiled
    Returns (success, error_message)
    """
    try:
        result = subprocess.run(
            ['solc', '--bin', contract_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return True, "OK"
        else:
            # Extract error message
            error = result.stderr
            # Get first error line for brevity
            first_error = error.split('\n')[0] if error else "Unknown error"
            return False, first_error
            
    except subprocess.TimeoutExpired:
        return False, "Compilation timeout"
    except Exception as e:
        return False, str(e)

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 verify_contracts.py <contracts_dir>")
        sys.exit(1)
    
    contracts_dir = sys.argv[1]
    
    if not os.path.exists(contracts_dir):
        print(f"[ERROR] Directory not found: {contracts_dir}")
        sys.exit(1)
    
    print("=" * 60)
    print("Contract Verification")
    print("=" * 60)
    
    sol_files = sorted(Path(contracts_dir).glob("*.sol"))
    
    if not sol_files:
        print(f"[ERROR] No .sol files found in {contracts_dir}")
        sys.exit(1)
    
    print(f"[INFO] Found {len(sol_files)} contracts to verify\n")
    
    success_count = 0
    failed_contracts = []
    
    for i, sol_file in enumerate(sol_files, 1):
        contract_name = sol_file.name
        print(f"[{i}/{len(sol_files)}] Verifying {contract_name}...", end=' ')
        
        success, message = verify_contract(str(sol_file))
        
        if success:
            print("✓ OK")
            success_count += 1
        else:
            print(f"✗ FAILED")
            failed_contracts.append((contract_name, message))
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"Total contracts:     {len(sol_files)}")
    print(f"✓ Successful:        {success_count}")
    print(f"✗ Failed:            {len(failed_contracts)}")
    print(f"Success rate:        {success_count/len(sol_files)*100:.1f}%")
    
    # Show failed contracts
    if failed_contracts:
        print("\n" + "=" * 60)
        print("FAILED CONTRACTS")
        print("=" * 60)
        
        # Group by error type
        errors_by_type = {}
        for name, error in failed_contracts:
            error_key = error[:80]  # First 80 chars as key
            if error_key not in errors_by_type:
                errors_by_type[error_key] = []
            errors_by_type[error_key].append(name)
        
        for error_msg, contracts in errors_by_type.items():
            print(f"\nError: {error_msg}")
            print(f"Affected contracts ({len(contracts)}):")
            for contract in contracts[:5]:  # Show first 5
                print(f"  - {contract}")
            if len(contracts) > 5:
                print(f"  ... and {len(contracts) - 5} more")
    
    print("\n" + "=" * 60)
    
    # Exit code
    sys.exit(0 if len(failed_contracts) == 0 else 1)

if __name__ == "__main__":
    main()