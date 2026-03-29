#!/usr/bin/env bash
# ============================================================================
# debug_mana_sigsegv5.sh – Deep MANA SIGSEGV diagnosis
#
# MANA's built-in test also crashes with SIGSEGV, so the issue is in MANA
# itself, not our app. This script investigates:
#   1. The Makefile_config used to build MANA
#   2. The patches applied to MANA source (especially switch-context.cpp)
#   3. Stack trace via GDB
#   4. Whether the lower-half can even start MPI
#   5. DMTCP's internal state
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

MANA_ROOT="${MANA_ROOT:-${HOME}/.local/share/guard-agent/dmtcp-src/mana}"
MANA_BIN="${MANA_ROOT}/bin"
MANA_LIB="${MANA_ROOT}/lib/dmtcp"
COORD_PORT="${COORD_PORT:-7905}"
COORD_HOST="$(hostname)"
CKPT_DIR="${REPO_ROOT}/build/test_mana_debug5/ckpt"
OUTPUT_DIR="${REPO_ROOT}/build/test_mana_debug5/output"

DMTCP_COMMAND="${MANA_BIN}/dmtcp_command"
DMTCP_LAUNCH="${MANA_BIN}/dmtcp_launch"
MANA_LAUNCH="${MANA_BIN}/mana_launch"
MANA_START_COORD="${MANA_BIN}/mana_start_coordinator"
LOWER_HALF="${MANA_BIN}/lower-half"
LIBMANA="${MANA_LIB}/libmana.so"

rm -rf "${CKPT_DIR}" "${OUTPUT_DIR}"
mkdir -p "${CKPT_DIR}" "${OUTPUT_DIR}"

export HWLOC_COMPONENTS="-linuxio"

echo "============================================================"
echo "  MANA SIGSEGV Deep Diagnosis (Phase 5)"
echo "============================================================"
echo ""

cleanup() {
    "${DMTCP_COMMAND}" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
    pkill -f "dmtcp_coordinator.*${COORD_PORT}" 2>/dev/null || true
}
trap cleanup EXIT

# ══════════════════════════════════════════════════════════════════════════
# 1. Check Makefile_config
# ══════════════════════════════════════════════════════════════════════════
echo "=== 1. Makefile_config ==="
MAKEFILE_CONFIG="${MANA_ROOT}/mpi-proxy-split/Makefile_config"
if [[ -f "${MAKEFILE_CONFIG}" ]]; then
    cat "${MAKEFILE_CONFIG}"
else
    echo "  NOT FOUND at ${MAKEFILE_CONFIG}"
    echo "  Looking for alternatives..."
    find "${MANA_ROOT}" -name "Makefile_config" 2>/dev/null
fi
echo ""

# ══════════════════════════════════════════════════════════════════════════
# 2. Check patched source files
# ══════════════════════════════════════════════════════════════════════════
echo "=== 2. Patched source files ==="

echo "--- switch-context.cpp (rdfsbase/wrfsbase lines) ---"
SWITCH_CTX="${MANA_ROOT}/mpi-proxy-split/lower-half/switch-context.cpp"
if [[ -f "${SWITCH_CTX}" ]]; then
    grep -n 'rdfsbase\|wrfsbase\|rex\.W\|\.byte 0x48\|ARCH_SET_FS\|ARCH_SET_GS' "${SWITCH_CTX}" 2>/dev/null || echo "  (no matches)"
else
    echo "  NOT FOUND"
fi
echo ""

echo "--- mpi_nextfunc.h (NEXT_FUNC macro) ---"
NEXTFUNC_H="${MANA_ROOT}/mpi-proxy-split/mpi-wrappers/mpi_nextfunc.h"
if [[ -f "${NEXTFUNC_H}" ]]; then
    grep -n 'typeof\|NEXT_FUNC\|PMPI_##func\|MPI_##func' "${NEXTFUNC_H}" | head -10 || echo "  (no matches)"
