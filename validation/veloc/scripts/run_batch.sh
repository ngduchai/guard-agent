#!/usr/bin/env bash
# Clean up child processes on exit to prevent zombies after Ctrl+C
_batch_cleanup() {
  pkill -9 -P $$ 2>/dev/null || true
  pkill -9 -f "mpirun|mpiexec|orted|failure_injector.py" 2>/dev/null || true
}
trap _batch_cleanup EXIT INT TERM

# Run validation for multiple applications from a file list.
#
# Usage:
#   ./run_batch.sh <app_list_file> [options]
#
# Options:
#   --mode <evaluate|iterative|validate>   Pipeline to run (default: evaluate)
#   --baseline                             Run baseline only (no guard-agent)
#   --guard-agent                          Run guard-agent only (default for iterative)
#   --max-iters N                          Max iterations per app (default: 5)
#   --continue                             Skip apps that already have results
#   --dry-run                              Show what would run, don't execute
#
# App list file format (one app per line, # comments, blank lines ignored):
#   # Fast apps
#   CoMD
#   miniVite
#   miniFE
#   # Slow apps
#   LAMMPS
#   AMReX
#
# Predefined app lists (create with --generate-list):
#   ./run_batch.sh --generate-list all     > apps_all.txt
#   ./run_batch.sh --generate-list fast    > apps_fast.txt
#   ./run_batch.sh --generate-list medium  > apps_medium.txt
#
# Examples:
#   # Run full evaluation (baseline + guard-agent + compare) for all apps in file
#   ./run_batch.sh apps.txt
#
#   # Run only guard-agent iterative loop
#   ./run_batch.sh apps.txt --mode iterative --guard-agent
#
#   # Run only baseline iterative loop
#   ./run_batch.sh apps.txt --mode iterative --baseline
#
#   # Resume from where we left off
#   ./run_batch.sh apps.txt --continue
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BUILD_DIR="$REPO_ROOT/build"

# --- Defaults ---
MODE="evaluate"
APPROACH=""
MAX_ITERS=10
CONTINUE=false
DRY_RUN=false
APP_LIST_FILE=""
EXTRA_ARGS=""

# --- App ordering (shortest → longest build time) ---
# Only apps with native checkpoint/restart in their reference code.
ALL_APPS_ORDERED=(
  CoMD miniVite CLAMR SW4lite VPIC
  Athena++ OpenLB LAMMPS SU2 SAMRAI AMReX WarpX
)

FAST_APPS=(CoMD miniVite CLAMR SW4lite VPIC Athena++)
MEDIUM_APPS=(OpenLB LAMMPS SU2)
HEAVY_APPS=(SAMRAI AMReX WarpX)

# --- Parse arguments ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)         MODE="$2"; shift 2 ;;
    --baseline)     APPROACH="--baseline"; shift ;;
    --reference)    APPROACH="--reference"; shift ;;
    --guard-agent)  APPROACH=""; shift ;;
    --max-iters)    MAX_ITERS="$2"; shift 2 ;;
    --continue)     CONTINUE=true; shift ;;
    --dry-run)      DRY_RUN=true; shift ;;
    --generate-list)
      case "${2:-all}" in
        all)    printf '%s\n' "${ALL_APPS_ORDERED[@]}" ;;
        fast)   printf '%s\n' "${FAST_APPS[@]}" ;;
        medium) printf '%s\n' "${MEDIUM_APPS[@]}" ;;
        heavy)  printf '%s\n' "${HEAVY_APPS[@]}" ;;
        *)      echo "Unknown list: $2. Use: all, fast, medium, heavy" >&2; exit 1 ;;
      esac
      exit 0 ;;
    -h|--help)
      sed -n '2,/^set -euo/{ /^#/s/^# \?//p }' "$0"; exit 0 ;;
    --)
      shift; EXTRA_ARGS="$*"; break ;;
    *)
      if [[ -z "$APP_LIST_FILE" ]]; then
        APP_LIST_FILE="$1"
      else
        # Collect unrecognized flags to forward to the runner script
        EXTRA_ARGS="${EXTRA_ARGS:+$EXTRA_ARGS }$1"
      fi
      shift ;;
  esac
done

if [[ -z "$APP_LIST_FILE" ]]; then
  echo "Usage: $0 <app_list_file> [options]" >&2
  echo "  Run '$0 --help' for details." >&2
  echo "  Generate a list: $0 --generate-list all > apps.txt" >&2
  exit 1
fi

if [[ ! -f "$APP_LIST_FILE" ]]; then
  echo "ERROR: App list file not found: $APP_LIST_FILE" >&2
  exit 1
fi

# --- Read app list (strip comments and blank lines) ---
mapfile -t APPS < <(grep -v '^\s*#' "$APP_LIST_FILE" | grep -v '^\s*$' | sed 's/^\s*//;s/\s*$//')

if [[ ${#APPS[@]} -eq 0 ]]; then
  echo "ERROR: No apps found in $APP_LIST_FILE" >&2
  exit 1
fi

# --- Resolve runner script ---
case "$MODE" in
  evaluate)  RUNNER="$SCRIPT_DIR/run_evaluate.sh" ;;
  iterative) RUNNER="$SCRIPT_DIR/run_iterative.sh" ;;
  validate)  RUNNER="$SCRIPT_DIR/run_validate.sh" ;;
  *)         echo "ERROR: Unknown mode '$MODE'. Use: evaluate, iterative, validate" >&2; exit 1 ;;
