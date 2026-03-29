#!/usr/bin/env bash
# ============================================================================
# debug_mana_sigsegv.sh – Diagnose MANA SIGSEGV on Aurora
#
# Run on a compute node to gather diagnostic information about why
# mana_launch crashes with SIGSEGV.
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

MANA_ROOT="${MANA_ROOT:-${HOME}/.local/share/guard-agent/dmtcp-src/mana}"
EXE="${REPO_ROOT}/build/validation_output/art_simple/build/dmtcp/art_simple_main"
DATA="${REPO_ROOT}/build/data/tooth_preprocessed.h5"
MANA_BIN="${MANA_ROOT}/bin"
MANA_LIB="${MANA_ROOT}/lib/dmtcp"

echo "============================================================"
echo "  MANA SIGSEGV Diagnostic Script"
echo "============================================================"
echo ""
echo "Date: $(date)"
echo "Host: $(hostname)"
echo "Kernel: $(uname -r)"
echo ""

# ── 1. Check binary linkage ──────────────────────────────────────────────
echo "=== 1. Binary linkage ==="
echo "Binary: ${EXE}"
echo ""
echo "--- ldd (full) ---"
ldd "${EXE}" 2>&1 || echo "(ldd failed)"
echo ""
echo "--- nm MPI symbols ---"
nm "${EXE}" 2>/dev/null | grep -i 'MPI_Init\|MPI_Finalize\|MPI_Comm_rank' | head -20 || echo "(no MPI symbols)"
echo ""

# ── 2. Check lower-half linkage ──────────────────────────────────────────
echo "=== 2. Lower-half binary ==="
echo "Binary: ${MANA_BIN}/lower-half"
echo ""
echo "--- ldd ---"
ldd "${MANA_BIN}/lower-half" 2>&1 || echo "(ldd failed)"
echo ""
echo "--- file ---"
file "${MANA_BIN}/lower-half" 2>&1 || true
echo ""

# ── 3. Check libmana.so ─────────────────────────────────────────────────
echo "=== 3. libmana.so ==="
echo "Path: ${MANA_LIB}/libmana.so"
echo ""
echo "--- ldd ---"
ldd "${MANA_LIB}/libmana.so" 2>&1 || echo "(ldd failed)"
echo ""
echo "--- nm (MPI wrapper symbols, first 30) ---"
nm -D "${MANA_LIB}/libmana.so" 2>/dev/null | grep -i 'MPI_' | head -30 || echo "(none)"
echo ""

# ── 4. Check libmpistub.so symbols ──────────────────────────────────────
echo "=== 4. libmpistub.so symbols ==="
echo "Path: ${MANA_LIB}/libmpistub.so"
echo ""
echo "--- nm -D (all defined symbols) ---"
nm -D "${MANA_LIB}/libmpistub.so" 2>/dev/null | grep ' T ' | head -50 || echo "(none)"
echo ""
echo "--- Does it have MPI_Aint_diff? ---"
nm -D "${MANA_LIB}/libmpistub.so" 2>/dev/null | grep 'MPI_Aint_diff' || echo "  NO - MPI_Aint_diff not in libmpistub.so"
echo ""

# ── 5. Check for symbol conflicts ───────────────────────────────────────
echo "=== 5. Symbol conflict check ==="
echo "--- MPI_Init in libmpistub.so ---"
nm -D "${MANA_LIB}/libmpistub.so" 2>/dev/null | grep 'MPI_Init' || echo "  (not found)"
echo ""
echo "--- MPI_Init in libmana.so ---"
nm -D "${MANA_LIB}/libmana.so" 2>/dev/null | grep 'MPI_Init' || echo "  (not found)"
echo ""
echo "--- MPI_Init in lower-half ---"
nm "${MANA_BIN}/lower-half" 2>/dev/null | grep 'MPI_Init' || echo "  (not found)"
echo ""

# ── 6. Check DMTCP JASSERT log locations ────────────────────────────────
echo "=== 6. JASSERT log locations ==="
echo "--- /tmp/dmtcp-* directories ---"
ls -la /tmp/dmtcp-* 2>/dev/null || echo "  (none found)"
echo ""
echo "--- DMTCP_TMPDIR ---"
echo "  DMTCP_TMPDIR=${DMTCP_TMPDIR:-<not set>}"
echo "  TMPDIR=${TMPDIR:-<not set>}"
echo ""

# ── 7. Test: Run lower-half directly (without app) ──────────────────────
echo "=== 7. Test: lower-half standalone ==="
echo "Running: ${MANA_BIN}/lower-half (should print usage or exit cleanly)"
timeout 5 "${MANA_BIN}/lower-half" 2>&1 || echo "  (exit code: $?)"
echo ""