else
    echo "  NOT FOUND"
fi
echo ""

echo "--- copy-stack.c (void* arithmetic) ---"
COPY_STACK="${MANA_ROOT}/mpi-proxy-split/lower-half/copy-stack.c"
if [[ -f "${COPY_STACK}" ]]; then
    grep -n 'rc2.*dest_mem_len\|char \*' "${COPY_STACK}" | head -5 || echo "  (no matches)"
else
    echo "  NOT FOUND"
fi
echo ""

# ══════════════════════════════════════════════════════════════════════════
# 3. Check lower-half binary details
# ══════════════════════════════════════════════════════════════════════════
echo "=== 3. lower-half binary details ==="
echo "File:"
file "${LOWER_HALF}" 2>/dev/null
echo ""
echo "Size: $(stat -c%s "${LOWER_HALF}" 2>/dev/null || echo unknown) bytes"
echo ""
echo "Symbols related to context switching:"
nm "${LOWER_HALF}" 2>/dev/null | grep -i 'switch_context\|save_context\|restore_context\|fsbase\|gsbase\|arch_prctl' | head -10 || echo "  (none)"
echo ""
echo "Symbols related to MPI init:"
nm "${LOWER_HALF}" 2>/dev/null | grep -i 'MPI_Init\|mpi_init\|lh_init\|lower_half_init' | head -10 || echo "  (none)"
echo ""

# ══════════════════════════════════════════════════════════════════════════
# 4. Try to get a stack trace with GDB
# ══════════════════════════════════════════════════════════════════════════
echo "=== 4. Stack trace via GDB ==="

# Find a simple MANA test
MANA_TEST=$(find "${MANA_ROOT}/mpi-proxy-split/test" -name "*.mana.exe" -type f 2>/dev/null | head -1)
if [[ -z "${MANA_TEST}" ]]; then
    MANA_TEST=$(find "${MANA_ROOT}" -name "*.mana.exe" -type f 2>/dev/null | head -1)
fi

if ! command -v gdb &>/dev/null; then
    echo "  GDB not available, skipping stack trace"
    echo ""
else
    echo "Using test: ${MANA_TEST:-none}"
    echo ""
    
    if [[ -n "${MANA_TEST}" ]]; then
        # Start coordinator
        "${DMTCP_COMMAND}" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
        sleep 0.5
        "${MANA_START_COORD}" --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1
        sleep 1
        
        # Create GDB commands file
        cat > "${OUTPUT_DIR}/gdb_cmds.txt" << 'EOF'
set pagination off
set confirm off
handle SIGSEGV stop print
run
bt full
info registers
info proc mappings
quit
EOF
        
        echo "[gdb] Running MANA test under GDB..."
        # We need to run dmtcp_launch under GDB, not mana_launch (which is Python)
        timeout 30 mpiexec -np 1 \
            gdb -batch -x "${OUTPUT_DIR}/gdb_cmds.txt" \
            --args "${DMTCP_LAUNCH}" --mpi \
            -h "${COORD_HOST}" -p "${COORD_PORT}" \
            --no-gzip --join-coordinator --disable-dl-plugin \
            --with-plugin "${LIBMANA}" \
            "${LOWER_HALF}" "${MANA_TEST}" \
            > "${OUTPUT_DIR}/gdb_output.txt" \
            2>&1 || true
        
        echo ""
        echo "--- GDB output (last 80 lines) ---"
        tail -80 "${OUTPUT_DIR}/gdb_output.txt" 2>/dev/null || echo "  (empty)"
        echo ""
    fi
fi

# ══════════════════════════════════════════════════════════════════════════
# 5. Try running lower-half directly (not through dmtcp_launch)
# ══════════════════════════════════════════════════════════════════════════
echo "=== 5. Run lower-half directly (no DMTCP) ==="
echo "This tests if the lower-half binary can even start."
echo ""

