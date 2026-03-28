#!/usr/bin/env bash
# ============================================================================
# test_mana_aurora.sh – MANA checkpoint/restart test for art_simple on Aurora
#
# Purpose:
#   Test MANA (MPI-Agnostic Network-Agnostic) transparent checkpoint/restart
#   with the statically-linked art_simple binary on ALCF Aurora.
#
# Prerequisites:
#   - art_simple_main built with DMTCP_STATIC_MPI=ON (no libmpi.so dependency)
#   - MANA installed via scripts/install_dmtcp_mana.sh
#   - HDF5 input data file (tooth_preprocessed.h5)
#
# Usage:
#   Option A – Interactive (on a compute node allocation):
#     qsub -I -l select=1 -l walltime=00:30:00 -A <project> -q debug
#     bash tests/examples/dmtcp/art_simple/test_mana_aurora.sh
#
#   Option B – Batch submission:
#     qsub tests/examples/dmtcp/art_simple/test_mana_aurora.sh
#
#   Option C – Direct run on a compute node (already allocated):
#     bash tests/examples/dmtcp/art_simple/test_mana_aurora.sh
#
# Environment variables (all optional):
#   DATA_PATH          – HDF5 input file
#   MANA_ROOT          – MANA source/build directory
#   NUM_PROCS          – number of MPI ranks (default: 1)
#   CHECKPOINT_DELAY   – seconds before checkpoint (default: 10)
#   TIMEOUT            – max seconds per phase (default: 300)
#   COORD_PORT         – coordinator port (default: 7901)
#   SKIP_COORDINATOR   – set to 1 if coordinator is already running
# ============================================================================
#PBS -l select=1
#PBS -l walltime=00:30:00
#PBS -l filesystems=home
#PBS -q debug
#PBS -j oe
#PBS -N mana_art_simple_test

set -euo pipefail

# If running under PBS, cd to the submission directory
if [[ -n "${PBS_O_WORKDIR:-}" ]]; then
    cd "${PBS_O_WORKDIR}"
fi

# ── Locate repo root ─────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

# ── Configuration ─────────────────────────────────────────────────────────
DATA_PATH="${DATA_PATH:-${REPO_ROOT}/build/data/tooth_preprocessed.h5}"
NUM_PROCS="${NUM_PROCS:-1}"
CHECKPOINT_DELAY="${CHECKPOINT_DELAY:-10}"
TIMEOUT="${TIMEOUT:-300}"
COORD_PORT="${COORD_PORT:-7901}"
SKIP_COORDINATOR="${SKIP_COORDINATOR:-0}"

# App arguments: <hdf5_input> <center> <num_outer_iter> <num_iter> <beg_index> <num_sino>
# Medium workload to ensure app runs long enough for checkpoint
APP_ARGS="${DATA_PATH} 294.078 5 2 0 2"

# Working directories
BUILD_DIR="${REPO_ROOT}/build/validation_output/art_simple/build/dmtcp"
OUTPUT_DIR="${REPO_ROOT}/build/test_mana/output"
CKPT_DIR="${REPO_ROOT}/build/test_mana/ckpt"

# ── Locate MANA ──────────────────────────────────────────────────────────
if [[ -n "${MANA_ROOT:-}" ]]; then
    MANA_BIN="${MANA_ROOT}/bin"
elif [[ -d "${HOME}/.local/share/guard-agent/dmtcp-src/mana" ]]; then
    MANA_ROOT="${HOME}/.local/share/guard-agent/dmtcp-src/mana"
    MANA_BIN="${MANA_ROOT}/bin"
elif [[ -x "${HOME}/.local/bin/mana_launch" ]]; then
    MANA_BIN="${HOME}/.local/bin"
    MANA_ROOT="${HOME}/.local"
else
    MANA_BIN="$(dirname "$(which mana_launch 2>/dev/null)" 2>/dev/null || true)"
    MANA_ROOT="$(dirname "${MANA_BIN}" 2>/dev/null || true)"
fi

if [[ -z "${MANA_BIN}" ]] || [[ ! -x "${MANA_BIN}/mana_launch" ]]; then
    echo "ERROR: mana_launch not found. Install MANA first:" >&2
    echo "  ./scripts/install_dmtcp_mana.sh" >&2
    echo "" >&2
    echo "Searched:" >&2
    echo "  \$MANA_ROOT/bin" >&2
    echo "  ~/.local/share/guard-agent/dmtcp-src/mana/bin" >&2
    echo "  ~/.local/bin" >&2
    echo "  \$PATH" >&2
    exit 1
fi

MANA_LAUNCH="${MANA_BIN}/mana_launch"
MANA_START_COORD="${MANA_BIN}/mana_start_coordinator"
MANA_RESTART="${MANA_BIN}/mana_restart"

