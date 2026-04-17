#!/usr/bin/env bash
#
# This script regenerates the reference headers for the post processor code generation checks.
# It iterates over operators listed in tests/test_operators.txt, calculates their hash,
# and updates (or creates) the corresponding reference file in src/cse/operator/
# using deterministic code generation.

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
OLB_ROOT="$( cd "$SCRIPT_DIR/../../.." >/dev/null 2>&1 && pwd )"
TEST_FILE="$SCRIPT_DIR/tests/test_operators.txt"
REF_DIR="$OLB_ROOT/src/cse/operator"

if [ ! -f "$TEST_FILE" ]; then
    echo "Error: Test definition file not found: $TEST_FILE"
    exit 1
fi

echo "Updating Operator Code Generation References..."

FAILED=0
COUNT=0

mapfile -t OPERATOR_LIST < "$TEST_FILE"

for OPERATOR_LINE in "${OPERATOR_LIST[@]}"; do
    if [ -z "$OPERATOR_LINE" ]; then
        continue
    fi

    ((++COUNT))

    # Split into Operator and Descriptor
    OPERATOR_STR=$(echo "$OPERATOR_LINE" | cut -d';' -f1)
    DESCRIPTOR_STR=$(echo "$OPERATOR_LINE" | cut -d';' -f2)

    # Compute hash to find reference file
    COMBINED_RAW="$OPERATOR_STR;$DESCRIPTOR_STR"

    OPERATOR_FORMATTED=$(python3 "$SCRIPT_DIR/source/format_common.py" "$COMBINED_RAW")
    HASH=$(echo -n "$OPERATOR_FORMATTED" | sha256sum | awk '{print $1}')

    REF_FILE="$REF_DIR/$HASH.cse.h"

    echo "[$COUNT] Updating $HASH..."

    # Generate code to a temporary file first
    TEMP_FILE=$(mktemp)
    if ! "$SCRIPT_DIR/optimize_post_processors.sh" --deterministic "$OPERATOR_STR" "$DESCRIPTOR_STR" < /dev/null > "$TEMP_FILE" 2>/dev/null; then
        echo "  [FAIL] Generation failed for $OPERATOR_STR"
        rm "$TEMP_FILE"
        FAILED=1
        continue
    fi

    # Move temporary file to reference path
    mv "$TEMP_FILE" "$REF_FILE"
done

if [ $FAILED -eq 0 ]; then
    echo "Successfully updated $COUNT reference headers."
    exit 0
else
    echo "Failed to update some reference headers."
    exit 1
fi
