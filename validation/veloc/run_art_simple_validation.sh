#!/usr/bin/env bash
# Run the full VeloC validation pipeline for art_simple vs veloc_art_simple.
#
# Baseline (original):  tests/examples/original/art_simple  (or build/examples/art_simple)
# Resilient:            build/examples_output/resilient_art_simple
#
# Usage (from repo root):
#   ./validation/veloc/run_art_simple_validation.sh [--skip-benchmarks] [--skip-report]
#
# Optional environment variables:
#   ORIGINAL_DIR   – path to the original codebase (default: build/examples/art_simple)
#   RESILIENT_DIR  – path to the resilient codebase (default: build/examples_output/resilient_art_simple)
#   DATA_PATH      – path to the HDF5 input file    (default: build/data/tooth_preprocessed.h5)
#                    (exported so benchmark JSON config can expand ${DATA_PATH:-...})
#   NUM_PROCS      – number of MPI ranks             (default: 4)
#   OUTPUT_DIR     – validation output directory     (default: build/validation_output/art_simple)
#   NUM_RUNS       – override benchmark repetitions for ALL scenarios (unset by default;
#                    when unset, each scenario uses its own num_runs from the JSON config;
#                    set to 1 for a quick smoke-test: NUM_RUNS=1 ./run_art_simple_validation.sh)
#
# Benchmark scenarios are defined in:
#   validation/veloc/benchmark_configs/art_simple.json
# Each scenario specifies its own num_runs, num_procs, app_args, and failure injection settings.
# NUM_RUNS (if set) takes priority over per-scenario num_runs in the JSON.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# Activate virtualenv if available (created by ./setup.sh).
if [[ -d "build/venv" ]]; then
  # shellcheck disable=SC1091
  source "build/venv/bin/activate"

  # Ensure validation Python dependencies are installed (matplotlib, numpy, etc.)
  REQS="${REPO_ROOT}/validation/requirements.txt"
  if [[ -f "${REQS}" ]]; then
    pip install -q -r "${REQS}"
  fi
fi

export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"

# ---------------------------------------------------------------------------
# Pre-flight: verify required external tools are available
# ---------------------------------------------------------------------------
MISSING_TOOLS=()
for tool in cmake mpirun; do
  if ! command -v "$tool" &>/dev/null; then
    MISSING_TOOLS+=("$tool")
  fi
done
if [[ ${#MISSING_TOOLS[@]} -gt 0 ]]; then
  echo ""
  echo "======================================================================" >&2
  echo "[run] ERROR: Required tool(s) not found: ${MISSING_TOOLS[*]}" >&2
  echo "" >&2
  echo "  Ensure these are installed and available in your PATH." >&2
  echo "  On HPC systems you may need to run:  module load cmake openmpi" >&2
  echo "  Current PATH: ${PATH}" >&2
  echo "======================================================================" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Configurable paths and parameters
# ---------------------------------------------------------------------------
ORIGINAL_DIR="${ORIGINAL_DIR:-${REPO_ROOT}/build/examples/art_simple}"
RESILIENT_DIR="${RESILIENT_DIR:-${REPO_ROOT}/build/examples_output/resilient_art_simple}"
# Export DATA_PATH so the benchmark JSON config can expand ${DATA_PATH:-...} via os.environ.
export DATA_PATH="${DATA_PATH:-${REPO_ROOT}/build/data/tooth_preprocessed.h5}"
NUM_PROCS="${NUM_PROCS:-4}"
OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/build/validation_output/art_simple}"

BENCHMARK_CONFIG="${REPO_ROOT}/validation/veloc/benchmark_configs/art_simple.json"
APPROACHES_CONFIG="${REPO_ROOT}/validation/veloc/benchmark_configs/art_simple_approaches.json"

COMMON_ARGS="${DATA_PATH} 294.078 5 2 0 4"

STATE_FILE="${OUTPUT_DIR}/pipeline_state.json"

# ---------------------------------------------------------------------------
# Detect incomplete previous run and ask user what to do
# ---------------------------------------------------------------------------
RESUME_FLAG=""

if [[ -f "${STATE_FILE}" ]]; then
  # Check if the run is already finished (has "finished": true in the JSON).
  if python3 -c "
import json, sys
state = json.load(open('${STATE_FILE}'))
sys.exit(0 if state.get('finished') else 1)
" 2>/dev/null; then
    echo ""
    echo "============================================================"
    echo "  A previous validation run in:"
    echo "    ${OUTPUT_DIR}"
    echo "  completed successfully."
    echo "============================================================"
    echo ""
    echo "Options:"
    echo "  [1] Re-run graphical report only  (skip correctness + benchmarks)"
    echo "  [2] Start a fresh run             (deletes previous output)"
    echo "  [3] Exit (keep previous results)"
    echo ""
    read -rp "Your choice [1/2/3]: " CHOICE
    case "${CHOICE}" in
      1)
        echo "[run] Re-running graphical report stage only..."
        RESUME_FLAG="--resume --skip-correctness --skip-benchmarks"
        # Clear the 'report' stage from state so validate.py will re-run it.
        python3 -c "
import json
p = '${STATE_FILE}'
state = json.load(open(p))
state['completed_stages'] = [s for s in state.get('completed_stages', []) if s != 'report']
state['finished'] = False
json.dump(state, open(p, 'w'), indent=2)
"
        ;;
      2)
        echo "[run] Removing previous output directory: ${OUTPUT_DIR}"
        rm -rf "${OUTPUT_DIR}"
        ;;
      *)
        echo "[run] Exiting. Previous results are preserved in ${OUTPUT_DIR}"
        exit 0
        ;;
    esac
  else
    # Incomplete previous run found.
    COMPLETED=$(python3 -c "
import json, sys
try:
    state = json.load(open('${STATE_FILE}'))
    stages = state.get('completed_stages', [])
    print(', '.join(stages) if stages else '(none)')
except Exception:
    print('(unknown)')
" 2>/dev/null || echo "(unknown)")

    LAST_UPDATED=$(python3 -c "
import json, sys
try:
    state = json.load(open('${STATE_FILE}'))
    print(state.get('last_updated') or state.get('started_at') or '(unknown)')
except Exception:
    print('(unknown)')
" 2>/dev/null || echo "(unknown)")

    echo ""
    echo "============================================================"
    echo "  An INCOMPLETE previous validation run was found in:"
    echo "    ${OUTPUT_DIR}"
    echo "  Last updated : ${LAST_UPDATED}"
    echo "  Completed    : ${COMPLETED}"
    echo "============================================================"
    echo ""
    echo "Options:"
    echo "  [1] Resume from last completed stage"
    echo "  [2] Start a completely fresh run  (deletes previous output)"
    echo "  [3] Exit (do nothing)"
    echo ""
    read -rp "Your choice [1/2/3]: " CHOICE
    case "${CHOICE}" in
      1)
        echo "[run] Resuming previous run..."
        RESUME_FLAG="--resume"
        ;;
      2)
        echo "[run] Removing previous output directory: ${OUTPUT_DIR}"
        rm -rf "${OUTPUT_DIR}"
        ;;
      3)
        echo "[run] Exiting. Previous run is preserved in ${OUTPUT_DIR}"
        exit 0
        ;;
      *)
        echo "[run] Invalid choice. Exiting."
        exit 1
        ;;
    esac
  fi
