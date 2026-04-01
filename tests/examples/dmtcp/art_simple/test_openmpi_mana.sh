#!/usr/bin/env bash
# ============================================================================
# test_openmpi_mana.sh – Step-by-step diagnostic for OpenMPI + MANA on Aurora
#
# Tests the full checkpoint/restart cycle:
#   Phase 1: Launch app under MANA + OpenMPI
#   Phase 2: Trigger checkpoint
#   Phase 3: Kill a rank (failure injection)
#   Phase 4: Restart from checkpoint
#   Phase 5: Verify output
#
# Usage:
#   bash tests/examples/dmtcp/art_simple/test_openmpi_mana.sh [--np N]
#
# Prerequisites:
#   - OpenMPI built at ~/.local (with Fortran support)
#   - MANA rebuilt against OpenMPI (via rebuild_mana_openmpi.sh)
#   - art_simple built against OpenMPI
#   - tooth_preprocessed.h5 data file
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

# ── Parse arguments ──────────────────────────────────────────────────────
NUM_PROCS=2
OUTER_ITERS=30  # ~30s runtime with np=2
while [[ $# -gt 0 ]]; do
    case "$1" in
        --np) NUM_PROCS="$2"; shift 2 ;;
        --iters) OUTER_ITERS="$2"; shift 2 ;;
        *) echo "Usage: $0 [--np N] [--iters N]"; exit 1 ;;
    esac
done

# ── Configuration ────────────────────────────────────────────────────────
MANA_ROOT="${MANA_ROOT:-${HOME}/.local/share/guard-agent/dmtcp-src/mana}"

# Auto-detect OpenMPI prefix from MANA lower-half's ldd output
_auto_detect_openmpi() {
    local _lower_half="${MANA_ROOT}/bin/lower-half"
    if [[ -x "${_lower_half}" ]]; then
        local _libmpi_path
        _libmpi_path="$(ldd "${_lower_half}" 2>/dev/null | grep 'libmpi\.so' | awk '{print $3}' | head -1)"
        if [[ -n "${_libmpi_path}" ]] && [[ -f "${_libmpi_path}" ]]; then
            local _prefix
            _prefix="$(dirname "$(dirname "${_libmpi_path}")")"
            if [[ -x "${_prefix}/bin/mpirun" ]]; then
                echo "${_prefix}"
                return
            fi
        fi
    fi
    for _candidate in "${HOME}/.local/openmpi" "${HOME}/.local"; do
        if [[ -x "${_candidate}/bin/mpirun" ]]; then
            echo "${_candidate}"; return
        fi
    done
    echo "${HOME}/.local"
}

if [[ -z "${OPENMPI_PREFIX:-}" ]]; then
    OPENMPI_PREFIX="$(_auto_detect_openmpi)"
    echo "[AUTO] Detected OpenMPI at: ${OPENMPI_PREFIX}"
fi
COORD_PORT="${COORD_PORT:-7908}"
COORD_HOST="$(hostname)"

MANA_BIN="${MANA_ROOT}/bin"
MANA_LAUNCH="${MANA_BIN}/mana_launch"
DMTCP_COMMAND="${MANA_BIN}/dmtcp_command"
DMTCP_COORD="${MANA_BIN}/dmtcp_coordinator"
DMTCP_RESTART="${MANA_BIN}/dmtcp_restart"

# Work directories
TEST_DIR="${REPO_ROOT}/build/test_openmpi_mana"
CKPT_DIR="${TEST_DIR}/ckpt"
RUN_DIR="${TEST_DIR}/run"
rm -rf "${TEST_DIR}"
mkdir -p "${CKPT_DIR}" "${RUN_DIR}"

# App
DATA_PATH="${REPO_ROOT}/build/data/tooth_preprocessed.h5"
APP_BUILD="${REPO_ROOT}/build/example_refs/dmtcp/art_simple/build_openmpi"
APP_EXE="${APP_BUILD}/art_simple_main"

# Env
export PATH="${OPENMPI_PREFIX}/bin:${PATH}"
export LD_LIBRARY_PATH="${OPENMPI_PREFIX}/lib:${OPENMPI_PREFIX}/lib64:${LD_LIBRARY_PATH:-}"
export HWLOC_COMPONENTS="-linuxio"