esac

# Also check generated runner scripts in build/
if [[ ! -f "$RUNNER" ]]; then
  case "$MODE" in
    evaluate)  RUNNER="$BUILD_DIR/run_evaluate.sh" ;;
    iterative) RUNNER="$BUILD_DIR/run_iterative.sh" ;;
    validate)  RUNNER="$BUILD_DIR/run_validate.sh" ;;
  esac
fi

if [[ ! -f "$RUNNER" ]]; then
  echo "ERROR: Runner script not found: $RUNNER" >&2
  echo "  Run ./setup.sh --clean first." >&2
  exit 1
fi

# --- Check if app already has results (for --continue) ---
_has_results() {
  local app="$1"
  case "$MODE" in
    evaluate)
      # Both baseline and guard-agent results exist
      [[ -f "$BUILD_DIR/iterative_logs/${app}_guard-agent/result.json" ]] && \
      [[ -f "$BUILD_DIR/iterative_logs/${app}_baseline/result.json" ]]
      ;;
    iterative)
      if [[ -n "$APPROACH" ]]; then
        [[ -f "$BUILD_DIR/iterative_logs/${app}_baseline/result.json" ]]
      else
        [[ -f "$BUILD_DIR/iterative_logs/${app}_guard-agent/result.json" ]]
      fi
      ;;
    validate)
      case "$APPROACH" in
        --baseline)   [[ -d "$BUILD_DIR/validation_output/${app}_baseline" ]] ;;
        --reference)  [[ -d "$BUILD_DIR/validation_output/${app}_reference" ]] ;;
        *)            [[ -d "$BUILD_DIR/validation_output/${app}" ]] ;;
      esac
      ;;
  esac
}

# --- Build runner command ---
_build_cmd() {
  local app="$1"
  local cmd="$RUNNER"

  case "$MODE" in
    evaluate)
      cmd="$cmd $app --max-iters $MAX_ITERS"
      ;;
    iterative)
      cmd="$cmd $APPROACH $app --max-iters $MAX_ITERS"
      ;;
    validate)
      cmd="$cmd $APPROACH $app"
      ;;
  esac

  # Forward any extra flags to the runner script
  if [[ -n "$EXTRA_ARGS" ]]; then
    cmd="$cmd $EXTRA_ARGS"
  fi

  echo "$cmd"
}

# --- Main ---
echo "════════════════════════════════════════════════════════════════════"
echo "  Batch validation runner"
echo "  Mode:     $MODE"
echo "  Approach: ${APPROACH:-both (evaluate)}"
echo "  Apps:     ${#APPS[@]} from $APP_LIST_FILE"
echo "  Max iter: $MAX_ITERS"
echo "  Continue: $CONTINUE"
[[ -n "$EXTRA_ARGS" ]] && echo "  Extra:    $EXTRA_ARGS"
echo "════════════════════════════════════════════════════════════════════"
echo ""

passed=0
failed=0
skipped=0
total=${#APPS[@]}

for i in "${!APPS[@]}"; do
  app="${APPS[$i]}"
  idx=$((i + 1))

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  [$idx/$total] $app"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  # Skip if --continue and results exist
  if $CONTINUE && _has_results "$app"; then
    echo "  [SKIP] Results already exist for $app"
    ((skipped++)) || true
    echo ""
    continue
  fi

  # Re-copy source from original for incomplete apps so that
  # modifications left by a previously interrupted OpenCode run
  # do not poison the next attempt.
  if $CONTINUE; then
    for _src_root in "$REPO_ROOT/tests/apps/vanillas" "$REPO_ROOT/tests/ecp/vanillas" "$REPO_ROOT/tests/examples/original"; do
      if [ -d "$_src_root/$app" ]; then
        # Only refresh the directory that this run will actually use
        case "$APPROACH" in
          --baseline) _dests=("$BUILD_DIR/tests_baseline/$app") ;;
          "")
            if [ "$MODE" = "evaluate" ]; then
              _dests=("$BUILD_DIR/tests/$app" "$BUILD_DIR/tests_baseline/$app")
            else
              _dests=("$BUILD_DIR/tests/$app")
            fi ;;
        esac
        for _dest in "${_dests[@]}"; do
          if [ -d "$_dest" ]; then
            echo "  [REFRESH] Re-copying $app → $(basename "$(dirname "$_dest")")"
            rm -rf "$_dest"
            cp -a "$_src_root/$app" "$_dest"
          fi
        done
        break
      fi
    done
  fi

  # Kill any stray processes from a previous app before starting the next one
  pkill -9 -f "mpirun|mpiexec|orted|failure_injector.py" 2>/dev/null || true

  cmd=$(_build_cmd "$app")

  if $DRY_RUN; then
    echo "  [DRY-RUN] Would run: $cmd"
    echo ""
    continue
  fi

  start_time=$(date +%s)
  if eval "$cmd"; then
    elapsed=$(( $(date +%s) - start_time ))
    echo "  [PASS] $app completed in ${elapsed}s"
    ((passed++)) || true
  else
    elapsed=$(( $(date +%s) - start_time ))
    echo "  [FAIL] $app failed after ${elapsed}s"
    ((failed++)) || true
  fi
  echo ""
done

echo "════════════════════════════════════════════════════════════════════"
echo "  Batch complete: $passed passed, $failed failed, $skipped skipped (of $total)"
echo "════════════════════════════════════════════════════════════════════"

exit $failed
