#!/usr/bin/env bash
# ============================================================================
# debug_mana_sigsegv6.sh – Isolate MANA SIGSEGV on Aurora
#
# The Makefile_config fix didn't resolve the crash. The lower-half was already
# linking against the correct Cray MPICH. The SIGSEGV is deeper.
#
# This script isolates the crash by testing each layer independently:
#   1. lower-half alone (no DMTCP)
#   2. DMTCP alone (no MANA plugin)
#   3. DMTCP + MANA plugin
#   4. Examine the crash address and memory maps
# ============================================================================

set -euo pipefail

MANA_ROOT="${MANA_ROOT:-${HOME}/.local/share/guard-agent/dmtcp-src/mana}"
MANA_BIN="${MANA_ROOT}/bin"
MANA_LIB="${MANA_ROOT}/lib/dmtcp"
COORD_PORT="${COORD_PORT:-7908}"
COORD_HOST="$(hostname)"
OUTDIR="${HOME}/diaspora/guard-agent/build/test_mana_debug6/output"
CKPT_DIR="${HOME}/diaspora/guard-agent/build/test_mana_debug6/ckpt"

mkdir -p "${OUTDIR}" "${CKPT_DIR}"

export HWLOC_COMPONENTS="-linuxio"

echo "============================================================"
echo "  MANA SIGSEGV Isolation (Phase 6)"
echo "============================================================"
echo ""

# ── Test 1: lower-half directly with correct LD_LIBRARY_PATH ──────────
echo "=== Test 1: lower-half directly (with LD_LIBRARY_PATH) ==="
echo ""

MANA_TEST=$(find "${MANA_ROOT}/mpi-proxy-split/test" -name "*.mana.exe" -type f 2>/dev/null | head -1)
if [[ -z "${MANA_TEST}" ]]; then
    echo "No .mana.exe test found"
else
    echo "Test binary: ${MANA_TEST}"
    echo "lower-half: ${MANA_BIN}/lower-half"
    echo ""
    
    # Set LD_LIBRARY_PATH to include libmpistub.so
    export LD_LIBRARY_PATH="${MANA_LIB}:${LD_LIBRARY_PATH:-}"
    
    echo "LD_LIBRARY_PATH: ${LD_LIBRARY_PATH}"
    echo ""
    
    echo "ldd of test binary:"
    ldd "${MANA_TEST}" 2>&1 | head -20
    echo ""
    
    echo "Running: ${MANA_BIN}/lower-half ${MANA_TEST}"
    timeout 10 "${MANA_BIN}/lower-half" "${MANA_TEST}" > "${OUTDIR}/test1_stdout.txt" 2> "${OUTDIR}/test1_stderr.txt" || true
    echo "Exit code: $?"
    echo "--- stdout ---"
    cat "${OUTDIR}/test1_stdout.txt" 2>/dev/null || true
    echo "--- stderr ---"
    cat "${OUTDIR}/test1_stderr.txt" 2>/dev/null || true
    echo ""
    
    echo "Running with mpiexec: mpiexec -np 1 ${MANA_BIN}/lower-half ${MANA_TEST}"
    timeout 10 mpiexec -np 1 "${MANA_BIN}/lower-half" "${MANA_TEST}" > "${OUTDIR}/test1b_stdout.txt" 2> "${OUTDIR}/test1b_stderr.txt" || true
    echo "Exit code: $?"
    echo "--- stdout ---"
    cat "${OUTDIR}/test1b_stdout.txt" 2>/dev/null || true
    echo "--- stderr ---"
    cat "${OUTDIR}/test1b_stderr.txt" 2>/dev/null || true
fi
echo ""

# ── Test 2: Simple hello world with DMTCP (no MANA) ──────────────────
echo "=== Test 2: DMTCP alone (no MANA plugin) ==="
echo ""

# Create a simple test program
SIMPLE_TEST="${OUTDIR}/hello_dmtcp"
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

if command -v gcc &>/dev/null; then
    gcc -o "${SIMPLE_TEST}" "${OUTDIR}/hello_dmtcp.c" 2>/dev/null