echo "============================================================"
echo "  OpenMPI + MANA Diagnostic Test"
echo "============================================================"
echo ""
echo "Config:"
echo "  NUM_PROCS:      ${NUM_PROCS}"
echo "  OUTER_ITERS:    ${OUTER_ITERS}"
echo "  OPENMPI_PREFIX: ${OPENMPI_PREFIX}"
echo "  MANA_ROOT:      ${MANA_ROOT}"
echo "  COORD_PORT:     ${COORD_PORT}"
echo "  APP_EXE:        ${APP_EXE}"
echo "  DATA_PATH:      ${DATA_PATH}"
echo "  TEST_DIR:       ${TEST_DIR}"
echo ""

# ── Pre-flight checks ───────────────────────────────────────────────────
echo "=== Pre-flight checks ==="
FAIL=false

for tool in "${MANA_LAUNCH}" "${DMTCP_COMMAND}" "${DMTCP_COORD}" "${DMTCP_RESTART}"; do
    if [[ -x "${tool}" ]]; then
        echo "[OK]   $(basename "${tool}"): ${tool}"
    else
        echo "[FAIL] $(basename "${tool}"): NOT FOUND at ${tool}"
        FAIL=true
    fi
done

if [[ -x "${APP_EXE}" ]]; then
    echo "[OK]   app: ${APP_EXE}"
else
    echo "[FAIL] app: NOT FOUND at ${APP_EXE}"
    echo "       Run rebuild_mana_openmpi.sh first."
    FAIL=true
fi

if [[ -f "${DATA_PATH}" ]]; then
    echo "[OK]   data: ${DATA_PATH}"
else
    echo "[FAIL] data: NOT FOUND at ${DATA_PATH}"
    FAIL=true
fi

# Check that MANA's lower-half links to OpenMPI
LOWER_HALF="${MANA_BIN}/lower-half"
if [[ -x "${LOWER_HALF}" ]]; then
    LH_MPI=$(ldd "${LOWER_HALF}" 2>/dev/null | grep libmpi || echo "none")
    echo "[INFO] lower-half MPI linkage: ${LH_MPI}"
    if echo "${LH_MPI}" | grep -q "${OPENMPI_PREFIX}"; then
        echo "[OK]   lower-half links to OpenMPI"
    else
        echo "[WARN] lower-half may not link to OpenMPI from ${OPENMPI_PREFIX}"
    fi
fi

# Check that app links to OpenMPI
if [[ -x "${APP_EXE}" ]]; then
    APP_MPI=$(ldd "${APP_EXE}" 2>/dev/null | grep libmpi || echo "none")
    echo "[INFO] app MPI linkage: ${APP_MPI}"
fi

if $FAIL; then
    echo ""
    echo "ABORT: Pre-flight checks failed."
    exit 1
fi
echo ""

# ── Write MANA argv override config ─────────────────────────────────────
cat > "${RUN_DIR}/mana_argv_override.conf" << ARGVEOF
center=294.078
num_outer_iter=${OUTER_ITERS}
num_iter=2
beg_index=0
nslices=4
ARGVEOF
echo "[OK] Wrote ${RUN_DIR}/mana_argv_override.conf"

# ── Phase 0: Kill any stale coordinator ──────────────────────────────────
"${DMTCP_COMMAND}" -h "${COORD_HOST}" --coord-port "${COORD_PORT}" --quit 2>/dev/null || true
sleep 0.5

# ══════════════════════════════════════════════════════════════════════════
# Phase 1: Launch app under MANA + OpenMPI
# ══════════════════════════════════════════════════════════════════════════
echo ""
echo "=== Phase 1: Launch app under MANA + OpenMPI ==="
echo ""

# Start coordinator WITHOUT --exit-on-last (so it survives rank kills)
echo "Starting coordinator on port ${COORD_PORT} ..."
"${DMTCP_COORD}" --daemon --coord-port "${COORD_PORT}" \
    --ckptdir "${CKPT_DIR}" -q -q
sleep 1

# Write .mana.rc
cat > "${HOME}/.mana.rc" << MANARC
Host: ${COORD_HOST}
Port: ${COORD_PORT}

MANARC
echo "[OK] Wrote ~/.mana.rc"

OMPI_MPIRUN="${OPENMPI_PREFIX}/bin/mpirun"

APP_ARGS=(
    "${DATA_PATH}"
    "294.078"
    "${OUTER_ITERS}"
    "2"
    "0"
    "4"
)

echo ""
echo "Launching: ${OMPI_MPIRUN} -np ${NUM_PROCS} ${MANA_LAUNCH} ... ${APP_EXE} ${APP_ARGS[*]}"
echo ""

