#!/usr/bin/env python3
"""
Echidna Test Runner untuk Reentrancy Detection
Automatic testing semua injected contracts
"""

import os
import re
import subprocess
import json
import time
import csv
from pathlib import Path
from typing import List, Dict

class EchidnaRunner:
    def __init__(self, contracts_dir: str, output_dir: str = "echidna-results"):
        self.contracts_dir = contracts_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        self.results = []
    
    def run_echidna(self, contract_path: str, timeout: int = 120) -> Dict:
        """
        Run Echidna on single contract
        """
        contract_name = os.path.basename(contract_path)
        print(f"\n[Testing] {contract_name}")
        
        # Extract contract name from file
        with open(contract_path, 'r') as f:
            content = f.read()
            # Find main contract name
            match = re.search(r'contract\s+(\w+)', content)
            main_contract = match.group(1) if match else contract_name.replace('.sol', '')
        
        result = {
            'file': contract_name,
            'contract': main_contract,
            'status': 'UNKNOWN',
            'detected': False,
            'time': 0,
            'output': ''
        }
        
        start_time = time.time()
        
        try:
            # Run Echidna
            cmd = [
                'echidna',
                contract_path,
                '--contract', main_contract,
                '--format', 'text',  # Changed from json to text for better error visibility
                '--test-mode', 'property',  # Changed to property mode for echidna_ functions
                '--corpus-dir', f'{self.output_dir}/corpus_{main_contract}',
                '--test-limit', '1000000'  # Number of test cases
            ]
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            result['time'] = time.time() - start_time
            result['output'] = process.stdout + process.stderr
            
            # Parse hasil
            if 'falsified' in process.stdout.lower():
                result['status'] = 'DETECTED'
                result['detected'] = True
                print(f"  ✓ DETECTED - Echidna found reentrancy vulnerability!")
            # [FIX] Terima 'passing' atau 'passed' sebagai tanda undetected
            elif 'passed' in process.stdout.lower() or 'passing' in process.stdout.lower():
                result['status'] = 'UNDETECTED'
                print(f"  ✗ UNDETECTED - Bug not found")
            else:
                result['status'] = 'ERROR'
                print(f"  ⚠ ERROR - Check output")
            
            # Save detailed output
            output_file = os.path.join(
                self.output_dir, 
                f"{contract_name}.txt"
            )
            with open(output_file, 'w') as f:
                f.write(result['output'])
            
        except subprocess.TimeoutExpired:
            result['status'] = 'TIMEOUT'
            result['time'] = timeout
            print(f"  ⏱ TIMEOUT after {timeout}s")
        
        except Exception as e:
            result['status'] = 'ERROR'
            result['time'] = time.time() - start_time
            result['output'] = str(e)
            print(f"  ✗ ERROR: {e}")
        
        return result
    
    def run_all(self) -> List[Dict]:
        """
        Run Echidna on all contracts in directory
        """
        sol_files = list(Path(self.contracts_dir).glob("*.sol"))
        
        print(f"[INFO] Found {len(sol_files)} contracts to test")
        print("=" * 60)
        
        for sol_file in sol_files:
            result = self.run_echidna(str(sol_file))
            self.results.append(result)
        
        # Generate summary
        self._generate_summary()
        
        return self.results
    
    def _generate_summary(self):
        """
        Generate summary CSV and statistics
        """
        # Save CSV
        csv_path = os.path.join(self.output_dir, "detection_results.csv")
        
        with open(csv_path, 'w', newline='') as csvfile:
            fieldnames = ['file', 'contract', 'status', 'detected', 'time']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in self.results:
                writer.writerow({k: result[k] for k in fieldnames})
        
        print("\n" + "=" * 60)
        print("DETECTION SUMMARY")
        print("=" * 60)
        
        # Statistics
        total = len(self.results)
        detected = sum(1 for r in self.results if r['detected'])
        undetected = sum(1 for r in self.results if r['status'] == 'UNDETECTED')
        errors = sum(1 for r in self.results if r['status'] == 'ERROR')
        timeouts = sum(1 for r in self.results if r['status'] == 'TIMEOUT')
        
        detection_rate = (detected / total * 100) if total > 0 else 0
        
        print(f"Total Contracts:    {total}")
        print(f"✓ Detected:         {detected} ({detection_rate:.1f}%)")
        print(f"✗ Undetected:       {undetected}")
        print(f"⚠ Errors:           {errors}")
        print(f"⏱ Timeouts:         {timeouts}")
        print(f"\nDetection Rate:     {detection_rate:.2f}%")
        print(f"\nResults saved to:   {csv_path}")
        
        # Save JSON summary
        summary_path = os.path.join(self.output_dir, "summary.json")
        with open(summary_path, 'w') as f:
            json.dump({
                'total_contracts': total,
                'detected': detected,
                'undetected': undetected,
                'errors': errors,
                'timeouts': timeouts,
                'detection_rate': detection_rate,
                'results': self.results
            }, f, indent=2)
        
        print(f"Summary JSON:       {summary_path}")


def main():
    import sys
    import re
    
    if len(sys.argv) < 2:
        print("Usage: python run_echidna_tests.py <injected_contracts_dir>")
        sys.exit(1)
    
    contracts_dir = sys.argv[1]
    
    if not os.path.exists(contracts_dir):
        print(f"[ERROR] Directory not found: {contracts_dir}")
        sys.exit(1)
    
    print("=" * 60)
    print("Echidna Reentrancy Detection Test Suite")
    print("=" * 60)
    
    runner = EchidnaRunner(contracts_dir)
    runner.run_all()


if __name__ == "__main__":
    main()