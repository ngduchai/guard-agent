#!/usr/bin/env bash
# ============================================================================
# debug_dmtcp_hang.sh – Why does dmtcp_launch hang on Aurora?
#
# Phase 8 findings:
#   - Coordinator starts fine, dmtcp_command can reach it from all hostnames
#   - dmtcp_launch with -h localhost HANGS (exit 124 = timeout)
#   - dmtcp_launch with -h 127.0.0.1 or hostname gets "Connection refused"
#     (because coordinator died after the localhost test timed out)
#   - No /tmp/dmtcp-* directory created (DMTCP never initializes)
#   - Exit code 99 = JASSERT failure in coordinatorapi.cpp:553
#
# This script focuses on WHY dmtcp_launch hangs when connecting to coordinator.
# ============================================================================

set +e

MANA_ROOT="${MANA_ROOT:-${HOME}/.local/share/guard-agent/dmtcp-src/mana}"
MANA_BIN="${MANA_ROOT}/bin"
MANA_LIB="${MANA_ROOT}/lib/dmtcp"
COORD_PORT="${COORD_PORT:-7911}"
OUTDIR="${HOME}/diaspora/guard-agent/build/test_dmtcp_hang/output"
CKPT_DIR="${HOME}/diaspora/guard-agent/build/test_dmtcp_hang/ckpt"

mkdir -p "${OUTDIR}" "${CKPT_DIR}"

export HWLOC_COMPONENTS="-linuxio"

echo "============================================================"
echo "  DMTCP Hang Diagnosis"
echo "============================================================"
echo ""

# Kill any existing coordinator
"${MANA_BIN}/dmtcp_command" --port "${COORD_PORT}" --quit 2>/dev/null || true
sleep 0.5

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
    ${CC_CMD} -o "${OUTDIR}/hello" "${OUTDIR}/hello.c" 2>&1
fi

# ── Test 1: Start coordinator WITHOUT --exit-on-last ──────────────────
echo "=== Test 1: Start coordinator (persistent, no --exit-on-last) ==="
echo ""

# Start coordinator that stays alive
"${MANA_BIN}/dmtcp_coordinator" -q --daemon \
    --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1
echo "Coordinator started on port ${COORD_PORT}, exit code: $?"

# Verify it's running
"${MANA_BIN}/dmtcp_command" -h localhost --port "${COORD_PORT}" -s 2>&1
echo ""

# ── Test 2: dmtcp_launch with --new-coordinator (no join) ─────────────
echo "=== Test 2: dmtcp_launch with --new-coordinator (different port) ==="
echo ""

NEW_PORT=$((COORD_PORT + 1))
echo "Running: dmtcp_launch --new-coordinator -p ${NEW_PORT} hello"
export JASSERT_STDERR=1
timeout 10 "${MANA_BIN}/dmtcp_launch" \
    --new-coordinator -p "${NEW_PORT}" \
    --no-gzip \
    "${OUTDIR}/hello" > "${OUTDIR}/test2_stdout.txt" 2> "${OUTDIR}/test2_stderr.txt"
echo "Exit code: $?"
echo "--- stdout ---"
cat "${OUTDIR}/test2_stdout.txt" 2>/dev/null
echo "--- stderr (last 20 lines) ---"
tail -20 "${OUTDIR}/test2_stderr.txt" 2>/dev/null
echo ""

# ── Test 3: dmtcp_launch with --any-coordinator (default) ─────────────
echo "=== Test 3: dmtcp_launch with --any-coordinator (default behavior) ==="
echo ""

ANY_PORT=$((COORD_PORT + 2))
echo "Running: dmtcp_launch --any-coordinator -p ${ANY_PORT} hello"
timeout 10 "${MANA_BIN}/dmtcp_launch" \
    --any-coordinator -p "${ANY_PORT}" \
    --no-gzip \
    "${OUTDIR}/hello" > "${OUTDIR}/test3_stdout.txt" 2> "${OUTDIR}/test3_stderr.txt"
echo "Exit code: $?"
echo "--- stdout ---"
cat "${OUTDIR}/test3_stdout.txt" 2>/dev/null
echo "--- stderr (last 20 lines) ---"
tail -20 "${OUTDIR}/test3_stderr.txt" 2>/dev/null
echo ""

# ── Test 4: dmtcp_launch with --join-coordinator to running coord ─────
echo "=== Test 4: dmtcp_launch with --join-coordinator to running coordinator ==="
echo ""

# Verify coordinator is still alive
echo "Coordinator status before test:"
"${MANA_BIN}/dmtcp_command" -h localhost --port "${COORD_PORT}" -s 2>&1
echo ""

echo "Running: dmtcp_launch -j -h localhost -p ${COORD_PORT} hello"
timeout 10 "${MANA_BIN}/dmtcp_launch" \
    -j -h localhost -p "${COORD_PORT}" \
    --no-gzip \
    "${OUTDIR}/hello" > "${OUTDIR}/test4_stdout.txt" 2> "${OUTDIR}/test4_stderr.txt"
echo "Exit code: $?"
echo "--- stdout ---"
cat "${OUTDIR}/test4_stdout.txt" 2>/dev/null
echo "--- stderr (last 20 lines) ---"
tail -20 "${OUTDIR}/test4_stderr.txt" 2>/dev/null
echo ""

echo "Coordinator status after test:"
"${MANA_BIN}/dmtcp_command" -h localhost --port "${COORD_PORT}" -s 2>&1
echo ""

# ── Test 5: strace dmtcp_launch to see where it hangs ────────────────
echo "=== Test 5: strace dmtcp_launch (where does it hang?) ==="
echo ""

