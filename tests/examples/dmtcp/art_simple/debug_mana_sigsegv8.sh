#!/usr/bin/env bash
# ============================================================================
# debug_mana_sigsegv8.sh – Diagnose DMTCP hang + coordinator detection
#
# Phase 7 findings:
#   - DMTCP alone hangs (exit 124 = timeout) on simple C hello
#   - mana_launch says "No MANA coordinator detected" even though coordinator
#     IS running — likely hostname mismatch (hostmgmt vs HSN network)
#   - Manual dmtcp_launch exits with code 99 (not SIGSEGV!)
#   - No SIGSEGV in strace — the crash is exit code 99
#
# This script:
#   1. Diagnoses the hostname/network mismatch
#   2. Tests DMTCP with verbose/debug output
#   3. Tests coordinator connectivity from different hostnames
#   4. Tests dmtcp_launch with JASSERT debug output
# ============================================================================

set +e

MANA_ROOT="${MANA_ROOT:-${HOME}/.local/share/guard-agent/dmtcp-src/mana}"
MANA_BIN="${MANA_ROOT}/bin"
MANA_LIB="${MANA_ROOT}/lib/dmtcp"
COORD_PORT="${COORD_PORT:-7910}"
OUTDIR="${HOME}/diaspora/guard-agent/build/test_mana_debug8/output"
CKPT_DIR="${HOME}/diaspora/guard-agent/build/test_mana_debug8/ckpt"

mkdir -p "${OUTDIR}" "${CKPT_DIR}"

export HWLOC_COMPONENTS="-linuxio"
export LD_LIBRARY_PATH="${MANA_LIB}:${LD_LIBRARY_PATH:-}"

echo "============================================================"
echo "  MANA Phase 8: DMTCP Hang + Coordinator Detection"
echo "============================================================"
echo ""

# Kill any existing coordinator on this port
"${MANA_BIN}/dmtcp_command" --port "${COORD_PORT}" --quit 2>/dev/null || true
sleep 0.5

# ── Test 1: Hostname/Network analysis ─────────────────────────────────
echo "=== Test 1: Hostname/Network analysis ==="
echo ""

echo "hostname:           $(hostname)"
echo "hostname -f:        $(hostname -f 2>/dev/null || echo 'N/A')"
echo "hostname -s:        $(hostname -s 2>/dev/null || echo 'N/A')"
echo "hostname -i:        $(hostname -i 2>/dev/null || echo 'N/A')"
echo ""

echo "All IP addresses:"
ip addr show 2>/dev/null | grep 'inet ' | awk '{print "  " $2 " on " $NF}'
echo ""

echo "Network interfaces:"
ip link show 2>/dev/null | grep -E '^[0-9]+:' | awk '{print "  " $2}'
echo ""

echo "Hostmgmt hostname resolution:"
getent hosts "$(hostname)" 2>/dev/null || echo "  (no entry)"
echo ""

echo "HSN hostname resolution:"
HSN_HOST="$(hostname -s).hsn.cm.aurora.alcf.anl.gov"
getent hosts "${HSN_HOST}" 2>/dev/null || echo "  (no entry for ${HSN_HOST})"
echo ""

# ── Test 2: Start coordinator and test connectivity from all hostnames ─
echo "=== Test 2: Coordinator connectivity from different hostnames ==="
echo ""

echo "Starting coordinator on port ${COORD_PORT}..."
"${MANA_BIN}/dmtcp_coordinator" --exit-on-last -q --daemon \
    --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1
echo "Exit code: $?"
echo ""

# Test connectivity from various hostnames
for HOST_VARIANT in \
    "localhost" \
    "127.0.0.1" \
    "$(hostname)" \
    "$(hostname -s 2>/dev/null)" \
    "$(hostname -f 2>/dev/null)" \
    "$(hostname -i 2>/dev/null | awk '{print $1}')" \
    ; do
    if [ -n "${HOST_VARIANT}" ] && [ "${HOST_VARIANT}" != "N/A" ]; then
        RESULT=$("${MANA_BIN}/dmtcp_command" -h "${HOST_VARIANT}" --port "${COORD_PORT}" -s 2>&1)
        RC=$?
        echo "  dmtcp_command -h '${HOST_VARIANT}' --port ${COORD_PORT} -s => exit ${RC}"
        if [ ${RC} -eq 0 ]; then
            echo "    $(echo "${RESULT}" | grep -E 'NUM_PEERS|RUNNING' | tr '\n' ' ')"
        else
            echo "    ${RESULT}" | head -2
        fi
    fi
