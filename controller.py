import os
import glob
import csv
import shutil
# Import modul buatan sendiri
from modules import performance, inspection
from modules.bug_injector import BugInjector 

# KONFIGURASI PATH
INPUT_DIR = "ready-contracts"
OUTPUT_DIR = "injected-contracts"
BUG_FILE = "bugs/reentrancy.txt"
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "injection_report.csv")

def prepare_environment():
    # Setup Direktori
    for d in [OUTPUT_DIR, LOG_DIR]:
        if not os.path.exists(d): os.makedirs(d)
        
    # Bersihkan output lama (Opsional, agar bersih)
    # shutil.rmtree(OUTPUT_DIR) 
    # os.makedirs(OUTPUT_DIR)

def main():
    prepare_environment()
    
    # 1. Baca Template Bug
    try:
        with open(BUG_FILE, 'r') as f:
            BUG_CONTENT = f.read()
    except FileNotFoundError:
        print(f"[ERROR] Template bug tidak ditemukan di {BUG_FILE}")
        exit()

    # 2. Ambil File Kontrak
    files = glob.glob(os.path.join(INPUT_DIR, "*.sol"))
    print(f"[*] Framework Injeksi Dimulai. Target: {len(files)} kontrak.\n")

    # 3. Eksekusi Loop & Reporting
    with open(LOG_FILE, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['File Name', 'Injection Status', 'Time Taken (s)', 'Inspection Result'])

        total_success = 0
        
        for f in files:
            # Init Timer
            timer = performance.Timer()
            timer.start()
            
            # --- PANGGIL MODUL INJECTOR ---
            # Kita lempar tanggung jawab teknis ke modul lain
            injector = BugInjector(f, BUG_CONTENT)
            
            # Kita minta dia menyimpan ke folder yang ditentukan di Config controller
            # (Perlu sedikit penyesuaian di class injector agar terima param output_dir, 
            # atau biarkan default jika sudah diset di class)
            result_path = injector.run() 
            # ------------------------------
            
            # Stop Timer
            duration = timer.stop()
            
            # Inspection (Quality Control)
            if result_path and os.path.exists(result_path):
                valid, message = inspection.inspect_file(result_path)
                status = "SUCCESS" if valid else "CORRUPTED"
                if valid: total_success += 1
            else:
                status = "FAILED"
                message = "AST/IO Error"
                result_path = "N/A"

            # Log ke CSV & Layar
            writer.writerow([os.path.basename(f), status, duration, message])
            print(f"[{status}] {os.path.basename(f)} | Time: {duration}s | Check: {message}")

    print(f"\n[DONE] Selesai. {total_success}/{len(files)} Sukses.")
    print(f"[INFO] Laporan tersimpan di {LOG_FILE}")

if __name__ == "__main__":
    main()