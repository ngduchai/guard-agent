#!/usr/bin/env bash
# ============================================================================
# debug_mana_sigsegv7.sh – Final MANA SIGSEGV isolation
#
# Phase 6 findings:
#   - fsgsbase works (not the crash cause)
#   - No memory map conflicts at 0x10000000
#   - DMTCP alone hangs (timeout) — suspicious
#   - "No MANA coordinator detected" in tests 3/6/9 because we used
#     dmtcp_coordinator directly instead of mana_start_coordinator
#   - The SIGSEGV in test_mana_aurora.sh is real (coordinator was detected)
#
# This script:
#   1. Uses mana_start_coordinator (writes ~/.mana.rc)
#   2. Tests DMTCP alone (no MANA) to see if DMTCP itself works
#   3. Tests MANA with a minimal MPI hello (built with mpistub)
#   4. Captures the actual SIGSEGV with strace
#   5. Examines the mana_launch Python script's coordinator detection
# ============================================================================

set +e

MANA_ROOT="${MANA_ROOT:-${HOME}/.local/share/guard-agent/dmtcp-src/mana}"
MANA_BIN="${MANA_ROOT}/bin"
MANA_LIB="${MANA_ROOT}/lib/dmtcp"
COORD_PORT="${COORD_PORT:-7909}"
COORD_HOST="$(hostname)"
OUTDIR="${HOME}/diaspora/guard-agent/build/test_mana_debug7/output"
CKPT_DIR="${HOME}/diaspora/guard-agent/build/test_mana_debug7/ckpt"

mkdir -p "${OUTDIR}" "${CKPT_DIR}"

export HWLOC_COMPONENTS="-linuxio"
export LD_LIBRARY_PATH="${MANA_LIB}:${LD_LIBRARY_PATH:-}"

echo "============================================================"
echo "  MANA SIGSEGV Final Isolation (Phase 7)"
echo "============================================================"
echo ""

# Kill any existing coordinator
"${MANA_BIN}/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
sleep 0.5

# ── Test 1: Understand mana_launch coordinator detection ──────────────
echo "=== Test 1: mana_launch coordinator detection ==="
echo ""

echo "Contents of ~/.mana.rc (before starting coordinator):"
cat "${HOME}/.mana.rc" 2>/dev/null || echo "  (file does not exist)"
echo ""

echo "mana_launch coordinator detection code:"
grep -n 'mana.rc\|coordinator\|status\|MANA_RC\|coord' "${MANA_BIN}/mana_launch" 2>/dev/null | head -20
echo ""

echo "mana_start_coordinator script:"
cat "${MANA_BIN}/mana_start_coordinator" 2>/dev/null | head -40
echo ""

# ── Test 2: Start coordinator with mana_start_coordinator ─────────────
echo "=== Test 2: Start coordinator with mana_start_coordinator ==="
echo ""

echo "Running: mana_start_coordinator --coord-port ${COORD_PORT} --ckptdir ${CKPT_DIR}"
"${MANA_BIN}/mana_start_coordinator" --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1
COORD_RC=$?
echo "Exit code: ${COORD_RC}"
echo ""

echo "Contents of ~/.mana.rc (after starting coordinator):"
cat "${HOME}/.mana.rc" 2>/dev/null || echo "  (file does not exist)"
echo ""

# Verify coordinator is running
echo "Coordinator status:"
"${MANA_BIN}/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" --status 2>&1
echo ""

# ── Test 3: DMTCP alone (no MANA) with proper coordinator ────────────
echo "=== Test 3: DMTCP alone (no MANA plugin) ==="
echo ""

# Compile simple test
cat > "${OUTDIR}/hello.c" << 'EOF'
#include <stdio.h>
#include <unistd.h>
int main() {
    printf("Hello from DMTCP test (pid=%d)\n", getpid());
    fflush(stdout);
    printf("DMTCP test done\n");
    fflush(stdout);
    return 0;
}
EOF

CC_CMD=""
if command -v gcc >/dev/null 2>&1; then CC_CMD="gcc";
elif command -v icx >/dev/null 2>&1; then CC_CMD="icx";
fi

