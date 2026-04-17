#!/usr/bin/env bash
#
# Checks if all generated CSE files are included in the generated header,
# and if all included files exist.

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
OLB_ROOT="$( cd "$SCRIPT_DIR/../../.." >/dev/null 2>&1 && pwd )"

check_directory() {
    local DIR_NAME="$1"
    local CSE_DIR="$OLB_ROOT/src/cse/$DIR_NAME"
    local HEADER_FILE="$CSE_DIR/generated_cse.h"

    echo "Checking $DIR_NAME..."

    if [ ! -d "$CSE_DIR" ]; then
        echo "Error: Directory $CSE_DIR does not exist."
        return 1
    fi

    if [ ! -f "$HEADER_FILE" ]; then
        echo "Error: Header file $HEADER_FILE does not exist."
        return 1
    fi

    local FAILED=0

    # 1. Check if all .cse.h files in directory are included in header
    # Exclude generated_cse.h
    # Use array to handle empty result
    mapfile -t FILES < <(find "$CSE_DIR" -maxdepth 1 -name "*.cse.h" | grep -v "generated_cse.h" | sort)

    for FILE in "${FILES[@]}"; do
        if [ -z "$FILE" ]; then continue; fi
        BASENAME=$(basename "$FILE")
        if ! grep -q "$BASENAME" "$HEADER_FILE"; then
            echo "  [FAIL] $BASENAME exists but is NOT included in generated_cse.h"
            FAILED=1
        fi
    done

    # 2. Check if all includes in header exist
    # Only check active includes starting with #
    mapfile -t INCLUDES < <(grep "^#include" "$HEADER_FILE" | cut -d'"' -f2)

    for INC in "${INCLUDES[@]}"; do
        if [ -z "$INC" ]; then continue; fi
        if [ ! -f "$CSE_DIR/$INC" ]; then
            echo "  [FAIL] Header includes $INC but file does NOT exist."
            FAILED=1
        fi
    done

    if [ "$FAILED" -eq 1 ]; then
        echo "  Checks FAILED for $DIR_NAME"
        return 1
    else
        echo "  Checks PASSED for $DIR_NAME"
        return 0
    fi
}

FAILED_GLOBAL=0

check_directory "dynamics" || FAILED_GLOBAL=1
check_directory "operator" || FAILED_GLOBAL=1

if [ "$FAILED_GLOBAL" -eq 1 ]; then
    echo "Overall Verification FAILED."
    exit 1
else
    echo "Overall Verification PASSED."
    exit 0
fi
