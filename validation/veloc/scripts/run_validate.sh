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
# Cold-replay detector (auto-enabled when tests/apps/configs/<APP>.yaml
# declares a perturbation: block — currently SAMRAI + Nyx).  Tune via:
#   --perturbation-fractions=25,50,75   override the slope-test kill fractions
#   --no-perturbation                   force-disable per-app perturbation
#
# Examples:
#   ./validation/veloc/scripts/run_validate.sh art_simple
#   ./validation/veloc/scripts/run_validate.sh --baseline art_simple --skip-benchmarks
#   ./validation/veloc/scripts/run_validate.sh --baseline SAMRAI --perturbation-fractions=25,50,75

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
USE_AUDIT_VANILLA=false
if [ "${1:-}" = "--baseline" ]; then
  USE_BASELINE=true
  shift
elif [ "${1:-}" = "--reference" ]; then
  USE_REFERENCE=true
  shift
elif [ "${1:-}" = "--audit-vanilla" ]; then
  # Audit mode: validate the vanilla against itself.  We expect the failure-free
  # run to PASS (vanilla works) and the failure-injected run's resilience proof
  # to FAIL (vanilla cannot recover).  This proves the vanilla is properly
  # stripped of all checkpoint capability before we use it as the agent's input.
  USE_AUDIT_VANILLA=true
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
  RESILIENT_EXE=$(_read_yaml "ckpt_executable_name")
  APP_ARGS=$(_read_yaml "app_args")
  COMPARISON=$(_read_yaml "comparison_flags")
  ORIGINAL_BUILD_CMD=$(_read_yaml "build_cmd")
  RESILIENT_BUILD_CMD=$(_read_yaml "ckpt_build_cmd")
  NUM_PROCS_FROM_YAML=$(_read_yaml "num_procs")
  APP_INPUT_SUBDIR=$(_read_yaml "app_input_subdir")
  INJECTION_DELAY_FROM_YAML=$(_read_yaml "injection_delay")
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
elif [ "$USE_AUDIT_VANILLA" = true ]; then
  # Point "resilient" at the same vanilla source so the failure-injected run
  # exercises the unmodified code; if it actually recovers we know the vanilla
  # still has hidden checkpoint capability.
  RESILIENT_SRC="$ORIGINAL_SRC"
  LABEL="audit (vanilla vs vanilla)"
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
elif [ "$USE_AUDIT_VANILLA" = true ]; then
  OUTPUT_DIR="$BUILD_DIR/audit_output/$APP_NAME"
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

# Reference-mode benchmarks: force vanilla input files to take precedence over
# the reference checkpointed code's own.  Reference upstream inputs are tuned
# for tiny demo scales (e.g. Athena++ blast: 1 mesh block) and fail or run a
# different workload than vanilla under our scenarios.
#
# If a per-app reference input patch exists at tests/apps/patches/<APP>/, we
# also build a tmp overlay (vanilla + patch) and pass it as the highest-
# priority input source.  This injects the extra parameters needed to enable
# the reference's native checkpoint mechanism (e.g. <output3> file_type=rst
# for Athena++) so the resilient run actually writes checkpoint files we can
# measure.  See tests/apps/patches/README.md for the convention.
_REF_OVERLAY_DIR=""
if [ "$USE_REFERENCE" = true ]; then
  # Reference apps use their NATIVE checkpoint mechanism (e.g. ROSS RIO,
  # SAMRAI restart, HDF5 plotfiles), NOT VeloC.  None ship a veloc.cfg.
  # The correctness stage's checkpoint-observed strategy requires veloc.cfg
  # (runner.py raises ValidationError otherwise — added 2026-04-28).
  # All 16 prior successful reference runs have stages=['benchmarks','report']
  # — correctness was always skipped.  Match that pattern.  Reference
  # benchmarks use inject_failures=false scenarios so they don't need
  # checkpoint-observed either; only failure-free wallclock + checkpoint
  # size are measured.
  CMD="$CMD --reference-input-priority --skip-correctness"
  _REF_PATCH_DIR="$REPO_ROOT/tests/apps/patches/$APP_NAME"
  if [ -d "$_REF_PATCH_DIR" ]; then
    _REF_OVERLAY_DIR=$(mktemp -d -t "ref_input_overlay.${APP_NAME}.XXXXXX")
    # Layer vanilla first (full input tree), then patch (sparse, overwrites).
    cp -a "$ORIGINAL_SRC/." "$_REF_OVERLAY_DIR/"
    cp -a "$_REF_PATCH_DIR/." "$_REF_OVERLAY_DIR/"
    CMD="$CMD --reference-input-overlay-dir $_REF_OVERLAY_DIR"
    echo "  Reference input overlay: $_REF_OVERLAY_DIR"
    echo "    (vanilla + patches from $_REF_PATCH_DIR)"
  fi
  # Reference-only env vars: bulk-output pruning, etc.
  case "$APP_NAME" in
    WarpX)
      # WarpX writes 30-50 GB of AMReX chkpoint files PER run.  With 3
      # nofail runs × 2 codebases that is up to ~300 GB concurrent — exceeds
      # typical disk budgets.  Enable PRUNE_BENCH_ARTIFACTS so the
      # metrics_collector deletes the bulk under benchmarks/.../run_N/diags
      # immediately after the run's elapsed/checkpoint metrics are persisted
      # to benchmark_progress.json.  Trust-gate inspection still has stdout/
      # stderr.  Recorded numbers are unaffected.
      #
      # WarpX-only by deliberate user decision: other apps' run-output is
      # small enough to keep around for inspection.  Do NOT add other apps
      # to this branch without re-confirming.
      export PRUNE_BENCH_ARTIFACTS=1
      echo "  Reference env: PRUNE_BENCH_ARTIFACTS=1 (heavy AMReX checkpoint output, WarpX-only)"
      ;;
  esac
