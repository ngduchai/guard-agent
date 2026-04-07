#!/usr/bin/env bash

# Usage: ./run_evaluate.sh <app_name> [--max-iters N]
#
# Runs the full evaluation pipeline:
#   1. Baseline:    opencode without guard-agent (iterative loop)
#   2. Guard-agent: opencode with guard-agent MCP (iterative loop)
#   3. Comparison:  side-by-side report with metrics
#
# Example:
#   ./validation/veloc/scripts/run_evaluate.sh art_simple
#   ./validation/veloc/scripts/run_evaluate.sh art_simple --max-iters 10

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

MAX_ITERS_FLAG=""
APP_NAME=""

for arg in "$@"; do
  case "$arg" in
    --max-iters) MAX_ITERS_FLAG="--max-iters"; continue ;;
    *)
      if [ "$MAX_ITERS_FLAG" = "--max-iters" ] && [ -z "$MAX_ITERS_VAL" ]; then
        MAX_ITERS_VAL="$arg"
        MAX_ITERS_FLAG="--max-iters $arg"
        continue
      fi
      [ -z "$APP_NAME" ] && APP_NAME="$arg"
      ;;
  esac
done

if [ -z "$APP_NAME" ]; then
  echo "Usage: run_evaluate.sh <app_name> [--max-iters N]" >&2
  exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  Full Evaluation: $APP_NAME"
echo "║  Baseline (no guard-agent) vs Guard-agent (with MCP tools)"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# --- Phase 1: Baseline ---
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Phase 1: Baseline (OpenCode without guard-agent)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
set +e
"$SCRIPT_DIR/run_iterative.sh" --baseline $MAX_ITERS_FLAG "$APP_NAME"
BASELINE_EXIT=$?
set -e
echo ""

# --- Phase 2: Guard-agent ---
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Phase 2: Guard-agent (OpenCode with guard-agent MCP)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
set +e
"$SCRIPT_DIR/run_iterative.sh" $MAX_ITERS_FLAG "$APP_NAME"
GUARDAGENT_EXIT=$?
set -e
echo ""

# --- Phase 3: Comparison ---
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Phase 3: Comparison"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
"$SCRIPT_DIR/run_compare.sh" "$APP_NAME"
echo ""

REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  Evaluation complete: $APP_NAME"
echo "║  Baseline exit:     $BASELINE_EXIT $([ $BASELINE_EXIT -eq 0 ] && echo '(PASS)' || echo '(FAIL)')"
echo "║  Guard-agent exit:  $GUARDAGENT_EXIT $([ $GUARDAGENT_EXIT -eq 0 ] && echo '(PASS)' || echo '(FAIL)')"
echo "║  Report: build/validation_output/comparison_${APP_NAME}.md"
echo "╚══════════════════════════════════════════════════════════════════════╝"
