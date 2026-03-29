#!/usr/bin/env bash
# ============================================================================
# debug_mana_sigsegv4.sh – Test MANA with built-in test + create shadow libs
#
# Findings so far:
#   - Coordinator works correctly
#   - SIGSEGV happens because libhdf5.so loads libmpi.so.12 in the upper-half
#   - --use-shadowlibs fails due to Python 3.6 (needs 3.7+ for capture_output)
#   - MANA has built-in test programs at mpi-proxy-split/test/*.mana.exe
#
# This script:
#   1. Tests MANA with a simple built-in test (no HDF5) to confirm MANA works
#   2. Manually creates shadow libs to fix the libhdf5.so → libmpi.so issue
#   3. Tests art_simple with shadow libs
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

# ── Configuration ─────────────────────────────────────────────────────────
MANA_ROOT="${MANA_ROOT:-${HOME}/.local/share/guard-agent/dmtcp-src/mana}"
MANA_BIN="${MANA_ROOT}/bin"
MANA_LIB="${MANA_ROOT}/lib/dmtcp"
COORD_PORT="${COORD_PORT:-7904}"
COORD_HOST="$(hostname)"
CKPT_DIR="${REPO_ROOT}/build/test_mana_debug4/ckpt"
OUTPUT_DIR="${REPO_ROOT}/build/test_mana_debug4/output"
DATA_PATH="${DATA_PATH:-${REPO_ROOT}/build/data/tooth_preprocessed.h5}"
EXE="${REPO_ROOT}/build/validation_output/art_simple/build/dmtcp/art_simple_main"
APP_ARGS="${DATA_PATH} 294.078 5 2 0 2"

DMTCP_COMMAND="${MANA_BIN}/dmtcp_command"
MANA_LAUNCH="${MANA_BIN}/mana_launch"
MANA_START_COORD="${MANA_BIN}/mana_start_coordinator"
LIBMANA="${MANA_LIB}/libmana.so"
LIBMPISTUB="${MANA_LIB}/libmpistub.so"

rm -rf "${CKPT_DIR}" "${OUTPUT_DIR}"
mkdir -p "${CKPT_DIR}" "${OUTPUT_DIR}"

export HWLOC_COMPONENTS="-linuxio"

echo "============================================================"
echo "  MANA SIGSEGV Diagnostic (Phase 4)"
echo "  – Built-in test + Shadow libs"
echo "============================================================"
echo ""

# ── Cleanup ───────────────────────────────────────────────────────────────
cleanup() {
    "${DMTCP_COMMAND}" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
    pkill -f "dmtcp_coordinator.*${COORD_PORT}" 2>/dev/null || true
    pkill -f "art_simple_main" 2>/dev/null || true
}
trap cleanup EXIT

# ── Helper: start coordinator ─────────────────────────────────────────────
start_coord() {
    "${DMTCP_COMMAND}" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
    sleep 0.5
    "${MANA_START_COORD}" --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1
    sleep 1
    if "${DMTCP_COMMAND}" -h "${COORD_HOST}" --port "${COORD_PORT}" --status 2>/dev/null; then
        echo "[coord] Coordinator is running."
    else
        echo "[coord] WARNING: Could not verify coordinator status"
    fi
}

# ══════════════════════════════════════════════════════════════════════════
# TEST 1: Run MANA built-in test (send_recv_loop.mana.exe)
# ══════════════════════════════════════════════════════════════════════════
echo "=== Test 1: MANA built-in test (send_recv_loop.mana.exe) ==="
echo ""

MANA_TEST="${MANA_ROOT}/mpi-proxy-split/test/send_recv_loop.mana.exe"
if [[ ! -x "${MANA_TEST}" ]]; then
    echo "  send_recv_loop.mana.exe not found, looking for alternatives..."
    MANA_TEST=$(find "${MANA_ROOT}" -name "*.mana.exe" -type f 2>/dev/null | head -1)
    if [[ -z "${MANA_TEST}" ]]; then
        echo "  No .mana.exe test programs found!"
        echo "  Trying to find any test executable..."
        MANA_TEST=$(find "${MANA_ROOT}/mpi-proxy-split/test" -name "*.exe" -type f 2>/dev/null | head -1)
    fi
fi

