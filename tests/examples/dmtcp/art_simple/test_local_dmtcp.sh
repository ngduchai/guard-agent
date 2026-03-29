#!/usr/bin/env bash
# ============================================================================
# test_local_dmtcp.sh – Local single-process DMTCP test for art_simple
#
# Purpose:
#   Reproduce the hang observed during DMTCP/MANA validation on remote nodes,
#   but on the LOCAL node with a SINGLE MPI process and MANA DISABLED.
#   This isolates whether the hang is caused by:
#     (a) DMTCP itself (checkpoint/restart of the process), or
#     (b) MANA / multi-node MPI interaction.
#
# What it does:
#   1. Builds art_simple with DYNAMIC MPI linking (no static MPI / no MANA).
#   2. Starts a dmtcp_coordinator.
#   3. Launches the app under dmtcp_launch with mpirun -np 1 (local only).
#   4. After a configurable delay, triggers a DMTCP checkpoint.
#   5. Kills the process (simulating failure).
#   6. Restarts from the checkpoint.
#   7. Reports success/failure and timing.
#
# Usage (from repo root):
#   bash tests/examples/dmtcp/art_simple/test_local_dmtcp.sh
#
# Environment variables:
#   DATA_PATH          – HDF5 input file (default: build/data/tooth_preprocessed.h5)
#   DMTCP_PREFIX       – DMTCP install prefix (default: auto-detect from marker)
#   CHECKPOINT_DELAY   – seconds to wait before checkpoint (default: 5)
#   TIMEOUT            – max seconds for each phase (default: 120)
#   SKIP_BUILD         – set to 1 to skip the build step
# ============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Configuration ─────────────────────────────────────────────────────────
DATA_PATH="${DATA_PATH:-${REPO_ROOT}/build/data/tooth_preprocessed.h5}"
CHECKPOINT_DELAY="${CHECKPOINT_DELAY:-5}"
TIMEOUT="${TIMEOUT:-120}"
SKIP_BUILD="${SKIP_BUILD:-0}"
DMTCP_DEBUG="${DMTCP_DEBUG:-0}"

# App arguments: <hdf5_input> <center> <num_outer_iter> <num_iter> <beg_index> <num_sino>
# Using medium workload (num_outer_iter=5, num_iter=2, num_sino=2) to ensure
# the app runs long enough for checkpoint to trigger.
APP_ARGS="${DATA_PATH} 294.078 5 2 0 2"

# Working directories
BUILD_DIR="${REPO_ROOT}/build/test_local_dmtcp/art_simple"
OUTPUT_DIR="${REPO_ROOT}/build/test_local_dmtcp/output"
CKPT_DIR="${REPO_ROOT}/build/test_local_dmtcp/ckpt"
COORD_PORT=7799

echo "============================================================"
echo "  DMTCP Local Single-Process Test for art_simple"
echo "  (MANA disabled – dynamic MPI linking, 1 process, local)"
echo "============================================================"
echo ""

# ── Locate DMTCP tools ───────────────────────────────────────────────────
if [[ -n "${DMTCP_PREFIX:-}" ]]; then
    DMTCP_BIN="${DMTCP_PREFIX}/bin"
elif [[ -f "${HOME}/.local/share/guard-agent/dmtcp_prefix" ]]; then
    DMTCP_BIN="$(cat "${HOME}/.local/share/guard-agent/dmtcp_prefix")/bin"
elif [[ -x "${HOME}/.local/bin/dmtcp_launch" ]]; then
    DMTCP_BIN="${HOME}/.local/bin"
else
    DMTCP_BIN="$(dirname "$(which dmtcp_launch 2>/dev/null)" 2>/dev/null || true)"
fi

if [[ -z "${DMTCP_BIN}" ]] || [[ ! -x "${DMTCP_BIN}/dmtcp_launch" ]]; then
    echo "ERROR: dmtcp_launch not found. Install DMTCP first:" >&2
    echo "  ./scripts/install_dmtcp_mana.sh" >&2
    exit 1
fi

DMTCP_LAUNCH="${DMTCP_BIN}/dmtcp_launch"
DMTCP_COORDINATOR="${DMTCP_BIN}/dmtcp_coordinator"
DMTCP_COMMAND="${DMTCP_BIN}/dmtcp_command"
DMTCP_RESTART="${DMTCP_BIN}/dmtcp_restart"

echo "[config] DMTCP tools    : ${DMTCP_BIN}"
echo "[config] DATA_PATH      : ${DATA_PATH}"
echo "[config] CKPT_DELAY     : ${CHECKPOINT_DELAY}s"
echo "[config] TIMEOUT        : ${TIMEOUT}s"
echo "[config] BUILD_DIR      : ${BUILD_DIR}"
echo "[config] CKPT_DIR       : ${CKPT_DIR}"
echo "[config] COORD_PORT     : ${COORD_PORT}"
echo "[config] APP_ARGS       : ${APP_ARGS}"
echo ""

