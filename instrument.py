import os
import re
import glob

# KONFIGURASI
INPUT_DIR = "contracts"
OUTPUT_DIR = "ready-contracts"

# FUNGSI YANG DIABAIKAN
IGNORE_FUNCTIONS = ["mint", "burn", "_mint", "_burn", "transfer", "_transfer", "transferFrom"]

class Instrument:
    def __init__(self, file_path):
        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        self.lines = []
        self.map_name = None

    def run(self):
        print(f"[*] Processing: {self.filename}")
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.lines = f.readlines()
        except Exception as e:
            print(f"    [!] Error reading file: {e}")
            return

        if not self.detect_mapping():
            print("    [-] Mapping not found.")
            return

        self.inject_state_var()
        self.inject_logic()
        self.inject_oracle()
        self.save()

    def detect_mapping(self):
        content = "".join(self.lines)
        # Regex mencari mapping saldo
        pattern = r"mapping\s*\(\s*address\s*=>\s*u?int\d*\s*\)\s*(?:public|private|internal)?\s+(\w+)\s*;"
        match = re.search(pattern, content)
        if match:
            self.map_name = match.group(1)
            print(f"    [INFO] Mapping detected: '{self.map_name}'")
            return True
        return False

    def inject_state_var(self):
        content = "".join(self.lines)
        
        # [ANTI-DUPLIKASI 1] Cek Variable dengan Regex (Tahan spasi/format)
        # Cocok dengan: "uint256 public totalDeposits", "uint totalDeposits", dll.
        if re.search(r"uint(256)?\s+(public\s+)?totalDeposits", content):
            print("    [SKIP] 'totalDeposits' variable already exists.")
            return

        # Injeksi jika belum ada
        for i, line in enumerate(self.lines):
            if "mapping" in line and self.map_name in line and ";" in line:
                self.lines.insert(i + 1, "    uint256 public totalDeposits; // [AUTO-INSTRUMENTED]\n")
                break

    def inject_logic(self):
        new_lines = []
        func_pattern = r"function\s+(\w+)\s*\("
        
        # Regex menangkap operasi saldo: balances[...] += val;
        balance_op_pattern = re.escape(self.map_name) + r"\[(.*?)\]\s*(\+=|-=)\s*([^;]+);"
        balance_reset_pattern = re.escape(self.map_name) + r"\[(.*?)\]\s*=\s*0;"

        i = 0
        current_function = ""
        
        while i < len(self.lines):
            line = self.lines[i]
            
            # Deteksi Nama Fungsi (untuk blacklist)
            func_match = re.search(func_pattern, line)
            if func_match:
                current_function = func_match.group(1)

            new_lines.append(line)

            # Cek Blacklist
            is_ignored = False
            if current_function:
                for blacklisted in IGNORE_FUNCTIONS:
                    if blacklisted in current_function.lower():
                        is_ignored = True
                        break
            
            if is_ignored:
                i += 1
                continue

            op_match = re.search(balance_op_pattern, line)
            reset_match = re.search(balance_reset_pattern, line)
            indent = line[:len(line) - len(line.lstrip())]

            # [KASUS 1] Operator += atau -=
            if op_match:
                op = op_match.group(2)
                val = op_match.group(3)
                
                # [ANTI-DUPLIKASI 2] Cek 3 baris ke depan
                already_present = False
                for k in range(1, 4):
                    if i + k < len(self.lines):
                        next_line = self.lines[i+k]
                        # Jika ada kata 'totalDeposits' dan ada tanda operasi (=, +=, -=)
                        if "totalDeposits" in next_line and ("=" in next_line or "+=" in next_line or "-=" in next_line):
                            already_present = True
                            print(f"    [SKIP] Logic present at line {i+k+1}")
                            break
                
                if not already_present:
                    if op == "+=":
                        new_lines.append(f"{indent}totalDeposits += {val};\n")
                    elif op == "-=":
                        new_lines.append(f"{indent}totalDeposits -= {val};\n")

            # [KASUS 2] Reset = 0
            elif reset_match:
                already_present = False
                for k in range(1, 4):
                    if i + k < len(self.lines):
                        next_line = self.lines[i+k]
                        if "totalDeposits" in next_line: # Cek sekedar keberadaan variabel
                            already_present = True
                            print(f"    [SKIP] Reset logic present at line {i+k+1}")
                            break
                
                if not already_present:
                    print(f"    [WARN] Balance reset (=0) detected in '{current_function}'. Manual fix needed.")
                    new_lines.append(f"{indent}// [TODO MANUAL] totalDeposits -= AMOUNT_VAR_HERE;\n")

            i += 1
        
        self.lines = new_lines

    def inject_oracle(self):
        content = "".join(self.lines)
        
        # [ANTI-DUPLIKASI 3] Cek keberadaan fungsi Oracle
        if "function echidna_test_solvency" in content:
            print("    [SKIP] Oracle function already exists.")
            return

        # Injeksi di akhir kontrak
        for i in range(len(self.lines) - 1, -1, -1):
            if "}" in self.lines[i]:
                oracle_code = [
                    "\n",
                    "    // [AUTO-INSTRUMENTED ORACLE]\n",
                    "    function echidna_test_solvency() public view returns (bool) {\n",
                    "        return address(this).balance >= totalDeposits;\n",
                    "    }\n"
                ]
                for code in reversed(oracle_code):
                    self.lines.insert(i, code)
                break

    def save(self):
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
        save_path = os.path.join(OUTPUT_DIR, self.filename)
        with open(save_path, 'w', encoding='utf-8') as f:
            f.writelines(self.lines)
        print(f"    [SUCCESS] Saved to {save_path}")

if __name__ == "__main__":
    if not os.path.exists(INPUT_DIR):
        os.makedirs(INPUT_DIR)
        print(f"[!] Folder '{INPUT_DIR}' created. Please add contracts.")
    else:
        files = glob.glob(os.path.join(INPUT_DIR, "*.sol"))
        print(f"[*] Found {len(files)} contracts. Starting instrumentation...\n")
        for f in files:
            tool = Instrument(f)
            tool.run()
        print("\n[DONE] Check 'ready-contracts/' folder.")