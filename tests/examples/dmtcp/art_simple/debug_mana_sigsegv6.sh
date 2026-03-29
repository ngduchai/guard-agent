#!/usr/bin/env bash
# ============================================================================
# debug_mana_sigsegv6.sh – Isolate MANA SIGSEGV on Aurora
#
# The Makefile_config fix didn't resolve the crash. The lower-half was already
# linking against the correct Cray MPICH. The SIGSEGV is deeper.
#
# This script isolates the crash by testing each layer independently.
# ============================================================================

# Don't use set -euo pipefail — we want to continue even if commands fail
set +e

MANA_ROOT="${MANA_ROOT:-${HOME}/.local/share/guard-agent/dmtcp-src/mana}"
MANA_BIN="${MANA_ROOT}/bin"
MANA_LIB="${MANA_ROOT}/lib/dmtcp"
COORD_PORT="${COORD_PORT:-7908}"
COORD_HOST="$(hostname)"
OUTDIR="${HOME}/diaspora/guard-agent/build/test_mana_debug6/output"
CKPT_DIR="${HOME}/diaspora/guard-agent/build/test_mana_debug6/ckpt"

mkdir -p "${OUTDIR}" "${CKPT_DIR}"

export HWLOC_COMPONENTS="-linuxio"
export LD_LIBRARY_PATH="${MANA_LIB}:${LD_LIBRARY_PATH:-}"

echo "============================================================"
echo "  MANA SIGSEGV Isolation (Phase 6)"
echo "============================================================"
echo ""
echo "MANA_ROOT: ${MANA_ROOT}"
echo "MANA_BIN: ${MANA_BIN}"
echo "MANA_LIB: ${MANA_LIB}"
echo "LD_LIBRARY_PATH: ${LD_LIBRARY_PATH}"
echo ""

# Find a MANA test binary
MANA_TEST=""
if [ -d "${MANA_ROOT}/mpi-proxy-split/test" ]; then
    MANA_TEST="$(find "${MANA_ROOT}/mpi-proxy-split/test" -name "*.mana.exe" -type f 2>/dev/null | head -1)"
fi
echo "MANA_TEST: ${MANA_TEST:-NONE FOUND}"
echo ""

# ── Test 1: lower-half directly ───────────────────────────────────────
echo "=== Test 1: lower-half directly (with LD_LIBRARY_PATH) ==="
echo ""

if [ -n "${MANA_TEST}" ] && [ -x "${MANA_TEST}" ]; then
    echo "Test binary: ${MANA_TEST}"
    echo "lower-half: ${MANA_BIN}/lower-half"
    echo ""
    
    echo "ldd of test binary:"
    ldd "${MANA_TEST}" 2>&1 | head -20 || echo "  (ldd failed)"
    echo ""
    
    echo "Running: ${MANA_BIN}/lower-half ${MANA_TEST}"
    timeout 10 "${MANA_BIN}/lower-half" "${MANA_TEST}" > "${OUTDIR}/test1_stdout.txt" 2> "${OUTDIR}/test1_stderr.txt"
    echo "Exit code: $?"
    echo "--- stdout ---"
    cat "${OUTDIR}/test1_stdout.txt" 2>/dev/null
    echo "--- stderr ---"
    cat "${OUTDIR}/test1_stderr.txt" 2>/dev/null
    echo ""
    
    echo "Running with mpiexec: mpiexec -np 1 ${MANA_BIN}/lower-half ${MANA_TEST}"
    timeout 10 mpiexec -np 1 "${MANA_BIN}/lower-half" "${MANA_TEST}" > "${OUTDIR}/test1b_stdout.txt" 2> "${OUTDIR}/test1b_stderr.txt"
    echo "Exit code: $?"
    echo "--- stdout ---"
    cat "${OUTDIR}/test1b_stdout.txt" 2>/dev/null
    echo "--- stderr ---"
    cat "${OUTDIR}/test1b_stderr.txt" 2>/dev/null
else
    echo "No .mana.exe test binary found, skipping"
fi
echo ""