# Also need dmtcp_command for checkpoint triggering
DMTCP_COMMAND="${MANA_BIN}/dmtcp_command"
if [[ ! -x "${DMTCP_COMMAND}" ]]; then
    # Try the DMTCP install prefix
    if [[ -f "${HOME}/.local/share/guard-agent/dmtcp_prefix" ]]; then
        DMTCP_PREFIX="$(cat "${HOME}/.local/share/guard-agent/dmtcp_prefix")"
        DMTCP_COMMAND="${DMTCP_PREFIX}/bin/dmtcp_command"
    elif [[ -x "${HOME}/.local/bin/dmtcp_command" ]]; then
        DMTCP_COMMAND="${HOME}/.local/bin/dmtcp_command"
    fi
fi

echo "============================================================"
echo "  MANA Checkpoint/Restart Test for art_simple on Aurora"
echo "============================================================"
echo ""
echo "[config] MANA_ROOT       : ${MANA_ROOT}"
echo "[config] MANA_BIN        : ${MANA_BIN}"
echo "[config] mana_launch     : ${MANA_LAUNCH}"
echo "[config] mana_coordinator: ${MANA_START_COORD}"
echo "[config] mana_restart    : ${MANA_RESTART}"
echo "[config] dmtcp_command   : ${DMTCP_COMMAND}"
echo "[config] DATA_PATH       : ${DATA_PATH}"
echo "[config] NUM_PROCS       : ${NUM_PROCS}"
echo "[config] CKPT_DELAY      : ${CHECKPOINT_DELAY}s"
echo "[config] TIMEOUT         : ${TIMEOUT}s"
echo "[config] BUILD_DIR       : ${BUILD_DIR}"
echo "[config] CKPT_DIR        : ${CKPT_DIR}"
echo "[config] COORD_PORT      : ${COORD_PORT}"
echo "[config] APP_ARGS        : ${APP_ARGS}"
echo ""

# ── Verify prerequisites ─────────────────────────────────────────────────
if [[ ! -x "${BUILD_DIR}/art_simple_main" ]]; then
    echo "ERROR: Executable not found: ${BUILD_DIR}/art_simple_main" >&2
    echo "  Build it first with:" >&2
    echo "    cd ${BUILD_DIR}" >&2
    echo "    cmake ~/diaspora/guard-agent/build/example_refs/dmtcp/art_simple -DDMTCP_STATIC_MPI=ON" >&2
    echo "    make" >&2
    exit 1
fi

# Verify no libmpi.so dependency
if ldd "${BUILD_DIR}/art_simple_main" 2>/dev/null | grep -q "libmpi\.so"; then
    echo "WARNING: art_simple_main still links libmpi.so dynamically!" >&2
    echo "  MANA requires static MPI linking. Rebuild with -DDMTCP_STATIC_MPI=ON" >&2
    echo "  Continuing anyway, but MANA may crash..." >&2
    echo ""
fi

if [[ ! -f "${DATA_PATH}" ]]; then
    echo "ERROR: HDF5 data file not found: ${DATA_PATH}" >&2
    echo "  Copy or symlink tooth_preprocessed.h5 to that location." >&2
    exit 1
fi

for tool in "${MANA_LAUNCH}" "${MANA_START_COORD}" "${DMTCP_COMMAND}"; do
    if [[ ! -x "${tool}" ]]; then
        echo "ERROR: Required tool not found or not executable: ${tool}" >&2
        exit 1
    fi
done

# ── Cleanup function ─────────────────────────────────────────────────────
cleanup() {
    echo ""
    echo "[cleanup] Stopping coordinator on port ${COORD_PORT} ..."
    "${DMTCP_COMMAND}" --port "${COORD_PORT}" --quit 2>/dev/null || true
    pkill -f "dmtcp_coordinator.*--port ${COORD_PORT}" 2>/dev/null || true
    pkill -f "art_simple_main" 2>/dev/null || true
}
trap cleanup EXIT

# ── Step 1: Clean previous state ─────────────────────────────────────────
rm -rf "${CKPT_DIR}" "${OUTPUT_DIR}"
mkdir -p "${CKPT_DIR}" "${OUTPUT_DIR}"

# ── Step 2: Start MANA coordinator ───────────────────────────────────────
# Kill any existing coordinator on this port
"${DMTCP_COMMAND}" --port "${COORD_PORT}" --quit 2>/dev/null || true
sleep 0.5

if [[ "${SKIP_COORDINATOR}" == "1" ]]; then
    echo "[coord] SKIP_COORDINATOR=1, assuming coordinator already running on port ${COORD_PORT}"