elif command -v icx &>/dev/null; then
    icx -o "${SIMPLE_TEST}" "${OUTDIR}/hello_dmtcp.c" 2>/dev/null
fi

if [[ -x "${SIMPLE_TEST}" ]]; then
    # Start coordinator
    "${MANA_BIN}/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
    sleep 0.5
    "${MANA_BIN}/dmtcp_coordinator" --daemon --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1 || true
    sleep 1
    
    echo "Running: dmtcp_launch (no MANA plugin) ${SIMPLE_TEST}"
    timeout 15 "${MANA_BIN}/dmtcp_launch" \
        -h "${COORD_HOST}" -p "${COORD_PORT}" \
        --no-gzip --join-coordinator \
        "${SIMPLE_TEST}" > "${OUTDIR}/test2_stdout.txt" 2> "${OUTDIR}/test2_stderr.txt" || true
    echo "Exit code: $?"
    echo "--- stdout ---"
    cat "${OUTDIR}/test2_stdout.txt" 2>/dev/null || true
    echo "--- stderr ---"
    cat "${OUTDIR}/test2_stderr.txt" 2>/dev/null || true
    
    "${MANA_BIN}/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
else
    echo "Could not compile simple test"
fi
echo ""

# ── Test 3: DMTCP + MANA plugin with simple MPI program ──────────────
echo "=== Test 3: DMTCP + MANA plugin (simple MPI) ==="
echo ""

# Create a minimal MPI program
SIMPLE_MPI="${OUTDIR}/hello_mpi"
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

# Build with mpistub
if command -v mpicc &>/dev/null; then
    # First build a normal MPI version to verify MPI works
    echo "Building normal MPI hello..."
    mpicc -o "${OUTDIR}/hello_mpi_normal" "${OUTDIR}/hello_mpi.c" 2>&1 || true
    if [[ -x "${OUTDIR}/hello_mpi_normal" ]]; then
        echo "Running normal MPI hello (no DMTCP):"
        timeout 10 mpiexec -np 1 "${OUTDIR}/hello_mpi_normal" 2>&1 || true
        echo ""
    fi
    
    # Build with mpistub for MANA
    echo "Building MANA-stub MPI hello..."
    MPI_INC="$(mpicc -show 2>/dev/null | grep -oP '\-I\S+' | head -1 || true)"
    if [[ -z "${MPI_INC}" ]]; then
        MPI_INC="-I$(dirname $(which mpicc))/../include"
    fi
    icx ${MPI_INC} -L"${MANA_LIB}" -lmpistub -o "${SIMPLE_MPI}" "${OUTDIR}/hello_mpi.c" 2>&1 || true
fi

if [[ -x "${SIMPLE_MPI}" ]]; then
    echo ""
    echo "ldd of MANA-stub MPI hello:"
    ldd "${SIMPLE_MPI}" 2>&1 | grep -E 'mpi|stub' || echo "  (no mpi/stub libs)"
    echo ""
    
    # Start coordinator
    "${MANA_BIN}/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
    sleep 0.5
    "${MANA_BIN}/dmtcp_coordinator" --daemon --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1 || true
    sleep 1
    
    echo "Running: mpiexec -np 1 mana_launch ${SIMPLE_MPI}"
    timeout 15 mpiexec -np 1 \
        "${MANA_BIN}/mana_launch" --verbose \
        --coord-host "${COORD_HOST}" --coord-port "${COORD_PORT}" \
        --ckptdir "${CKPT_DIR}" --no-gzip \
        "${SIMPLE_MPI}" > "${OUTDIR}/test3_stdout.txt" 2> "${OUTDIR}/test3_stderr.txt" || true
    echo "Exit code: $?"
    echo "--- stdout ---"
    cat "${OUTDIR}/test3_stdout.txt" 2>/dev/null || true
    echo "--- stderr ---"
    cat "${OUTDIR}/test3_stderr.txt" 2>/dev/null || true
    
    "${MANA_BIN}/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
fi
echo ""

# ── Test 4: Check lower-half memory layout ────────────────────────────
echo "=== Test 4: lower-half binary analysis ==="
echo ""

echo "lower-half ELF segments (text segment address):"
readelf -l "${MANA_BIN}/lower-half" 2>/dev/null | grep -E 'LOAD|Entry' || true
echo ""