# ── Verify data file exists ──────────────────────────────────────────────
if [[ ! -f "${DATA_PATH}" ]]; then
    echo "ERROR: HDF5 data file not found: ${DATA_PATH}" >&2
    echo "  Copy or symlink tooth_preprocessed.h5 to that location." >&2
    exit 1
fi

# ── Cleanup function ─────────────────────────────────────────────────────
cleanup() {
    echo ""
    echo "[cleanup] Stopping coordinator on port ${COORD_PORT} ..."
    "${DMTCP_COMMAND}" --port "${COORD_PORT}" --quit 2>/dev/null || true
    # Kill any leftover processes
    pkill -f "dmtcp_coordinator.*--port ${COORD_PORT}" 2>/dev/null || true
    pkill -f "art_simple_main" 2>/dev/null || true
}
trap cleanup EXIT

# ── Step 1: Build with DYNAMIC MPI (no MANA) ─────────────────────────────
if [[ "${SKIP_BUILD}" == "1" ]] && [[ -x "${BUILD_DIR}/art_simple_main" ]]; then
    echo "[build] SKIP_BUILD=1 and executable exists, skipping build."
else
    echo "[build] Building art_simple with DYNAMIC MPI (DMTCP_STATIC_MPI=OFF) ..."
    mkdir -p "${BUILD_DIR}"
    cmake -S "${SCRIPT_DIR}" -B "${BUILD_DIR}" \
        -DDMTCP_STATIC_MPI=OFF \
        -DCMAKE_BUILD_TYPE=Release 2>&1 | tail -5
    cmake --build "${BUILD_DIR}" -j"$(nproc)" 2>&1 | tail -5
    echo "[build] Done. Executable: ${BUILD_DIR}/art_simple_main"
fi
echo ""

if [[ ! -x "${BUILD_DIR}/art_simple_main" ]]; then
    echo "ERROR: Build failed – executable not found: ${BUILD_DIR}/art_simple_main" >&2
    exit 1
fi

# ── Step 2: Clean previous checkpoint data ────────────────────────────────
rm -rf "${CKPT_DIR}" "${OUTPUT_DIR}"
mkdir -p "${CKPT_DIR}" "${OUTPUT_DIR}"

# ── Step 3: Start DMTCP coordinator ──────────────────────────────────────
# Kill any existing coordinator on this port first
"${DMTCP_COMMAND}" --port "${COORD_PORT}" --quit 2>/dev/null || true
sleep 0.5

echo "[coord] Starting dmtcp_coordinator on port ${COORD_PORT} ..."
"${DMTCP_COORDINATOR}" --daemon --port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" --quiet
sleep 1

# Verify coordinator is running
if ! "${DMTCP_COMMAND}" --port "${COORD_PORT}" --status 2>/dev/null; then
    echo "ERROR: dmtcp_coordinator failed to start on port ${COORD_PORT}" >&2
    exit 1
fi
echo "[coord] Coordinator is running."
echo ""

# ── Step 4: Launch app under DMTCP (single process, no MANA) ─────────────
# Key differences from the validation runner:
#   - Uses dmtcp_launch directly (no --with-plugin mana)
#   - mpirun -np 1 (single local process)
#   - Dynamic MPI linking (no static libmpi.a)
#
# IMPORTANT: We do NOT wrap mpirun under dmtcp_launch.
# Instead, we use mpirun to launch "dmtcp_launch <app>".
# Wrapping mpirun itself causes DMTCP to intercept hwloc's topology
# discovery which opens block devices like /dev/nvme0n1, triggering:
#   "JASSERT(false) failed; Unimplemented file type."
#
# Additionally, we disable hwloc's Linux I/O component to prevent
# any residual block-device enumeration inside the MPI rank process.
export HWLOC_COMPONENTS="-linuxio"

LAUNCH_CMD="mpirun --oversubscribe -np 1 ${DMTCP_LAUNCH} --coord-port ${COORD_PORT} --no-gzip ${BUILD_DIR}/art_simple_main ${APP_ARGS}"

echo "[launch] Command: ${LAUNCH_CMD}"
echo "[launch] Starting app ..."
echo ""

${LAUNCH_CMD} \
    > "${OUTPUT_DIR}/stdout_initial.txt" \
    2> "${OUTPUT_DIR}/stderr_initial.txt" &
APP_PID=$!

echo "[launch] App PID (dmtcp_launch wrapper): ${APP_PID}"

# ── Step 5: Wait, then checkpoint ─────────────────────────────────────────
echo "[ckpt] Waiting ${CHECKPOINT_DELAY}s before triggering checkpoint ..."
sleep "${CHECKPOINT_DELAY}"

