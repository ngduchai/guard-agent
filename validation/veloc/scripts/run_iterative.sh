#!/usr/bin/env bash
set -e

# Usage: ./run_iterative.sh [--baseline] <app_name> [--max-iters N]
#
# Automated evaluation loop:
#   1. Run OpenCode non-interactively with the app's prompt
#   2. Run correctness validation
#   3. If PASS -> done
#   4. If FAIL -> feed error logs back to OpenCode and repeat
#
# Captures per-iteration metrics: elapsed time, validation result.
# Saves enriched result.json with timing data for comparison.
#
# Modes:
#   ./run_iterative.sh art_simple              # with guard-agent MCP
#   ./run_iterative.sh --baseline art_simple   # without guard-agent (baseline)
#
# Options:
#   --max-iters N    Maximum iterations (default: 5)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BUILD_DIR="$REPO_ROOT/build"

# Activate venv
if [ -f "$BUILD_DIR/venv/bin/activate" ]; then
  . "$BUILD_DIR/venv/bin/activate"
fi
export PYTHONPATH="${REPO_ROOT}"

# --- Parse args ---
USE_BASELINE=false
MAX_ITERS=5

while [ $# -gt 0 ]; do
  case "$1" in
    --baseline)   USE_BASELINE=true; shift ;;
    --max-iters)  MAX_ITERS="$2"; shift 2 ;;
    -*)           echo "Unknown option: $1" >&2; exit 1 ;;
    *)            break ;;
  esac
done

APP_NAME="${1:?Usage: run_iterative.sh [--baseline] <app_name> [--max-iters N]}"

# --- Resolve paths ---
if [ "$USE_BASELINE" = true ]; then
  APP_DIR="$BUILD_DIR/tests_baseline/$APP_NAME"
  LABEL="baseline"
  VALIDATE_FLAG="--baseline"
else
  APP_DIR="$BUILD_DIR/tests/$APP_NAME"
  LABEL="guard-agent"
  VALIDATE_FLAG=""
fi

if [ ! -d "$APP_DIR" ]; then
  echo "ERROR: App directory not found: $APP_DIR" >&2
  exit 1
fi

PROMPT_FILE="$APP_DIR/prompt.txt"
if [ ! -f "$PROMPT_FILE" ]; then
  echo "ERROR: No prompt.txt found in $APP_DIR" >&2
  exit 1
fi

INITIAL_PROMPT="$(cat "$PROMPT_FILE")"
LOG_DIR="$BUILD_DIR/iterative_logs/${APP_NAME}_${LABEL}"
mkdir -p "$LOG_DIR"

echo "════════════════════════════════════════════════════════════════════"
echo "  Iterative evaluation: $APP_NAME ($LABEL)"
echo "════════════════════════════════════════════════════════════════════"
echo "  App directory: $APP_DIR"
echo "  Max iterations: $MAX_ITERS"
echo "  Logs: $LOG_DIR"
echo ""

# --- Metrics accumulators ---
TOTAL_ELAPSED="0.0"
TOTAL_INPUT_TOKENS=0
TOTAL_OUTPUT_TOKENS=0
TOTAL_TOKENS=0
ITER_METRICS=""  # will be built as JSON array entries
EVAL_START=$(date +%s.%N)

# --- Iteration loop ---
for ITER in $(seq 1 "$MAX_ITERS"); do
  echo ""
  echo "╔══════════════════════════════════════════════════════════════════╗"
  echo "║  Iteration $ITER / $MAX_ITERS"
  echo "╚══════════════════════════════════════════════════════════════════╝"
  echo ""

  ITER_LOG="$LOG_DIR/iter_${ITER}"
  mkdir -p "$ITER_LOG"

  # --- Step 1: Build the prompt ---
  if [ "$ITER" -eq 1 ]; then
    PROMPT="$INITIAL_PROMPT"
  else
    # Feed back the validation error from the previous iteration
    PREV_LOG="$LOG_DIR/iter_$((ITER - 1))"
    PROMPT="The previous attempt to make this code resilient with VeloC checkpointing failed validation.

Here is the validation output from the failed run:

--- VALIDATION STDOUT ---
$(tail -100 "$PREV_LOG/validate_stdout.txt" 2>/dev/null || echo "(no stdout)")

--- VALIDATION STDERR ---
$(tail -100 "$PREV_LOG/validate_stderr.txt" 2>/dev/null || echo "(no stderr)")

--- BUILD OUTPUT ---
$(tail -50 "$PREV_LOG/build_output.txt" 2>/dev/null || echo "(no build output)")

