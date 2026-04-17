#!/usr/bin/env bash
#
# This script generates CSE optimized code for a specific dynamics class.
#
# Usage: ./optimize_dynamics.sh [--deterministic] [--install] [--skip-header-update] "dynamics::Tuple<...>"
#
# The script outputs the generated header content to stdout, unless --install is specified.

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
OLB_ROOT="$( cd "$SCRIPT_DIR/../../.." >/dev/null 2>&1 && pwd )"

# Parse arguments
DETERMINISTIC_FLAG=""
INSTALL_FLAG=0
SKIP_HEADER_UPDATE=0
DYNAMICS_RAW=""

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
      DYNAMICS_RAW="$1"
      shift
      ;;
  esac
done

if [ -z "$DYNAMICS_RAW" ]; then
    echo "Usage: $0 [--deterministic] [--install] [--skip-header-update] \"dynamics::Tuple<...>\"" >&2
    exit 1
fi

# Preprocessing
DYNAMICS_FORMATTED=$(python3 "$SCRIPT_DIR/source/format_common.py" "$DYNAMICS_RAW")

if [ -z "$DYNAMICS_FORMATTED" ]; then
    echo "Error: Failed to format dynamics string." >&2
    exit 1
fi

# Compute hash for unique identification
DYNAMICS_HASH=$(echo -n "$DYNAMICS_FORMATTED" | sha256sum | awk '{print $1}')

# Setup temporary workspace
WORK_DIR=$(mktemp -d -t cse_optimize_dynamics.XXXXXX)

# Cleanup function
cleanup() {
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

# Extraction
cat <<EOF > "$WORK_DIR/Makefile"
EXAMPLE = $DYNAMICS_HASH
OLB_ROOT := $OLB_ROOT
include \$(OLB_ROOT)/default.mk
EOF

# Create a dummy input file to satisfy extraction.py
touch "$WORK_DIR/$DYNAMICS_HASH.txt"

# Run extraction.py
python3 "$SCRIPT_DIR/source/extraction.py" \
    "$DYNAMICS_FORMATTED" \
    "$SCRIPT_DIR/source/templates/dynamics/extract.cpp.template" \
    "$WORK_DIR/$DYNAMICS_HASH.txt" \
    "$WORK_DIR/" \
    "$WORK_DIR/" \
    "dynamics" >&2

if [ ! -f "$WORK_DIR/$DYNAMICS_HASH.out" ]; then
    echo "Error: Extraction failed, .out file not found." >&2
    exit 1
fi

# Optimization
# Run optimize.py
python3 "$SCRIPT_DIR/source/optimize.py" \
    "$WORK_DIR/$DYNAMICS_HASH.out" \
    "$SCRIPT_DIR/source/templates/dynamics/dynamics.cse.template" \
    "$WORK_DIR/$DYNAMICS_HASH.cse.h" \
    $DETERMINISTIC_FLAG >&2

if [ ! -f "$WORK_DIR/$DYNAMICS_HASH.cse.h" ]; then
    echo "Error: Optimization failed, .cse.h file not found." >&2
    exit 1
fi

# Append Generation Info
if git rev-parse --git-dir > /dev/null 2>&1; then
    COMMIT_HASH=$(git rev-parse HEAD)
    echo "" >> "$WORK_DIR/$DYNAMICS_HASH.cse.h"
    echo "// Generation Info: commit=$COMMIT_HASH" >> "$WORK_DIR/$DYNAMICS_HASH.cse.h"
fi

# Output or Install
if [ "$INSTALL_FLAG" -eq 1 ]; then
    TARGET_DIR="$OLB_ROOT/src/cse/dynamics"
    TARGET_FILE="$TARGET_DIR/$DYNAMICS_HASH.cse.h"
    HEADER_FILE="$TARGET_DIR/generated_cse.h"

    # Ensure target directory exists
    mkdir -p "$TARGET_DIR"

    # Install file
    cp "$WORK_DIR/$DYNAMICS_HASH.cse.h" "$TARGET_FILE"
    echo "Installed generated code to $TARGET_FILE" >&2

    if [ "$SKIP_HEADER_UPDATE" -eq 0 ]; then
        # Check if header includes this file
        if ! grep -q "$DYNAMICS_HASH.cse.h" "$HEADER_FILE"; then
            echo "Adding include to $HEADER_FILE" >&2
            # Append nicely formatted include
            echo "" >> "$HEADER_FILE"
            echo "//$DYNAMICS_FORMATTED" >> "$HEADER_FILE"
            echo "#include \"$DYNAMICS_HASH.cse.h\"" >> "$HEADER_FILE"
        else
            echo "Header already includes $DYNAMICS_HASH.cse.h" >&2
        fi
    fi
else
    cat "$WORK_DIR/$DYNAMICS_HASH.cse.h"
fi
