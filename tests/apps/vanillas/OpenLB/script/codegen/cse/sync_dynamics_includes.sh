#!/usr/bin/env bash
#
# This script updates src/cse/dynamics/generated_cse.h to include all .cse.h files in that directory.
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
OLB_ROOT="$( cd "$SCRIPT_DIR/../../.." >/dev/null 2>&1 && pwd )"

python3 "$SCRIPT_DIR/source/update_cse_includes.py" dynamics "$OLB_ROOT"
