import os
import re
import json
import subprocess

class BugInjector:
    def __init__(self, file_path, bug_content):
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.bug_template = bug_content
        self.source_code = ""
        self.ast_json = None
        self.mapping_name = "balances"
        self.contract_name = ""

    def run(self):
        # 1. Baca Source Code
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.source_code = f.read()
        except Exception as e:
            return None # Gagal baca file

        # 2. Deteksi Mapping
        self.detect_mapping()

        # 3. Generate AST
        if not self.generate_ast(): return None

        # 4. Cari Posisi
        pos = self.find_injection_point()
        if pos == -1: return None

        # 5. Injeksi & Simpan
        return self.inject_and_save(pos)

    def detect_mapping(self):
        pattern = r"mapping\s*\(\s*address\s*=>\s*u?int\d*\s*\)\s*(?:public|private|internal)?\s+(\w+)\s*;"
        match = re.search(pattern, self.source_code)
        if match: self.mapping_name = match.group(1)

    def generate_ast(self):
        try:
            result = subprocess.run(
                ['solc', '--ast-compact-json', self.file_path],
                capture_output=True, text=True, check=True
            )
            output_str = result.stdout
            json_start = output_str.find('{')
            if json_start == -1: return False
            self.ast_json = json.loads(output_str[json_start:])
            return True
        except: return False

    def find_injection_point(self):
        if not self.ast_json: return -1
        for node in self.ast_json.get('nodes', []):
            if node.get('nodeType') == 'ContractDefinition':
                self.contract_name = node.get('name')
                src = node.get('src', "")
                parts = src.split(':')
                return int(parts[0]) + int(parts[1]) - 1
        return -1

    def inject_and_save(self, pos, output_dir="injected-contracts"):
        # Pastikan direktori output ada (Handling di level injector untuk keamanan)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        custom_bug = self.bug_template.replace("{MAPPING_NAME}", self.mapping_name)
        
        # Rakit Code
        final_code = self.source_code[:pos] + "\n" + custom_bug + "\n" + self.source_code[pos:]
        
        # Rename Contract
        if self.contract_name:
            new_name = self.contract_name + "_Injected"
            final_code = re.sub(r"contract\s+" + re.escape(self.contract_name), f"contract {new_name}", final_code, count=1)

        # Simpan
        new_filename = self.file_name.replace(".sol", "_Injected.sol")
        out_path = os.path.join(output_dir, new_filename)
        
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(final_code)
        
        return out_path