else
    echo "[coord] Starting MANA coordinator on port ${COORD_PORT} ..."
    # mana_start_coordinator is a wrapper that starts dmtcp_coordinator
    # with the MANA plugin loaded
    "${MANA_START_COORD}" --port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1 || {
        echo "[coord] mana_start_coordinator failed, trying manual start..."
        # Fallback: start coordinator manually with MANA plugin
        MANA_PLUGIN="${MANA_ROOT}/lib/dmtcp/libmana.so"
        if [[ ! -f "${MANA_PLUGIN}" ]]; then
            # Try finding it in the build tree
            MANA_PLUGIN="$(find "${MANA_ROOT}" -name 'libmana.so' -type f 2>/dev/null | head -1)"
        fi
        if [[ -n "${MANA_PLUGIN}" ]] && [[ -f "${MANA_PLUGIN}" ]]; then
            echo "[coord] Using MANA plugin: ${MANA_PLUGIN}"
            "${MANA_BIN}/dmtcp_coordinator" --daemon --port "${COORD_PORT}" \
                --ckptdir "${CKPT_DIR}" 2>&1 || true
        else
            echo "ERROR: Cannot find libmana.so plugin" >&2
            exit 1
        fi
    }
    sleep 1
fi

# Verify coordinator is running
if "${DMTCP_COMMAND}" --port "${COORD_PORT}" --status 2>/dev/null; then
    echo "[coord] Coordinator is running."
else
    echo "WARNING: Could not verify coordinator status (may still be starting)" >&2
fi
echo ""

# ── Step 3: Set environment ──────────────────────────────────────────────
# Disable hwloc Linux I/O to prevent block device enumeration crashes
export HWLOC_COMPONENTS="-linuxio"

# ── Step 4: Launch app under MANA ────────────────────────────────────────
# MANA launch procedure:
#   mpiexec -np N mana_launch [--ckptdir DIR] [--coord-port PORT] ./app args
#
# On Aurora, use mpiexec (Cray MPICH launcher).
# mana_launch wraps the application with MANA's split-process architecture.

LAUNCH_CMD="mpiexec -np ${NUM_PROCS} ${MANA_LAUNCH} --coord-port ${COORD_PORT} --ckptdir ${CKPT_DIR} --no-gzip ${BUILD_DIR}/art_simple_main ${APP_ARGS}"

echo "[launch] Command:"
echo "  ${LAUNCH_CMD}"
echo ""
echo "[launch] Starting app under MANA ..."
echo ""

${LAUNCH_CMD} \
    > "${OUTPUT_DIR}/stdout_initial.txt" \
    2> "${OUTPUT_DIR}/stderr_initial.txt" &
APP_PID=$!

echo "[launch] Wrapper PID: ${APP_PID}"

# ── Step 5: Wait, then checkpoint ─────────────────────────────────────────
echo "[ckpt] Waiting ${CHECKPOINT_DELAY}s before triggering checkpoint ..."
sleep "${CHECKPOINT_DELAY}"

# Check if app is still running
if ! kill -0 "${APP_PID}" 2>/dev/null; then
    WAIT_EXIT=0
    wait "${APP_PID}" || WAIT_EXIT=$?
    echo ""
    echo "[result] App finished BEFORE checkpoint (exit code: ${WAIT_EXIT})"
    echo ""
    echo "--- stdout ---"
    cat "${OUTPUT_DIR}/stdout_initial.txt" 2>/dev/null || true
    echo ""
    echo "--- stderr ---"
    cat "${OUTPUT_DIR}/stderr_initial.txt" 2>/dev/null || true
    echo ""
    if [[ "${WAIT_EXIT}" -eq 0 ]]; then
        echo "============================================================"
        echo "  App completed successfully WITHOUT checkpoint."
        echo "  Increase CHECKPOINT_DELAY or workload size to test ckpt."
        echo "============================================================"
    else
        echo "============================================================"
        echo "  App FAILED (exit=${WAIT_EXIT}) before checkpoint."
        echo "  Check stderr above for details."
        echo "============================================================"
    fi
    exit "${WAIT_EXIT}"
fi

echo "[ckpt] Triggering MANA/DMTCP checkpoint ..."
CKPT_START=$(date +%s%N)
if timeout "${TIMEOUT}" "${DMTCP_COMMAND}" --port "${COORD_PORT}" --checkpoint; then
    CKPT_END=$(date +%s%N)
    CKPT_MS=$(( (CKPT_END - CKPT_START) / 1000000 ))
    echo "[ckpt] Checkpoint completed in ${CKPT_MS}ms"
else
    echo "[ckpt] WARNING: Checkpoint command failed or timed out!"
    echo "[ckpt] stderr from initial run:"
    tail -20 "${OUTPUT_DIR}/stderr_initial.txt" 2>/dev/null || true
fi