# ── Test 2: Simple hello world with DMTCP (no MANA) ──────────────────
echo "=== Test 2: DMTCP alone (no MANA plugin) ==="
echo ""

cat > "${OUTDIR}/hello_dmtcp.c" << 'EOF'
#include <stdio.h>
#include <unistd.h>
int main() {
    printf("Hello from DMTCP test (pid=%d)\n", getpid());
    fflush(stdout);
    sleep(2);
    printf("DMTCP test done\n");
    return 0;
}
EOF

SIMPLE_TEST="${OUTDIR}/hello_dmtcp"
CC_CMD=""
if command -v gcc >/dev/null 2>&1; then
    CC_CMD="gcc"
elif command -v icx >/dev/null 2>&1; then
    CC_CMD="icx"
elif command -v cc >/dev/null 2>&1; then
    CC_CMD="cc"
fi

if [ -n "${CC_CMD}" ]; then
    echo "Compiling with: ${CC_CMD}"
    ${CC_CMD} -o "${SIMPLE_TEST}" "${OUTDIR}/hello_dmtcp.c" 2>&1
fi

if [ -x "${SIMPLE_TEST}" ]; then
    # Kill any existing coordinator on this port
    "${MANA_BIN}/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
    sleep 0.5
    "${MANA_BIN}/dmtcp_coordinator" --daemon --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1
    sleep 1
    
    echo "Running: dmtcp_launch (no MANA plugin) ${SIMPLE_TEST}"
    timeout 15 "${MANA_BIN}/dmtcp_launch" \
        -h "${COORD_HOST}" -p "${COORD_PORT}" \
        --no-gzip --join-coordinator \
        "${SIMPLE_TEST}" > "${OUTDIR}/test2_stdout.txt" 2> "${OUTDIR}/test2_stderr.txt"
    echo "Exit code: $?"
    echo "--- stdout ---"
    cat "${OUTDIR}/test2_stdout.txt" 2>/dev/null
    echo "--- stderr ---"
    cat "${OUTDIR}/test2_stderr.txt" 2>/dev/null
    
    "${MANA_BIN}/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
else
    echo "Could not compile simple test (CC_CMD=${CC_CMD})"
fi
echo ""

# ── Test 3: DMTCP + MANA plugin with simple MPI program ──────────────
echo "=== Test 3: DMTCP + MANA plugin (simple MPI) ==="
echo ""

cat > "${OUTDIR}/hello_mpi.c" << 'EOF'
#include <stdio.h>
#include <mpi.h>
int main(int argc, char **argv) {
    int rank, size;
    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    printf("Hello from rank %d of %d\n", rank, size);
    fflush(stdout);
    MPI_Finalize();
    printf("MPI_Finalize done\n");
    return 0;
}
EOF

# First test: normal MPI (no DMTCP)
echo "--- Normal MPI hello (no DMTCP) ---"
if command -v mpicc >/dev/null 2>&1; then
    mpicc -o "${OUTDIR}/hello_mpi_normal" "${OUTDIR}/hello_mpi.c" 2>&1
    if [ -x "${OUTDIR}/hello_mpi_normal" ]; then
        echo "Running: mpiexec -np 1 hello_mpi_normal"
        timeout 10 mpiexec -np 1 "${OUTDIR}/hello_mpi_normal" 2>&1
        echo "Exit code: $?"
    fi
else
    echo "mpicc not found"
fi
echo ""

# Second test: MANA-stub MPI hello
echo "--- MANA-stub MPI hello ---"
SIMPLE_MPI="${OUTDIR}/hello_mpi_mana"

# Get MPI include path
MPI_INC_DIR=""
if command -v mpicc >/dev/null 2>&1; then
    # Try to extract -I flags from mpicc -show
    MPI_INC_DIR="$(mpicc -show 2>/dev/null | tr ' ' '\n' | grep '^-I' | head -1)"
    if [ -z "${MPI_INC_DIR}" ]; then
        # Fallback: use mpicc's parent directory
        MPI_BIN_DIR="$(dirname "$(which mpicc)")"
        MPI_INC_DIR="-I${MPI_BIN_DIR}/../include"
    fi
fi
echo "MPI include: ${MPI_INC_DIR}"