if [ -n "${CC_CMD}" ]; then
    ${CC_CMD} -o "${OUTDIR}/hello" "${OUTDIR}/hello.c" 2>&1
fi

if [ -x "${OUTDIR}/hello" ]; then
    echo "Running: dmtcp_launch (no MANA) hello"
    timeout 10 "${MANA_BIN}/dmtcp_launch" \
        -h "${COORD_HOST}" -p "${COORD_PORT}" \
        --no-gzip --join-coordinator \
        "${OUTDIR}/hello" 2>&1
    echo "Exit code: $?"
else
    echo "Could not compile test"
fi
echo ""

# ── Test 4: MANA with minimal MPI hello ──────────────────────────────
echo "=== Test 4: MANA with minimal MPI hello ==="
echo ""

# Build minimal MPI hello with mpistub
cat > "${OUTDIR}/hello_mpi.c" << 'EOF'
#include <stdio.h>
#include <mpi.h>
int main(int argc, char **argv) {
    int rank, size;
    printf("Before MPI_Init\n"); fflush(stdout);
    MPI_Init(&argc, &argv);
    printf("After MPI_Init\n"); fflush(stdout);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    printf("Hello from rank %d of %d\n", rank, size);
    fflush(stdout);
    MPI_Finalize();
    printf("After MPI_Finalize\n"); fflush(stdout);
    return 0;
}
EOF

MPI_INC=""
if command -v mpicc >/dev/null 2>&1; then
    MPI_INC="$(mpicc -show 2>/dev/null | tr ' ' '\n' | grep '^-I' | head -1)"
    if [ -z "${MPI_INC}" ]; then
        MPI_INC="-I$(dirname $(which mpicc))/../include"
    fi
fi

SIMPLE_MPI="${OUTDIR}/hello_mpi_mana"
if [ -n "${CC_CMD}" ] && [ -n "${MPI_INC}" ]; then
    echo "Building: ${CC_CMD} ${MPI_INC} -L${MANA_LIB} -lmpistub -o ${SIMPLE_MPI}"
    ${CC_CMD} ${MPI_INC} -L"${MANA_LIB}" -lmpistub -o "${SIMPLE_MPI}" "${OUTDIR}/hello_mpi.c" 2>&1
fi

if [ -x "${SIMPLE_MPI}" ]; then
    echo ""
    echo "ldd:"
    ldd "${SIMPLE_MPI}" 2>&1 | grep -E 'mpi|stub'
    echo ""
    echo "nm MPI symbols:"
    nm "${SIMPLE_MPI}" 2>/dev/null | grep -i 'MPI_' | head -5
    echo ""
    
    echo "Running: mpiexec -np 1 mana_launch --verbose hello_mpi_mana"
    timeout 30 mpiexec -np 1 \
        "${MANA_BIN}/mana_launch" --verbose \
        --coord-host "${COORD_HOST}" --coord-port "${COORD_PORT}" \
        --ckptdir "${CKPT_DIR}" --no-gzip \
        "${SIMPLE_MPI}" > "${OUTDIR}/test4_stdout.txt" 2> "${OUTDIR}/test4_stderr.txt"
    echo "Exit code: $?"
    echo "--- stdout ---"
    cat "${OUTDIR}/test4_stdout.txt" 2>/dev/null
    echo "--- stderr ---"
    cat "${OUTDIR}/test4_stderr.txt" 2>/dev/null
else
    echo "Could not compile MANA-stub MPI hello"
fi
echo ""

# ── Test 5: Manual dmtcp_launch with MANA plugin ─────────────────────
echo "=== Test 5: Manual dmtcp_launch with MANA plugin ==="
echo ""

