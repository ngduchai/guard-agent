#!/usr/bin/env bash
# ============================================================================
# debug_mana_sigsegv3.sh – Diagnose MANA SIGSEGV: shadow libs & HDF5 conflict
#
# Key finding: The binary links both libmpistub.so AND libmpi.so.12 (via
# libhdf5.so DT_NEEDED). This creates two sets of MPI symbols in the
# upper-half, conflicting with MANA's split-process model.
#
# This script tests:
#   1. mana_launch --use-shadowlibs (MANA's mechanism for this exact issue)
#   2. LD_PRELOAD libmpistub.so to override libmpi.so.12 symbols
#   3. Full mana_launch script to understand shadow lib mechanism
#   4. DMTCP tmpdir for JASSERT logs
#   5. Makefile_config to check MANA build configuration
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

# ── Configuration ─────────────────────────────────────────────────────────
MANA_ROOT="${MANA_ROOT:-${HOME}/.local/share/guard-agent/dmtcp-src/mana}"
MANA_BIN="${MANA_ROOT}/bin"
MANA_LIB="${MANA_ROOT}/lib/dmtcp"
COORD_PORT="${COORD_PORT:-7903}"
COORD_HOST="$(hostname)"
CKPT_DIR="${REPO_ROOT}/build/test_mana_debug3/ckpt"
OUTPUT_DIR="${REPO_ROOT}/build/test_mana_debug3/output"
TMPDIR_DMTCP="${REPO_ROOT}/build/test_mana_debug3/tmpdir"
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
LIBMPISTUB="${MANA_LIB}/libmpistub.so"

rm -rf "${CKPT_DIR}" "${OUTPUT_DIR}" "${TMPDIR_DMTCP}"
mkdir -p "${CKPT_DIR}" "${OUTPUT_DIR}" "${TMPDIR_DMTCP}"

echo "============================================================"
echo "  MANA SIGSEGV Diagnostic (Phase 3) – Shadow Libs & HDF5"
echo "============================================================"
echo ""

# ── Cleanup ───────────────────────────────────────────────────────────────
cleanup() {
    "${DMTCP_COMMAND}" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
    pkill -f "dmtcp_coordinator.*${COORD_PORT}" 2>/dev/null || true
    pkill -f "art_simple_main" 2>/dev/null || true
}
trap cleanup EXIT

# ── Test 1: Full mana_launch script ──────────────────────────────────────
echo "=== Test 1: Full mana_launch script ==="
cat "${MANA_LAUNCH}" 2>/dev/null || echo "  NOT FOUND"
echo ""
echo "---"
echo ""

# ── Test 2: Check for shadow lib infrastructure ──────────────────────────
echo "=== Test 2: Shadow lib infrastructure ==="
echo "Looking for shadow lib files in MANA_ROOT..."
find "${MANA_ROOT}" -name "*shadow*" -o -name "*Shadow*" 2>/dev/null || echo "  (none)"
echo ""
echo "Looking for mpi_unimpl_wrappers or similar..."
find "${MANA_ROOT}/lib" -name "*.so" 2>/dev/null | while read f; do
    echo "  $(basename "$f"): $(file "$f" 2>/dev/null | cut -d: -f2)"
done
echo ""

# ── Test 3: Check Makefile_config ─────────────────────────────────────────
echo "=== Test 3: Makefile_config ==="
if [[ -f "${MANA_ROOT}/Makefile_config" ]]; then
    cat "${MANA_ROOT}/Makefile_config"
else
    echo "  NOT FOUND"
    echo "  Looking for config files..."
    find "${MANA_ROOT}" -maxdepth 2 -name "Makefile*" -o -name "*.config" -o -name "config.*" 2>/dev/null | head -10
fi
echo ""

# ── Test 4: Check mana_start_coordinator script ──────────────────────────
echo "=== Test 4: mana_start_coordinator script ==="
cat "${MANA_START_COORD}" 2>/dev/null || echo "  NOT FOUND"
echo ""
echo "---"
echo ""

# ── Test 5: Start coordinator with DMTCP_TMPDIR ──────────────────────────
echo "=== Test 5: Run with --use-shadowlibs ==="

"${DMTCP_COMMAND}" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
sleep 0.5

echo "[coord] Starting coordinator..."
"${MANA_START_COORD}" --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1
sleep 1

if "${DMTCP_COMMAND}" -h "${COORD_HOST}" --port "${COORD_PORT}" --status 2>/dev/null; then
    echo "[coord] Coordinator is running."