if [ -n "${CC_CMD}" ] && [ -n "${MPI_INC_DIR}" ]; then
    echo "Building: ${CC_CMD} ${MPI_INC_DIR} -L${MANA_LIB} -lmpistub -o ${SIMPLE_MPI} hello_mpi.c"
    ${CC_CMD} ${MPI_INC_DIR} -L"${MANA_LIB}" -lmpistub -o "${SIMPLE_MPI}" "${OUTDIR}/hello_mpi.c" 2>&1
fi

if [ -x "${SIMPLE_MPI}" ]; then
    echo ""
    echo "ldd of MANA-stub MPI hello:"
    ldd "${SIMPLE_MPI}" 2>&1 | grep -E 'mpi|stub'
    echo ""
    
    # Start coordinator
    "${MANA_BIN}/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
    sleep 0.5
    "${MANA_BIN}/dmtcp_coordinator" --daemon --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1
    sleep 1
    
    echo "Running: mpiexec -np 1 mana_launch ${SIMPLE_MPI}"
    timeout 15 mpiexec -np 1 \
        "${MANA_BIN}/mana_launch" --verbose \
        --coord-host "${COORD_HOST}" --coord-port "${COORD_PORT}" \
        --ckptdir "${CKPT_DIR}" --no-gzip \
        "${SIMPLE_MPI}" > "${OUTDIR}/test3_stdout.txt" 2> "${OUTDIR}/test3_stderr.txt"
    echo "Exit code: $?"
    echo "--- stdout ---"
    cat "${OUTDIR}/test3_stdout.txt" 2>/dev/null
    echo "--- stderr ---"
    cat "${OUTDIR}/test3_stderr.txt" 2>/dev/null
    
    "${MANA_BIN}/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
else
    echo "Could not compile MANA-stub MPI hello"
fi
echo ""

# ── Test 4: lower-half binary analysis ────────────────────────────────
echo "=== Test 4: lower-half binary analysis ==="
echo ""

echo "lower-half ELF segments:"
readelf -l "${MANA_BIN}/lower-half" 2>/dev/null | grep -E 'LOAD|Entry|Type' | head -10
echo ""

echo "lower-half NEEDED libraries:"
readelf -d "${MANA_BIN}/lower-half" 2>/dev/null | grep NEEDED
echo ""

echo "lower-half symbols (init/context):"
nm "${MANA_BIN}/lower-half" 2>/dev/null | grep -iE 'CheckAndEnable|FsGs|context|_start' | head -10
echo ""

# ── Test 5: CPU fsgsbase support ──────────────────────────────────────
echo "=== Test 5: CPU fsgsbase support ==="
echo ""

echo "CPU flags (fsgsbase):"
grep -o 'fsgsbase' /proc/cpuinfo 2>/dev/null | head -1 || echo "fsgsbase NOT found in /proc/cpuinfo"
echo ""

echo "Kernel version: $(uname -r)"
echo ""

cat > "${OUTDIR}/test_fsgsbase.c" << 'FSGSEOF'
#include <stdio.h>
#include <stdint.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <asm/prctl.h>
#include <signal.h>
#include <setjmp.h>

static sigjmp_buf jmpbuf;
static void handler(int sig) { siglongjmp(jmpbuf, 1); }

int main() {
    uint64_t fsbase = 0;
    
    /* Test 1: arch_prctl */
    if (syscall(SYS_arch_prctl, ARCH_GET_FS, &fsbase) == 0) {
        printf("arch_prctl ARCH_GET_FS: 0x%lx\n", fsbase);
    } else {
        printf("arch_prctl ARCH_GET_FS: FAILED\n");
    }
    
    /* Test 2: rdfsbase instruction */
    signal(SIGSEGV, handler);
    signal(SIGILL, handler);
    if (sigsetjmp(jmpbuf, 1) == 0) {
        uint64_t val;
        asm volatile(".byte 0x48; rdfsbase %0" : "=r" (val) :: "memory");
        printf("rdfsbase instruction: 0x%lx (WORKS)\n", val);
    } else {
        printf("rdfsbase instruction: SIGILL/SIGSEGV (NOT supported by kernel)\n");
    }
    
    /* Test 3: wrfsbase instruction */
    if (sigsetjmp(jmpbuf, 1) == 0) {
        asm volatile(".byte 0x48; wrfsbase %0" :: "r" (fsbase) : "memory");
        printf("wrfsbase instruction: WORKS\n");
    } else {
        printf("wrfsbase instruction: SIGILL/SIGSEGV (NOT supported by kernel)\n");
    }
    
    return 0;
}
FSGSEOF

