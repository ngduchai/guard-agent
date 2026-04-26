#!/usr/bin/env bash
set -e

# Clean up child processes on exit to prevent zombies after Ctrl+C
_cleanup() {
  pkill -9 -P $$ 2>/dev/null || true
  pkill -9 -f "failure_injector.py" 2>/dev/null || true
}
trap _cleanup EXIT INT TERM

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
MAX_ITERS=10
INJECTION_DELAY=""
GROUND_TRUTH_DIR=""

APP_NAME=""
while [ $# -gt 0 ]; do
  case "$1" in
    --baseline)          USE_BASELINE=true; shift ;;
    --max-iters)         MAX_ITERS="$2"; shift 2 ;;
    --injection-delay)   INJECTION_DELAY="$2"; shift 2 ;;
    --ground-truth-dir)  GROUND_TRUTH_DIR="$2"; shift 2 ;;
    -*)                  echo "Unknown option: $1" >&2; exit 1 ;;
    *)                   APP_NAME="$1"; shift ;;
  esac
done

if [ -z "$APP_NAME" ]; then
  echo "Usage: run_iterative.sh [--baseline] <app_name> [--max-iters N]" >&2
  exit 1
fi

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

# Re-copy source from original to ensure a clean starting point.
# Prevents stale modifications from a previous interrupted run.
for _src_root in "$REPO_ROOT/tests/apps/vanillas" "$REPO_ROOT/tests/ecp/vanillas" "$REPO_ROOT/tests/examples/original"; do
  if [ -d "$_src_root/$APP_NAME" ]; then
    echo "[REFRESH] Re-copying $APP_NAME source (clean)"
    rm -rf "$APP_DIR"
    # Ensure parent (build/tests_baseline/ or build/tests/) exists.  Bare
    # `cp` does not create missing parents and earlier overnight cleanup
    # may have removed the parent dir entirely.
    mkdir -p "$(dirname "$APP_DIR")"
    cp -a "$_src_root/$APP_NAME" "$APP_DIR"
    break
  fi
done

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
    # Feed back the validation error from the previous iteration.
    # The fallback prompt deliberately ships only the raw artefacts (the
    # validator output and the build output) plus the failure-analysis
    # discipline from the original prompt.txt.  We do NOT include a checklist
    # of what to do (initialise X, register Y, finalise Z, link library W) —
    # the whole point of the experiment is to measure whether the agent can
    # diagnose its own failure and decide for itself what to change.  Listing
    # API steps here would short-circuit that judgment and contaminate every
    # iteration past the first.  See ISSUES.md issue #18.
    PREV_LOG="$LOG_DIR/iter_$((ITER - 1))"
    PROMPT="Your previous attempt to make this code resilient against
mid-execution process failures was rejected by the validation pipeline.
The raw output of that pipeline is below.

--- VALIDATION STDOUT (last 100 lines) ---
$(tail -100 "$PREV_LOG/validate_stdout.txt" 2>/dev/null || echo "(no stdout)")

--- VALIDATION STDERR (last 100 lines) ---
$(tail -100 "$PREV_LOG/validate_stderr.txt" 2>/dev/null || echo "(no stderr)")

--- BUILD OUTPUT (last 50 lines) ---
$(tail -50 "$PREV_LOG/build_output.txt" 2>/dev/null || echo "(no build output)")

Continue working in the current directory.  Apply the same narration and
failure-analysis discipline you were given originally:

  1. Quote the exact error message you are reacting to.
  2. State your hypothesis for the root cause.
  3. Describe the specific change you intend to make and why it
     should fix it.

