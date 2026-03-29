#!/usr/bin/env bash
# ============================================================================
# debug_dmtcp_hang4.sh – Find the exact busy-loop location in libdmtcp.so
#
# Phase 3 findings:
#   - Process state: R (running) — confirmed CPU busy loop in userspace
#   - /proc/PID/syscall: "running" — not in any syscall
#   - No GDB on Aurora compute nodes
#   - --disable-all-plugins also hangs — core libdmtcp.so issue
#   - DMTCP source at ${HOME}/.local/share/guard-agent/dmtcp-src/dmtcp/
#
# This script:
#   1. Finds the constructor in libdmtcp.so using objdump
#   2. Reads DMTCP source to understand the constructor
#   3. Uses /proc/PID/stat to sample the instruction pointer
#   4. Uses addr2line to map addresses to source lines
# ============================================================================

set +e

MANA_ROOT="${MANA_ROOT:-${HOME}/.local/share/guard-agent/dmtcp-src/mana}"
MANA_BIN="${MANA_ROOT}/bin"
MANA_LIB="${MANA_ROOT}/lib/dmtcp"
DMTCP_SRC="${HOME}/.local/share/guard-agent/dmtcp-src/dmtcp"
OUTDIR="${HOME}/diaspora/guard-agent/build/test_dmtcp_hang4/output"

mkdir -p "${OUTDIR}"

export HWLOC_COMPONENTS="-linuxio"

echo "============================================================"
echo "  DMTCP Hang Diagnosis - Phase 4 (Exact Location)"
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

# ── Test 1: Find .init_array / constructors in libdmtcp.so ───────────
echo "=== Test 1: libdmtcp.so constructors (.init_array) ==="
echo ""

echo "readelf -d libdmtcp.so (INIT/INIT_ARRAY):"
readelf -d "${MANA_LIB}/libdmtcp.so" 2>/dev/null | grep -iE 'INIT|FINI'
echo ""

echo "readelf -S libdmtcp.so (.init_array section):"
readelf -S "${MANA_LIB}/libdmtcp.so" 2>/dev/null | grep -iE 'init_array|ctors'
echo ""

echo "objdump -s -j .init_array libdmtcp.so:"
objdump -s -j .init_array "${MANA_LIB}/libdmtcp.so" 2>/dev/null
echo ""

echo "objdump -t libdmtcp.so | grep constructor/init:"
objdump -t "${MANA_LIB}/libdmtcp.so" 2>/dev/null | grep -iE 'constructor\|_GLOBAL__sub_I\|__static_init\|frame_dummy' | head -20
echo ""

# ── Test 2: DMTCP source - constructor functions ─────────────────────
echo "=== Test 2: DMTCP source constructor functions ==="
echo ""

echo "DMTCP source directory:"
ls "${DMTCP_SRC}/src/" 2>/dev/null | head -30
echo ""

echo "Constructor attributes in DMTCP source:"
grep -rn '__attribute__.*constructor' "${DMTCP_SRC}/src/" 2>/dev/null | head -20
echo ""

echo "DmtcpWorker constructor (first 50 lines):"
grep -n -A 50 'DmtcpWorker::DmtcpWorker' "${DMTCP_SRC}/src/dmtcpworker.cpp" 2>/dev/null | head -55
echo ""

echo "initializeMtcpEngine:"
grep -n -A 30 'initializeMtcpEngine' "${DMTCP_SRC}/src/mtcpinterface.cpp" 2>/dev/null | head -35
echo ""

echo "ThreadList::init:"
grep -n -A 30 'void ThreadList::init' "${DMTCP_SRC}/src/threadlist.cpp" 2>/dev/null | head -35
echo ""

echo "MTCP thread_start / thread_init:"
grep -rn 'thread_start\|thread_init\|mtcp_sys_' "${DMTCP_SRC}/src/mtcp/" 2>/dev/null | head -20
echo ""

# ── Test 3: Sample instruction pointer of hanging process ────────────
echo "=== Test 3: Sample instruction pointer ==="
echo ""

# Launch hanging process
LD_PRELOAD="${MANA_LIB}/libdmtcp.so" "${OUTDIR}/hello" &
HANG_PID=$!
sleep 2

if kill -0 ${HANG_PID} 2>/dev/null; then
    echo "Process PID=${HANG_PID} is hanging"
    echo ""
    
    # Get the base address of libdmtcp.so
    DMTCP_BASE=$(grep 'libdmtcp.so' /proc/${HANG_PID}/maps 2>/dev/null | head -1 | cut -d'-' -f1)
    echo "libdmtcp.so base address: 0x${DMTCP_BASE}"
    echo ""
    
    # Sample the instruction pointer using /proc/PID/stat
    # Field 30 (kstkeip) is the instruction pointer
    echo "Sampling instruction pointer from /proc/${HANG_PID}/stat (10 samples):"
    for i in $(seq 1 10); do
        # /proc/PID/stat field 30 is kstkeip (instruction pointer)
        STAT=$(cat /proc/${HANG_PID}/stat 2>/dev/null)
        # Extract field 30 (kstkeip)
        IP=$(echo "${STAT}" | awk '{print $30}')
        echo "  Sample ${i}: IP=${IP} (hex: $(printf '0x%x' ${IP} 2>/dev/null))"
        sleep 0.2
    done
    echo ""
    
    # Also try /proc/PID/syscall which shows sp and ip when running
    echo "/proc/${HANG_PID}/syscall (5 samples):"
    for i in $(seq 1 5); do
        cat /proc/${HANG_PID}/syscall 2>/dev/null
        echo ""
        sleep 0.2
    done
    echo ""
    
    # Try to use addr2line if available
    if command -v addr2line >/dev/null 2>&1 && [ -n "${DMTCP_BASE}" ]; then
        echo "addr2line for sampled IPs:"
        for i in $(seq 1 3); do
            IP=$(cat /proc/${HANG_PID}/stat 2>/dev/null | awk '{print $30}')
            if [ -n "${IP}" ] && [ "${IP}" != "0" ]; then
                # Calculate offset from base
                OFFSET=$(printf '0x%x' $((IP - 0x${DMTCP_BASE})) 2>/dev/null)
                echo "  IP=0x$(printf '%x' ${IP}), offset=${OFFSET}:"
                addr2line -e "${MANA_LIB}/libdmtcp.so" -f -C "${OFFSET}" 2>/dev/null
            fi
            sleep 0.2
        done
        echo ""
    fi
    
    # Try perf if available
    if command -v perf >/dev/null 2>&1; then
        echo "perf top for PID ${HANG_PID} (3 second sample):"
        timeout 3 perf record -p ${HANG_PID} -o "${OUTDIR}/perf.data" 2>/dev/null
        perf report -i "${OUTDIR}/perf.data" --stdio 2>/dev/null | head -30
        echo ""
    fi
    
    kill -9 ${HANG_PID} 2>/dev/null
    wait ${HANG_PID} 2>/dev/null