if [ -n "${CC_CMD}" ]; then
    ${CC_CMD} -o "${OUTDIR}/test_fsgsbase" "${OUTDIR}/test_fsgsbase.c" 2>&1
    if [ -x "${OUTDIR}/test_fsgsbase" ]; then
        "${OUTDIR}/test_fsgsbase" 2>&1
    else
        echo "Could not compile fsgsbase test"
    fi
fi
echo ""

# ── Test 6: JASSERT logs ─────────────────────────────────────────────
echo "=== Test 6: JASSERT logs ==="
echo ""

JASSERT_DIR="${OUTDIR}/jassert_logs"
mkdir -p "${JASSERT_DIR}"

# Use the art_simple binary or MANA test
TEST_BIN=""
ART_SIMPLE="${HOME}/diaspora/guard-agent/build/validation_output/art_simple/build/dmtcp/art_simple_main"
if [ -x "${ART_SIMPLE}" ]; then
    TEST_BIN="${ART_SIMPLE}"
    TEST_ARGS="${HOME}/diaspora/guard-agent/build/data/tooth_preprocessed.h5 294.078 5 2 0 2"
elif [ -n "${MANA_TEST}" ] && [ -x "${MANA_TEST}" ]; then
    TEST_BIN="${MANA_TEST}"
    TEST_ARGS=""
fi

if [ -n "${TEST_BIN}" ]; then
    # Start coordinator
    "${MANA_BIN}/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
    sleep 0.5
    "${MANA_BIN}/dmtcp_coordinator" --daemon --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1
    sleep 1
    
    export DMTCP_TMPDIR="${JASSERT_DIR}"
    export JASSERT_STDERR=1
    
    echo "Running with JASSERT_STDERR=1 DMTCP_TMPDIR=${JASSERT_DIR}"
    echo "Binary: ${TEST_BIN}"
    timeout 15 mpiexec -np 1 \
        "${MANA_BIN}/mana_launch" --verbose \
        --coord-host "${COORD_HOST}" --coord-port "${COORD_PORT}" \
        --ckptdir "${CKPT_DIR}" --no-gzip \
        ${TEST_BIN} ${TEST_ARGS} > "${OUTDIR}/test6_stdout.txt" 2> "${OUTDIR}/test6_stderr.txt"
    echo "Exit code: $?"
    echo ""
    echo "--- stderr (first 80 lines) ---"
    head -80 "${OUTDIR}/test6_stderr.txt" 2>/dev/null
    echo ""
    echo "--- JASSERT log files ---"
    ls -la "${JASSERT_DIR}/" 2>/dev/null
    for f in "${JASSERT_DIR}"/jassert*; do
        if [ -f "$f" ]; then
            echo ""
            echo "--- $f (last 30 lines) ---"
            tail -30 "$f"
        fi
    done
    
    # Also check /tmp for DMTCP files
    echo ""
    echo "--- /tmp/dmtcp-* files ---"
    ls -la /tmp/dmtcp-* 2>/dev/null || echo "  (none)"
    
    unset DMTCP_TMPDIR JASSERT_STDERR
    "${MANA_BIN}/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
else
    echo "No test binary available"
fi
echo ""

# ── Test 7: Kernel settings ──────────────────────────────────────────
echo "=== Test 7: Kernel settings ==="
echo ""

echo "ASLR (randomize_va_space): $(cat /proc/sys/kernel/randomize_va_space 2>/dev/null || echo N/A)"
echo "ptrace_scope: $(cat /proc/sys/kernel/yama/ptrace_scope 2>/dev/null || echo N/A)"
echo "mmap_min_addr: $(cat /proc/sys/vm/mmap_min_addr 2>/dev/null || echo N/A)"
echo ""