# ── 8. Test: Run with DMTCP_JASSERT_LOG ─────────────────────────────────
echo "=== 8. Test: mana_launch with JASSERT logging ==="
export DMTCP_TMPDIR="/tmp/mana_debug_$$"
mkdir -p "${DMTCP_TMPDIR}"
export JASSERT_STDERR=1

# Start coordinator
echo "Starting coordinator..."
"${MANA_BIN}/dmtcp_coordinator" --daemon --port 7902 \
    --ckptdir "${DMTCP_TMPDIR}" 2>&1 || true
sleep 1

echo "Launching with verbose JASSERT logging..."
echo "Command: mpiexec -np 1 ${MANA_BIN}/mana_launch --verbose --coord-port 7902 --ckptdir ${DMTCP_TMPDIR} --no-gzip ${EXE} ${DATA} 294.078 1 1 0 1"
echo ""

# Run with timeout, capture all output
timeout 30 mpiexec -np 1 "${MANA_BIN}/mana_launch" \
    --verbose --coord-port 7902 \
    --ckptdir "${DMTCP_TMPDIR}" --no-gzip \
    "${EXE}" "${DATA}" 294.078 1 1 0 1 \
    > "${DMTCP_TMPDIR}/stdout.txt" \
    2> "${DMTCP_TMPDIR}/stderr.txt" || true

echo "--- stdout ---"
cat "${DMTCP_TMPDIR}/stdout.txt" 2>/dev/null || true
echo ""
echo "--- stderr (last 50 lines) ---"
tail -50 "${DMTCP_TMPDIR}/stderr.txt" 2>/dev/null || true
echo ""

# Check for JASSERT logs
echo "--- JASSERT logs ---"
find "${DMTCP_TMPDIR}" -name "jassertlog*" -exec echo "File: {}" \; -exec cat {} \; 2>/dev/null || echo "  (none)"
echo ""
find /tmp/dmtcp-* -name "jassertlog*" -newer "${DMTCP_TMPDIR}" -exec echo "File: {}" \; -exec tail -30 {} \; 2>/dev/null || echo "  (none in /tmp/dmtcp-*)"
echo ""

# Cleanup coordinator
"${MANA_BIN}/dmtcp_command" --port 7902 --quit 2>/dev/null || true

# ── 9. Test: Run app WITHOUT MANA (plain mpiexec) ───────────────────────
echo "=== 9. Test: plain mpiexec (no MANA) ==="
echo "Running: mpiexec -np 1 ${EXE} ${DATA} 294.078 1 1 0 1"
timeout 30 mpiexec -np 1 "${EXE}" "${DATA}" 294.078 1 1 0 1 \
    > "${DMTCP_TMPDIR}/plain_stdout.txt" \
    2> "${DMTCP_TMPDIR}/plain_stderr.txt" || true
PLAIN_EXIT=$?
echo "Exit code: ${PLAIN_EXIT}"
echo "--- stdout (last 10 lines) ---"
tail -10 "${DMTCP_TMPDIR}/plain_stdout.txt" 2>/dev/null || true
echo "--- stderr ---"
cat "${DMTCP_TMPDIR}/plain_stderr.txt" 2>/dev/null || true
echo ""

# ── 10. Test: Run with LD_DEBUG to see symbol resolution ────────────────
echo "=== 10. Test: LD_DEBUG=libs (first 50 lines) ==="
echo "Running with LD_DEBUG=libs to see library loading order..."
timeout 10 env LD_DEBUG=libs mpiexec -np 1 "${MANA_BIN}/mana_launch" \
    --verbose --coord-port 7902 \
    --ckptdir "${DMTCP_TMPDIR}" --no-gzip \
    "${EXE}" "${DATA}" 294.078 1 1 0 1 \
    > /dev/null 2> "${DMTCP_TMPDIR}/ld_debug.txt" || true
head -100 "${DMTCP_TMPDIR}/ld_debug.txt" 2>/dev/null || true
echo ""

echo "============================================================"
echo "  Diagnostic output saved to: ${DMTCP_TMPDIR}/"
echo "============================================================"
echo ""
echo "Key files to examine:"
echo "  ${DMTCP_TMPDIR}/stderr.txt     - MANA launch stderr"
echo "  ${DMTCP_TMPDIR}/stdout.txt     - MANA launch stdout"
echo "  ${DMTCP_TMPDIR}/ld_debug.txt   - LD_DEBUG output"
echo "  ${DMTCP_TMPDIR}/plain_*.txt    - Plain mpiexec output"