fi

# Workload-pin env vars: applied UNIVERSALLY (vanilla baseline, reference,
# LLM-baseline, audit) so vanilla and the comparison binary run the same
# numerical workload.  Without this, vanilla auto-computes a different
# iteration count than reference (HPCG: numberOfCgSets via opt_worst_time)
# and the bench comparison silently runs different workloads.
#
# Vanilla source has been edited to also read these env vars (HPCG
# tests/apps/vanillas/HPCG/src/main.cpp) — they are workload knobs, not
# checkpoint code, so they don't violate the vanilla-strip invariant.
# Other binaries that don't read them (LLM baseline, audit's vanilla)
# harmlessly ignore the env var.
case "$APP_NAME" in
  HPCG)
    # HPCG: pin numberOfCgSets so vanilla and reference run identical
    # workloads + reference's checkpoint format stays dimension-stable
    # across kill/restart pairs.  CKPT_EVERY is reference-only-relevant
    # (vanilla lacks the checkpoint code path) but harmless if exported.
    export CKPT_EVERY=10
    export HPCG_FIXED_SETS=180
    echo "  Workload-pin env (universal): CKPT_EVERY=$CKPT_EVERY HPCG_FIXED_SETS=$HPCG_FIXED_SETS"
    ;;
  PRK_Stencil)
    # PRK Stencil: CKPT_EVERY only controls checkpoint cadence, not
    # workload size.  Exporting universally is harmless to vanilla.
    # 2026-05-16: bumped 1000 -> 10000 per longer-interval sweep that
    # showed thrashing kicks in around 5+ ckpts. At 33000-iter run with
    # CKPT_EVERY=10000: 3 ckpts x ~256MB = ~768MB I/O — well below
    # thrashing threshold. Probe wall = 246.19s vs vanilla 249.28s
    # (zero overhead). Sweep data:
    # build/_experiment_state/prk_longer_interval_sweep.log.
    # Use ":=" so external CKPT_EVERY (e.g., from a manual probe) wins.
    : "${CKPT_EVERY:=10000}"
    export CKPT_EVERY
    echo "  Workload-pin env (universal): CKPT_EVERY=$CKPT_EVERY"
    ;;
esac

# Per-app stdout truncation env (HyPar Fix B, 2026-05-03).  Apps that
# emit hundreds of MB of stdout per run cause OOM when the runner reads
# the full file into a Python string for the RunResult.stdout field.
# Bound the in-memory copy to the last N lines (on-disk file is
# unchanged — streaming comparator reads from disk).
case "$APP_NAME" in
  HyPar)
    # HyPar's n_iter=2.5M produces 375 MB stdout per run.  Per-step output
    # ('iter=N t=X ...') × 2.5M lines.  Last 1000 lines covers the
    # 'Completed time integration', 'L1 Error', 'L2 Error', 'Linfinity Error'
    # signature plus generous margin.
    export BENCH_STDOUT_TRUNCATE_LINES=1000
    echo "  Stdout truncation: BENCH_STDOUT_TRUNCATE_LINES=$BENCH_STDOUT_TRUNCATE_LINES (HyPar 375MB stdout OOM mitigation)"
    ;;
esac
# Make sure the overlay is cleaned up when run_validate.sh exits.
_cleanup_overlay() {
  if [ -n "$_REF_OVERLAY_DIR" ] && [ -d "$_REF_OVERLAY_DIR" ]; then
    rm -rf "$_REF_OVERLAY_DIR"
  fi
}
trap _cleanup_overlay EXIT INT TERM

