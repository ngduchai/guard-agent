#!/usr/bin/env bash
# ============================================================================
# debug_dmtcp_hang2.sh – Pinpoint where DMTCP hangs after execve
#
# Phase 8/hang findings:
#   - dmtcp_launch successfully connects to coordinator
#   - dmtcp_launch successfully execve()'s the target binary
#   - After execve, the process HANGS (killed by SIGTERM from timeout)
#   - This means libdmtcp.so (LD_PRELOAD) hangs during initialization
#   - No output, no JASSERT errors, no /tmp/dmtcp-* directory
#
# This script captures ALL syscalls after execve to find the hang point.
# ============================================================================

set +e

MANA_ROOT="${MANA_ROOT:-${HOME}/.local/share/guard-agent/dmtcp-src/mana}"
MANA_BIN="${MANA_ROOT}/bin"
MANA_LIB="${MANA_ROOT}/lib/dmtcp"
COORD_PORT="${COORD_PORT:-7915}"
OUTDIR="${HOME}/diaspora/guard-agent/build/test_dmtcp_hang2/output"
CKPT_DIR="${HOME}/diaspora/guard-agent/build/test_dmtcp_hang2/ckpt"

mkdir -p "${OUTDIR}" "${CKPT_DIR}"

export HWLOC_COMPONENTS="-linuxio"

echo "============================================================"
echo "  DMTCP Hang Diagnosis - Phase 2 (Full strace)"
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

# Start persistent coordinator
"${MANA_BIN}/dmtcp_coordinator" -q --daemon \
    --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1
echo "Coordinator started on port ${COORD_PORT}"
echo ""

# ── Test 1: Full strace (ALL syscalls) ────────────────────────────────
echo "=== Test 1: Full strace of dmtcp_launch ==="
echo ""

if command -v strace >/dev/null 2>&1; then
    echo "Running: strace -f -tt dmtcp_launch -j -h localhost -p ${COORD_PORT} hello"
    echo "(timeout 15 seconds)"
    timeout 15 strace -f -tt \
        -o "${OUTDIR}/strace_full.log" \
        "${MANA_BIN}/dmtcp_launch" \
        -j -h localhost -p "${COORD_PORT}" \
        --no-gzip \
        "${OUTDIR}/hello" 2>&1
    echo "Exit code: $?"
    echo ""

    # Find the PID that does the final execve (the target process)
    TARGET_PID=$(grep 'execve.*hello.*= 0' "${OUTDIR}/strace_full.log" 2>/dev/null | tail -1 | awk '{print $1}')
    echo "Target process PID: ${TARGET_PID}"
    echo ""

    if [ -n "${TARGET_PID}" ]; then
        echo "--- Last 50 syscalls of target process (PID ${TARGET_PID}) ---"
        grep "^${TARGET_PID}" "${OUTDIR}/strace_full.log" 2>/dev/null | tail -50
        echo ""

        echo "--- All open/openat calls by target process ---"
        grep "^${TARGET_PID}.*open" "${OUTDIR}/strace_full.log" 2>/dev/null | head -30
        echo ""

        echo "--- All connect/bind/listen calls by target process ---"
        grep "^${TARGET_PID}.*\(connect\|bind\|listen\|accept\)" "${OUTDIR}/strace_full.log" 2>/dev/null
        echo ""

        echo "--- All futex/poll/select/epoll calls by target process ---"
        grep "^${TARGET_PID}.*\(futex\|poll\|select\|epoll\|nanosleep\)" "${OUTDIR}/strace_full.log" 2>/dev/null | tail -20
        echo ""

        echo "--- All mmap/mprotect calls by target process ---"
        grep "^${TARGET_PID}.*\(mmap\|mprotect\)" "${OUTDIR}/strace_full.log" 2>/dev/null | tail -20
        echo ""

        echo "--- All write calls by target process ---"
        grep "^${TARGET_PID}.*write" "${OUTDIR}/strace_full.log" 2>/dev/null | head -20
        echo ""

        echo "--- All read calls by target process (last 20) ---"
        grep "^${TARGET_PID}.*read" "${OUTDIR}/strace_full.log" 2>/dev/null | tail -20
        echo ""
    fi

    echo "--- Total lines in strace log ---"
    wc -l "${OUTDIR}/strace_full.log" 2>/dev/null
    echo ""
fi

# ── Test 2: Check what LD_PRELOAD DMTCP sets ─────────────────────────
echo "=== Test 2: DMTCP environment variables ==="
echo ""

echo "Check what env vars dmtcp_launch sets:"
# Use a wrapper that prints env before exec
cat > "${OUTDIR}/print_env.sh" << 'ENVEOF'
#!/bin/bash
echo "=== DMTCP Environment ==="
env | grep -iE 'DMTCP|LD_PRELOAD|LD_LIBRARY' | sort
echo "=== End ==="
exec "$@"
ENVEOF
chmod +x "${OUTDIR}/print_env.sh"

# Create a wrapper binary that prints its own env
cat > "${OUTDIR}/show_env.c" << 'EOF'
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
extern char **environ;
int main() {
    char **env = environ;
    printf("PID=%d\n", getpid());
    while (*env) {
        if (strstr(*env, "DMTCP") || strstr(*env, "LD_PRELOAD") || strstr(*env, "LD_LIBRARY")) {
            printf("%s\n", *env);
        }
        env++;
    }
    fflush(stdout);
    return 0;
}
EOF