echo "lower-half symbols related to init/context:"
nm "${MANA_BIN}/lower-half" 2>/dev/null | grep -iE 'init|context|fsbase|gsbase|prctl|arch_' | head -20 || true
echo ""

echo "lower-half NEEDED libraries:"
readelf -d "${MANA_BIN}/lower-half" 2>/dev/null | grep NEEDED || true
echo ""

# ── Test 5: Check if fsgsbase is supported ────────────────────────────
echo "=== Test 5: CPU fsgsbase support ==="
echo ""

echo "CPU flags (fsgsbase):"
grep -o 'fsgsbase' /proc/cpuinfo 2>/dev/null | head -1 || echo "fsgsbase NOT found in /proc/cpuinfo"
echo ""

echo "Kernel version:"
uname -r
echo ""

echo "arch_prctl test:"
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
    
    // Test 1: arch_prctl
    if (syscall(SYS_arch_prctl, ARCH_GET_FS, &fsbase) == 0) {
        printf("arch_prctl ARCH_GET_FS: 0x%lx\n", fsbase);
    } else {
        printf("arch_prctl ARCH_GET_FS: FAILED\n");
    }
    
    // Test 2: rdfsbase instruction
    signal(SIGSEGV, handler);
    signal(SIGILL, handler);
    if (sigsetjmp(jmpbuf, 1) == 0) {
        uint64_t val;
        asm volatile(".byte 0x48; rdfsbase %0" : "=r" (val) :: "memory");
        printf("rdfsbase instruction: 0x%lx (WORKS)\n", val);
    } else {
        printf("rdfsbase instruction: SIGILL/SIGSEGV (NOT supported)\n");
    }
    
    // Test 3: wrfsbase instruction
    if (sigsetjmp(jmpbuf, 1) == 0) {
        asm volatile(".byte 0x48; wrfsbase %0" :: "r" (fsbase) : "memory");
        printf("wrfsbase instruction: WORKS\n");
    } else {
        printf("wrfsbase instruction: SIGILL/SIGSEGV (NOT supported)\n");
    }
    
    return 0;
}
FSGSEOF

if command -v icx &>/dev/null; then
    icx -o "${OUTDIR}/test_fsgsbase" "${OUTDIR}/test_fsgsbase.c" 2>/dev/null
elif command -v gcc &>/dev/null; then
    gcc -o "${OUTDIR}/test_fsgsbase" "${OUTDIR}/test_fsgsbase.c" 2>/dev/null
fi

if [[ -x "${OUTDIR}/test_fsgsbase" ]]; then
    "${OUTDIR}/test_fsgsbase" 2>&1 || true
fi
echo ""

# ── Test 6: Check JASSERT logs with DMTCP_TMPDIR ─────────────────────
echo "=== Test 6: JASSERT logs ==="
echo ""

JASSERT_DIR="${OUTDIR}/jassert_logs"
mkdir -p "${JASSERT_DIR}"

if [[ -n "${MANA_TEST:-}" ]] && [[ -x "${MANA_TEST}" ]]; then
    # Start coordinator
    "${MANA_BIN}/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
    sleep 0.5
    "${MANA_BIN}/dmtcp_coordinator" --daemon --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1 || true
    sleep 1
    
    export DMTCP_TMPDIR="${JASSERT_DIR}"
    export JASSERT_STDERR=1
    
    echo "Running MANA test with JASSERT_STDERR=1 and DMTCP_TMPDIR=${JASSERT_DIR}"
    timeout 15 mpiexec -np 1 \
        "${MANA_BIN}/mana_launch" --verbose \
        --coord-host "${COORD_HOST}" --coord-port "${COORD_PORT}" \
        --ckptdir "${CKPT_DIR}" --no-gzip \
        "${MANA_TEST}" > "${OUTDIR}/test6_stdout.txt" 2> "${OUTDIR}/test6_stderr.txt" || true
    echo "Exit code: $?"
    echo ""
    echo "--- stderr (first 50 lines) ---"
    head -50 "${OUTDIR}/test6_stderr.txt" 2>/dev/null || true
    echo ""
    echo "--- JASSERT log files ---"
    ls -la "${JASSERT_DIR}/" 2>/dev/null || echo "  (no files)"
    for f in "${JASSERT_DIR}"/jassert*; do
        if [[ -f "$f" ]]; then
            echo ""
            echo "--- $f (last 30 lines) ---"
            tail -30 "$f"
        fi
    done
    
    unset DMTCP_TMPDIR JASSERT_STDERR
    "${MANA_BIN}/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