"${OMPI_MPIRUN}" -np "${NUM_PROCS}" \
    "${MANA_LAUNCH}" \
    --coord-host "${COORD_HOST}" --coord-port "${COORD_PORT}" \
    --ckptdir "${CKPT_DIR}" --no-gzip \
    "${APP_EXE}" "${APP_ARGS[@]}" \
    > "${RUN_DIR}/stdout_phase1.txt" 2> "${RUN_DIR}/stderr_phase1.txt" &
MPI_PID=$!
echo "Launched with PID ${MPI_PID}"

# Wait for app to start (look for reconstruction output)
echo "Waiting for app to start..."
STARTUP_DEADLINE=$((SECONDS + 30))
APP_STARTED=false
while [[ $SECONDS -lt $STARTUP_DEADLINE ]]; do
    if ! kill -0 "${MPI_PID}" 2>/dev/null; then
        echo "[FAIL] App exited early!"
        wait "${MPI_PID}" 2>/dev/null
        APP_EXIT=$?
        echo "Exit code: ${APP_EXIT}"
        echo "--- stdout (last 20 lines) ---"
        tail -20 "${RUN_DIR}/stdout_phase1.txt" 2>/dev/null || true
        echo "--- stderr (last 20 lines) ---"
        tail -20 "${RUN_DIR}/stderr_phase1.txt" 2>/dev/null || true
        exit 1
    fi
    if grep -q "Outer iteration" "${RUN_DIR}/stdout_phase1.txt" 2>/dev/null; then
        APP_STARTED=true
        echo "[OK] App is running (saw 'Outer iteration' in output)"
        break
    fi
    sleep 1
done

if ! $APP_STARTED; then
    echo "[WARN] Did not see 'Outer iteration' in output, but app is still running"
    echo "--- stdout so far ---"
    cat "${RUN_DIR}/stdout_phase1.txt" 2>/dev/null || true
    echo "--- stderr so far ---"
    cat "${RUN_DIR}/stderr_phase1.txt" 2>/dev/null || true
fi

# ══════════════════════════════════════════════════════════════════════════
# Phase 2: Trigger checkpoint
# ══════════════════════════════════════════════════════════════════════════
echo ""
echo "=== Phase 2: Trigger checkpoint ==="
echo ""

# Wait a bit for the app to do some work
echo "Waiting 5s for app to progress..."
sleep 5

if ! kill -0 "${MPI_PID}" 2>/dev/null; then
    echo "[FAIL] App already exited before checkpoint!"
    wait "${MPI_PID}" 2>/dev/null || true
    echo "--- stdout (last 20 lines) ---"
    tail -20 "${RUN_DIR}/stdout_phase1.txt"
    exit 1
fi

echo "Triggering checkpoint..."
"${DMTCP_COMMAND}" -h "${COORD_HOST}" --coord-port "${COORD_PORT}" --checkpoint 2>&1
CKPT_EXIT=$?
echo "Checkpoint command exit: ${CKPT_EXIT}"

# Wait for checkpoint files
echo "Waiting for checkpoint files..."
CKPT_DEADLINE=$((SECONDS + 30))
CKPT_READY=false
while [[ $SECONDS -lt $CKPT_DEADLINE ]]; do
    CKPT_FILES=$(find "${CKPT_DIR}" -name "ckpt_*.dmtcp" -type f 2>/dev/null)
    if [[ -n "${CKPT_FILES}" ]]; then
        CKPT_READY=true
        break
    fi
    sleep 0.5
done

if $CKPT_READY; then
    CKPT_COUNT=$(echo "${CKPT_FILES}" | wc -l)
    CKPT_SIZE=$(du -sh "${CKPT_DIR}" 2>/dev/null | cut -f1)
    echo "[OK] Checkpoint created: ${CKPT_COUNT} file(s), total ${CKPT_SIZE}"
    echo "Files:"
    echo "${CKPT_FILES}" | while read -r f; do
        echo "  $(basename "$f") ($(stat -c%s "$f" 2>/dev/null | numfmt --to=iec-i 2>/dev/null || stat -c%s "$f"))"
    done