Then make the change."
  fi

  # Save the prompt for debugging
  printf '%s\n' "$PROMPT" > "$ITER_LOG/prompt.txt"

  # --- Step 2: Run OpenCode (timed) ---
  echo "[iter $ITER] Running OpenCode ($LABEL)..."
  OPENCODE_START=$(date +%s.%N)
  OPENCODE_START_MS=$(date +%s%3N)
  cd "$APP_DIR"

  # Hard cap on OpenCode wallclock per iteration.  The opencode CLI has been
  # observed to hang indefinitely on a stalled SSE/Argo response (the body
  # of a tool-call round-trip never closes), blocking the whole iterative
  # pipeline.  900 s is generous — typical iterations finish in < 5 min.
  # Override via OPENCODE_TIMEOUT env var if needed.
  # 1800 s default (was 900): observed iter 1 of CoMD/HPCG/SPARTA exceeding
  # 900 s during the *productive* exploration phase (40+ steps, multi-MB
  # context, source files getting edited but the LLM not yet finishing).
  # 1800 s gives iter 1 room to actually converge instead of being killed
  # mid-edit-batch; iters 2+ that just react to a build error still finish
  # in under 5 min so the cap doesn't matter for them.  Override via
  # OPENCODE_TIMEOUT env var (e.g. for slower providers).
  OPENCODE_TIMEOUT="${OPENCODE_TIMEOUT:-1800}"
  # --dangerously-skip-permissions is paired with a strict deny-list in
  # ~/.config/opencode/opencode.json's "permission" block:
  #   - edit/write/patch: ALLOW only under build/tests_baseline/** and
  #     build/tests/**; DENY everywhere else
  #   - bash: DENY (the iterative loop runs all builds externally)
  #   - webfetch/websearch/external_directory: DENY
  # With those denies in place, --dangerously-skip-permissions only auto-
  # approves the *safe* operations (read/list/grep/glob anywhere, edits
  # within the per-app codebase) and explicit denies still apply.
  #
  # Model selection: OPENCODE_MODEL env var (default: argo/claudeopus47).
  # Available models from opencode.json (Argo dev gateway):
  #   argo/claudeopus47    Claude Opus 4.7 (default — highest-quality Anthropic)
  #   argo/claudeopus46    Claude Opus 4.6
  #   argo/claudesonnet46  Claude Sonnet 4.6
  #   argo/claudehaiku45   Claude Haiku 4.5
  #   argo/gpt54           GPT-5.4 (highest-quality OpenAI)
  #   argo/gemini25pro     Gemini 2.5 Pro (highest-quality Google)
  OPENCODE_MODEL="${OPENCODE_MODEL:-argo/claudeopus47}"
  echo "[iter $ITER] OpenCode model: $OPENCODE_MODEL"
  timeout --kill-after=10 "$OPENCODE_TIMEOUT" \
    opencode run --dangerously-skip-permissions --model "$OPENCODE_MODEL" "$PROMPT" \
    > "$ITER_LOG/opencode_stdout.txt" 2> "$ITER_LOG/opencode_stderr.txt" \
    || {
      _ec=$?
      if [ "$_ec" = 124 ] || [ "$_ec" = 137 ]; then
        echo "[iter $ITER] OpenCode timed out after ${OPENCODE_TIMEOUT}s — treating as iteration failure" \
          | tee -a "$ITER_LOG/opencode_stderr.txt"
      fi
      true
    }

  cd "$REPO_ROOT"
  OPENCODE_END=$(date +%s.%N)
  # awk emits a leading 0 for fractions (unlike bc which would write
  # ".865" instead of "0.865" — invalid JSON when interpolated below).
  OPENCODE_ELAPSED=$(awk "BEGIN { printf \"%.9f\", $OPENCODE_END - $OPENCODE_START }" 2>/dev/null || echo "0")
  echo "[iter $ITER] OpenCode finished in ${OPENCODE_ELAPSED}s"

  # --- Per-iter inspection: pull tool-call breakdown + file-change stats ---
  # Writes inspection.json + inspection.md into the iter dir so a later
  # human / agent can quickly see WHAT OpenCode did this iteration without
  # re-querying the SQLite DB.  Best-effort — failures here do not affect
  # the iterative loop.
  python3 -m validation.veloc.scripts.inspect_iter "$ITER_LOG" --write \
    >> "$ITER_LOG/inspection.run.log" 2>&1 || true

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

  # Build extra flags for validate.sh
  EXTRA_VALIDATE_FLAGS=""
  [ -n "$INJECTION_DELAY" ] && EXTRA_VALIDATE_FLAGS="$EXTRA_VALIDATE_FLAGS --injection-delay $INJECTION_DELAY"
  [ -n "$GROUND_TRUTH_DIR" ] && EXTRA_VALIDATE_FLAGS="$EXTRA_VALIDATE_FLAGS --ground-truth-dir $GROUND_TRUTH_DIR"

  set +e
  "$SCRIPT_DIR/run_validate.sh" $VALIDATE_FLAG "$APP_NAME" \
    --skip-benchmarks --skip-report \
    $EXTRA_VALIDATE_FLAGS \
    > "$ITER_LOG/validate_stdout.txt" 2> "$ITER_LOG/validate_stderr.txt"
  VALIDATE_EXIT=$?
  set -e

  VALIDATE_END=$(date +%s.%N)
  # awk preserves leading zero for fractions; bc would strip it (".865"
  # → invalid JSON).  Same fix applied to OPENCODE_ELAPSED + ITER_ELAPSED
  # + TOTAL_ELAPSED below for consistency across all four float fields.
  VALIDATE_ELAPSED=$(awk "BEGIN { printf \"%.9f\", $VALIDATE_END - $VALIDATE_START }" 2>/dev/null || echo "0")
  ITER_ELAPSED=$(awk "BEGIN { printf \"%.9f\", $OPENCODE_ELAPSED + $VALIDATE_ELAPSED }" 2>/dev/null || echo "0")
  TOTAL_ELAPSED=$(awk "BEGIN { printf \"%.9f\", $TOTAL_ELAPSED + $ITER_ELAPSED }" 2>/dev/null || echo "0")

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
