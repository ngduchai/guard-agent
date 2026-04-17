#!/usr/bin/env bash
#
# This script generates CSE optimized code for a specific post processor operator.
#
# Usage: ./optimize_post_processors.sh [--deterministic] [--install] [--skip-header-update] "Operator<...>" "Descriptor<...>"
#
# The script outputs the generated header content to stdout, unless --install is specified.

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
OLB_ROOT="$( cd "$SCRIPT_DIR/../../.." >/dev/null 2>&1 && pwd )"

# Parse arguments
DETERMINISTIC_FLAG=""
INSTALL_FLAG=0
SKIP_HEADER_UPDATE=0
OPERATOR_RAW=""
DESCRIPTOR_RAW=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --deterministic)
      DETERMINISTIC_FLAG="--deterministic"
      shift
      ;;
    --install)
      INSTALL_FLAG=1
      shift
      ;;
    --skip-header-update)
      SKIP_HEADER_UPDATE=1
      shift
      ;;
    *)
      if [ -z "$OPERATOR_RAW" ]; then
          OPERATOR_RAW="$1"
      elif [ -z "$DESCRIPTOR_RAW" ]; then
          DESCRIPTOR_RAW="$1"
      else
          echo "Error: Too many arguments." >&2
          echo "Usage: $0 [--deterministic] [--install] [--skip-header-update] \"Operator<...>\" \"Descriptor<...>\"" >&2
          exit 1
      fi
      shift
      ;;
  esac
done

if [ -z "$OPERATOR_RAW" ] || [ -z "$DESCRIPTOR_RAW" ]; then
    echo "Usage: $0 [--deterministic] [--install] [--skip-header-update] \"Operator<...>\" \"Descriptor<...>\"" >&2
    exit 1
fi

# Combine
COMBINED_RAW="$OPERATOR_RAW;$DESCRIPTOR_RAW"

# Preprocessing
OPERATOR_FORMATTED=$(python3 "$SCRIPT_DIR/source/format_common.py" "$COMBINED_RAW")

if [ -z "$OPERATOR_FORMATTED" ]; then
    echo "Error: Failed to format operator string." >&2
    exit 1
fi

# Compute hash for unique identification
OPERATOR_HASH=$(echo -n "$OPERATOR_FORMATTED" | sha256sum | awk '{print $1}')

# Setup temporary workspace
WORK_DIR=$(mktemp -d -t cse_optimize_operator.XXXXXX)

# Cleanup function
cleanup() {
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

# Extraction
cat <<EOF > "$WORK_DIR/Makefile"
EXAMPLE = $OPERATOR_HASH
OLB_ROOT := $OLB_ROOT
include \$(OLB_ROOT)/default.mk
EOF

# Create a dummy input file to satisfy extraction.py
touch "$WORK_DIR/$OPERATOR_HASH.txt"

# Run extraction.py
python3 "$SCRIPT_DIR/source/extraction.py" \
    "$OPERATOR_FORMATTED" \
    "$SCRIPT_DIR/source/templates/operator/extract.cpp.template" \
    "$WORK_DIR/$OPERATOR_HASH.txt" \
    "$WORK_DIR/" \
    "$WORK_DIR/" \
    "operator" >&2

if [ ! -f "$WORK_DIR/$OPERATOR_HASH.out" ]; then
    echo "Error: Extraction failed, .out file not found." >&2
    exit 1
fi

# Optimization
# Run optimize.py
python3 "$SCRIPT_DIR/source/optimize.py" \
    "$WORK_DIR/$OPERATOR_HASH.out" \
    "$SCRIPT_DIR/source/templates/operator/operator.cse.template" \
    "$WORK_DIR/$OPERATOR_HASH.cse.h" \
    $DETERMINISTIC_FLAG >&2

if [ ! -f "$WORK_DIR/$OPERATOR_HASH.cse.h" ]; then
    echo "Error: Optimization failed, .cse.h file not found." >&2
    exit 1
fi

# Append Generation Info
if git rev-parse --git-dir > /dev/null 2>&1; then
    COMMIT_HASH=$(git rev-parse HEAD)
    echo "" >> "$WORK_DIR/$OPERATOR_HASH.cse.h"
    echo "// Generation Info: commit=$COMMIT_HASH" >> "$WORK_DIR/$OPERATOR_HASH.cse.h"
fi

# Output or Install
if [ "$INSTALL_FLAG" -eq 1 ]; then
    TARGET_DIR="$OLB_ROOT/src/cse/operator"
    TARGET_FILE="$TARGET_DIR/$OPERATOR_HASH.cse.h"
    HEADER_FILE="$TARGET_DIR/generated_cse.h"

    # Ensure target directory exists
    mkdir -p "$TARGET_DIR"

    # Install file
    cp "$WORK_DIR/$OPERATOR_HASH.cse.h" "$TARGET_FILE"
    echo "Installed generated code to $TARGET_FILE" >&2

    if [ "$SKIP_HEADER_UPDATE" -eq 0 ]; then
        # Check if header includes this file
        if ! grep -q "$OPERATOR_HASH.cse.h" "$HEADER_FILE"; then
            echo "Adding include to $HEADER_FILE" >&2
            echo "" >> "$HEADER_FILE"
            echo "//$OPERATOR_FORMATTED" >> "$HEADER_FILE"
            echo "#include \"$OPERATOR_HASH.cse.h\"" >> "$HEADER_FILE"
        else
            echo "Header already includes $OPERATOR_HASH.cse.h" >&2
        fi
    fi
else
    cat "$WORK_DIR/$OPERATOR_HASH.cse.h"
fi
