#!/bin/bash

# Regenerate Injected Contracts Script
# Cleans old injections and creates new ones with fixed templates

set -e  # Exit on error

echo "============================================================"
echo "Regenerating Injected Contracts"
echo "============================================================"

# Configuration
READY_CONTRACTS_DIR="ready-contracts"
INJECTED_DIR="injected-contracts"
ECHIDNA_RESULTS_DIR="echidna-results"
INJECTOR_SCRIPT="fixed_reentrancy_injector.py"

# Step 1: Clean old artifacts
echo ""
echo "[1/4] Cleaning old artifacts..."
rm -rf "$INJECTED_DIR"
rm -rf "$ECHIDNA_RESULTS_DIR"
rm -rf crytic-export
echo "  ✓ Cleaned"

# Step 2: Create directories
echo ""
echo "[2/4] Creating directories..."
mkdir -p "$INJECTED_DIR"
mkdir -p "$ECHIDNA_RESULTS_DIR"
echo "  ✓ Directories created"

# Step 3: Inject bugs
echo ""
echo "[3/4] Injecting bugs into contracts..."

for contract in "$READY_CONTRACTS_DIR"/*.sol; do
    if [ -f "$contract" ]; then
        contract_name=$(basename "$contract")
        echo ""
        echo "  Processing: $contract_name"
        
        python3 "$INJECTOR_SCRIPT" "$contract" "$INJECTED_DIR"
        
        if [ $? -eq 0 ]; then
            echo "    ✓ Injected successfully"
        else
            echo "    ✗ Failed to inject"
        fi
    fi
done

echo ""
echo "  ✓ All injections completed"

# Step 4: Count results
echo ""
echo "[4/4] Summary..."
num_injected=$(find "$INJECTED_DIR" -name "*.sol" | wc -l)
echo "  Total injected contracts: $num_injected"

# Check if any contract was generated
if [ "$num_injected" -eq 0 ]; then
    echo ""
    echo "  ⚠ WARNING: No contracts were generated!"
    echo "  Please check if contracts exist in: $READY_CONTRACTS_DIR"
    exit 1
fi

echo ""
echo "============================================================"
echo "✓ Regeneration Complete!"
echo "============================================================"
echo ""
echo "Next steps:"
echo "  1. Verify contracts: ls -la $INJECTED_DIR"
echo "  2. Test compilation: solc --version && solc $INJECTED_DIR/*.sol"
echo "  3. Run Echidna: python3 run_echidna_tests.py $INJECTED_DIR"
echo ""