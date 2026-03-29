#!/usr/bin/env bash
# ============================================================================
# debug_mana_sigsegv2.sh – Diagnose MANA SIGSEGV with coordinator running
#
# The coordinator is now starting correctly, but the app crashes with SIGSEGV
# inside MANA's split-process mechanism. This script captures:
#   1. JASSERT logs (DMTCP's internal debug logging)
#   2. LD_DEBUG output to see library loading order
#   3. mana_launch verbose output
#   4. Tries running with a minimal MPI hello-world to isolate the issue
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

# ── Configuration ─────────────────────────────────────────────────────────
MANA_ROOT="${MANA_ROOT:-${HOME}/.local/share/guard-agent/dmtcp-src/mana}"
MANA_BIN="${MANA_ROOT}/bin"
MANA_LIB="${MANA_ROOT}/lib/dmtcp"
COORD_PORT="${COORD_PORT:-7902}"
COORD_HOST="$(hostname)"
CKPT_DIR="${REPO_ROOT}/build/test_mana_debug/ckpt"
OUTPUT_DIR="${REPO_ROOT}/build/test_mana_debug/output"
DATA_PATH="${DATA_PATH:-${REPO_ROOT}/build/data/tooth_preprocessed.h5}"
EXE="${REPO_ROOT}/build/validation_output/art_simple/build/dmtcp/art_simple_main"
APP_ARGS="${DATA_PATH} 294.078 5 2 0 2"

DMTCP_COORDINATOR="${MANA_BIN}/dmtcp_coordinator"
DMTCP_COMMAND="${MANA_BIN}/dmtcp_command"
DMTCP_LAUNCH="${MANA_BIN}/dmtcp_launch"
MANA_LAUNCH="${MANA_BIN}/mana_launch"
MANA_START_COORD="${MANA_BIN}/mana_start_coordinator"
LOWER_HALF="${MANA_BIN}/lower-half"
LIBMANA="${MANA_LIB}/libmana.so"

rm -rf "${CKPT_DIR}" "${OUTPUT_DIR}"
mkdir -p "${CKPT_DIR}" "${OUTPUT_DIR}"

echo "============================================================"
echo "  MANA SIGSEGV Diagnostic (Phase 2)"
echo "============================================================"
echo ""
echo "COORD_HOST: ${COORD_HOST}"
echo "COORD_PORT: ${COORD_PORT}"
echo "EXE:        ${EXE}"
echo ""

# ── Cleanup ───────────────────────────────────────────────────────────────
cleanup() {
    "${DMTCP_COMMAND}" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
    pkill -f "dmtcp_coordinator.*${COORD_PORT}" 2>/dev/null || true
    pkill -f "art_simple_main" 2>/dev/null || true
}
trap cleanup EXIT

# ── Test 1: Verify binary linkage ─────────────────────────────────────────
echo "=== Test 1: Binary linkage ==="
echo "nm MPI_Init count: $(nm "${EXE}" 2>/dev/null | grep -c ' T .*MPI_Init' || echo 0)"
echo "ldd | grep mpi:"
ldd "${EXE}" 2>/dev/null | grep -i mpi || echo "  (none)"
echo ""

# ── Test 2: Check lower-half binary ──────────────────────────────────────
echo "=== Test 2: lower-half binary ==="
file "${LOWER_HALF}" 2>/dev/null || echo "  NOT FOUND"
echo "ldd lower-half | grep mpi:"
ldd "${LOWER_HALF}" 2>/dev/null | grep -i mpi || echo "  (none)"
echo ""

# ── Test 3: Check libmana.so ─────────────────────────────────────────────
echo "=== Test 3: libmana.so ==="
file "${LIBMANA}" 2>/dev/null || echo "  NOT FOUND"
echo "nm libmana.so | grep MPI_Init:"
nm -D "${LIBMANA}" 2>/dev/null | grep 'MPI_Init' | head -5 || echo "  (none)"
echo "nm libmana.so | grep PMPI_Init:"
nm -D "${LIBMANA}" 2>/dev/null | grep 'PMPI_Init' | head -5 || echo "  (none)"
echo ""

# ── Test 4: Check what mana_launch actually does ─────────────────────────
echo "=== Test 4: mana_launch script content (first 50 lines) ==="
head -50 "${MANA_LAUNCH}" 2>/dev/null || echo "  NOT FOUND"
echo ""

# ── Test 5: Start coordinator and run with JASSERT_STDERR ─────────────────
echo "=== Test 5: Run under MANA with JASSERT_STDERR=1 ==="

# Kill any existing coordinator on this port
"${DMTCP_COMMAND}" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
sleep 0.5

# Start coordinator
echo "[coord] Starting coordinator..."
"${MANA_START_COORD}" --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1
sleep 1

if "${DMTCP_COMMAND}" -h "${COORD_HOST}" --port "${COORD_PORT}" --status 2>/dev/null; then
    echo "[coord] Coordinator is running."
else
    echo "[coord] WARNING: Could not verify coordinator status"
fi
echo ""

# Run with JASSERT_STDERR to get DMTCP internal logs on stderr
echo "[launch] Running with JASSERT_STDERR=1 and HWLOC_COMPONENTS=-linuxio..."
export HWLOC_COMPONENTS="-linuxio"
export JASSERT_STDERR=1

