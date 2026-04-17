#!/usr/bin/env bash
# This script checks the code generation for a set of test dynamics.

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
OLB_ROOT="$( cd "$SCRIPT_DIR/../../.." >/dev/null 2>&1 && pwd )"
TEST_FILE="$SCRIPT_DIR/tests/test_dynamics.txt"
REF_DIR="$OLB_ROOT/src/cse/dynamics"

if [ ! -f "$TEST_FILE" ]; then
    echo "Error: Test definition file not found: $TEST_FILE"
    exit 1
fi

echo "Running Code Generation Checks..."

FAILED=0
COUNT=0

mapfile -t DYNAMICS_LIST < "$TEST_FILE"

for DYNAMICS in "${DYNAMICS_LIST[@]}"; do
    if [ -z "$DYNAMICS" ]; then
        continue
    fi

    ((++COUNT))

    # 1. Format dynamics to compute hash
    DYNAMICS_FORMATTED=$(python3 "$SCRIPT_DIR/source/format_common.py" "$DYNAMICS")
    HASH=$(echo -n "$DYNAMICS_FORMATTED" | sha256sum | awk '{print $1}')

    echo "[$COUNT] Checking $HASH..."

    # 2. Check if reference exists
    REF_FILE="$REF_DIR/$HASH.cse.h"
    if [ ! -f "$REF_FILE" ]; then
        echo "  [FAIL] Reference file $REF_FILE missing for hash $HASH"
        FAILED=1
        continue
    fi

    # 3. Generate code
    GEN_FILE=$(mktemp)
    if ! "$SCRIPT_DIR/optimize_dynamics.sh" --deterministic "$DYNAMICS" < /dev/null > "$GEN_FILE" 2>/dev/null; then
        echo "  [FAIL] Generation failed for $DYNAMICS"
        rm "$GEN_FILE"
        FAILED=1
        continue
    fi

    # 4. Compare, ignoring the generation info line which contains commit hash
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