if [[ -n "${MANA_TEST}" && -x "${MANA_TEST}" ]]; then
    echo "Using test: ${MANA_TEST}"
    echo ""
    
    # Check its linkage
    echo "Test binary linkage:"
    echo "  nm MPI_Init count: $(nm "${MANA_TEST}" 2>/dev/null | grep -c ' T .*MPI_Init' || echo 0)"
    echo "  ldd | grep mpi:"
    ldd "${MANA_TEST}" 2>/dev/null | grep -i mpi || echo "    (none)"
    echo "  DT_NEEDED:"
    readelf -d "${MANA_TEST}" 2>/dev/null | grep NEEDED || echo "    (none)"
    echo ""
    
    start_coord
    echo ""
    
    echo "[launch] Running MANA built-in test..."
    timeout 30 mpiexec -np 1 \
        "${MANA_LAUNCH}" --verbose \
        --coord-host "${COORD_HOST}" --coord-port "${COORD_PORT}" \
        --ckptdir "${CKPT_DIR}" --no-gzip \
        "${MANA_TEST}" \
        > "${OUTPUT_DIR}/stdout_builtin.txt" \
        2> "${OUTPUT_DIR}/stderr_builtin.txt"
    BUILTIN_EXIT=$?
    
    echo ""
    echo "Exit code: ${BUILTIN_EXIT}"
    echo "--- stdout ---"
    cat "${OUTPUT_DIR}/stdout_builtin.txt" 2>/dev/null || echo "  (empty)"
    echo "--- stderr (last 30 lines) ---"
    tail -30 "${OUTPUT_DIR}/stderr_builtin.txt" 2>/dev/null || echo "  (empty)"
    echo ""
    
    if [[ "${BUILTIN_EXIT}" -eq 0 ]]; then
        echo "✓ MANA works with built-in test! The issue is specific to art_simple/HDF5."
    elif [[ "${BUILTIN_EXIT}" -eq 139 ]]; then
        echo "✗ MANA SIGSEGV even with built-in test! MANA itself is broken on this platform."
    else
        echo "✗ MANA failed with exit code ${BUILTIN_EXIT}"
    fi
else
    echo "  No test executable found. Skipping."
fi
echo ""

# ══════════════════════════════════════════════════════════════════════════
# TEST 2: Manually create shadow libs
# ══════════════════════════════════════════════════════════════════════════
echo "=== Test 2: Manually create shadow libs ==="
echo ""
echo "The shadow lib mechanism creates stub versions of libmpi.so that"
echo "redirect MPI calls through libmpistub.so, preventing the real"
echo "libmpi.so.12 from being loaded when libhdf5.so requests it."
echo ""

# Find the real libmpi.so path
REAL_LIBMPI=$(ldd "${EXE}" 2>/dev/null | grep 'libmpi\.so\.12' | awk '{print $3}')
echo "Real libmpi.so.12: ${REAL_LIBMPI}"

# The shadow lib directory
SHADOW_DIR="${MANA_ROOT}/lib/tmp"
echo "Shadow lib dir: ${SHADOW_DIR}"
echo ""

# Create shadow directory
rm -rf "${SHADOW_DIR}"
mkdir -p "${SHADOW_DIR}"

# Create a symlink from libmpi.so.12 -> libmpistub.so in the shadow dir
# This way, when libhdf5.so tries to load libmpi.so.12, it gets the stub instead
echo "Creating shadow symlinks..."
ln -sfv "${LIBMPISTUB}" "${SHADOW_DIR}/libmpi.so.12"
ln -sfv "${LIBMPISTUB}" "${SHADOW_DIR}/libmpi.so"

# Also create symlinks for any other MPI libs that might be needed
REAL_LIBMPICXX=$(ldd "${MANA_BIN}/lower-half" 2>/dev/null | grep 'libmpicxx' | awk '{print $3}')
if [[ -n "${REAL_LIBMPICXX}" ]]; then
    MPICXX_NAME=$(basename "${REAL_LIBMPICXX}")
    ln -sfv "${LIBMPISTUB}" "${SHADOW_DIR}/${MPICXX_NAME}"
fi

echo ""
echo "Shadow dir contents:"
ls -la "${SHADOW_DIR}/"
echo ""

# ══════════════════════════════════════════════════════════════════════════
# TEST 3: Run art_simple with shadow libs
# ══════════════════════════════════════════════════════════════════════════
echo "=== Test 3: Run art_simple with shadow libs ==="
echo ""
echo "The lower-half checks for ${MANA_ROOT}/lib/tmp and adds it to"
echo "LD_LIBRARY_PRELOAD if it exists."
echo ""

start_coord
echo ""

