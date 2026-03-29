#!/usr/bin/env bash
# ============================================================================
# test_mana_aurora.sh – MANA checkpoint/restart test for art_simple on Aurora
#
# Purpose:
#   Test MANA (MPI-Agnostic Network-Agnostic) transparent checkpoint/restart
#   with art_simple on ALCF Aurora.
#
# Prerequisites:
#   - MANA fully built (libmana.so + lower-half + libmpistub.so must exist)
#     Install via: ./scripts/install_dmtcp_mana.sh
#   - art_simple_main built with -DDMTCP_USE_MANA_STUB=ON
#   - HDF5 input data file (tooth_preprocessed.h5)
#
# Usage:
#   Option A – Interactive (on a compute node allocation):
#     qsub -I -l select=1 -l walltime=00:30:00 -A <project> -q debug
#     cd ~/diaspora/guard-agent
#     bash tests/examples/dmtcp/art_simple/test_mana_aurora.sh
#
#   Option B – Batch submission:
#     qsub tests/examples/dmtcp/art_simple/test_mana_aurora.sh
#
# Environment variables (all optional):
#   DATA_PATH          – HDF5 input file
#   MANA_ROOT          – MANA source/build directory
#   NUM_PROCS          – number of MPI ranks (default: 1)
#   CHECKPOINT_DELAY   – seconds before checkpoint (default: 10)
#   TIMEOUT            – max seconds per phase (default: 300)
#   COORD_PORT         – coordinator port (default: 7901)
#   SKIP_BUILD         – set to 1 to skip the rebuild step
# ============================================================================
#PBS -l select=1
#PBS -l walltime=00:30:00
#PBS -l filesystems=home
#PBS -q debug
#PBS -j oe
#PBS -N mana_art_simple_test

set -euo pipefail

# ── Locate repo root (resolve BEFORE any cd) ─────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

# If running under PBS, cd to the submission directory
if [[ -n "${PBS_O_WORKDIR:-}" ]]; then
    cd "${PBS_O_WORKDIR}"
fi

# ── Configuration ─────────────────────────────────────────────────────────
DATA_PATH="${DATA_PATH:-${REPO_ROOT}/build/data/tooth_preprocessed.h5}"
NUM_PROCS="${NUM_PROCS:-1}"
CHECKPOINT_DELAY="${CHECKPOINT_DELAY:-10}"
TIMEOUT="${TIMEOUT:-300}"
COORD_PORT="${COORD_PORT:-7901}"
SKIP_BUILD="${SKIP_BUILD:-0}"

# App arguments: <hdf5_input> <center> <num_outer_iter> <num_iter> <beg_index> <num_sino>
APP_ARGS="${DATA_PATH} 294.078 5 2 0 2"

# Working directories
BUILD_DIR="${REPO_ROOT}/build/validation_output/art_simple/build/dmtcp"
OUTPUT_DIR="${REPO_ROOT}/build/test_mana/output"
CKPT_DIR="${REPO_ROOT}/build/test_mana/ckpt"

# ── Locate MANA ──────────────────────────────────────────────────────────
if [[ -n "${MANA_ROOT:-}" ]]; then
    : # use provided MANA_ROOT
elif [[ -d "${HOME}/.local/share/guard-agent/dmtcp-src/mana" ]]; then
    MANA_ROOT="${HOME}/.local/share/guard-agent/dmtcp-src/mana"
else
    echo "ERROR: MANA not found. Install via: ./scripts/install_dmtcp_mana.sh" >&2
    exit 1
fi

MANA_BIN="${MANA_ROOT}/bin"
MANA_LIB="${MANA_ROOT}/lib/dmtcp"
DMTCP_LAUNCH="${MANA_BIN}/dmtcp_launch"
DMTCP_COMMAND="${MANA_BIN}/dmtcp_command"
DMTCP_COORDINATOR="${MANA_BIN}/dmtcp_coordinator"
DMTCP_RESTART="${MANA_BIN}/dmtcp_restart"
MANA_LAUNCH="${MANA_BIN}/mana_launch"
MANA_START_COORD="${MANA_BIN}/mana_start_coordinator"
MANA_RESTART="${MANA_BIN}/mana_restart"
LIBMANA="${MANA_LIB}/libmana.so"
LOWER_HALF="${MANA_BIN}/lower-half"
LIBMPISTUB="${MANA_LIB}/libmpistub.so"

echo "============================================================"
echo "  MANA Checkpoint/Restart Test for art_simple on Aurora"
echo "============================================================"
echo ""
echo "[config] MANA_ROOT       : ${MANA_ROOT}"
echo "[config] DATA_PATH       : ${DATA_PATH}"
echo "[config] NUM_PROCS       : ${NUM_PROCS}"
echo "[config] CKPT_DELAY      : ${CHECKPOINT_DELAY}s"
echo "[config] TIMEOUT         : ${TIMEOUT}s"
echo "[config] BUILD_DIR       : ${BUILD_DIR}"
echo "[config] CKPT_DIR        : ${CKPT_DIR}"
echo "[config] COORD_PORT      : ${COORD_PORT}"
echo "[config] APP_ARGS        : ${APP_ARGS}"
echo ""