if command -v strace >/dev/null 2>&1; then
    echo "Running: strace -f -e trace=network,process dmtcp_launch -j -h localhost -p ${COORD_PORT} hello"
    timeout 10 strace -f -e trace=network,process \
        -o "${OUTDIR}/strace_dmtcp.log" \
        "${MANA_BIN}/dmtcp_launch" \
        -j -h localhost -p "${COORD_PORT}" \
        --no-gzip \
        "${OUTDIR}/hello" > "${OUTDIR}/test5_stdout.txt" 2> "${OUTDIR}/test5_stderr.txt"
    echo "Exit code: $?"
    echo ""
    
    echo "--- strace: connect() calls ---"
    grep 'connect(' "${OUTDIR}/strace_dmtcp.log" 2>/dev/null
    echo ""
    
    echo "--- strace: socket() calls ---"
    grep 'socket(' "${OUTDIR}/strace_dmtcp.log" 2>/dev/null
    echo ""
    
    echo "--- strace: clone/fork ---"
    grep -E 'clone|fork|exec' "${OUTDIR}/strace_dmtcp.log" 2>/dev/null | head -20
    echo ""
    
    echo "--- strace: last 30 lines ---"
    tail -30 "${OUTDIR}/strace_dmtcp.log" 2>/dev/null
    echo ""
else
    echo "strace not available"
fi

# ── Test 6: Check if DMTCP_TMPDIR matters ────────────────────────────
echo "=== Test 6: dmtcp_launch with explicit DMTCP_TMPDIR ==="
echo ""

export DMTCP_TMPDIR="${OUTDIR}/dmtcp_tmp"
mkdir -p "${DMTCP_TMPDIR}"

echo "Running: DMTCP_TMPDIR=${DMTCP_TMPDIR} dmtcp_launch --new-coordinator hello"
timeout 10 "${MANA_BIN}/dmtcp_launch" \
    --new-coordinator -p $((COORD_PORT + 3)) \
    --tmpdir "${DMTCP_TMPDIR}" \
    --no-gzip \
    "${OUTDIR}/hello" > "${OUTDIR}/test6_stdout.txt" 2> "${OUTDIR}/test6_stderr.txt"
echo "Exit code: $?"
echo "--- stdout ---"
cat "${OUTDIR}/test6_stdout.txt" 2>/dev/null
echo "--- stderr (last 20 lines) ---"
tail -20 "${OUTDIR}/test6_stderr.txt" 2>/dev/null
echo ""

echo "DMTCP_TMPDIR contents:"
ls -la "${DMTCP_TMPDIR}/" 2>/dev/null
echo ""

echo "/tmp/dmtcp-* contents:"
ls -la /tmp/dmtcp-${USER}@* 2>/dev/null || echo "  (none)"
echo ""

unset DMTCP_TMPDIR

# ── Test 7: Check /tmp permissions and filesystem ────────────────────
echo "=== Test 7: /tmp filesystem check ==="
echo ""

echo "df /tmp:"
df -h /tmp 2>/dev/null
echo ""

echo "mount | grep tmp:"
mount 2>/dev/null | grep -i tmp
echo ""

echo "ls -la /tmp/ | head:"
ls -la /tmp/ 2>/dev/null | head -10
echo ""

echo "Can write to /tmp?"
touch /tmp/test_dmtcp_write_$$ 2>&1 && echo "  YES" && rm -f /tmp/test_dmtcp_write_$$
echo ""

echo "Can create directory in /tmp?"
mkdir -p /tmp/test_dmtcp_dir_$$ 2>&1 && echo "  YES" && rmdir /tmp/test_dmtcp_dir_$$
echo ""

# ── Test 8: Check if DMTCP uses /proc/self/exe or similar ────────────
echo "=== Test 8: DMTCP binary analysis ==="
echo ""

echo "dmtcp_launch file type:"
file "${MANA_BIN}/dmtcp_launch" 2>/dev/null
echo ""

echo "dmtcp_launch linked libraries:"
ldd "${MANA_BIN}/dmtcp_launch" 2>/dev/null | head -20
echo ""

echo "dmtcp_launch RPATH:"
readelf -d "${MANA_BIN}/dmtcp_launch" 2>/dev/null | grep -i 'rpath\|runpath'
echo ""

echo "DMTCP plugins directory:"
ls -la "${MANA_ROOT}/lib/dmtcp/" 2>/dev/null
echo ""

# ── Test 9: Simplest possible DMTCP test ─────────────────────────────
echo "=== Test 9: Simplest possible DMTCP (no flags, default everything) ==="
echo ""

echo "Running: dmtcp_launch /bin/echo hello"
timeout 10 "${MANA_BIN}/dmtcp_launch" \
    /bin/echo hello > "${OUTDIR}/test9_stdout.txt" 2> "${OUTDIR}/test9_stderr.txt"
echo "Exit code: $?"
echo "--- stdout ---"
cat "${OUTDIR}/test9_stdout.txt" 2>/dev/null
echo "--- stderr (last 20 lines) ---"
tail -20 "${OUTDIR}/test9_stderr.txt" 2>/dev/null
echo ""

unset JASSERT_STDERR

# Cleanup
"${MANA_BIN}/dmtcp_command" --port "${COORD_PORT}" --quit 2>/dev/null || true
"${MANA_BIN}/dmtcp_command" --port $((COORD_PORT + 1)) --quit 2>/dev/null || true
"${MANA_BIN}/dmtcp_command" --port $((COORD_PORT + 2)) --quit 2>/dev/null || true
"${MANA_BIN}/dmtcp_command" --port $((COORD_PORT + 3)) --quit 2>/dev/null || true

echo "============================================================"
echo "  DMTCP Hang Diagnosis complete. Output in: ${OUTDIR}"
echo "============================================================"
