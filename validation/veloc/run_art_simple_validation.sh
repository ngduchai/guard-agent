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
#   DATA_PATH      – path to the HDF5 input file    (default: data/tooth_preprocessed.h5)
#   NUM_PROCS      – number of MPI ranks             (default: 4)
#   OUTPUT_DIR     – validation output directory     (default: build/validation_output/art_simple)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# Activate virtualenv if available (created by ./setup.sh).
if [[ -d "build/venv" ]]; then
  # shellcheck disable=SC1091
  source "build/venv/bin/activate"
fi

export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"

# ---------------------------------------------------------------------------
# Configurable paths and parameters
# ---------------------------------------------------------------------------
ORIGINAL_DIR="${ORIGINAL_DIR:-${REPO_ROOT}/build/examples/art_simple}"
RESILIENT_DIR="${RESILIENT_DIR:-${REPO_ROOT}/build/examples_output/resilient_art_simple}"
DATA_PATH="${DATA_PATH:-${REPO_ROOT}/build/data/tooth_preprocessed.h5}"
NUM_PROCS="${NUM_PROCS:-4}"
OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/build/validation_output/art_simple}"

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
# Run the validation framework
# ---------------------------------------------------------------------------
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
  ${RESUME_FLAG} \
  "$@"