Please analyze the errors above and fix the VeloC checkpoint injection.
The code is in the current directory. Review what was done wrong, fix it, and ensure:
1. VeloC is properly initialized after MPI_Init
2. Critical state is registered with VELOC_Mem_protect
3. Restart logic checks for existing checkpoints before the main loop
4. Checkpoints are taken inside the main computation loop
5. VeloC is finalized before MPI_Finalize
6. veloc.cfg exists with valid scratch/persistent paths
7. CMakeLists.txt links veloc-client"
  fi

  # Save the prompt for debugging
  printf '%s\n' "$PROMPT" > "$ITER_LOG/prompt.txt"

  # --- Step 2: Run OpenCode (timed) ---
  echo "[iter $ITER] Running OpenCode ($LABEL)..."
  OPENCODE_START=$(date +%s.%N)
  OPENCODE_START_MS=$(date +%s%3N)
  cd "$APP_DIR"

  opencode run "$PROMPT" > "$ITER_LOG/opencode_stdout.txt" 2> "$ITER_LOG/opencode_stderr.txt" || true

  cd "$REPO_ROOT"
  OPENCODE_END=$(date +%s.%N)
  OPENCODE_ELAPSED=$(echo "$OPENCODE_END - $OPENCODE_START" | bc 2>/dev/null || echo "0")
  echo "[iter $ITER] OpenCode finished in ${OPENCODE_ELAPSED}s"

  # --- Extract token usage from OpenCode's SQLite DB ---
  OPENCODE_DB="$HOME/.local/share/opencode/opencode.db"
  ITER_INPUT_TOKENS=0
  ITER_OUTPUT_TOKENS=0
  ITER_TOTAL_TOKENS=0
  if [ -f "$OPENCODE_DB" ]; then
    TOKENS_JSON=$(python3 -c "
import sqlite3, json, sys
try:
    db = sqlite3.connect('$OPENCODE_DB')
    c = db.cursor()
    c.execute('''
        SELECT m.session_id,
               COALESCE(SUM(json_extract(m.data, \"$.tokens.input\")), 0),
               COALESCE(SUM(json_extract(m.data, \"$.tokens.output\")), 0),
               COALESCE(SUM(json_extract(m.data, \"$.tokens.total\")), 0)
        FROM message m
        JOIN session s ON m.session_id = s.id
        WHERE s.directory = '$APP_DIR'
          AND json_extract(m.data, \"$.role\") = \"assistant\"
          AND json_extract(m.data, \"$.tokens.total\") IS NOT NULL
          AND s.time_created >= $OPENCODE_START_MS
        GROUP BY m.session_id
        ORDER BY s.time_created DESC
        LIMIT 1
    ''')
    row = c.fetchone()
    db.close()
    if row:
        print(json.dumps({'input': int(row[1]), 'output': int(row[2]), 'total': int(row[3])}))
    else:
        print(json.dumps({'input': 0, 'output': 0, 'total': 0}))
except Exception as e:
    print(json.dumps({'input': 0, 'output': 0, 'total': 0, 'error': str(e)}), file=sys.stderr)
    print(json.dumps({'input': 0, 'output': 0, 'total': 0}))
" 2>/dev/null)
    ITER_INPUT_TOKENS=$(echo "$TOKENS_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('input',0))" 2>/dev/null || echo "0")
    ITER_OUTPUT_TOKENS=$(echo "$TOKENS_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('output',0))" 2>/dev/null || echo "0")
    ITER_TOTAL_TOKENS=$(echo "$TOKENS_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo "0")
    echo "[iter $ITER] Tokens: input=$ITER_INPUT_TOKENS output=$ITER_OUTPUT_TOKENS total=$ITER_TOTAL_TOKENS"
  fi

  # --- Step 3: Run correctness validation (timed) ---
  echo "[iter $ITER] Running correctness validation..."
  VALIDATE_START=$(date +%s.%N)

  set +e
  "$SCRIPT_DIR/run_validate.sh" $VALIDATE_FLAG "$APP_NAME" \
    --skip-benchmarks --skip-report \
    > "$ITER_LOG/validate_stdout.txt" 2> "$ITER_LOG/validate_stderr.txt"
  VALIDATE_EXIT=$?
  set -e

  VALIDATE_END=$(date +%s.%N)
  VALIDATE_ELAPSED=$(echo "$VALIDATE_END - $VALIDATE_START" | bc 2>/dev/null || echo "0")
  ITER_ELAPSED=$(echo "$OPENCODE_ELAPSED + $VALIDATE_ELAPSED" | bc 2>/dev/null || echo "0")
  TOTAL_ELAPSED=$(echo "$TOTAL_ELAPSED + $ITER_ELAPSED" | bc 2>/dev/null || echo "0")

  # Extract build output for feedback (if build failed)
  grep -A 20 "Build failed\|CMake Error\|make.*Error\|error:" \
    "$ITER_LOG/validate_stdout.txt" "$ITER_LOG/validate_stderr.txt" \
    > "$ITER_LOG/build_output.txt" 2>/dev/null || true

  # Record per-iteration metrics
  ITER_PASSED="false"
  [ "$VALIDATE_EXIT" -eq 0 ] && ITER_PASSED="true"

  # Accumulate token counts
  TOTAL_INPUT_TOKENS=$((TOTAL_INPUT_TOKENS + ITER_INPUT_TOKENS))
  TOTAL_OUTPUT_TOKENS=$((TOTAL_OUTPUT_TOKENS + ITER_OUTPUT_TOKENS))
  TOTAL_TOKENS=$((TOTAL_TOKENS + ITER_TOTAL_TOKENS))

  # Save per-iteration metrics
  cat > "$ITER_LOG/metrics.json" << EOFMETRICS
{
  "iter": $ITER,
  "opencode_elapsed_s": $OPENCODE_ELAPSED,
  "validation_elapsed_s": $VALIDATE_ELAPSED,
  "total_elapsed_s": $ITER_ELAPSED,
  "validation_passed": $ITER_PASSED,
  "input_tokens": $ITER_INPUT_TOKENS,
  "output_tokens": $ITER_OUTPUT_TOKENS,
  "total_tokens": $ITER_TOTAL_TOKENS
}
EOFMETRICS

  # Append to JSON array string
  [ -n "$ITER_METRICS" ] && ITER_METRICS="${ITER_METRICS},"
  ITER_METRICS="${ITER_METRICS}
    {\"iter\": $ITER, \"opencode_elapsed_s\": $OPENCODE_ELAPSED, \"validation_elapsed_s\": $VALIDATE_ELAPSED, \"total_elapsed_s\": $ITER_ELAPSED, \"validation_passed\": $ITER_PASSED, \"input_tokens\": $ITER_INPUT_TOKENS, \"output_tokens\": $ITER_OUTPUT_TOKENS, \"total_tokens\": $ITER_TOTAL_TOKENS}"

  # --- Step 4: Check result ---
  if [ "$VALIDATE_EXIT" -eq 0 ]; then
    EVAL_END=$(date +%s.%N)
    WALL_ELAPSED=$(echo "$EVAL_END - $EVAL_START" | bc 2>/dev/null || echo "0")

    echo ""
    echo "════════════════════════════════════════════════════════════════════"
    echo "  PASS — Correctness validation passed on iteration $ITER"
    echo "  Total OpenCode+validation time: ${TOTAL_ELAPSED}s"
    echo "  Wall-clock time: ${WALL_ELAPSED}s"
    echo "  Total tokens: ${TOTAL_TOKENS} (input: ${TOTAL_INPUT_TOKENS}, output: ${TOTAL_OUTPUT_TOKENS})"
    echo "════════════════════════════════════════════════════════════════════"

    cat > "$LOG_DIR/result.json" << EOFRESULT
{
  "app_name": "$APP_NAME",
  "mode": "$LABEL",
  "passed": true,
  "iterations": $ITER,
  "max_iters": $MAX_ITERS,
  "total_elapsed_s": $TOTAL_ELAPSED,
  "wall_elapsed_s": $WALL_ELAPSED,
  "total_input_tokens": $TOTAL_INPUT_TOKENS,
  "total_output_tokens": $TOTAL_OUTPUT_TOKENS,
  "total_tokens": $TOTAL_TOKENS,
  "per_iteration": [$ITER_METRICS
  ]
}
EOFRESULT
    exit 0
  else
    echo "[iter $ITER] FAIL — Validation failed (${ITER_ELAPSED}s). $([ "$ITER" -lt "$MAX_ITERS" ] && echo "Retrying..." || echo "Max iterations reached.")"
    grep -E "FATAL|FAIL|Error|error:" "$ITER_LOG/validate_stderr.txt" 2>/dev/null | head -5
  fi
done

# --- Max iterations exhausted ---
EVAL_END=$(date +%s.%N)
WALL_ELAPSED=$(echo "$EVAL_END - $EVAL_START" | bc 2>/dev/null || echo "0")

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "  FAIL — Did not pass after $MAX_ITERS iterations"
echo "  Total OpenCode+validation time: ${TOTAL_ELAPSED}s"
echo "  Wall-clock time: ${WALL_ELAPSED}s"
echo "  Total tokens: ${TOTAL_TOKENS} (input: ${TOTAL_INPUT_TOKENS}, output: ${TOTAL_OUTPUT_TOKENS})"
echo "════════════════════════════════════════════════════════════════════"
echo "  Logs: $LOG_DIR"

cat > "$LOG_DIR/result.json" << EOFRESULT
{
  "app_name": "$APP_NAME",
  "mode": "$LABEL",
  "passed": false,
  "iterations": $MAX_ITERS,
  "max_iters": $MAX_ITERS,
  "total_elapsed_s": $TOTAL_ELAPSED,
  "wall_elapsed_s": $WALL_ELAPSED,
  "total_input_tokens": $TOTAL_INPUT_TOKENS,
  "total_output_tokens": $TOTAL_OUTPUT_TOKENS,
  "total_tokens": $TOTAL_TOKENS,
  "per_iteration": [$ITER_METRICS
  ]
}
EOFRESULT
exit 1
