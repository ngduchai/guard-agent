#!/usr/bin/env bash
# ============================================================================
# debug_dmtcp_hang3.sh – Pinpoint the busy-loop in libdmtcp.so constructor
#
# Phase 2 findings:
#   - After execve, the target process loads libdmtcp.so via LD_PRELOAD
#   - Last syscall is brk() at 05:22:29.279439
#   - SIGTERM arrives at 05:22:44.027516 (~15 seconds later)
#   - NO syscalls in between = process is in a USERSPACE BUSY LOOP
#   - LD_PRELOAD=libdmtcp.so hello also hangs (no coordinator needed)
#   - JASSERT_STDERR=1 produces no output (hang before JASSERT init)
#   - AppArmor is ENABLED (lockdown,capability,apparmor)
#
# This script:
#   1. Uses GDB to find where the busy loop is
#   2. Checks AppArmor profiles
#   3. Tests with --disable-all-plugins
#   4. Checks DMTCP source for constructor functions
# ============================================================================

set +e

MANA_ROOT="${MANA_ROOT:-${HOME}/.local/share/guard-agent/dmtcp-src/mana}"
MANA_BIN="${MANA_ROOT}/bin"
MANA_LIB="${MANA_ROOT}/lib/dmtcp"
DMTCP_SRC="${MANA_ROOT}/.."
COORD_PORT="${COORD_PORT:-7916}"
OUTDIR="${HOME}/diaspora/guard-agent/build/test_dmtcp_hang3/output"
CKPT_DIR="${HOME}/diaspora/guard-agent/build/test_dmtcp_hang3/ckpt"

mkdir -p "${OUTDIR}" "${CKPT_DIR}"

export HWLOC_COMPONENTS="-linuxio"

echo "============================================================"
echo "  DMTCP Hang Diagnosis - Phase 3 (Busy Loop Location)"
echo "============================================================"
echo ""

# Compile simple test
cat > "${OUTDIR}/hello.c" << 'EOF'
#include <stdio.h>
#include <unistd.h>
int main() {
    printf("Hello from DMTCP test (pid=%d)\n", getpid());
    fflush(stdout);
    return 0;
}
EOF

CC_CMD=""
if command -v gcc >/dev/null 2>&1; then CC_CMD="gcc";
elif command -v icx >/dev/null 2>&1; then CC_CMD="icx";
fi

if [ -n "${CC_CMD}" ]; then
    ${CC_CMD} -g -o "${OUTDIR}/hello" "${OUTDIR}/hello.c" 2>&1
fi

# ── Test 1: AppArmor investigation ────────────────────────────────────
echo "=== Test 1: AppArmor investigation ==="
echo ""

echo "AppArmor enabled:"
cat /sys/module/apparmor/parameters/enabled 2>/dev/null
echo ""

echo "AppArmor mode:"
cat /sys/module/apparmor/parameters/mode 2>/dev/null || echo "  (not available)"
echo ""

echo "AppArmor profiles:"
cat /sys/kernel/security/apparmor/profiles 2>/dev/null | head -20 || echo "  (not available or no permission)"
echo ""

echo "aa-status (if available):"
aa-status 2>/dev/null | head -20 || echo "  (not available)"
echo ""

echo "dmesg AppArmor entries (last 20):"
dmesg 2>/dev/null | grep -i apparmor | tail -20 || echo "  (not available)"
echo ""

# ── Test 2: Find DMTCP constructor functions ─────────────────────────
echo "=== Test 2: DMTCP constructor functions ==="
echo ""

echo "Constructor attributes in DMTCP source:"
grep -rn '__attribute__.*constructor\|__attribute__.*init_priority' \
    "${DMTCP_SRC}/src/" "${DMTCP_SRC}/jalib/" \
    2>/dev/null | grep -v '.o:' | head -20
echo ""

echo "DmtcpWorker constructor:"
grep -rn 'DmtcpWorker\|dmtcpWorker\|DMTCP_WORKER' \
    "${DMTCP_SRC}/src/dmtcpworker.cpp" "${DMTCP_SRC}/src/dmtcpworker.h" \
    2>/dev/null | head -20
echo ""

echo "initializeMtcpEngine / mtcp:"
grep -rn 'initializeMtcpEngine\|mtcp_init\|ThreadList::init' \
    "${DMTCP_SRC}/src/" 2>/dev/null | grep -v '.o:' | head -20
echo ""

# ── Test 3: GDB backtrace of the hanging process ─────────────────────
echo "=== Test 3: GDB backtrace of hanging process ==="
echo ""

if command -v gdb >/dev/null 2>&1; then
    # Launch the hanging process in background
    LD_PRELOAD="${MANA_LIB}/libdmtcp.so" "${OUTDIR}/hello" &
    HANG_PID=$!
    echo "Launched hello with LD_PRELOAD, PID=${HANG_PID}"
    
    # Wait a moment for it to start hanging
    sleep 2
    
    # Check if it's still running (should be, since it hangs)
    if kill -0 ${HANG_PID} 2>/dev/null; then
        echo "Process is still running (confirmed hang)"
        echo ""
        
        # Get backtrace with GDB
        echo "GDB backtrace:"
        gdb -batch -ex "thread apply all bt" -p ${HANG_PID} 2>&1 | head -50
        echo ""
        
        echo "GDB info registers:"
        gdb -batch -ex "info registers rip rsp rbp" -p ${HANG_PID} 2>&1 | head -10
        echo ""
        
        echo "GDB disassemble at current location:"
        gdb -batch -ex "x/20i \$rip" -p ${HANG_PID} 2>&1 | head -25
        echo ""
        
        # Kill the hanging process
        kill -9 ${HANG_PID} 2>/dev/null
        wait ${HANG_PID} 2>/dev/null
    else
        echo "Process already exited (not hanging?)"
        wait ${HANG_PID} 2>/dev/null
        echo "Exit code: $?"
    fi