if [ -x "${SIMPLE_MPI}" ]; then
    echo "Running dmtcp_launch directly (bypassing mana_launch Python script):"
    echo "  dmtcp_launch --mpi -h ${COORD_HOST} -p ${COORD_PORT} --no-gzip --join-coordinator --disable-dl-plugin --with-plugin ${MANA_LIB}/libmana.so ${MANA_BIN}/lower-half ${SIMPLE_MPI}"
    echo ""
    
    timeout 30 mpiexec -np 1 \
        "${MANA_BIN}/dmtcp_launch" --mpi \
        -h "${COORD_HOST}" -p "${COORD_PORT}" \
        --no-gzip --join-coordinator --disable-dl-plugin \
        --with-plugin "${MANA_LIB}/libmana.so" \
        "${MANA_BIN}/lower-half" "${SIMPLE_MPI}" > "${OUTDIR}/test5_stdout.txt" 2> "${OUTDIR}/test5_stderr.txt"
    echo "Exit code: $?"
    echo "--- stdout ---"
    cat "${OUTDIR}/test5_stdout.txt" 2>/dev/null
    echo "--- stderr ---"
    cat "${OUTDIR}/test5_stderr.txt" 2>/dev/null
fi
echo ""

# ── Test 6: strace the actual crash ──────────────────────────────────
echo "=== Test 6: strace the actual crash ==="
echo ""

if command -v strace >/dev/null 2>&1 && [ -x "${SIMPLE_MPI}" ]; then
    echo "Running with strace -f (following forks)..."
    timeout 30 mpiexec -np 1 \
        strace -f -o "${OUTDIR}/strace_mana.log" \
        "${MANA_BIN}/dmtcp_launch" --mpi \
        -h "${COORD_HOST}" -p "${COORD_PORT}" \
        --no-gzip --join-coordinator --disable-dl-plugin \
        --with-plugin "${MANA_LIB}/libmana.so" \
        "${MANA_BIN}/lower-half" "${SIMPLE_MPI}" 2>&1
    echo "Exit code: $?"
    echo ""
    
    # Find SIGSEGV
    echo "--- SIGSEGV in strace ---"
    grep 'SIGSEGV\|si_addr' "${OUTDIR}/strace_mana.log" 2>/dev/null | head -10
    echo ""
    
    # Find the PID that crashed
    CRASH_PID=$(grep 'SIGSEGV' "${OUTDIR}/strace_mana.log" 2>/dev/null | head -1 | awk '{print $1}')
    if [ -n "${CRASH_PID}" ]; then
        echo "Crash PID: ${CRASH_PID}"
        echo ""
        echo "--- Last 30 syscalls before SIGSEGV (PID ${CRASH_PID}) ---"
        grep "^${CRASH_PID}" "${OUTDIR}/strace_mana.log" 2>/dev/null | grep -B30 'SIGSEGV' | tail -30
        echo ""
        
        echo "--- arch_prctl calls (PID ${CRASH_PID}) ---"
        grep "^${CRASH_PID}.*arch_prctl" "${OUTDIR}/strace_mana.log" 2>/dev/null
        echo ""
        
        echo "--- clone/fork calls ---"
        grep -E 'clone|fork' "${OUTDIR}/strace_mana.log" 2>/dev/null | head -10
    fi
elif ! command -v strace >/dev/null 2>&1; then
    echo "strace not available"
fi
echo ""

# ── Test 7: Check if the issue is --disable-dl-plugin ─────────────────
echo "=== Test 7: Without --disable-dl-plugin ==="
echo ""

if [ -x "${SIMPLE_MPI}" ]; then
    echo "Running dmtcp_launch WITHOUT --disable-dl-plugin:"
    timeout 30 mpiexec -np 1 \
        "${MANA_BIN}/dmtcp_launch" --mpi \
        -h "${COORD_HOST}" -p "${COORD_PORT}" \
        --no-gzip --join-coordinator \
        --with-plugin "${MANA_LIB}/libmana.so" \
        "${MANA_BIN}/lower-half" "${SIMPLE_MPI}" > "${OUTDIR}/test7_stdout.txt" 2> "${OUTDIR}/test7_stderr.txt"
    echo "Exit code: $?"
    echo "--- stdout ---"
    cat "${OUTDIR}/test7_stdout.txt" 2>/dev/null
    echo "--- stderr ---"
    cat "${OUTDIR}/test7_stderr.txt" 2>/dev/null
fi
echo ""

# Cleanup
"${MANA_BIN}/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true

echo "============================================================"
echo "  Diagnostic complete. Output files in: ${OUTDIR}"
echo "============================================================"