fi
echo ""

# ── Test 4: Disassemble libdmtcp.so around the _init function ────────
echo "=== Test 4: Disassemble libdmtcp.so _init and constructors ==="
echo ""

# Get the _init address
INIT_ADDR=$(readelf -d "${MANA_LIB}/libdmtcp.so" 2>/dev/null | grep 'INIT)' | awk '{print $3}' | head -1)
echo "INIT address: ${INIT_ADDR}"

if [ -n "${INIT_ADDR}" ]; then
    echo "Disassembly around INIT (${INIT_ADDR}):"
    objdump -d --start-address="${INIT_ADDR}" "${MANA_LIB}/libdmtcp.so" 2>/dev/null | head -30
    echo ""
fi

# Get .init_array entries and disassemble each
echo "Disassembling .init_array function pointers:"
objdump -s -j .init_array "${MANA_LIB}/libdmtcp.so" 2>/dev/null | tail -n +5 | while read -r line; do
    # Parse hex bytes from objdump output
    ADDR_PART=$(echo "${line}" | awk '{print $2 $3 $4 $5}')
    if [ -n "${ADDR_PART}" ]; then
        # Convert little-endian hex to address (take first 8 bytes = 16 hex chars)
        # Each column is 4 bytes in little-endian
        for col in 2 3 4 5; do
            HEX=$(echo "${line}" | awk "{print \$$col}")
            if [ -n "${HEX}" ] && [ "${#HEX}" -eq 8 ]; then
                # Reverse byte order (little-endian to big-endian)
                REVERSED="${HEX:6:2}${HEX:4:2}${HEX:2:2}${HEX:0:2}"
                FUNC_ADDR="0x${REVERSED}"
                # Only process non-zero addresses
                if [ "${FUNC_ADDR}" != "0x00000000" ]; then
                    echo "  Constructor at ${FUNC_ADDR}:"
                    objdump -d --start-address="${FUNC_ADDR}" "${MANA_LIB}/libdmtcp.so" 2>/dev/null | head -5
                    if command -v addr2line >/dev/null 2>&1; then
                        addr2line -e "${MANA_LIB}/libdmtcp.so" -f -C "${FUNC_ADDR}" 2>/dev/null
                    fi
                    echo ""
                fi
            fi
        done
    fi
done
echo ""

# ── Test 5: Check DMTCP's MTCP code for busy loops ──────────────────
echo "=== Test 5: MTCP busy loop patterns ==="
echo ""

echo "Spin loops in DMTCP source:"
grep -rn 'while.*true\|for.*;;.*\|while.*1\)\|SPIN\|spin_lock\|busy.*wait\|busywait' \
    "${DMTCP_SRC}/src/" "${DMTCP_SRC}/src/mtcp/" 2>/dev/null | head -20
echo ""

echo "Atomic operations / CAS loops:"
grep -rn 'compare_exchange\|__sync_\|__atomic_\|cmpxchg\|xchg' \
    "${DMTCP_SRC}/src/" "${DMTCP_SRC}/src/mtcp/" 2>/dev/null | head -20
echo ""

echo "Signal-based synchronization:"
grep -rn 'sigwait\|sigsuspend\|sigtimedwait\|sem_wait\|futex' \
    "${DMTCP_SRC}/src/" "${DMTCP_SRC}/src/mtcp/" 2>/dev/null | head -20
echo ""

# ── Test 6: Check if DMTCP was built with debug info ─────────────────
echo "=== Test 6: Debug info in libdmtcp.so ==="
echo ""

echo "Has debug info?"
readelf -S "${MANA_LIB}/libdmtcp.so" 2>/dev/null | grep -i debug
echo ""

echo "file command:"
file "${MANA_LIB}/libdmtcp.so" 2>/dev/null
echo ""

# ── Test 7: Check DMTCP config.log for build details ─────────────────
echo "=== Test 7: DMTCP build configuration ==="
echo ""

echo "config.log (first 30 lines):"
head -30 "${DMTCP_SRC}/config.log" 2>/dev/null
echo ""

echo "config.status:"
head -10 "${DMTCP_SRC}/config.status" 2>/dev/null
echo ""

echo "Makefile CC/CXX:"
grep -E '^CC |^CXX |^CFLAGS |^CXXFLAGS ' "${DMTCP_SRC}/Makefile" 2>/dev/null | head -10
echo ""

echo "============================================================"
echo "  Phase 4 complete. Output in: ${OUTDIR}"
echo "============================================================"
