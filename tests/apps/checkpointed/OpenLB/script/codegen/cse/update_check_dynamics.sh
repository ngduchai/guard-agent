#!/usr/bin/env bash
#
# This script regenerates the reference headers for the code generation checks.
# It iterates over dynamics listed in tests/test_dynamics.txt, calculates their hash,
# and updates (or creates) the corresponding reference file in src/cse/dynamics/
# using deterministic code generation.

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
OLB_ROOT="$( cd "$SCRIPT_DIR/../../.." >/dev/null 2>&1 && pwd )"
TEST_FILE="$SCRIPT_DIR/tests/test_dynamics.txt"
REF_DIR="$OLB_ROOT/src/cse/dynamics"

if [ ! -f "$TEST_FILE" ]; then
    echo "Error: Test definition file not found: $TEST_FILE"
    exit 1
fi

echo "Updating Code Generation References..."

FAILED=0
COUNT=0

mapfile -t DYNAMICS_LIST < "$TEST_FILE"

for DYNAMICS in "${DYNAMICS_LIST[@]}"; do
    if [ -z "$DYNAMICS" ]; then
        continue
    fi

    ((++COUNT))

    # 1. Format dynamics to compute hash (Using python script for consistency)
    DYNAMICS_FORMATTED=$(python3 "$SCRIPT_DIR/source/format_common.py" "$DYNAMICS")
    HASH=$(echo -n "$DYNAMICS_FORMATTED" | sha256sum | awk '{print $1}')

    REF_FILE="$REF_DIR/$HASH.cse.h"

    echo "[$COUNT] Updating $HASH..."

    # 2. Generate code to a temporary file first
    TEMP_FILE=$(mktemp)
    if ! "$SCRIPT_DIR/optimize_dynamics.sh" --deterministic "$DYNAMICS" < /dev/null > "$TEMP_FILE" 2>/dev/null; then
        echo "  [FAIL] Generation failed for $DYNAMICS"
        rm "$TEMP_FILE"
        FAILED=1
        continue
    fi

    # 3. Move temporary file to reference path
    mv "$TEMP_FILE" "$REF_FILE"
done

if [ $FAILED -eq 0 ]; then
    echo "Successfully updated $COUNT reference headers."
    exit 0
else
    echo "Failed to update some reference headers."
    exit 1
fi
