import os
import re
import glob

# KONFIGURASI
INPUT_DIR = "contracts"
OUTPUT_DIR = "ready-contracts"

# DAFTAR FUNGSI YANG DIABAIKAN (BLACKLIST)
# Fungsi-fungsi ini memanipulasi saldo tapi TIDAK melibatkan uang fisik masuk/keluar
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
            return

        if not self.detect_mapping():
            return

        self.inject_state_var()
        self.inject_logic()
        self.inject_oracle()
        self.save()

    def detect_mapping(self):
        content = "".join(self.lines)
        pattern = r"mapping\s*\(\s*address\s*=>\s*u?int\d*\s*\)\s*(?:public|private|internal)?\s+(\w+)\s*;"
        match = re.search(pattern, content)
        if match:
            self.map_name = match.group(1)
            return True
        return False

    def inject_state_var(self):
        for i, line in enumerate(self.lines):
            # Perbaikan deteksi baris mapping agar lebih robust
            if "mapping" in line and self.map_name in line and ";" in line:
                self.lines.insert(i + 1, "    uint256 public totalDeposits; // [AUTO-INSTRUMENTED]\n")
                break

    def inject_logic(self):
        current_function = None
        new_lines = []
        
        func_pattern = r"function\s+(\w+)\s*\("
        
        # 1. Regex untuk += dan -=
        balance_op_pattern = re.escape(self.map_name) + r"\[(.*?)\]\s*(\+=|-=)\s*([^;]+);"
        
        # 2. Regex untuk = 0 (Reset Pattern)
        balance_reset_pattern = re.escape(self.map_name) + r"\[(.*?)\]\s*=\s*0;"

        for line in self.lines:
            func_match = re.search(func_pattern, line)
            if func_match:
                current_function = func_match.group(1)

            # Cek Blacklist
            is_ignored = False
            if current_function:
                for blacklisted in IGNORE_FUNCTIONS:
                    if blacklisted in current_function.lower():
                        is_ignored = True
                        break

            # Cek Pattern += / -=
            op_match = re.search(balance_op_pattern, line)
            # Cek Pattern = 0
            reset_match = re.search(balance_reset_pattern, line)

            new_lines.append(line)

            if is_ignored:
                continue

            indent = line[:len(line) - len(line.lstrip())]

            if op_match:
                op = op_match.group(2)
                val = op_match.group(3)
                if op == "+=":
                    new_lines.append(f"{indent}totalDeposits += {val};\n")
                elif op == "-=":
                    new_lines.append(f"{indent}totalDeposits -= {val};\n")
            
            elif reset_match:
                # KITA TIDAK BISA OTOMATIS TAHU NILAI 'AMOUNT' YANG DIHAPUS
                # JADI KITA KASIH KOMENTAR TODO AGAR ANDA SADAR
                print(f"    [WARN] Found balance reset (= 0) in '{current_function}'. Manual fix needed!")
                new_lines.append(f"{indent}// [TODO MANUAL] totalDeposits -= AMOUNT_VAR_HERE;\n")

        self.lines = new_lines

    def inject_oracle(self):
        # Cari kurung kurawal penutup terakhir '}'
        # Kita scan dari bawah ke atas
        for i in range(len(self.lines) - 1, -1, -1):
            if "}" in self.lines[i]:
                oracle_code = [
                    "\n",
                    "    // [AUTO-INSTRUMENTED ORACLE]\n",
                    "    function echidna_test_solvency() public view returns (bool) {\n",
                    "        return address(this).balance >= totalDeposits;\n",
                    "    }\n"
                ]
                # Sisipkan SEBELUM kurung tutup terakhir
                for code in reversed(oracle_code):
                    self.lines.insert(i, code)
                break

    def save(self):
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
        save_path = os.path.join(OUTPUT_DIR, self.filename)
        with open(save_path, 'w', encoding='utf-8') as f:
            f.writelines(self.lines)

if __name__ == "__main__":
    if not os.path.exists(INPUT_DIR):
        print(f"[!] Please create '{INPUT_DIR}' and put .sol files there.")
    else:
        files = glob.glob(os.path.join(INPUT_DIR, "*.sol"))
        print(f"[*] Found {len(files)} contracts. Starting smart instrumentation...\n")
        for f in files:
            tool = Instrument(f)
            tool.run()
        print("\n[DONE] Check 'contracts/' folder.")