# List checkpoint files
echo "[ckpt] Checkpoint files:"
find "${CKPT_DIR}" -name "ckpt_*.dmtcp" -exec ls -lh {} \; 2>/dev/null || echo "  (none found)"
echo ""

# ── Step 6: Kill the app (simulate failure) ───────────────────────────────
echo "[kill] Killing app process (simulating failure) ..."
ART_PID=$(pgrep -f "art_simple_main" 2>/dev/null | head -1 || true)
if [[ -n "${ART_PID}" ]]; then
    echo "[kill] Found art_simple_main PID: ${ART_PID}"
    kill -9 "${ART_PID}" 2>/dev/null || true
else
    echo "[kill] art_simple_main not found, killing wrapper PID ${APP_PID}"
    kill -9 "${APP_PID}" 2>/dev/null || true
fi

wait "${APP_PID}" 2>/dev/null || true
sleep 2
echo "[kill] Process terminated."
echo ""

# ── Step 7: Restart from checkpoint ──────────────────────────────────────
CKPT_FILES=$(find "${CKPT_DIR}" -name "ckpt_*.dmtcp" 2>/dev/null | head -1 || true)
RESTART_SCRIPT=$(find "${CKPT_DIR}" -name "dmtcp_restart_script*.sh" 2>/dev/null | head -1 || true)

if [[ -z "${CKPT_FILES}" ]] && [[ -z "${RESTART_SCRIPT}" ]]; then
    echo "============================================================"
    echo "  RESULT: FAILED – No checkpoint files found!"
    echo "  The checkpoint did not produce any files."
    echo ""
    echo "  Possible causes:"
    echo "    - MANA plugin not loaded correctly"
    echo "    - Coordinator not running"
    echo "    - App crashed before checkpoint"
    echo ""
    echo "  Initial run stderr:"
    cat "${OUTPUT_DIR}/stderr_initial.txt" 2>/dev/null || true
    echo "============================================================"
    exit 1
fi

echo "[restart] Restarting from checkpoint ..."

# MANA restart: use mana_restart which wraps dmtcp_restart with the
# MANA plugin for MPI re-initialization
if [[ -x "${MANA_RESTART}" ]]; then
    RESTART_CMD="mpiexec -np ${NUM_PROCS} ${MANA_RESTART} --coord-port ${COORD_PORT} --ckptdir ${CKPT_DIR} --no-gzip"
else
    # Fallback to restart script
    RESTART_CMD="bash ${RESTART_SCRIPT}"
fi

echo "[restart] Command: ${RESTART_CMD}"
RESTART_START=$(date +%s)

timeout "${TIMEOUT}" ${RESTART_CMD} \
    > "${OUTPUT_DIR}/stdout_restart.txt" \
    2> "${OUTPUT_DIR}/stderr_restart.txt"
RESTART_EXIT=$?

RESTART_END=$(date +%s)
RESTART_ELAPSED=$((RESTART_END - RESTART_START))

echo ""
echo "[restart] Restart completed: exit=${RESTART_EXIT}, elapsed=${RESTART_ELAPSED}s"

# ── Step 8: Report results ───────────────────────────────────────────────
echo ""
echo "============================================================"
echo "  RESULTS"
echo "============================================================"
echo ""
echo "--- Initial run stdout (last 20 lines) ---"
tail -20 "${OUTPUT_DIR}/stdout_initial.txt" 2>/dev/null || echo "(empty)"
echo ""
echo "--- Initial run stderr (last 20 lines) ---"
tail -20 "${OUTPUT_DIR}/stderr_initial.txt" 2>/dev/null || echo "(empty)"
echo ""
echo "--- Restart stdout (last 20 lines) ---"
tail -20 "${OUTPUT_DIR}/stdout_restart.txt" 2>/dev/null || echo "(empty)"
echo ""
echo "--- Restart stderr (last 20 lines) ---"
tail -20 "${OUTPUT_DIR}/stderr_restart.txt" 2>/dev/null || echo "(empty)"
echo ""

# Check for output file
for d in "${OUTPUT_DIR}" "${BUILD_DIR}" "."; do
    if [[ -f "${d}/recon.h5" ]]; then
        echo "[output] recon.h5 found in ${d} – reconstruction completed!"
        break
    fi
done

if [[ "${RESTART_EXIT}" -eq 0 ]]; then
    echo ""
    echo "============================================================"
    echo "  RESULT: SUCCESS"
    echo "  MANA checkpoint/restart works on Aurora!"
    echo "============================================================"
else
    echo ""
    echo "============================================================"
    echo "  RESULT: FAILED (restart exit code: ${RESTART_EXIT})"
    echo "  Check stderr output above for details."
    echo "============================================================"
fi

exit "${RESTART_EXIT}"