# When the resilient build produces a different binary name than vanilla
# (e.g. ROSS: vanilla 'phold' vs resilient 'pholdio'), pass it explicitly.
# RESILIENT_EXE (read from app.yaml's ckpt_executable field) only applies when
# the resilient codebase is the upstream REFERENCE checkpointed source — that's
# where the variant-binary lives (e.g. ROSS reference uses `pholdio` from its
# native RIO model; vanilla and LLM-baseline only have `phold`).
# In --baseline mode the LLM-modified code is built from vanilla source which
# does NOT contain the variant-binary target, so passing this flag would force
# the LLM to invent infrastructure it doesn't have access to (saw this break
# ROSS_baseline iter 1 with `make: *** No rule to make target 'pholdio'`).
# In --audit-vanilla mode the resilient side IS the vanilla, also has no variant.
if [ "$USE_REFERENCE" = true ] && [ -n "${RESILIENT_EXE:-}" ] && [ "$RESILIENT_EXE" != "$EXE_NAME" ]; then
  CMD="$CMD --resilient-executable-name \"$RESILIENT_EXE\""
fi

# Append original/resilient args if set
if [ -n "$APP_ARGS" ]; then
  CMD="$CMD --original-args \"$APP_ARGS\" --resilient-args \"$APP_ARGS\""
fi

# Pass num_procs from app.yaml so apps with restrictive rank counts (e.g.
# HyPar's 1D/FPDoubleWell example pinned to iproc=1) honor that in the
# correctness stage.  Benchmarks already drive their own num_procs via the
# per-scenario JSON.
if [ -n "${NUM_PROCS_FROM_YAML:-}" ]; then
  CMD="$CMD --num-procs $NUM_PROCS_FROM_YAML"
fi

# Pass app_input_subdir so the runner knows where to find input data files
# for apps whose run.cmd starts with `cd <subdir> && mpirun ...` (SPARTA,
# SPPARKS, HyPar, OpenLB, MMSP, QMCPACK).  The contents of that subdirectory
# are flattened into the per-run cwd so the binary finds inputs by simple
# cwd-relative names.
if [ -n "${APP_INPUT_SUBDIR:-}" ]; then
  CMD="$CMD --app-input-subdir \"$APP_INPUT_SUBDIR\""
fi

# Pass per-app injection_delay override when set in app.yaml (run.injection_delay).
# Useful when the adaptive 1/3-of-baseline default would overshoot the resilient
# run because system load makes baseline much slower than resilient (CLAMR).
# Skip if user already supplied --injection-delay on the command line.
if [ -n "${INJECTION_DELAY_FROM_YAML:-}" ] && ! [[ "$*" =~ "--injection-delay" ]]; then
  CMD="$CMD --injection-delay $INJECTION_DELAY_FROM_YAML"
fi

# In audit-vanilla mode the resilient source is the same vanilla, so the
# resilient build command must match the original.  Without this override the
# resilient side would either lack a build command or pick up a stale
# ckpt_build_cmd from app.yaml (none should exist on a properly-stripped
# vanilla, but be defensive).  We also force the report/benchmark stages off
# since the audit only cares about correctness + the resilience proof, and we
# discard per-app injection_delay overrides — those are tuned for production
# runs (often early kills to stress recovery) and would defeat the audit's
# 0.95×baseline late-kill policy that makes the wall-time bound discriminating.
if [ "$USE_AUDIT_VANILLA" = true ]; then
  RESILIENT_BUILD_CMD="$ORIGINAL_BUILD_CMD"
  INJECTION_DELAY_FROM_YAML=""
  # --vanilla-audit switches the correctness stage to Validation A
  # (accuracy vs reference + non-recovery signal); validate.py auto-derives
  # the reference path from tests/apps/vanillas/<APP> → tests/apps/checkpointed/<APP>.
  CMD="$CMD --skip-benchmarks --skip-report --vanilla-audit"
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
  pkill -9 -f "failure_injector.py" 2>/dev/null || true
  [ -n "${_ORIG_BUILD_FILE:-}" ] && rm -f "$_ORIG_BUILD_FILE"
  [ -n "${_RES_BUILD_FILE:-}" ] && rm -f "$_RES_BUILD_FILE"
}
trap _cleanup EXIT INT TERM

# Kill leftover MPI/injector processes from a previous interrupted run.
# Note: we do NOT pkill by $EXE_NAME because that pattern can match
# the current shell script's own command line (e.g. "miniVite" in
# "run_validate.sh --reference miniVite"), causing self-kill.
pkill -9 -f "mpirun|mpiexec|orted|failure_injector.py" 2>/dev/null || true

# Quote $CMD so embedded `"   pattern   "` (multi-space-leading patterns from
# app.yaml's keep_patterns) survive word-splitting.  Without quotes bash drops
# the inner double-quotes during word-split, collapsing leading whitespace and
# breaking apps whose stable comparison line is identified by indentation
# (LAMMPS' "      2000", SPARTA's "   20000").
eval "$CMD"
_exit=$?

exit $_exit