# ── Pre-flight: check MANA components ────────────────────────────────────
MANA_READY=true
MISSING=()

for comp in "${LIBMANA}:libmana.so" "${LOWER_HALF}:lower-half" "${LIBMPISTUB}:libmpistub.so" "${DMTCP_LAUNCH}:dmtcp_launch"; do
    path="${comp%%:*}"
    name="${comp##*:}"
    if [[ -e "${path}" ]]; then
        echo "[check] ✓ ${name}: ${path}"
    else
        echo "[check] ✗ ${name}: MISSING (${path})"
        MANA_READY=false
        MISSING+=("${name}")
    fi
done
echo ""

if [[ "${MANA_READY}" != "true" ]]; then
    echo "ERROR: MANA is not fully built. Missing: ${MISSING[*]}" >&2
    echo "  Rebuild MANA: cd ${MANA_ROOT} && make -j\$(nproc) && make install" >&2
    exit 1
fi

# ── Pre-flight: check data file ──────────────────────────────────────────
if [[ ! -f "${DATA_PATH}" ]]; then
    echo "ERROR: HDF5 data file not found: ${DATA_PATH}" >&2
    exit 1
fi

# ── Step 0: Rebuild with MANA stub if needed ─────────────────────────────
EXE="${BUILD_DIR}/art_simple_main"

_needs_rebuild() {
    if [[ ! -x "${EXE}" ]]; then
        echo "[build] Executable not found, need to build"
        return 0
    fi
    # Check if the binary has real MPI symbols (it shouldn't for MANA)
    local mpi_init_count
    mpi_init_count=$(nm "${EXE}" 2>/dev/null | grep -c ' T .*MPI_Init' || true)
    if [[ "${mpi_init_count}" -gt 0 ]]; then
        echo "[build] Binary has ${mpi_init_count} MPI_Init symbols (statically linked MPI)"
        echo "[build] MANA requires linking against libmpistub, not real MPI"
        return 0
    fi
    # Check if it links against libmpistub
    if ldd "${EXE}" 2>/dev/null | grep -q 'libmpistub'; then
        echo "[build] Binary correctly links against libmpistub"
        return 1
    fi
    # Check if it links against real libmpi
    if ldd "${EXE}" 2>/dev/null | grep -q 'libmpi\.so'; then
        echo "[build] Binary links against real libmpi.so (not compatible with MANA)"
        return 0
    fi
    echo "[build] Cannot determine MPI linkage, rebuilding to be safe"
    return 0
}

if [[ "${SKIP_BUILD}" != "1" ]] && _needs_rebuild; then
    echo "[build] Rebuilding art_simple_main with MANA stub ..."
    echo ""

    # Source directory (where CMakeLists.txt and source files are)
    SRC_DIR="${REPO_ROOT}/build/example_refs/dmtcp/art_simple"
    if [[ ! -f "${SRC_DIR}/CMakeLists.txt" ]]; then
        # Try the git-tracked location
        SRC_DIR="${REPO_ROOT}/tests/examples/dmtcp/art_simple"
    fi
    if [[ ! -f "${SRC_DIR}/CMakeLists.txt" ]]; then
        echo "ERROR: CMakeLists.txt not found in ${SRC_DIR}" >&2
        exit 1
    fi

    # Check that source files exist (they may be in a different location)
    if [[ ! -f "${SRC_DIR}/main.cc" ]]; then
        # Source files might be in the build output directory
        EXAMPLE_SRC="${REPO_ROOT}/build/examples_output/resilient_art_simple"
        if [[ -f "${EXAMPLE_SRC}/main.cc" ]]; then
            echo "[build] Copying source files from ${EXAMPLE_SRC} ..."
            cp -v "${EXAMPLE_SRC}/main.cc" "${EXAMPLE_SRC}/art_simple.cc" \
                  "${EXAMPLE_SRC}/art_simple.h" "${SRC_DIR}/" 2>/dev/null || true
        fi
    fi

    rm -rf "${BUILD_DIR}"
    mkdir -p "${BUILD_DIR}"
    cd "${BUILD_DIR}"

    echo "[build] cmake -DDMTCP_USE_MANA_STUB=ON -DMANA_ROOT=${MANA_ROOT} ${SRC_DIR}"
    cmake -DDMTCP_USE_MANA_STUB=ON -DMANA_ROOT="${MANA_ROOT}" "${SRC_DIR}"
    echo ""
    echo "[build] make -j$(nproc)"
    make -j"$(nproc)"
    echo ""

    # Verify the build
    if [[ ! -x "${EXE}" ]]; then
        echo "ERROR: Build failed, executable not found: ${EXE}" >&2
        exit 1
    fi

    echo "[build] Verifying linkage ..."
    echo "  nm MPI_Init count: $(nm "${EXE}" 2>/dev/null | grep -c ' T .*MPI_Init' || echo 0)"
    echo "  ldd | grep mpi:"
    ldd "${EXE}" 2>/dev/null | grep -i mpi || echo "    (no MPI shared libs)"
    echo ""

    cd "${REPO_ROOT}"
