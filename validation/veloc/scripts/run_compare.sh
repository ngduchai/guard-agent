#!/usr/bin/env bash
set -e

# Usage: ./run_compare.sh <app_name>
#
# Compares validation results between:
#   - build/validation_output/<app>_baseline/  (OpenCode without guard-agent)
#   - build/validation_output/<app>/           (OpenCode with guard-agent)
#
# Also diffs the source code changes and checks VeloC API coverage.
# Requires both validations to have been run first.
#
# Example:
#   ./validation/veloc/scripts/run_validate.sh --baseline art_simple
#   ./validation/veloc/scripts/run_validate.sh art_simple
#   ./validation/veloc/scripts/run_compare.sh art_simple

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BUILD_DIR="$REPO_ROOT/build"

# Activate venv
if [ -f "$BUILD_DIR/venv/bin/activate" ]; then
  . "$BUILD_DIR/venv/bin/activate"
fi
export PYTHONPATH="${REPO_ROOT}"

APP_NAME="${1:?Usage: run_compare.sh <app_name>}"

# --- Resolve paths ---
BASELINE_OUTPUT="$BUILD_DIR/validation_output/${APP_NAME}_baseline"
GUARDAGENT_OUTPUT="$BUILD_DIR/validation_output/${APP_NAME}"
BASELINE_SRC="$BUILD_DIR/tests_baseline/$APP_NAME"
GUARDAGENT_SRC="$BUILD_DIR/tests/$APP_NAME"
REPORT_DIR="$BUILD_DIR/validation_output"

# --- Resolve original source ---
ORIGINAL_SRC=""
if [ -d "$REPO_ROOT/tests/examples/original/$APP_NAME" ]; then
  ORIGINAL_SRC="$REPO_ROOT/tests/examples/original/$APP_NAME"
elif [ -d "$REPO_ROOT/tests/ecp/vanillas/$APP_NAME" ]; then
  ORIGINAL_SRC="$REPO_ROOT/tests/ecp/vanillas/$APP_NAME"
fi

# --- Check prerequisites ---
MISSING=false
if [ ! -d "$BASELINE_OUTPUT" ]; then
  echo "WARNING: Baseline validation not found at $BASELINE_OUTPUT" >&2
  echo "  Run: ./validation/veloc/scripts/run_validate.sh --baseline $APP_NAME" >&2
  MISSING=true
fi
if [ ! -d "$GUARDAGENT_OUTPUT" ]; then
  echo "WARNING: Guard-agent validation not found at $GUARDAGENT_OUTPUT" >&2
  echo "  Run: ./validation/veloc/scripts/run_validate.sh $APP_NAME" >&2
  MISSING=true
fi
if [ "$MISSING" = true ]; then
  echo "" >&2
  echo "Run both validations first, then compare." >&2
  exit 1
fi

# --- Resolve iterative result files ---
BASELINE_RESULT="$BUILD_DIR/iterative_logs/${APP_NAME}_baseline/result.json"
GUARDAGENT_RESULT="$BUILD_DIR/iterative_logs/${APP_NAME}_guard-agent/result.json"

ITER_FLAGS=""
[ -f "$BASELINE_RESULT" ] && ITER_FLAGS="$ITER_FLAGS --iterative-result-a $BASELINE_RESULT"
[ -f "$GUARDAGENT_RESULT" ] && ITER_FLAGS="$ITER_FLAGS --iterative-result-b $GUARDAGENT_RESULT"

python -m validation.veloc.compare "$APP_NAME" \
  --output-dir-a "$BASELINE_OUTPUT" \
  --label-a "Baseline (no guard-agent)" \
  --output-dir-b "$GUARDAGENT_OUTPUT" \
  --label-b "With guard-agent" \
  --original-src "$ORIGINAL_SRC" \
  --resilient-src-a "$BASELINE_SRC" \
  --resilient-src-b "$GUARDAGENT_SRC" \
  --report-dir "$REPORT_DIR" \
  $ITER_FLAGS