# Use timeout to prevent hanging
timeout 30 mpiexec -np 1 \
    "${MANA_LAUNCH}" --verbose \
    --coord-host "${COORD_HOST}" --coord-port "${COORD_PORT}" \
    --ckptdir "${CKPT_DIR}" --no-gzip \
    "${EXE}" ${APP_ARGS} \
    > "${OUTPUT_DIR}/stdout_jassert.txt" \
    2> "${OUTPUT_DIR}/stderr_jassert.txt" || true

echo ""
echo "--- stdout (last 30 lines) ---"
tail -30 "${OUTPUT_DIR}/stdout_jassert.txt" 2>/dev/null || echo "  (empty)"
echo ""
echo "--- stderr (last 80 lines) ---"
tail -80 "${OUTPUT_DIR}/stderr_jassert.txt" 2>/dev/null || echo "  (empty)"
echo ""

# ── Test 6: Check JASSERT log files ──────────────────────────────────────
echo "=== Test 6: JASSERT log files ==="
JASSERT_DIR="/tmp/dmtcp-${USER}@${COORD_HOST}"
echo "Looking in: ${JASSERT_DIR}"
if [[ -d "${JASSERT_DIR}" ]]; then
    ls -la "${JASSERT_DIR}/" 2>/dev/null || true
    echo ""
    echo "--- Latest jassertlog (last 50 lines) ---"
    LATEST_LOG=$(ls -t "${JASSERT_DIR}"/jassertlog.* 2>/dev/null | head -1)
    if [[ -n "${LATEST_LOG}" ]]; then
        echo "File: ${LATEST_LOG}"
        tail -50 "${LATEST_LOG}" 2>/dev/null || true
    else
        echo "  No jassertlog files found"
    fi
else
    echo "  Directory not found"
    echo "  Trying /tmp/dmtcp-*:"
    ls -la /tmp/dmtcp-* 2>/dev/null || echo "  No /tmp/dmtcp-* directories"
fi
echo ""

# ── Test 7: Try running dmtcp_launch directly (bypass mana_launch) ────────
echo "=== Test 7: Direct dmtcp_launch (bypass mana_launch wrapper) ==="

# Kill coordinator and restart fresh
"${DMTCP_COMMAND}" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
sleep 0.5
"${MANA_START_COORD}" --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1
sleep 1

echo "[launch] Running dmtcp_launch directly with libmana.so..."
echo "  Command: mpiexec -np 1 ${DMTCP_LAUNCH} --mpi"
echo "    -h ${COORD_HOST} -p ${COORD_PORT}"
echo "    --no-gzip --join-coordinator --disable-dl-plugin"
echo "    --with-plugin ${LIBMANA}"
echo "    ${LOWER_HALF} ${EXE} ${APP_ARGS}"

timeout 30 mpiexec -np 1 \
    "${DMTCP_LAUNCH}" --mpi \
    -h "${COORD_HOST}" -p "${COORD_PORT}" \
    --no-gzip --join-coordinator --disable-dl-plugin \
    --with-plugin "${LIBMANA}" \
    "${LOWER_HALF}" "${EXE}" ${APP_ARGS} \
    > "${OUTPUT_DIR}/stdout_direct.txt" \
    2> "${OUTPUT_DIR}/stderr_direct.txt" || true

echo ""
echo "--- stdout (last 30 lines) ---"
tail -30 "${OUTPUT_DIR}/stdout_direct.txt" 2>/dev/null || echo "  (empty)"
echo ""
echo "--- stderr (last 80 lines) ---"
tail -80 "${OUTPUT_DIR}/stderr_direct.txt" 2>/dev/null || echo "  (empty)"
echo ""

# ── Test 8: Try a minimal test (just lower-half alone) ────────────────────
echo "=== Test 8: Run lower-half alone (no app) ==="
echo "  This tests if MANA's lower-half can initialize MPI at all."

# Kill coordinator and restart fresh
"${DMTCP_COMMAND}" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
sleep 0.5
"${MANA_START_COORD}" --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1
sleep 1

# Try running lower-half with no app (it should init MPI and wait)
timeout 10 mpiexec -np 1 \
    "${DMTCP_LAUNCH}" --mpi \
    -h "${COORD_HOST}" -p "${COORD_PORT}" \
    --no-gzip --join-coordinator --disable-dl-plugin \
    --with-plugin "${LIBMANA}" \
    "${LOWER_HALF}" \
    > "${OUTPUT_DIR}/stdout_lh.txt" \
    2> "${OUTPUT_DIR}/stderr_lh.txt" || true

echo ""
echo "--- stdout ---"
cat "${OUTPUT_DIR}/stdout_lh.txt" 2>/dev/null || echo "  (empty)"
echo ""
echo "--- stderr (last 30 lines) ---"
tail -30 "${OUTPUT_DIR}/stderr_lh.txt" 2>/dev/null || echo "  (empty)"
echo ""

# ── Test 9: Check MANA version and build info ────────────────────────────
echo "=== Test 9: MANA build info ==="
echo "MANA_ROOT: ${MANA_ROOT}"
echo ""
echo "git log (last commit):"
cd "${MANA_ROOT}" && git log --oneline -1 2>/dev/null || echo "  (not a git repo)"
cd "${REPO_ROOT}"
echo ""
echo "Makefile_config:"
cat "${MANA_ROOT}/Makefile_config" 2>/dev/null || echo "  (not found)"
echo ""

echo "============================================================"
echo "  Diagnostic complete. Output files in: ${OUTPUT_DIR}"
echo "============================================================"
