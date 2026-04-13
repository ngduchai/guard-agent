#!/usr/bin/env bash

# Usage: ./run_evaluate.sh <app_name> [--max-iters N]
#
# Runs the full evaluation pipeline:
#   0. Ground truth: build + run original code to get correct output and timing
#   1. Baseline:     opencode without guard-agent (iterative loop)
#   2. Guard-agent:  opencode with guard-agent MCP (iterative loop)
#   3. Comparison:   side-by-side report with metrics
#
# The ground truth execution time determines the failure injection delay
# (1/3 of runtime), ensuring failures are injected after at least one
# checkpoint has been written.
#
# Example:
#   ./validation/veloc/scripts/run_evaluate.sh art_simple
#   ./validation/veloc/scripts/run_evaluate.sh art_simple --max-iters 10

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BUILD_DIR="$REPO_ROOT/build"

# Activate venv
if [ -f "$BUILD_DIR/venv/bin/activate" ]; then
  . "$BUILD_DIR/venv/bin/activate"
fi
export PYTHONPATH="${REPO_ROOT}"

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

# ── Phase 0: Ground truth ────────────────────────────────────────────────────
# Build and run the original (unmodified) code ONCE to get:
#   - Correct output (for comparison)
#   - Execution time (to compute injection delay)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Phase 0: Ground truth (build + run original code)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

GROUND_TRUTH_DIR="$BUILD_DIR/validation_output/${APP_NAME}/ground_truth"

# Resolve original source
ORIGINAL_SRC=""
if [ -d "$REPO_ROOT/tests/examples/original/$APP_NAME" ]; then
  ORIGINAL_SRC="$REPO_ROOT/tests/examples/original/$APP_NAME"
elif [ -d "$REPO_ROOT/tests/ecp/vanillas/$APP_NAME" ]; then
  ORIGINAL_SRC="$REPO_ROOT/tests/ecp/vanillas/$APP_NAME"
elif [ -d "$REPO_ROOT/tests/apps/vanillas/$APP_NAME" ]; then
  ORIGINAL_SRC="$REPO_ROOT/tests/apps/vanillas/$APP_NAME"
else
  echo "ERROR: Original source not found for '$APP_NAME'." >&2
  exit 1
fi

# Load app config for exe name and args
APP_CONFIG="$REPO_ROOT/validation/veloc/app_configs/${APP_NAME}.json"

_cfg_val() {
  python3 -c "
import json, os
try:
    cfg = json.load(open('$APP_CONFIG'))
    keys = '$1'.split('.')
    val = cfg
    for k in keys:
        val = val[k]
    if isinstance(val, list):
        print(' '.join(os.path.expandvars(str(v)) for v in val))
    else:
        print(os.path.expandvars(str(val)))
except (KeyError, TypeError, FileNotFoundError):
    print('$2')
" 2>/dev/null
}

# Set env defaults from app config
if [ -f "$APP_CONFIG" ]; then
  eval "$(python3 -c "
import json, os
try:
    cfg = json.load(open('$APP_CONFIG'))
    for k, v in cfg.get('env_defaults', {}).items():
        if k not in os.environ:
            val = v if os.path.isabs(v) else os.path.join('$BUILD_DIR', v)
            print(f'export {k}=\"{val}\"')
except (FileNotFoundError, KeyError):
    pass
" 2>/dev/null)"
fi

EXE_NAME=$(_cfg_val "executable_name" "$APP_NAME")
APP_ARGS=$(_cfg_val "app_args" "")
NUM_PROCS=$(_cfg_val "num_procs" "4")

# Run the ground truth: build original + execute + capture timing
echo "  Original source: $ORIGINAL_SRC"
echo "  Executable:      $EXE_NAME"
echo "  Output:          $GROUND_TRUTH_DIR"
echo ""

python3 -c "
import json, sys, time
from pathlib import Path
sys.path.insert(0, '$REPO_ROOT')
from validation.veloc.runner import run_baseline

ground_truth_dir = Path('$GROUND_TRUTH_DIR')
ground_truth_dir.mkdir(parents=True, exist_ok=True)

app_args = '''$APP_ARGS'''.split() if '''$APP_ARGS'''.strip() else []

result = run_baseline(
    source_dir=Path('$ORIGINAL_SRC'),
    build_dir=Path('$BUILD_DIR/validation_output/$APP_NAME/build/original'),
    output_dir=ground_truth_dir,
    executable_name='$EXE_NAME',
    num_procs=$NUM_PROCS,
    app_args=app_args,
)

# Save metadata
meta = {'elapsed_s': result.elapsed_s, 'exit_code': result.exit_code}
(ground_truth_dir / 'ground_truth_meta.json').write_text(json.dumps(meta, indent=2))

print(f'[ground truth] Completed in {result.elapsed_s:.1f}s (exit={result.exit_code})')

# Compute and report injection delay
delay = max(5.0, min(result.elapsed_s / 3.0, 300.0))
print(f'[ground truth] Injection delay (1/3 runtime): {delay:.1f}s')

# Write delay to a file so the shell script can read it
(ground_truth_dir / 'injection_delay.txt').write_text(f'{delay:.1f}')
"

if [ $? -ne 0 ]; then
  echo "ERROR: Ground truth run failed." >&2
  exit 1
fi

# Read computed injection delay
INJECTION_DELAY=$(cat "$GROUND_TRUTH_DIR/injection_delay.txt" 2>/dev/null || echo "auto")
echo ""
echo "  Ground truth execution time captured."
echo "  Injection delay: ${INJECTION_DELAY}s"
echo ""

# --- Phase 1: Guard-agent ---
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Phase 1: Guard-agent (OpenCode with guard-agent MCP)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
set +e
"$SCRIPT_DIR/run_iterative.sh" $MAX_ITERS_FLAG \
  --injection-delay "$INJECTION_DELAY" \
  --ground-truth-dir "$GROUND_TRUTH_DIR" \
  "$APP_NAME"
GUARDAGENT_EXIT=$?
set -e
echo ""

# --- Phase 2: Without guard-agent ---
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Phase 2: Without guard-agent (OpenCode alone)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
set +e
"$SCRIPT_DIR/run_iterative.sh" --baseline $MAX_ITERS_FLAG \
  --injection-delay "$INJECTION_DELAY" \
  --ground-truth-dir "$GROUND_TRUTH_DIR" \
  "$APP_NAME"
BASELINE_EXIT=$?
set -e
echo ""

# --- Phase 3: Comparison ---
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Phase 3: Comparison"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
"$SCRIPT_DIR/run_compare.sh" "$APP_NAME"
echo ""

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  Evaluation complete: $APP_NAME"
echo "║  Guard-agent exit:  $GUARDAGENT_EXIT $([ $GUARDAGENT_EXIT -eq 0 ] && echo '(PASS)' || echo '(FAIL)')"
echo "║  Baseline exit:     $BASELINE_EXIT $([ $BASELINE_EXIT -eq 0 ] && echo '(PASS)' || echo '(FAIL)')"
echo "║  Report: build/validation_output/comparison_${APP_NAME}.md"
echo "╚══════════════════════════════════════════════════════════════════════╝"
