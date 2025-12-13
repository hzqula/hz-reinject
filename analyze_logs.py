import sys
import os
import re
from datetime import datetime

def parse_timestamp(line):
    # Mencari format [YYYY-MM-DD HH:MM:SS.mm]
    match = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\]", line)
    if match:
        return datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S.%f")
    return None

def analyze_hybrid_log(file_path):
    if not os.path.exists(file_path):
        print("   [!] File log tidak ditemukan.")
        return

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"   [!] Gagal membaca file: {e}")
        return

    # Header Tabel
    print(f"\n   {'WAKTU (s)':<10} | {'STATUS (DETEKSI)':<20} | {'LOKASI KODE (AKTIVASI)':<30}")
    print("   " + "-"*75)

    # Variabel State
    start_time = None
    detection_time = None
    bug_activated = False
    status = "UNDETECTED" # Default
    failure_msg = "-"
    trace_loc = "-"
    
    # 1. Analisis Baris per Baris
    for line in lines:
        # A. Ambil Waktu Awal (Baris log pertama yang punya waktu)
        current_time = parse_timestamp(line)
        if current_time and start_time is None:
            start_time = current_time
        
        # B. Cek Deteksi (Falsified)
        if "falsified!" in line:
            status = "DETECTED (FAIL) 💥"
            if current_time:
                detection_time = current_time
        
        # C. Cek Error ABI (Kasus CrowdsaleRefund)
        if "No tests found in ABI" in line:
            status = "ERROR (No Tests) ⚠️"
            failure_msg = "Fungsi tes tidak ditemukan (Cek public/external)"

        # D. Cek Aktivasi (Call Sequence)
        # Echidna mencetak "withdraw_buggy(...)" di dalam Call sequence
        if "withdraw_buggy" in line:
            bug_activated = True
            # Coba ambil argumen atau info tambahan
            trace_loc = "withdraw_buggy() terpanggil"

    # 2. Hitung Durasi Deteksi
    time_taken_str = "-"
    if start_time and detection_time:
        delta = (detection_time - start_time).total_seconds()
        time_taken_str = f"{delta:.2f}"
    elif status == "UNDETECTED" and start_time and current_time:
        # Jika tidak ketemu, ambil durasi total running
        delta = (current_time - start_time).total_seconds()
        time_taken_str = f"{delta:.2f} (Timeout)"

    # 3. Print Hasil dalam Tabel
    print(f"   {time_taken_str:<10} | {status:<20} | {trace_loc:<30}")
    
    if failure_msg != "-":
        print(f"   {'':<10} | -> Info: {failure_msg}")

    print("   " + "-"*75)
    
    # Kesimpulan Akhir
    if bug_activated:
        print("   [ANALISIS] ✅ Bug Teraktivasi (Fungsi `withdraw_buggy` berhasil dipanggil).")
    elif status.startswith("ERROR"):
        print("   [ANALISIS] ⚠️ Pengujian Gagal (Masalah konfigurasi/ABI).")
    else:
        print("   [ANALISIS] ❌ Bug TIDAK Teraktivasi (Fungsi tidak pernah dipanggil/blocked).")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze_hybrid_log(sys.argv[1])