done
echo ""

# ── Test 3: What does mana_launch read from .mana.rc? ────────────────
echo "=== Test 3: mana_launch .mana.rc parsing ==="
echo ""

echo "Full mana_launch script (coordinator detection section):"
sed -n '100,170p' "${MANA_BIN}/mana_launch" 2>/dev/null
echo ""

echo "Contents of ~/.mana.rc:"
cat "${HOME}/.mana.rc" 2>/dev/null
echo ""

# ── Test 4: DMTCP alone with JASSERT debug ───────────────────────────
echo "=== Test 4: DMTCP alone with JASSERT debug ==="
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
    ${CC_CMD} -o "${OUTDIR}/hello" "${OUTDIR}/hello.c" 2>&1
fi

if [ -x "${OUTDIR}/hello" ]; then
    # First verify the program works without DMTCP
    echo "4a. Running hello WITHOUT DMTCP:"
    "${OUTDIR}/hello"
    echo "Exit code: $?"
    echo ""

    # Now with DMTCP, using localhost
    echo "4b. Running dmtcp_launch with -h localhost:"
    export DMTCP_TMPDIR="${OUTDIR}/dmtcp_tmp"
    mkdir -p "${DMTCP_TMPDIR}"
    export JASSERT_STDERR=1
    timeout 10 "${MANA_BIN}/dmtcp_launch" \
        -h localhost -p "${COORD_PORT}" \
        --no-gzip --join-coordinator \
        "${OUTDIR}/hello" > "${OUTDIR}/test4b_stdout.txt" 2> "${OUTDIR}/test4b_stderr.txt"
    echo "Exit code: $?"
    echo "--- stdout ---"
    cat "${OUTDIR}/test4b_stdout.txt" 2>/dev/null
    echo "--- stderr (last 30 lines) ---"
    tail -30 "${OUTDIR}/test4b_stderr.txt" 2>/dev/null
    echo ""

    # With 127.0.0.1
    echo "4c. Running dmtcp_launch with -h 127.0.0.1:"
    timeout 10 "${MANA_BIN}/dmtcp_launch" \
        -h 127.0.0.1 -p "${COORD_PORT}" \
        --no-gzip --join-coordinator \
        "${OUTDIR}/hello" > "${OUTDIR}/test4c_stdout.txt" 2> "${OUTDIR}/test4c_stderr.txt"
    echo "Exit code: $?"
    echo "--- stdout ---"
    cat "${OUTDIR}/test4c_stdout.txt" 2>/dev/null
    echo "--- stderr (last 30 lines) ---"
    tail -30 "${OUTDIR}/test4c_stderr.txt" 2>/dev/null
    echo ""

    # With hostname
    echo "4d. Running dmtcp_launch with -h $(hostname):"
    timeout 10 "${MANA_BIN}/dmtcp_launch" \
        -h "$(hostname)" -p "${COORD_PORT}" \
        --no-gzip --join-coordinator \
        "${OUTDIR}/hello" > "${OUTDIR}/test4d_stdout.txt" 2> "${OUTDIR}/test4d_stderr.txt"
    echo "Exit code: $?"
    echo "--- stdout ---"
    cat "${OUTDIR}/test4d_stdout.txt" 2>/dev/null
    echo "--- stderr (last 30 lines) ---"
    tail -30 "${OUTDIR}/test4d_stderr.txt" 2>/dev/null
    echo ""

    unset JASSERT_STDERR
    unset DMTCP_TMPDIR
fi

# ── Test 5: DMTCP version and capabilities ───────────────────────────
echo "=== Test 5: DMTCP version and capabilities ==="
echo ""

echo "dmtcp_launch --version:"
"${MANA_BIN}/dmtcp_launch" --version 2>&1 | head -5
echo ""

echo "dmtcp_launch --help (first 30 lines):"
"${MANA_BIN}/dmtcp_launch" --help 2>&1 | head -30
echo ""

echo "dmtcp_coordinator --help (first 30 lines):"
"${MANA_BIN}/dmtcp_coordinator" --help 2>&1 | head -30
echo ""