fi
echo ""

# ── Test 7: Check /proc/sys/kernel settings ───────────────────────────
echo "=== Test 7: Kernel settings ==="
echo ""

echo "ASLR (randomize_va_space):"
cat /proc/sys/kernel/randomize_va_space 2>/dev/null || echo "  (cannot read)"
echo ""

echo "ptrace_scope:"
cat /proc/sys/kernel/yama/ptrace_scope 2>/dev/null || echo "  (cannot read)"
echo ""

echo "mmap_min_addr:"
cat /proc/sys/vm/mmap_min_addr 2>/dev/null || echo "  (cannot read)"
echo ""

# ── Test 8: Check if lower-half text segment conflicts ────────────────
echo "=== Test 8: Memory map analysis ==="
echo ""

echo "lower-half is linked with -Ttext-segment=0x10000000"
echo "Checking if this address range is available..."
echo ""

# Run a process and check its memory map
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
            // Check if any region overlaps with 0x10000000-0x20000000
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
    
    printf("\nFull memory map:\n");
    f = fopen("/proc/self/maps", "r");
    while (fgets(line, sizeof(line), f)) {
        printf("  %s", line);
    }
    fclose(f);
    
    return 0;
}
MMAPEOF

if command -v icx &>/dev/null; then
    icx -o "${OUTDIR}/check_mmap" "${OUTDIR}/check_mmap.c" 2>/dev/null
elif command -v gcc &>/dev/null; then
    gcc -o "${OUTDIR}/check_mmap" "${OUTDIR}/check_mmap.c" 2>/dev/null
fi

if [[ -x "${OUTDIR}/check_mmap" ]]; then
    "${OUTDIR}/check_mmap" 2>&1 | head -40 || true
fi
echo ""

# ── Test 9: strace the crash ─────────────────────────────────────────
echo "=== Test 9: strace analysis ==="
echo ""

if command -v strace &>/dev/null; then
    if [[ -n "${MANA_TEST:-}" ]] && [[ -x "${MANA_TEST}" ]]; then
        # Start coordinator
        "${MANA_BIN}/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
        sleep 0.5
        "${MANA_BIN}/dmtcp_coordinator" --daemon --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1 || true
        sleep 1
        
        echo "Running with strace (last 50 syscalls before crash)..."
        timeout 15 mpiexec -np 1 strace -f -o "${OUTDIR}/strace.log" \
            "${MANA_BIN}/mana_launch" --verbose \
            --coord-host "${COORD_HOST}" --coord-port "${COORD_PORT}" \
            --ckptdir "${CKPT_DIR}" --no-gzip \
            "${MANA_TEST}" 2>&1 || true
        
        echo ""
        echo "--- Last 50 lines of strace (main process) ---"
        # Find the process that crashed
        grep -l 'SIGSEGV' "${OUTDIR}/strace.log" 2>/dev/null && \
            tail -50 "${OUTDIR}/strace.log" || \
            echo "  (no SIGSEGV found in strace)"
        echo ""
        
        # Look for the crash specifically
        echo "--- SIGSEGV details ---"
        grep -A2 'SIGSEGV' "${OUTDIR}/strace.log" 2>/dev/null || echo "  (none)"
        echo ""
        
        echo "--- Last mmap/mprotect/arch_prctl calls ---"
        grep -E 'mmap|mprotect|arch_prctl|clone' "${OUTDIR}/strace.log" 2>/dev/null | tail -20 || true
        
        "${MANA_BIN}/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" --quit 2>/dev/null || true
    fi
else
    echo "strace not available"
fi
echo ""

echo "============================================================"
echo "  Diagnostic complete. Output files in: ${OUTDIR}"
echo "============================================================"