fi

if [[ ! -x "${EXE}" ]]; then
    echo "ERROR: Executable not found: ${EXE}" >&2
    echo "  Build with: cd ${BUILD_DIR} && cmake -DDMTCP_USE_MANA_STUB=ON -DMANA_ROOT=${MANA_ROOT} <src_dir> && make" >&2
    exit 1
fi

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
"${DMTCP_COMMAND}" --port "${COORD_PORT}" --quit 2>/dev/null || true
sleep 0.5

echo "[coord] Starting MANA coordinator on port ${COORD_PORT} ..."
"${MANA_START_COORD}" --port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1 || {
    echo "[coord] mana_start_coordinator failed, trying manual start..."
    "${DMTCP_COORDINATOR}" --daemon --port "${COORD_PORT}" \
        --ckptdir "${CKPT_DIR}" 2>&1 || true
}
sleep 1

if "${DMTCP_COMMAND}" --port "${COORD_PORT}" --status 2>/dev/null; then
    echo "[coord] Coordinator is running."
else
    echo "WARNING: Could not verify coordinator status" >&2
fi
echo ""

# ── Step 3: Set environment ──────────────────────────────────────────────
export HWLOC_COMPONENTS="-linuxio"

# ── Step 4: Launch app under MANA ────────────────────────────────────────
LAUNCH_CMD="mpiexec -np ${NUM_PROCS} ${MANA_LAUNCH} --verbose --coord-port ${COORD_PORT} --ckptdir ${CKPT_DIR} --no-gzip ${EXE} ${APP_ARGS}"

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
    if [[ "${WAIT_EXIT}" -eq 139 ]]; then
        echo "============================================================"
        echo "  RESULT: SIGSEGV (signal 11)"
        echo ""
        echo "  Check that the binary was built with -DDMTCP_USE_MANA_STUB=ON"
        echo "  and links against libmpistub.so (not libmpi.a or libmpi.so)."
        echo ""
        echo "  Verify with:"
        echo "    nm ${EXE} | grep -c 'MPI_Init'  # should be 0"
        echo "    ldd ${EXE} | grep mpi  # should show libmpistub.so"
        echo "============================================================"
    elif [[ "${WAIT_EXIT}" -eq 0 ]]; then
        echo "============================================================"
        echo "  App completed successfully WITHOUT checkpoint."
        echo "  Increase CHECKPOINT_DELAY or workload size."
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
    echo "[ckpt] WARNING: Checkpoint failed or timed out!"
fi

echo "[ckpt] Checkpoint files:"
find "${CKPT_DIR}" -name "ckpt_*.dmtcp" -exec ls -lh {} \; 2>/dev/null || echo "  (none)"
echo ""

# ── Step 6: Kill the app ─────────────────────────────────────────────────
echo "[kill] Killing app process ..."
ART_PID=$(pgrep -f "art_simple_main" 2>/dev/null | head -1 || true)
if [[ -n "${ART_PID}" ]]; then
    kill -9 "${ART_PID}" 2>/dev/null || true
else
    kill -9 "${APP_PID}" 2>/dev/null || true
fi
wait "${APP_PID}" 2>/dev/null || true
sleep 2
echo "[kill] Done."
echo ""

# ── Step 7: Restart ──────────────────────────────────────────────────────
CKPT_FILES=$(find "${CKPT_DIR}" -name "ckpt_*.dmtcp" 2>/dev/null | head -1 || true)
if [[ -z "${CKPT_FILES}" ]]; then
    echo "RESULT: FAILED – No checkpoint files found!"
    exit 1
fi

echo "[restart] Restarting from checkpoint ..."
RESTART_CMD="mpiexec -np ${NUM_PROCS} ${MANA_RESTART} --coord-port ${COORD_PORT} --ckptdir ${CKPT_DIR} --no-gzip"
echo "[restart] Command: ${RESTART_CMD}"

timeout "${TIMEOUT}" ${RESTART_CMD} \
    > "${OUTPUT_DIR}/stdout_restart.txt" \
    2> "${OUTPUT_DIR}/stderr_restart.txt"
RESTART_EXIT=$?

echo ""
echo "--- Restart stdout (last 20 lines) ---"
tail -20 "${OUTPUT_DIR}/stdout_restart.txt" 2>/dev/null || true
echo "--- Restart stderr (last 20 lines) ---"
tail -20 "${OUTPUT_DIR}/stderr_restart.txt" 2>/dev/null || true

if [[ "${RESTART_EXIT}" -eq 0 ]]; then
    echo ""
    echo "RESULT: SUCCESS – MANA checkpoint/restart works!"
else
    echo ""
    echo "RESULT: FAILED (restart exit=${RESTART_EXIT})"
fi

exit "${RESTART_EXIT}"