# ── Test 6: Direct dmtcp_launch without mpiexec ──────────────────────
echo "=== Test 6: Direct dmtcp_launch (no mpiexec) with MANA ==="
echo ""

# Build MPI hello with mpistub
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
    ${CC_CMD} ${MPI_INC} -L"${MANA_LIB}" -lmpistub -o "${SIMPLE_MPI}" "${OUTDIR}/hello_mpi.c" 2>&1
fi

if [ -x "${SIMPLE_MPI}" ]; then
    echo "6a. Direct dmtcp_launch with MANA (no mpiexec), -h localhost:"
    export JASSERT_STDERR=1
    timeout 15 "${MANA_BIN}/dmtcp_launch" --mpi \
        -h localhost -p "${COORD_PORT}" \
        --no-gzip --join-coordinator --disable-dl-plugin \
        --with-plugin "${MANA_LIB}/libmana.so" \
        "${MANA_BIN}/lower-half" "${SIMPLE_MPI}" > "${OUTDIR}/test6a_stdout.txt" 2> "${OUTDIR}/test6a_stderr.txt"
    echo "Exit code: $?"
    echo "--- stdout ---"
    cat "${OUTDIR}/test6a_stdout.txt" 2>/dev/null
    echo "--- stderr (last 40 lines) ---"
    tail -40 "${OUTDIR}/test6a_stderr.txt" 2>/dev/null
    echo ""

    echo "6b. Direct mana_launch (no mpiexec), --coord-host localhost:"
    timeout 15 "${MANA_BIN}/mana_launch" --verbose \
        --coord-host localhost --coord-port "${COORD_PORT}" \
        --ckptdir "${CKPT_DIR}" --no-gzip \
        "${SIMPLE_MPI}" > "${OUTDIR}/test6b_stdout.txt" 2> "${OUTDIR}/test6b_stderr.txt"
    echo "Exit code: $?"
    echo "--- stdout ---"
    cat "${OUTDIR}/test6b_stdout.txt" 2>/dev/null
    echo "--- stderr (last 40 lines) ---"
    tail -40 "${OUTDIR}/test6b_stderr.txt" 2>/dev/null
    echo ""

    unset JASSERT_STDERR
fi

# ── Test 7: Check exit code 99 meaning ───────────────────────────────
echo "=== Test 7: Exit code 99 investigation ==="
echo ""

echo "Searching DMTCP source for exit code 99:"
grep -rn 'exit(99)\|_exit(99)\|EXIT_CODE.*99\|DMTCP_FAIL_RC\|99' \
    "${MANA_ROOT}/../src/"*.cpp "${MANA_ROOT}/../src/"*.h \
    "${MANA_ROOT}/../jalib/"*.cpp "${MANA_ROOT}/../jalib/"*.h \
    2>/dev/null | grep -v '.o:' | head -20
echo ""

echo "Searching MANA source for exit code 99:"
grep -rn 'exit(99)\|_exit(99)' \
    "${MANA_ROOT}/"*.cpp "${MANA_ROOT}/"*.h \
    "${MANA_ROOT}/mpi-proxy-split/"*.cpp "${MANA_ROOT}/mpi-proxy-split/"*.h \
    2>/dev/null | grep -v '.o:' | head -20
echo ""

# ── Test 8: Check /tmp/dmtcp-* directory ─────────────────────────────
echo "=== Test 8: DMTCP temp directory ==="
echo ""

echo "Contents of /tmp/dmtcp-${USER}@*:"
ls -la /tmp/dmtcp-${USER}@* 2>/dev/null || echo "  (no /tmp/dmtcp-* directories)"
echo ""

echo "JASSERT log files:"
find /tmp -name 'jassertlog.*' -user "${USER}" 2>/dev/null | head -10
echo ""

if ls /tmp/dmtcp-${USER}@*/jassertlog.* 2>/dev/null | head -1 | read -r LOGFILE; then
    echo "Latest JASSERT log (last 30 lines):"
    tail -30 "${LOGFILE}" 2>/dev/null
fi
echo ""

# Cleanup
"${MANA_BIN}/dmtcp_command" --port "${COORD_PORT}" --quit 2>/dev/null || true

echo "============================================================"
echo "  Phase 8 complete. Output files in: ${OUTDIR}"
echo "============================================================"
