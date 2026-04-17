#!/usr/bin/env bash
set -e

# Usage: ./run_validate.sh [--baseline] <app_name> [extra validate.py args...]
#
# Validates agent-modified code against the original unmodified source.
# App-specific settings (executable name, args, comparison method) are loaded
# from validation/veloc/app_configs/<app_name>.json.
#
# Modes:
#   ./run_validate.sh art_simple              # validate build/tests/art_simple
#   ./run_validate.sh --baseline art_simple   # validate build/tests_baseline/art_simple
#
# The injection delay defaults to 'auto' (computed from baseline runtime).
# Override with: --injection-delay 10.0
#
# Examples:
#   ./validation/veloc/scripts/run_validate.sh art_simple
#   ./validation/veloc/scripts/run_validate.sh --baseline art_simple --skip-benchmarks

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BUILD_DIR="$REPO_ROOT/build"

# Activate venv
if [ -f "$BUILD_DIR/venv/bin/activate" ]; then
  . "$BUILD_DIR/venv/bin/activate"
fi
export PYTHONPATH="${REPO_ROOT}"

# --- Parse approach flag ---
USE_BASELINE=false
USE_REFERENCE=false
if [ "${1:-}" = "--baseline" ]; then
  USE_BASELINE=true
  shift
elif [ "${1:-}" = "--reference" ]; then
  USE_REFERENCE=true
  shift
fi

APP_NAME="${1:?Usage: run_validate.sh [--baseline] <app_name> [extra args...]}"
shift

# --- Load per-app config ---
APP_CONFIG="$REPO_ROOT/validation/veloc/app_configs/${APP_NAME}.json"
APP_YAML=""

# Check for app.yaml in the 20-app set
for _yaml_dir in "$REPO_ROOT/tests/apps/vanillas/$APP_NAME" \
                 "$BUILD_DIR/tests/$APP_NAME" \
                 "$BUILD_DIR/tests_baseline/$APP_NAME"; do
  if [ -f "$_yaml_dir/app.yaml" ]; then
    APP_YAML="$_yaml_dir/app.yaml"
    break
  fi
done

_read_yaml() {
  # Read a field from app.yaml using yaml_to_config.py helper.
  python3 -m validation.veloc.yaml_to_config "$APP_YAML" "$1" 2>/dev/null
}

_read_config() {
  # Read a value from the app config JSON. Returns empty string if not found.
  python3 -c "
import json, os, sys
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
    print('')
" 2>/dev/null
}

_read_comparison_flags() {
  # Build comparison CLI flags from the app config.
  python3 -c "
import json, sys
try:
    cfg = json.load(open('$APP_CONFIG'))
    comp = cfg.get('comparison', {})
    flags = []
    if comp.get('method'):
        flags.extend(['--comparison-method', comp['method']])
    if comp.get('ssim_threshold') is not None:
        flags.extend(['--ssim-threshold', str(comp['ssim_threshold'])])
    if comp.get('hdf5_dataset'):
        flags.extend(['--hdf5-dataset', comp['hdf5_dataset']])
    if comp.get('output_file_name'):
        flags.extend(['--output-file-name', comp['output_file_name']])
    print(' '.join(flags))
except (FileNotFoundError, KeyError):
    print('--comparison-method hash')
" 2>/dev/null
}

_set_env_defaults() {
  # Export env_defaults from app config (only if not already set).
  python3 -c "
import json, os
try:
    cfg = json.load(open('$APP_CONFIG'))
    for k, v in cfg.get('env_defaults', {}).items():
        if k not in os.environ:
            # Resolve relative paths against BUILD_DIR
            val = v if os.path.isabs(v) else os.path.join('$BUILD_DIR', v)
            print(f'export {k}=\"{val}\"')
except (FileNotFoundError, KeyError):
    pass
" 2>/dev/null
}

# --- Resolve executable name ---
EXE_NAME=""
APP_ARGS=""
COMPARISON="--comparison-method hash"

if [ -f "$APP_CONFIG" ]; then
  # JSON config takes priority (legacy 5-app format)
  EXE_NAME=$(_read_config "executable_name")
  eval "$(_set_env_defaults)"
  APP_ARGS=$(_read_config "app_args")
  COMPARISON=$(_read_comparison_flags)
elif [ -n "$APP_YAML" ]; then
  # Fall back to app.yaml (20-app format)
  EXE_NAME=$(_read_yaml "executable_name")
  APP_ARGS=$(_read_yaml "app_args")
  COMPARISON=$(_read_yaml "comparison_flags")
  ORIGINAL_BUILD_CMD=$(_read_yaml "build_cmd")
  RESILIENT_BUILD_CMD=$(_read_yaml "ckpt_build_cmd")
fi

# Fallback: try to extract from CMakeLists.txt
if [ -z "$EXE_NAME" ]; then
  RESILIENT_SRC_TMP="$BUILD_DIR/tests/$APP_NAME"
  [ "$USE_BASELINE" = true ] && RESILIENT_SRC_TMP="$BUILD_DIR/tests_baseline/$APP_NAME"
  CMAKE_FILE="$RESILIENT_SRC_TMP/CMakeLists.txt"
  if [ -f "$CMAKE_FILE" ]; then
    EXE_NAME=$(grep -oP 'add_executable\s*\(\s*\K\S+' "$CMAKE_FILE" 2>/dev/null | head -1)
  fi
fi
# Final fallback
[ -z "$EXE_NAME" ] && EXE_NAME="$APP_NAME"