# ── Test 8: Memory map analysis ──────────────────────────────────────
echo "=== Test 8: Memory map analysis ==="
echo ""

echo "lower-half is linked with -Ttext-segment=0x10000000"
echo "Checking if this address range is available..."

cat > "${OUTDIR}/check_mmap.c" << 'MMAPEOF'
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main() {
    FILE *f = fopen("/proc/self/maps", "r");
    if (!f) { perror("fopen"); return 1; }
    
    char line[512];
    int conflict = 0;
    printf("Memory regions near 0x10000000:\n");
    while (fgets(line, sizeof(line), f)) {
        unsigned long start, end;
        if (sscanf(line, "%lx-%lx", &start, &end) == 2) {
            if (start < 0x20000000UL && end > 0x10000000UL) {
                printf("  CONFLICT: %s", line);
                conflict = 1;
            }
        }
    }
    if (!conflict) {
        printf("  No conflicts found\n");
    }
    fclose(f);
    return 0;
}
MMAPEOF

if [ -n "${CC_CMD}" ]; then
    ${CC_CMD} -o "${OUTDIR}/check_mmap" "${OUTDIR}/check_mmap.c" 2>&1
    if [ -x "${OUTDIR}/check_mmap" ]; then
        "${OUTDIR}/check_mmap" 2>&1
    fi
fi
echo ""

# ── Test 9: strace the crash ─────────────────────────────────────────
echo "=== Test 9: strace analysis ==="
echo ""

if ! command -v strace >/dev/null 2>&1; then
    echo "strace not available, skipping"
else
    if [ -n "${TEST_BIN}" ]; then
        # Start coordinator
        "${MANA_BIN}/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
        sleep 0.5
        "${MANA_BIN}/dmtcp_coordinator" --daemon --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1
        sleep 1
        
        echo "Running with strace..."
        timeout 15 mpiexec -np 1 strace -f -o "${OUTDIR}/strace.log" \
            "${MANA_BIN}/mana_launch" --verbose \
            --coord-host "${COORD_HOST}" --coord-port "${COORD_PORT}" \
            --ckptdir "${CKPT_DIR}" --no-gzip \
            ${TEST_BIN} ${TEST_ARGS} 2>&1
        
        echo ""
        echo "--- SIGSEGV details ---"
        grep -B5 -A2 'SIGSEGV' "${OUTDIR}/strace.log" 2>/dev/null | head -30 || echo "  (no SIGSEGV in strace)"
        echo ""
        
        echo "--- Last arch_prctl/mmap/mprotect calls before crash ---"
        grep -E 'arch_prctl|mmap|mprotect' "${OUTDIR}/strace.log" 2>/dev/null | tail -20
        
        "${MANA_BIN}/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
    fi
fi
echo ""

# ── Test 10: What does mana_launch actually execute? ──────────────────
echo "=== Test 10: mana_launch command expansion ==="
echo ""

if [ -f "${MANA_BIN}/mana_launch" ]; then
    echo "mana_launch is a:"
    file "${MANA_BIN}/mana_launch" 2>/dev/null
    echo ""
    
    # If it's a script, show what command it would run
    if file "${MANA_BIN}/mana_launch" 2>/dev/null | grep -q 'script\|text'; then
        echo "Key lines from mana_launch:"
        grep -n 'dmtcp_launch\|exec\|lower-half\|libmana' "${MANA_BIN}/mana_launch" 2>/dev/null | head -10
        echo ""
    fi
    
    # Show what mana_launch would execute by adding --dry-run or echoing
    echo "Simulating mana_launch command:"
    echo "  dmtcp_launch --mpi -h ${COORD_HOST} -p ${COORD_PORT} --no-gzip --join-coordinator --disable-dl-plugin --with-plugin ${MANA_LIB}/libmana.so ${MANA_BIN}/lower-half <app>"
fi
echo ""

echo "============================================================"
echo "  Diagnostic complete. Output files in: ${OUTDIR}"
echo "============================================================"