fi

# ---------------------------------------------------------------------------
# Build optional --benchmark-num-runs flag (only when NUM_RUNS is set).
# When NUM_RUNS is set it overrides per-scenario num_runs in the JSON config.
# When NUM_RUNS is unset, per-scenario num_runs from the JSON is used.
# ---------------------------------------------------------------------------
NUM_RUNS_FLAG=""
if [[ -n "${NUM_RUNS:-}" ]]; then
  NUM_RUNS_FLAG="--benchmark-num-runs ${NUM_RUNS}"
fi

# ---------------------------------------------------------------------------
# Auto-detect comparison approaches
# ---------------------------------------------------------------------------
APPROACHES_FLAG=""
if [[ -f "${APPROACHES_CONFIG}" ]]; then
  APPROACHES_FLAG="--approaches-config ${APPROACHES_CONFIG}"
fi

# ---------------------------------------------------------------------------
# Run the validation framework
# ---------------------------------------------------------------------------
echo ""
echo "[run] Configuration:"
echo "  ORIGINAL_DIR     : ${ORIGINAL_DIR}"
echo "  RESILIENT_DIR    : ${RESILIENT_DIR}"
if [[ -n "${APPROACHES_FLAG}" ]]; then
  echo "  APPROACHES_CONFIG: ${APPROACHES_CONFIG}"
fi
echo "  NUM_PROCS        : ${NUM_PROCS}"
echo "  BENCHMARK_CONFIG : ${BENCHMARK_CONFIG}"
if [[ -n "${NUM_RUNS:-}" ]]; then
  echo "  NUM_RUNS         : ${NUM_RUNS}  (overrides per-scenario num_runs in JSON)"
else
  echo "  NUM_RUNS         : (unset – using per-scenario num_runs from JSON)"
fi
echo "  OUTPUT_DIR       : ${OUTPUT_DIR}"
echo ""

python -m validation.veloc.validate \
  "${ORIGINAL_DIR}" \
  "${RESILIENT_DIR}" \
  --executable-name art_simple_main \
  --num-procs "${NUM_PROCS}" \
  --original-args "${COMMON_ARGS}" \
  --resilient-args "${COMMON_ARGS}" \
  --output-dir "${OUTPUT_DIR}" \
  --comparison-method ssim \
  --ssim-threshold 0.9999 \
  --hdf5-dataset data \
  --output-file-name recon.h5 \
  --max-attempts 10 \
  --injection-delay 10.0 \
  --install-resilient \
  --veloc-config-name veloc.cfg \
  --benchmark-config "${BENCHMARK_CONFIG}" \
  ${NUM_RUNS_FLAG} \
  ${RESUME_FLAG} \
  ${APPROACHES_FLAG} \
  "$@"
