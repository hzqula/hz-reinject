#!/bin/bash

# KONFIGURASI
INJECT_DIR="injected-contracts"
RESULT_FILE="results.csv"
TIMEOUT=120  # Waktu maksimum per kontrak (detik). 120 = 2 menit.

# Buat Header CSV
echo "Contract File,Status,Time Taken" > $RESULT_FILE

echo "[*] Memulai Eksperimen Massal Echidna..."
echo "[*] Hasil akan disimpan di $RESULT_FILE"

# Loop semua file .sol di folder injeksi
for file in $INJECT_DIR/*.sol; do
    [ -e "$file" ] || continue
    
    # Ambil nama file dan nama kontrak
    filename=$(basename "$file")
    contract_name=$(grep -oP "contract \K\w+" "$file" | head -1)

    echo "---------------------------------------------------"
    echo "[*] Testing: $contract_name ($filename)"
    
    # Jalankan Echidna dengan timeout
    # Kita cari kata "failed" di output untuk menentukan status
    start_time=$(date +%s)
    
    output=$(timeout $TIMEOUT echidna "$file" --contract "$contract_name" 2>&1)
    exit_code=$?
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))

    # Analisis Hasil
    if echo "$output" | grep -q "echidna_test_solvency: failed"; then
        echo "    -> RESULT: DETECTED (FAIL) 💥"
        status="DETECTED"
    elif echo "$output" | grep -q "echidna_test_solvency: passing"; then
        echo "    -> RESULT: UNDETECTED (PASS) ❌"
        status="UNDETECTED"
    else
        echo "    -> RESULT: ERROR / TIMEOUT ⚠️"
        status="ERROR"
    fi

    # Simpan ke CSV
    echo "$filename,$status,$duration" >> $RESULT_FILE
done

echo "---------------------------------------------------"
echo "[*] Eksperimen Selesai. Cek file $RESULT_FILE"