# --- Resolve original source directory ---
ORIGINAL_SRC=""
if [ -d "$REPO_ROOT/tests/examples/original/$APP_NAME" ]; then
  ORIGINAL_SRC="$REPO_ROOT/tests/examples/original/$APP_NAME"
elif [ -d "$REPO_ROOT/tests/ecp/vanillas/$APP_NAME" ]; then
  ORIGINAL_SRC="$REPO_ROOT/tests/ecp/vanillas/$APP_NAME"
elif [ -d "$REPO_ROOT/tests/apps/vanillas/$APP_NAME" ]; then
  ORIGINAL_SRC="$REPO_ROOT/tests/apps/vanillas/$APP_NAME"
else
  echo "ERROR: Original source not found for '$APP_NAME'." >&2
  echo "  Checked: tests/examples/original/$APP_NAME" >&2
  echo "  Checked: tests/ecp/vanillas/$APP_NAME" >&2
  echo "  Checked: tests/apps/vanillas/$APP_NAME" >&2
  exit 1
fi

# --- Resilient source (agent-modified or reference) ---
if [ "$USE_REFERENCE" = true ]; then
  RESILIENT_SRC="$REPO_ROOT/tests/apps/checkpointed/$APP_NAME"
  LABEL="reference (human-written)"
elif [ "$USE_BASELINE" = true ]; then
  RESILIENT_SRC="$BUILD_DIR/tests_baseline/$APP_NAME"
  LABEL="baseline (no guard-agent)"
else
  RESILIENT_SRC="$BUILD_DIR/tests/$APP_NAME"
  LABEL="with guard-agent"
fi
if [ ! -d "$RESILIENT_SRC" ]; then
  echo "ERROR: Resilient source not found at $RESILIENT_SRC" >&2
  exit 1
fi

# --- Resolve benchmark config if available ---
BENCH_CONFIG=""
BENCH_FILE="$REPO_ROOT/validation/veloc/benchmark_configs/${APP_NAME}.json"
if [ -f "$BENCH_FILE" ]; then
  BENCH_CONFIG="--benchmark-config $BENCH_FILE"
fi

# --- Output directory ---
if [ "$USE_REFERENCE" = true ]; then
  OUTPUT_DIR="$BUILD_DIR/validation_output/${APP_NAME}_reference"
elif [ "$USE_BASELINE" = true ]; then
  OUTPUT_DIR="$BUILD_DIR/validation_output/${APP_NAME}_baseline"
else
  OUTPUT_DIR="$BUILD_DIR/validation_output/$APP_NAME"
fi

echo "════════════════════════════════════════════════════════════════════"
echo "  Validating: $APP_NAME ($LABEL)"
echo "════════════════════════════════════════════════════════════════════"
echo "  Original:  $ORIGINAL_SRC"
echo "  Resilient: $RESILIENT_SRC"
echo "  Executable: $EXE_NAME"
echo "  Output:    $OUTPUT_DIR"
echo ""

# Build the validation command
CMD="python -m validation.veloc.validate \
  \"$ORIGINAL_SRC\" \
  \"$RESILIENT_SRC\" \
  --executable-name \"$EXE_NAME\" \
  --output-dir \"$OUTPUT_DIR\" \
  --install-resilient \
  $COMPARISON \
  $BENCH_CONFIG"

# Append original/resilient args if set
if [ -n "$APP_ARGS" ]; then
  CMD="$CMD --original-args \"$APP_ARGS\" --resilient-args \"$APP_ARGS\""
fi

# Append any extra user args
if [ $# -gt 0 ]; then
  CMD="$CMD $*"
fi

# Write build commands to temp files to avoid shell quoting issues
# (build commands can contain nested quotes like CFLAGS="-O3 -Wno-unused-result")
_ORIG_BUILD_FILE=""
_RES_BUILD_FILE=""
if [ -n "${ORIGINAL_BUILD_CMD:-}" ]; then
  _ORIG_BUILD_FILE=$(mktemp)
  echo "$ORIGINAL_BUILD_CMD" > "$_ORIG_BUILD_FILE"
  CMD="$CMD --original-build-cmd @$_ORIG_BUILD_FILE"
fi
if [ -n "${RESILIENT_BUILD_CMD:-}" ]; then
  _RES_BUILD_FILE=$(mktemp)
  echo "$RESILIENT_BUILD_CMD" > "$_RES_BUILD_FILE"
  CMD="$CMD --resilient-build-cmd @$_RES_BUILD_FILE"
fi

# Kill any leftover child processes on exit (Ctrl+C, error, or normal exit).
# Prevents zombie mpirun/app processes from consuming resources after an
# interrupted benchmark run.
_cleanup() {
  # Kill all descendant processes of this script
  pkill -9 -P $$ 2>/dev/null || true
  # Also kill by executable name in case they were re-parented
  if [ -n "${EXE_NAME:-}" ]; then
    pkill -9 -f "$EXE_NAME" 2>/dev/null || true
  fi
  pkill -9 -f "failure_injector.py" 2>/dev/null || true
  [ -n "${_ORIG_BUILD_FILE:-}" ] && rm -f "$_ORIG_BUILD_FILE"
  [ -n "${_RES_BUILD_FILE:-}" ] && rm -f "$_RES_BUILD_FILE"
}
trap _cleanup EXIT INT TERM

# Kill leftover processes from a previous interrupted run before starting
if [ -n "${EXE_NAME:-}" ]; then
  pkill -9 -f "$EXE_NAME" 2>/dev/null || true
fi
pkill -9 -f "mpirun|mpiexec|orted|failure_injector.py" 2>/dev/null || true

eval $CMD
_exit=$?

exit $_exit