echo "[launch] Running art_simple with shadow libs in place..."
timeout 30 mpiexec -np 1 \
    "${MANA_LAUNCH}" --verbose \
    --coord-host "${COORD_HOST}" --coord-port "${COORD_PORT}" \
    --ckptdir "${CKPT_DIR}" --no-gzip \
    "${EXE}" ${APP_ARGS} \
    > "${OUTPUT_DIR}/stdout_shadow.txt" \
    2> "${OUTPUT_DIR}/stderr_shadow.txt"
SHADOW_EXIT=$?

echo ""
echo "Exit code: ${SHADOW_EXIT}"
echo "--- stdout ---"
cat "${OUTPUT_DIR}/stdout_shadow.txt" 2>/dev/null || echo "  (empty)"
echo "--- stderr (last 50 lines) ---"
tail -50 "${OUTPUT_DIR}/stderr_shadow.txt" 2>/dev/null || echo "  (empty)"
echo ""

if [[ "${SHADOW_EXIT}" -eq 0 ]]; then
    echo "✓ Shadow libs fixed the issue!"
elif [[ "${SHADOW_EXIT}" -eq 139 ]]; then
    echo "✗ Still SIGSEGV with shadow libs"
else
    echo "✗ Failed with exit code ${SHADOW_EXIT}"
fi
echo ""

# Clean up shadow dir
rm -rf "${SHADOW_DIR}"

# ══════════════════════════════════════════════════════════════════════════
# TEST 4: Fix mana_shadow_mpi_libs.py for Python 3.6 and run
# ══════════════════════════════════════════════════════════════════════════
echo "=== Test 4: Fix mana_shadow_mpi_libs.py for Python 3.6 ==="
echo ""

SHADOW_SCRIPT="${MANA_BIN}/mana_shadow_mpi_libs.py"
if [[ -f "${SHADOW_SCRIPT}" ]]; then
    echo "Current Python version:"
    python3 --version 2>&1
    echo ""
    
    echo "The script uses capture_output=True (Python 3.7+)."
    echo "Creating a fixed copy..."
    
    # Create a fixed version
    FIXED_SCRIPT="${OUTPUT_DIR}/mana_shadow_mpi_libs_fixed.py"
    sed 's/capture_output=True/stdout=subprocess.PIPE, stderr=subprocess.PIPE/g' \
        "${SHADOW_SCRIPT}" > "${FIXED_SCRIPT}"
    chmod +x "${FIXED_SCRIPT}"
    
    echo "Running fixed shadow script..."
    python3 "${FIXED_SCRIPT}" "${EXE}" "${MANA_ROOT}/lib" 2>&1 || true
    
    echo ""
    echo "Shadow lib dir after running script:"
    ls -la "${MANA_ROOT}/lib/tmp/" 2>/dev/null || echo "  (not created)"
    echo ""
    
    if [[ -d "${MANA_ROOT}/lib/tmp" ]]; then
        echo "Shadow libs created! Testing art_simple..."
        
        start_coord
        echo ""
        
        timeout 30 mpiexec -np 1 \
            "${MANA_LAUNCH}" --verbose \
            --coord-host "${COORD_HOST}" --coord-port "${COORD_PORT}" \
            --ckptdir "${CKPT_DIR}" --no-gzip \
            "${EXE}" ${APP_ARGS} \
            > "${OUTPUT_DIR}/stdout_fixed_shadow.txt" \
            2> "${OUTPUT_DIR}/stderr_fixed_shadow.txt"
        FIXED_EXIT=$?
        
        echo ""
        echo "Exit code: ${FIXED_EXIT}"
        echo "--- stdout ---"
        cat "${OUTPUT_DIR}/stdout_fixed_shadow.txt" 2>/dev/null || echo "  (empty)"
        echo "--- stderr (last 50 lines) ---"
        tail -50 "${OUTPUT_DIR}/stderr_fixed_shadow.txt" 2>/dev/null || echo "  (empty)"
        echo ""
        
        if [[ "${FIXED_EXIT}" -eq 0 ]]; then
            echo "✓ Fixed shadow libs work!"
        elif [[ "${FIXED_EXIT}" -eq 139 ]]; then
            echo "✗ Still SIGSEGV with fixed shadow libs"
        else
            echo "✗ Failed with exit code ${FIXED_EXIT}"
        fi
        
        # Clean up
        rm -rf "${MANA_ROOT}/lib/tmp"
    fi
else
    echo "  mana_shadow_mpi_libs.py not found"
fi
echo ""

echo "============================================================"
echo "  Diagnostic complete. Output files in: ${OUTPUT_DIR}"
echo "============================================================"
