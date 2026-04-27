#!/usr/bin/env bash
# One-shot follow-up: wait for the in-flight Phase 4 (PID $1) to exit, then
# benchmark the reference (human-written) checkpointed code under the SAME
# scenarios used by the LLM-baseline benchmark, so per-app comparison is
# direct (same num_procs / injection_delay / failures_per_run / num_runs
# from validation/veloc/benchmark_configs/<APP>.json).
#
# Usage:  phase4_reference_followup.sh <phase4_pid>
#
# Output: build/phase4_logs/<tier>_reference.log per tier
#         build/validation_output/<APP>_reference/ per app
set -u

if [ $# -ne 1 ]; then
  echo "Usage: $0 <phase4_pid>" >&2
  exit 2
fi
PHASE4_PID="$1"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BUILD_DIR="$REPO_ROOT/build"
PHASE4_LOG_DIR="$BUILD_DIR/phase4_logs"
mkdir -p "$PHASE4_LOG_DIR"

if [ -f "$BUILD_DIR/venv/bin/activate" ]; then
  . "$BUILD_DIR/venv/bin/activate"
fi
export PYTHONPATH="$REPO_ROOT"

echo "[phase4-ref] Waiting for Phase 4 PID $PHASE4_PID to exit..."
# tail --pid is a clean blocking wait that doesn't require us to be the parent.
tail --pid="$PHASE4_PID" -f /dev/null
echo "[phase4-ref] Phase 4 exited at $(date -u +%H:%M:%SZ); starting reference benchmarks."

# Process tiers in the same order Phase 4 does.  Each tier's cleared-app list
# was already filtered by Phase 4 against the audit_summary (PASS apps only).
for tier in fast mid slow; do
  filtered_list="$PHASE4_LOG_DIR/apps_${tier}_cleared.txt"
  if [ ! -f "$filtered_list" ]; then
    echo "[phase4-ref] tier=$tier: no cleared-app list ($filtered_list); skipping."
    continue
  fi

  echo ""
  echo "════════════════════════════════════════════════════════════════════"
  echo "[phase4-ref] tier=$tier step=reference starting at $(date -u +%H:%M:%SZ)"
  echo "════════════════════════════════════════════════════════════════════"

  bash "$SCRIPT_DIR/run_batch.sh" "$filtered_list" \
       --mode validate --reference --continue \
       > "$PHASE4_LOG_DIR/${tier}_reference.log" 2>&1 || true

  echo "[phase4-ref] tier=$tier step=reference finished at $(date -u +%H:%M:%SZ)"
done

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "[phase4-ref] All reference benchmarks complete."
echo "[phase4-ref] Per-app pairs: build/validation_output/<APP>_{baseline,reference}/"
echo "════════════════════════════════════════════════════════════════════"
