#!/usr/bin/env bash
# This script checks the code generation for a set of test operators.

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
OLB_ROOT="$( cd "$SCRIPT_DIR/../../.." >/dev/null 2>&1 && pwd )"
TEST_FILE="$SCRIPT_DIR/tests/test_operators.txt"
# Reference directory is src/cse/operator
REF_DIR="$OLB_ROOT/src/cse/operator"

if [ ! -f "$TEST_FILE" ]; then
    echo "Error: Test definition file not found: $TEST_FILE"
    exit 1
fi

echo "Running Operator Code Generation Checks..."

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

    echo "[$COUNT] Checking $HASH..."
    echo "  Target: $OPERATOR_STR with $DESCRIPTOR_STR"

    # Check if reference exists
    REF_FILE="$REF_DIR/$HASH.cse.h"
    if [ ! -f "$REF_FILE" ]; then
        echo "  [FAIL] Reference file missing for hash $HASH"
        FAILED=1
        continue
    fi

    # Generate code
    GEN_FILE=$(mktemp)
    if ! "$SCRIPT_DIR/optimize_post_processors.sh" --deterministic "$OPERATOR_STR" "$DESCRIPTOR_STR" < /dev/null > "$GEN_FILE" 2>/dev/null; then
        echo "  [FAIL] Generation failed for $OPERATOR_STR"
        rm "$GEN_FILE"
        FAILED=1
        continue
    fi

    # Compare
    if diff -q -I "^// Generation Info:" "$REF_FILE" "$GEN_FILE" >/dev/null; then
        echo "  [PASS]"
    else
        echo "  [FAIL] Output differs from reference"
        echo "  Diff:"
        diff -I "^// Generation Info:" "$REF_FILE" "$GEN_FILE" | head -n 10
        FAILED=1
    fi

    rm "$GEN_FILE"
done

if [ $FAILED -eq 0 ]; then
    echo "All $COUNT tests PASSED."
    exit 0
else
    echo "Some tests FAILED."
    exit 1
fi