# Check if app is still running
if ! kill -0 "${APP_PID}" 2>/dev/null; then
    WAIT_EXIT=0
    wait "${APP_PID}" || WAIT_EXIT=$?
    echo ""
    echo "[result] App finished BEFORE checkpoint (exit code: ${WAIT_EXIT})"
    echo "[result] This means the workload is too short for the checkpoint delay."
    echo "[result] stdout:"
    cat "${OUTPUT_DIR}/stdout_initial.txt"
    echo ""
    echo "[result] stderr:"
    cat "${OUTPUT_DIR}/stderr_initial.txt"
    echo ""
    if [[ "${WAIT_EXIT}" -eq 0 ]]; then
        echo "============================================================"
        echo "  RESULT: App completed successfully WITHOUT checkpoint."
        echo "  The hang is NOT in basic DMTCP launch."
        echo "  Try increasing CHECKPOINT_DELAY or workload size."
        echo "============================================================"
    else
        echo "============================================================"
        echo "  RESULT: App FAILED (exit=${WAIT_EXIT}) before checkpoint."
        echo "  Check stderr above for details."
        echo "============================================================"
    fi
    exit "${WAIT_EXIT}"
fi

echo "[ckpt] Triggering DMTCP checkpoint ..."
CKPT_START=$(date +%s%N)
if timeout "${TIMEOUT}" "${DMTCP_COMMAND}" --port "${COORD_PORT}" --checkpoint; then
    CKPT_END=$(date +%s%N)
    CKPT_MS=$(( (CKPT_END - CKPT_START) / 1000000 ))
    echo "[ckpt] Checkpoint completed in ${CKPT_MS}ms"
else
    echo "[ckpt] WARNING: Checkpoint command failed or timed out!"
fi

# List checkpoint files
echo "[ckpt] Checkpoint files:"
ls -lh "${CKPT_DIR}"/ckpt_*.dmtcp 2>/dev/null || echo "  (none found)"
echo ""

# ── Step 6: Kill the app (simulate failure) ───────────────────────────────
echo "[kill] Killing app process ..."
# Find the actual art_simple_main process
ART_PID=$(pgrep -f "art_simple_main" 2>/dev/null | head -1 || true)
if [[ -n "${ART_PID}" ]]; then
    echo "[kill] Found art_simple_main PID: ${ART_PID}"
    kill -9 "${ART_PID}" 2>/dev/null || true
else
    echo "[kill] art_simple_main process not found, killing wrapper PID ${APP_PID}"
    kill -9 "${APP_PID}" 2>/dev/null || true
fi

# Wait for mpirun/dmtcp_launch to exit
wait "${APP_PID}" 2>/dev/null || true
sleep 1
echo "[kill] Process terminated."
echo ""

# ── Step 7: Restart from checkpoint ──────────────────────────────────────
CKPT_FILES=$(ls "${CKPT_DIR}"/ckpt_*.dmtcp 2>/dev/null || true)
RESTART_SCRIPT="${CKPT_DIR}/dmtcp_restart_script.sh"

if [[ -z "${CKPT_FILES}" ]] && [[ ! -f "${RESTART_SCRIPT}" ]]; then
    echo "============================================================"
    echo "  RESULT: FAILED – No checkpoint files found!"
    echo "  The checkpoint did not produce any files."
    echo "============================================================"
    exit 1
fi

echo "[restart] Restarting from checkpoint ..."
if [[ -f "${RESTART_SCRIPT}" ]]; then
    RESTART_CMD="bash ${RESTART_SCRIPT}"
else
    RESTART_CMD="${DMTCP_RESTART} --coord-port ${COORD_PORT} ${CKPT_FILES}"
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
tail -20 "${OUTPUT_DIR}/stdout_initial.txt"
echo ""
echo "--- Initial run stderr (last 10 lines) ---"
tail -10 "${OUTPUT_DIR}/stderr_initial.txt"
echo ""
echo "--- Restart stdout (last 20 lines) ---"
tail -20 "${OUTPUT_DIR}/stdout_restart.txt"
echo ""
echo "--- Restart stderr (last 10 lines) ---"
tail -10 "${OUTPUT_DIR}/stderr_restart.txt"
echo ""

# Check for output file
if [[ -f "${OUTPUT_DIR}/recon.h5" ]] || [[ -f "${BUILD_DIR}/recon.h5" ]]; then
    echo "[output] recon.h5 found – reconstruction completed!"
elif [[ -f "recon.h5" ]]; then
    echo "[output] recon.h5 found in cwd – reconstruction completed!"
fi

if [[ "${RESTART_EXIT}" -eq 0 ]]; then
    echo ""
    echo "============================================================"
    echo "  RESULT: SUCCESS"
    echo "  DMTCP checkpoint/restart works locally with 1 process."
    echo "  The hang on remote nodes is likely caused by MANA or"
    echo "  multi-node MPI interaction, NOT by DMTCP itself."
    echo "============================================================"
else
    echo ""
    echo "============================================================"
    echo "  RESULT: FAILED (restart exit code: ${RESTART_EXIT})"
    echo "  DMTCP checkpoint/restart ALSO fails locally."
    echo "  The problem is in DMTCP itself, not MANA/remote nodes."
    echo "  Check stderr output above for details."
    echo "============================================================"
fi

exit "${RESTART_EXIT}"