else
    echo "GDB not available"
    echo ""
    
    # Alternative: use /proc/PID/syscall and /proc/PID/wchan
    echo "Using /proc to inspect hanging process..."
    LD_PRELOAD="${MANA_LIB}/libdmtcp.so" "${OUTDIR}/hello" &
    HANG_PID=$!
    sleep 2
    
    if kill -0 ${HANG_PID} 2>/dev/null; then
        echo "Process PID=${HANG_PID} is hanging"
        echo ""
        
        echo "/proc/${HANG_PID}/status:"
        cat /proc/${HANG_PID}/status 2>/dev/null | head -20
        echo ""
        
        echo "/proc/${HANG_PID}/syscall:"
        cat /proc/${HANG_PID}/syscall 2>/dev/null
        echo ""
        
        echo "/proc/${HANG_PID}/wchan:"
        cat /proc/${HANG_PID}/wchan 2>/dev/null
        echo ""
        
        echo "/proc/${HANG_PID}/stack:"
        cat /proc/${HANG_PID}/stack 2>/dev/null | head -20
        echo ""
        
        echo "/proc/${HANG_PID}/maps (libdmtcp region):"
        grep 'libdmtcp\|dmtcp' /proc/${HANG_PID}/maps 2>/dev/null
        echo ""
        
        # Sample the instruction pointer multiple times
        echo "Sampling RIP (instruction pointer) 5 times:"
        for i in 1 2 3 4 5; do
            cat /proc/${HANG_PID}/syscall 2>/dev/null
            sleep 0.5
        done
        echo ""
        
        kill -9 ${HANG_PID} 2>/dev/null
        wait ${HANG_PID} 2>/dev/null
    fi
fi
echo ""

# ── Test 4: dmtcp_launch with --disable-all-plugins ──────────────────
echo "=== Test 4: dmtcp_launch with --disable-all-plugins ==="
echo ""

# Start coordinator
"${MANA_BIN}/dmtcp_command" --port "${COORD_PORT}" --quit 2>/dev/null || true
sleep 0.5
"${MANA_BIN}/dmtcp_coordinator" -q --daemon \
    --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1

echo "Running: dmtcp_launch --disable-all-plugins -j -h localhost -p ${COORD_PORT} hello"
timeout 10 "${MANA_BIN}/dmtcp_launch" \
    --disable-all-plugins \
    -j -h localhost -p "${COORD_PORT}" \
    --no-gzip \
    "${OUTDIR}/hello" > "${OUTDIR}/test4_stdout.txt" 2> "${OUTDIR}/test4_stderr.txt"
echo "Exit code: $?"
echo "--- stdout ---"
cat "${OUTDIR}/test4_stdout.txt" 2>/dev/null
echo "--- stderr ---"
tail -20 "${OUTDIR}/test4_stderr.txt" 2>/dev/null
echo ""

# ── Test 5: Check DMTCP's ThreadList / MTCP initialization ───────────
echo "=== Test 5: DMTCP ThreadList / MTCP source ==="
echo ""

echo "ThreadList::init source:"
grep -A 30 'void ThreadList::init' "${DMTCP_SRC}/src/threadlist.cpp" 2>/dev/null | head -35
echo ""

echo "initializeMtcpEngine source:"
grep -A 30 'initializeMtcpEngine' "${DMTCP_SRC}/src/mtcpinterface.cpp" 2>/dev/null | head -35
echo ""

echo "DmtcpWorker constructor source:"
grep -A 40 'DmtcpWorker::DmtcpWorker' "${DMTCP_SRC}/src/dmtcpworker.cpp" 2>/dev/null | head -45
echo ""

# ── Test 6: Check if the issue is the DMTCP build (icx vs gcc) ──────
echo "=== Test 6: DMTCP build compiler ==="
echo ""

echo "How was DMTCP built?"
head -20 "${DMTCP_SRC}/config.log" 2>/dev/null
echo ""

echo "DMTCP configure flags:"
grep 'configure' "${DMTCP_SRC}/config.log" 2>/dev/null | head -5
echo ""

echo "CC/CXX used:"
grep -E '^CC=|^CXX=|^CFLAGS=|^CXXFLAGS=' "${DMTCP_SRC}/config.log" 2>/dev/null | head -10
echo ""

# ── Test 7: nm libdmtcp.so for constructor symbols ──────────────────
echo "=== Test 7: libdmtcp.so constructor symbols ==="
echo ""

echo "Constructor/init symbols in libdmtcp.so:"
nm "${MANA_LIB}/libdmtcp.so" 2>/dev/null | grep -iE 'constructor\|_init\|dmtcpWorker\|ThreadList' | head -20
echo ""

echo "All global text symbols in libdmtcp.so (first 30):"
nm -g "${MANA_LIB}/libdmtcp.so" 2>/dev/null | grep ' T ' | head -30
echo ""

# Cleanup
"${MANA_BIN}/dmtcp_command" --port "${COORD_PORT}" --quit 2>/dev/null || true

echo "============================================================"
echo "  Phase 3 complete. Output in: ${OUTDIR}"
echo "============================================================"