if [[ -n "${MANA_TEST}" ]]; then
    echo "Command: ${LOWER_HALF} ${MANA_TEST}"
    timeout 10 "${LOWER_HALF}" "${MANA_TEST}" \
        > "${OUTPUT_DIR}/stdout_lh_direct.txt" \
        2> "${OUTPUT_DIR}/stderr_lh_direct.txt" || true
    
    echo "--- stdout ---"
    cat "${OUTPUT_DIR}/stdout_lh_direct.txt" 2>/dev/null || echo "  (empty)"
    echo "--- stderr ---"
    cat "${OUTPUT_DIR}/stderr_lh_direct.txt" 2>/dev/null || echo "  (empty)"
    echo ""
    
    echo "Now with mpiexec:"
    timeout 10 mpiexec -np 1 "${LOWER_HALF}" "${MANA_TEST}" \
        > "${OUTPUT_DIR}/stdout_lh_mpiexec.txt" \
        2> "${OUTPUT_DIR}/stderr_lh_mpiexec.txt" || true
    
    echo "--- stdout ---"
    cat "${OUTPUT_DIR}/stdout_lh_mpiexec.txt" 2>/dev/null || echo "  (empty)"
    echo "--- stderr ---"
    cat "${OUTPUT_DIR}/stderr_lh_mpiexec.txt" 2>/dev/null || echo "  (empty)"
fi
echo ""

# ══════════════════════════════════════════════════════════════════════════
# 6. Check DMTCP version and config
# ══════════════════════════════════════════════════════════════════════════
echo "=== 6. DMTCP/MANA version info ==="
echo "dmtcp_launch --version:"
"${DMTCP_LAUNCH}" --version 2>&1 || echo "  (failed)"
echo ""
echo "MANA git log:"
cd "${MANA_ROOT}" && git log --oneline -3 2>/dev/null || echo "  (not a git repo or no commits)"
cd "${REPO_ROOT}"
echo ""
echo "MANA DMTCP submodule git log:"
cd "${MANA_ROOT}/dmtcp" && git log --oneline -3 2>/dev/null || echo "  (not a git repo)"
cd "${REPO_ROOT}"
echo ""

# ══════════════════════════════════════════════════════════════════════════
# 7. Check config.log for build details
# ══════════════════════════════════════════════════════════════════════════
echo "=== 7. MANA configure details ==="
echo "--- config.log (compiler info) ---"
if [[ -f "${MANA_ROOT}/config.log" ]]; then
    grep -A2 'CC\|CXX\|CFLAGS\|CXXFLAGS\|LDFLAGS\|host_os\|host_cpu' "${MANA_ROOT}/config.log" | head -30
else
    echo "  NOT FOUND"
fi
echo ""
echo "--- MANA dmtcp/config.log (compiler info) ---"
if [[ -f "${MANA_ROOT}/dmtcp/config.log" ]]; then
    grep -A2 'CC\|CXX\|CFLAGS\|CXXFLAGS\|LDFLAGS\|host_os\|host_cpu' "${MANA_ROOT}/dmtcp/config.log" | head -30
else
    echo "  NOT FOUND"
fi
echo ""

# ══════════════════════════════════════════════════════════════════════════
# 8. Check if MANA was built on a login node vs compute node
# ══════════════════════════════════════════════════════════════════════════
echo "=== 8. Build vs runtime environment ==="
echo "Current hostname: $(hostname)"
echo "Current MPI:"
which mpicc 2>/dev/null && mpicc --version 2>&1 | head -1 || echo "  mpicc not found"
echo ""
echo "libmpi.so.12 location:"
ldconfig -p 2>/dev/null | grep libmpi || echo "  (not in ldconfig)"
echo "From ldd:"
ldd "${LOWER_HALF}" 2>/dev/null | grep libmpi || echo "  (none)"
echo ""

echo "============================================================"
echo "  Diagnostic complete. Output files in: ${OUTPUT_DIR}"
echo "============================================================"