if [ -n "${CC_CMD}" ]; then
    ${CC_CMD} -o "${OUTDIR}/show_env" "${OUTDIR}/show_env.c" 2>&1
fi

if [ -x "${OUTDIR}/show_env" ]; then
    echo "Running show_env WITHOUT DMTCP:"
    "${OUTDIR}/show_env"
    echo ""

    echo "Running show_env WITH DMTCP (timeout 10s):"
    timeout 10 "${MANA_BIN}/dmtcp_launch" \
        -j -h localhost -p "${COORD_PORT}" \
        --no-gzip \
        "${OUTDIR}/show_env" 2>&1
    echo "Exit code: $?"
    echo ""
fi

# ── Test 3: Check if libdmtcp.so can be loaded at all ────────────────
echo "=== Test 3: Manual LD_PRELOAD of libdmtcp.so ==="
echo ""

echo "libdmtcp.so location:"
ls -la "${MANA_LIB}/libdmtcp.so" 2>/dev/null
echo ""

echo "libdmtcp.so dependencies:"
ldd "${MANA_LIB}/libdmtcp.so" 2>/dev/null
echo ""

echo "Running hello with LD_PRELOAD=libdmtcp.so (no coordinator, should fail gracefully):"
timeout 5 env LD_PRELOAD="${MANA_LIB}/libdmtcp.so" "${OUTDIR}/hello" 2>&1
echo "Exit code: $?"
echo ""

# ── Test 4: Check DMTCP plugin loading ────────────────────────────────
echo "=== Test 4: DMTCP plugin list ==="
echo ""

echo "Default plugins loaded by dmtcp_launch:"
grep -r 'plugin\|PLUGIN\|preload\|PRELOAD' "${MANA_ROOT}/../src/dmtcp_launch.cpp" 2>/dev/null | head -20
echo ""

echo "Plugin search paths:"
grep -r 'pluginDir\|DMTCP_ROOT\|lib/dmtcp' "${MANA_ROOT}/../src/dmtcp_launch.cpp" 2>/dev/null | head -10
echo ""

# ── Test 5: Check if the issue is specific plugins ───────────────────
echo "=== Test 5: dmtcp_launch with --disable-all-plugins ==="
echo ""

echo "Checking if --disable-all-plugins exists:"
"${MANA_BIN}/dmtcp_launch" --help 2>&1 | grep -i 'disable.*plugin\|plugin'
echo ""

# ── Test 6: Check DMTCP_ROOT and related paths ──────────────────────
echo "=== Test 6: DMTCP paths ==="
echo ""

echo "DMTCP_ROOT env: ${DMTCP_ROOT:-not set}"
echo "MANA_ROOT: ${MANA_ROOT}"
echo ""

echo "bin/ contents:"
ls "${MANA_BIN}/" 2>/dev/null | head -20
echo ""

echo "lib/ contents:"
ls "${MANA_ROOT}/lib/" 2>/dev/null
echo ""

echo "lib/dmtcp/ contents:"
ls "${MANA_ROOT}/lib/dmtcp/" 2>/dev/null
echo ""

# ── Test 7: Run dmtcp_launch with DMTCP_ABORT_ON_FAILURE ─────────────
echo "=== Test 7: dmtcp_launch with debug env vars ==="
echo ""

echo "Running with DMTCP_ABORT_ON_FAILURE=1 JASSERT_STDERR=1:"
export DMTCP_ABORT_ON_FAILURE=1
export JASSERT_STDERR=1
timeout 10 "${MANA_BIN}/dmtcp_launch" \
    -j -h localhost -p "${COORD_PORT}" \
    --no-gzip \
    "${OUTDIR}/hello" > "${OUTDIR}/test7_stdout.txt" 2> "${OUTDIR}/test7_stderr.txt"
echo "Exit code: $?"
echo "--- stdout ---"
cat "${OUTDIR}/test7_stdout.txt" 2>/dev/null
echo "--- stderr (last 30 lines) ---"
tail -30 "${OUTDIR}/test7_stderr.txt" 2>/dev/null
echo ""
unset DMTCP_ABORT_ON_FAILURE
unset JASSERT_STDERR

# ── Test 8: Check if /proc/sys/kernel/yama/ptrace_scope blocks DMTCP ─
echo "=== Test 8: Security settings ==="
echo ""

echo "ptrace_scope:"
cat /proc/sys/kernel/yama/ptrace_scope 2>/dev/null || echo "  (not available)"
echo ""

echo "seccomp status:"
grep Seccomp /proc/self/status 2>/dev/null || echo "  (not available)"
echo ""

echo "SELinux:"
getenforce 2>/dev/null || echo "  (not available or not installed)"
echo ""

echo "AppArmor:"
cat /sys/module/apparmor/parameters/enabled 2>/dev/null || echo "  (not available)"
echo ""

echo "Kernel version:"
uname -r
echo ""

echo "Kernel security modules:"
cat /sys/kernel/security/lsm 2>/dev/null || echo "  (not available)"
echo ""

# Cleanup
"${MANA_BIN}/dmtcp_command" --port "${COORD_PORT}" --quit 2>/dev/null || true

echo "============================================================"
echo "  DMTCP Hang Diagnosis Phase 2 complete."
echo "  Full strace log: ${OUTDIR}/strace_full.log"
echo "============================================================"