fi
echo ""

export HWLOC_COMPONENTS="-linuxio"
export DMTCP_TMPDIR="${TMPDIR_DMTCP}"

echo "[launch] Running with --use-shadowlibs..."
timeout 30 mpiexec -np 1 \
    "${MANA_LAUNCH}" --verbose --use-shadowlibs \
    --coord-host "${COORD_HOST}" --coord-port "${COORD_PORT}" \
    --ckptdir "${CKPT_DIR}" --no-gzip \
    --tmpdir "${TMPDIR_DMTCP}" \
    "${EXE}" ${APP_ARGS} \
    > "${OUTPUT_DIR}/stdout_shadow.txt" \
    2> "${OUTPUT_DIR}/stderr_shadow.txt" || true

echo ""
echo "--- stdout ---"
cat "${OUTPUT_DIR}/stdout_shadow.txt" 2>/dev/null || echo "  (empty)"
echo ""
echo "--- stderr (last 50 lines) ---"
tail -50 "${OUTPUT_DIR}/stderr_shadow.txt" 2>/dev/null || echo "  (empty)"
echo ""

# ── Test 6: Check DMTCP_TMPDIR for logs ──────────────────────────────────
echo "=== Test 6: DMTCP_TMPDIR contents ==="
echo "DMTCP_TMPDIR: ${TMPDIR_DMTCP}"
find "${TMPDIR_DMTCP}" -type f 2>/dev/null | head -20 || echo "  (empty)"
echo ""
echo "Also checking /tmp for dmtcp dirs:"
ls -la /tmp/dmtcp-* 2>/dev/null || echo "  No /tmp/dmtcp-* directories"
echo ""

# ── Test 7: Try with LD_PRELOAD to force libmpistub first ─────────────────
echo "=== Test 7: Run with LD_PRELOAD=libmpistub.so ==="

"${DMTCP_COMMAND}" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
sleep 0.5
"${MANA_START_COORD}" --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1
sleep 1

echo "[launch] Running with LD_PRELOAD=${LIBMPISTUB}..."
timeout 30 env LD_PRELOAD="${LIBMPISTUB}" mpiexec -np 1 \
    "${MANA_LAUNCH}" --verbose \
    --coord-host "${COORD_HOST}" --coord-port "${COORD_PORT}" \
    --ckptdir "${CKPT_DIR}" --no-gzip \
    "${EXE}" ${APP_ARGS} \
    > "${OUTPUT_DIR}/stdout_preload.txt" \
    2> "${OUTPUT_DIR}/stderr_preload.txt" || true

echo ""
echo "--- stdout ---"
cat "${OUTPUT_DIR}/stdout_preload.txt" 2>/dev/null || echo "  (empty)"
echo ""
echo "--- stderr (last 50 lines) ---"
tail -50 "${OUTPUT_DIR}/stderr_preload.txt" 2>/dev/null || echo "  (empty)"
echo ""

# ── Test 8: Check if MANA has a built-in hello world test ─────────────────
echo "=== Test 8: MANA test programs ==="
echo "Looking for test/example programs in MANA..."
find "${MANA_ROOT}" -name "*.exe" -o -name "hello*" -o -name "test_*" -o -name "*_test" 2>/dev/null | head -10 || echo "  (none)"
echo ""
echo "Looking in contrib/mpi-proxy-split/test/:"
ls "${MANA_ROOT}/contrib/mpi-proxy-split/test/" 2>/dev/null | head -20 || echo "  (not found)"
echo ""

# ── Test 9: Check readelf for NEEDED entries ──────────────────────────────
echo "=== Test 9: DT_NEEDED entries ==="
echo "art_simple_main NEEDED:"
readelf -d "${EXE}" 2>/dev/null | grep NEEDED || echo "  (none)"
echo ""
echo "libhdf5.so NEEDED:"
HDF5_SO=$(ldd "${EXE}" 2>/dev/null | grep 'libhdf5\.so' | awk '{print $3}')
if [[ -n "${HDF5_SO}" ]]; then
    readelf -d "${HDF5_SO}" 2>/dev/null | grep NEEDED || echo "  (none)"
else
    echo "  (libhdf5.so not found in ldd)"
fi
echo ""
echo "libmpistub.so NEEDED:"
readelf -d "${LIBMPISTUB}" 2>/dev/null | grep NEEDED || echo "  (none)"
echo ""

echo "============================================================"
echo "  Diagnostic complete. Output files in: ${OUTPUT_DIR}"
echo "============================================================"