else
    echo "[FAIL] No checkpoint files created!"
    echo "--- ckpt_dir contents ---"
    ls -la "${CKPT_DIR}/" 2>/dev/null || true
    echo "--- stderr ---"
    tail -20 "${RUN_DIR}/stderr_phase1.txt"
    # Cleanup
    kill "${MPI_PID}" 2>/dev/null || true
    wait "${MPI_PID}" 2>/dev/null || true
    "${DMTCP_COMMAND}" -h "${COORD_HOST}" --coord-port "${COORD_PORT}" --quit 2>/dev/null || true
    exit 1
fi

# Show iteration progress
echo ""
CURRENT_ITER=$(grep -c "Outer iteration" "${RUN_DIR}/stdout_phase1.txt" 2>/dev/null || echo 0)
echo "App progress: ~${CURRENT_ITER}/${OUTER_ITERS} outer iterations at checkpoint time"

# ══════════════════════════════════════════════════════════════════════════
# Phase 3: Kill one rank (failure injection)
# ══════════════════════════════════════════════════════════════════════════
echo ""
echo "=== Phase 3: Kill one rank (failure injection) ==="
echo ""

# Find rank processes
echo "Looking for rank processes..."
RANK_PIDS=$(ps -e -o pid,ppid,cmd --no-headers 2>/dev/null | \
    grep "art_simple" | \
    grep -v "mpirun\|python\|grep\|mana_launch\|dmtcp_launch\|dmtcp_command\|dmtcp_coordinator\|dmtcp_restart" | \
    awk '{print $1}')

if [[ -n "${RANK_PIDS}" ]]; then
    RANK_COUNT=$(echo "${RANK_PIDS}" | wc -l)
    echo "Found ${RANK_COUNT} rank process(es): ${RANK_PIDS}"

    # Kill the first rank
    TARGET_PID=$(echo "${RANK_PIDS}" | head -1)
    echo "Killing rank PID ${TARGET_PID} (SIGKILL)..."
    kill -9 "${TARGET_PID}" 2>/dev/null || echo "[WARN] Could not kill PID ${TARGET_PID}"
else
    echo "[WARN] No rank processes found via ps"
    echo "--- ps output (art_simple) ---"
    ps -e -o pid,ppid,cmd --no-headers 2>/dev/null | grep art_simple || echo "(none)"
    echo ""
    echo "--- all dmtcp/mana processes ---"
    ps -e -o pid,ppid,cmd --no-headers 2>/dev/null | grep -E "dmtcp|mana|lower-half" || echo "(none)"
fi

# Wait for mpirun to exit
echo "Waiting for mpirun to crash..."
MPI_TIMEOUT=$((SECONDS + 30))
while kill -0 "${MPI_PID}" 2>/dev/null && [[ $SECONDS -lt $MPI_TIMEOUT ]]; do
    sleep 0.5
done

if kill -0 "${MPI_PID}" 2>/dev/null; then
    echo "[WARN] mpirun still running after 30s, force killing..."
    kill -9 "${MPI_PID}" 2>/dev/null || true
fi
wait "${MPI_PID}" 2>/dev/null || true
MPI_EXIT=$?
echo "[OK] mpirun exited (code=${MPI_EXIT})"

echo ""
echo "--- Phase 1 stdout (last 10 lines) ---"
tail -10 "${RUN_DIR}/stdout_phase1.txt" 2>/dev/null || true
echo ""

# ══════════════════════════════════════════════════════════════════════════
# Phase 4: Restart from checkpoint
# ══════════════════════════════════════════════════════════════════════════
echo ""
echo "=== Phase 4: Restart from checkpoint ==="
echo ""

# Collect checkpoint files
CKPT_FILE_LIST=$(find "${CKPT_DIR}" -name "ckpt_*.dmtcp" -type f 2>/dev/null | sort)
CKPT_FILE_ARRAY=()
while IFS= read -r f; do
    [[ -n "$f" ]] && CKPT_FILE_ARRAY+=("$f")
done <<< "${CKPT_FILE_LIST}"

echo "Checkpoint files for restart:"
for f in "${CKPT_FILE_ARRAY[@]}"; do
    echo "  $(basename "$f")"
done
echo ""

# Use dmtcp_restart directly (NOT mana_restart — see commit 0c482a8)
RESTART_CMD=(
    "${DMTCP_RESTART}"
    "-j"
    "-h" "${COORD_HOST}"
    "-p" "${COORD_PORT}"
    "${CKPT_FILE_ARRAY[@]}"
)

echo "Restart command: ${RESTART_CMD[*]:0:5} ..."
echo ""

"${RESTART_CMD[@]}" \
    > "${RUN_DIR}/stdout_restart.txt" 2> "${RUN_DIR}/stderr_restart.txt" &
