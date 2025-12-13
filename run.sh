#!/bin/bash

# KONFIGURASI
INJECT_DIR="injected-contracts"
RESULT_FILE="results.csv"
LOG_DIR="json-logs"
TIMEOUT=120

# Bersihkan artifact lama agar kompilasi fresh
rm -rf crytic-export
mkdir -p $LOG_DIR

# Buat Header CSV
echo "Contract File,Status,Time Taken" > $RESULT_FILE

echo "[*] Memulai Eksperimen (Mode Hybrid Log)..."

for file in $INJECT_DIR/*.sol; do
    [ -e "$file" ] || continue
    
    filename=$(basename "$file")
    # Ambil nama kontrak (asumsi nama kontrak = nama file tanpa .sol agar lebih aman)
    # Atau gunakan regex contract yang sudah ada
    contract_name=$(grep -oP "contract \K\w+" "$file" | head -1)
    
    # File output kita sebut .json.log karena isinya campuran
    json_output="$LOG_DIR/${filename}.json"

    echo "==================================================="
    echo "[*] Target: $contract_name ($filename)"
    
    start_time=$(date +%s)
    
    # 1. JALANKAN ECHIDNA
    # Gunakan --format json tapi simpan sebagai teks biasa
    timeout $TIMEOUT echidna "$file" --contract "$contract_name" --format json > "$json_output" 2>&1
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))

    # 2. ANALISIS LOG (Pakai script Python baru)
    python3 analyze_logs.py "$json_output"

    # 3. TENTUKAN STATUS UNTUK CSV
    # Kita grep kata kunci 'falsified' yang menandakan failure di Echidna
    if grep -q "falsified" "$json_output"; then
        status="DETECTED"
    else
        status="UNDETECTED"
    fi

    # Simpan ke CSV Rekap
    echo "$filename,$status,$duration" >> $RESULT_FILE
done

echo "==================================================="
echo "[*] Selesai. Cek file $RESULT_FILE"