#!/usr/bin/env bash
#
# This script regenerates all dynamics currently included in src/cse/dynamics/generated_cse.h.
# It reads the included files to extract the exact configuration string from the code.
# It handles hash changes by cleaning up old files and includes.
# It supports parallel execution and OOM protection.
#
# Usage: ./regenerate_dynamics.sh [-j <jobs>] [--max-memory <GB>]

set -e -o pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
OLB_ROOT="$( cd "$SCRIPT_DIR/../../.." >/dev/null 2>&1 && pwd )"
HEADER_FILE="$OLB_ROOT/src/cse/dynamics/generated_cse.h"
DYNAMICS_DIR="$OLB_ROOT/src/cse/dynamics"

JOBS=1
MAX_MEMORY="" # In KB for ulimit, argument will be in GB

while [[ $# -gt 0 ]]; do
  case $1 in
    -j|--jobs)
      JOBS="$2"
      shift 2
      ;;
    --max-memory)
      MAX_MEMORY=$(($2 * 1024 * 1024))
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [ ! -f "$HEADER_FILE" ]; then
    echo "Error: $HEADER_FILE not found." >&2
    exit 1
fi

CURRENT_COMMIT=""
if git rev-parse --git-dir > /dev/null 2>&1; then
    CURRENT_COMMIT=$(git rev-parse HEAD)
fi

echo "Regenerating dynamics from $HEADER_FILE..."
if [ -n "$CURRENT_COMMIT" ]; then
    echo "Current commit: $CURRENT_COMMIT"
fi
echo "Parallel jobs: $JOBS"
if [ -n "$MAX_MEMORY" ]; then
    echo "Memory limit: $((MAX_MEMORY / 1024)) MB"
fi

# Temp dir for job coordination
JOB_DIR=$(mktemp -d -t cse_regen_jobs.XXXXXX)
trap 'rm -rf "$JOB_DIR"' EXIT

# Get list of included files
grep "^#include" "$HEADER_FILE" | grep ".cse.h" | sed 's/#include "//;s/"//' > "$JOB_DIR/file_list.txt"

# Arrays to store plan
declare -a TASKS_CONFIG
declare -a TASKS_OLD_HASH
declare -a TASKS_NEW_HASH
declare -a TASKS_ACTION # SKIP, REGEN

count=0

# Phase 1: Analysis
echo "Analyzing existing files..."
while read -r filename; do
    filepath="$DYNAMICS_DIR/$filename"
    current_hash=${filename%.cse.h}

    if [ -f "$filepath" ]; then
        # Check generation info
        generated_commit=""
        if [ -n "$CURRENT_COMMIT" ]; then
            # Read the last few lines to find generation info
            # Use || true to prevent exit on grep failure if not found
            generated_commit=$(grep "// Generation Info: commit=" "$filepath" | tail -n 1 | cut -d= -f2 || true)
        fi

        if [ -n "$CURRENT_COMMIT" ] && [ "$generated_commit" == "$CURRENT_COMMIT" ]; then
            echo "  $filename: Up-to-date (commit match). Skipping."
            continue
        fi

        # Extract config string
        config_string=$(python3 "$SCRIPT_DIR/source/read_cse_file.py" "$filepath" "dynamics" || true)

        if [ -n "$config_string" ]; then
            formatted_string=$(python3 "$SCRIPT_DIR/source/format_common.py" "$config_string")
            new_hash=$(echo -n "$formatted_string" | sha256sum | awk '{print $1}')

            TASKS_CONFIG[$count]="$config_string"
            TASKS_OLD_HASH[$count]="$current_hash"
            TASKS_NEW_HASH[$count]="$new_hash"
            TASKS_ACTION[$count]="REGEN"

            if [ "$current_hash" != "$new_hash" ]; then
                echo "  $filename: Hash mismatch -> $new_hash. Will regenerate and rename."
            else
                echo "  $filename: Hash match. Will regenerate."
            fi

            count=$((count + 1))
        else
            echo "  Error: Could not extract configuration from $filename" >&2
        fi
    else
        echo "  Warning: Included file $filename not found. Skipping." >&2
    fi
done < "$JOB_DIR/file_list.txt"

echo "Analysis complete. $count files to regenerate."

if [ "$count" -eq 0 ]; then
    exit 0
fi

# Phase 2: Execution
echo "Starting regeneration..."

run_task() {
    local idx=$1
    local config="${TASKS_CONFIG[$idx]}"
    local old_hash="${TASKS_OLD_HASH[$idx]}"

    # Set memory limit if configured
    if [ -n "$MAX_MEMORY" ]; then
        ulimit -v "$MAX_MEMORY"
    fi

    # Run optimization without updating header
    if "$SCRIPT_DIR/optimize_dynamics.sh" --install --skip-header-update "$config" > /dev/null 2>&1; then
        echo "$idx:SUCCESS" > "$JOB_DIR/$idx.status"
    else
        echo "$idx:FAILURE" > "$JOB_DIR/$idx.status"
    fi
}

# Run tasks in parallel batches
idx=0
while [ $idx -lt $count ]; do
    # Spawn up to JOBS
    running=0
    for ((j=0; j<JOBS; j++)); do
        if [ $idx -lt $count ]; then
            run_task $idx &
            idx=$((idx + 1))
            running=$((running + 1))
        fi
    done

    # Wait for this batch
    wait

    # Check progress (simple print)
    echo "  Processed $idx / $count"
done

# Phase 3: Finalization
echo "Finalizing updates..."

for ((i=0; i<count; i++)); do
    status_file="$JOB_DIR/$i.status"
    if [ -f "$status_file" ]; then
        status=$(cat "$status_file")
        if [[ "$status" == *":SUCCESS" ]]; then
            old_hash="${TASKS_OLD_HASH[$i]}"
            new_hash="${TASKS_NEW_HASH[$i]}"

            if [ "$old_hash" != "$new_hash" ]; then
                old_file="$DYNAMICS_DIR/$old_hash.cse.h"
                new_file="$DYNAMICS_DIR/$new_hash.cse.h"

                # Cleanup old file
                if [ -f "$old_file" ]; then
                    rm "$old_file"
                fi

                # Update header: replace old include with new include
                echo "  Updating header: $old_hash -> $new_hash"
                escaped_old=$(echo "$old_hash.cse.h" | sed 's/\./\\./g')
                sed -i "s/$escaped_old/$new_hash.cse.h/" "$HEADER_FILE"
            else
                echo "  Updated $old_hash.cse.h"
            fi
        else
            echo "  Failed to regenerate: ${TASKS_OLD_HASH[$i]}" >&2
        fi
    else
        echo "  Internal error: Status missing for task $i" >&2
    fi
done

echo "Regeneration complete."