RESTART_PID=$!
echo "Restart PID: ${RESTART_PID}"

# Wait for restart to complete
echo "Waiting for restored app to finish (timeout: 300s) ..."
RESTART_DEADLINE=$((SECONDS + 300))
RESTORE_DONE=false
while [[ $SECONDS -lt $RESTART_DEADLINE ]]; do
    if ! kill -0 "${RESTART_PID}" 2>/dev/null; then
        RESTORE_DONE=true
        break
    fi
    # Check for completion markers
    if grep -q "Save the reconstruction" "${RUN_DIR}/stdout_restart.txt" 2>/dev/null; then
        echo "[INFO] Saw 'Save the reconstruction' in restart output"
        RESTORE_DONE=true
        break
    fi
    sleep 2
done

wait "${RESTART_PID}" 2>/dev/null || true
RESTART_EXIT=$?

if $RESTORE_DONE; then
    echo "[OK] Restart completed (exit=${RESTART_EXIT})"
else
    echo "[WARN] Restart timed out or still running (exit=${RESTART_EXIT})"
fi

echo ""
echo "--- Restart stdout ---"
cat "${RUN_DIR}/stdout_restart.txt" 2>/dev/null || echo "(empty)"
echo ""
echo "--- Restart stderr (last 20 lines) ---"
tail -20 "${RUN_DIR}/stderr_restart.txt" 2>/dev/null || echo "(empty)"
echo ""

# ══════════════════════════════════════════════════════════════════════════
# Phase 5: Verify output
# ══════════════════════════════════════════════════════════════════════════
echo ""
echo "=== Phase 5: Verify output ==="
echo ""

# Check for recon.h5 in run directory
OUTPUT_FILE="${RUN_DIR}/recon.h5"
if [[ -f "${OUTPUT_FILE}" ]]; then
    OUTPUT_SIZE=$(stat -c%s "${OUTPUT_FILE}" 2>/dev/null || echo "?")
    OUTPUT_MTIME=$(stat -c%Y "${OUTPUT_FILE}" 2>/dev/null || echo "?")
    echo "[OK] Output file exists: ${OUTPUT_FILE}"
    echo "     Size: ${OUTPUT_SIZE} bytes"
    echo "     Modified: $(date -d @${OUTPUT_MTIME} 2>/dev/null || echo "${OUTPUT_MTIME}")"
else
    echo "[WARN] Output file not found at ${OUTPUT_FILE}"
    echo "       Checking other locations..."
    for loc in "${TEST_DIR}" "${CKPT_DIR}" "/tmp" "."; do
        FOUND=$(find "${loc}" -name "recon.h5" -type f 2>/dev/null | head -1)
        if [[ -n "${FOUND}" ]]; then
            echo "       Found: ${FOUND}"
            OUTPUT_FILE="${FOUND}"
            break
        fi
    done
fi

# ── Cleanup ──────────────────────────────────────────────────────────────
"${DMTCP_COMMAND}" -h "${COORD_HOST}" --coord-port "${COORD_PORT}" --quit 2>/dev/null || true

echo ""
echo "============================================================"
echo "  Test Summary"
echo "============================================================"
echo ""
echo "  Phase 1 (Launch):     $(kill -0 "${MPI_PID}" 2>/dev/null && echo 'RUNNING' || echo 'DONE')"
echo "  Phase 2 (Checkpoint): $([ -n "${CKPT_FILES:-}" ] && echo "OK (${CKPT_COUNT} files)" || echo 'FAIL')"
echo "  Phase 3 (Kill):       $([ -n "${TARGET_PID:-}" ] && echo "OK (killed PID ${TARGET_PID})" || echo 'SKIP')"
echo "  Phase 4 (Restart):    exit=${RESTART_EXIT}"
echo "  Phase 5 (Output):     $([ -f "${OUTPUT_FILE}" ] && echo 'OK' || echo 'MISSING')"
echo ""

if [[ "${RESTART_EXIT}" -eq 0 ]] && [[ -f "${OUTPUT_FILE}" ]]; then
    echo "  RESULT: PASS"
else
    echo "  RESULT: FAIL (restart_exit=${RESTART_EXIT}, output=$([ -f "${OUTPUT_FILE}" ] && echo 'found' || echo 'missing'))"
fi
echo ""
echo "  Full logs: ${TEST_DIR}/"
echo "============================================================"
