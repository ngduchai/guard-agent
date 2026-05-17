#!/usr/bin/env bash
# correctness_retry.sh — Re-run correctness validation for the apps that
# failed (or never started) during the overnight benchmark batch.
#
# Failures from /tmp/overnight.log:
#   PRK_Stencil  — stale source-tree state files loaded a final-iteration
#                  checkpoint, starving the failure injector
#   SAMRAI       — disk filled to 100% during the (massive) build
#   ROSS         — same: build couldn't run with disk full
#   WarpX        — never started: batch hung on the cascading failures
#   QMCPACK      — never started: same
#   Nyx          — never started: same
#
# All causes have been addressed in source:
#   - 72 GB freed from /tmp; 245 MB stale state files removed from
#     tests/apps/checkpointed/PRK_Stencil/Stencil/
#   - validation/veloc/runner.py now skips checkpoint-looking files
#     (prk_stencil_state-*, *.ckpt, *.veloc, veloc_ckpts/, ckpt_iter*)
#     in _symlink_input_data so future stale artifacts do not poison runs
#   - .gitignore extended to keep the cruft out of git
#
# Usage:
#   ./scripts/correctness_retry.sh
#
# Run in foreground (small scope, ~45 min wallclock).  The output is
# tee'd to /tmp/correctness_retry.log for post-run inspection.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

APPS_LIST="/tmp/apps_failed.txt"
LOG="/tmp/correctness_retry.log"

# --- Wipe the 6 apps' stale validation_output dirs so the run starts fresh.
#     (The other 14 apps' results from the overnight run are preserved.)
APPS=(PRK_Stencil SAMRAI ROSS WarpX QMCPACK Nyx)
for app in "${APPS[@]}"; do
  rm -rf "build/validation_output/${app}_reference"
done

# --- Build the focused apps file.
printf '%s\n' "${APPS[@]}" > "$APPS_LIST"

# --- Verify environment.
if [ ! -f .venv/bin/activate ]; then
  echo "ERROR: .venv/bin/activate not found. Run ./setup.sh first." >&2
  exit 1
fi
if [ ! -x build/run_batch.sh ]; then
  echo "ERROR: build/run_batch.sh missing. Run ./setup.sh first." >&2
  exit 1
fi

source .venv/bin/activate
export PYTHONPATH="$(pwd)"

echo "════════════════════════════════════════════════════════════════════"
echo "  Correctness retry for ${#APPS[@]} apps:  ${APPS[*]}"
echo "  Log: $LOG"
echo "════════════════════════════════════════════════════════════════════"

# --- Run the focused batch.
./build/run_batch.sh "$APPS_LIST" \
  --mode validate \
  --reference \
  --skip-benchmarks \
  --continue \
  2>&1 | tee "$LOG"

# --- Summary.
echo
echo "════════════════════════════════════════════════════════════════════"
echo "  Final scoreboard"
echo "════════════════════════════════════════════════════════════════════"
grep -E "^\s*\[(PASS|FAIL)\]" "$LOG" || echo "  (no results — check $LOG for fatal errors)"

PASS_COUNT=$(grep -c '\[PASS\]' "$LOG" 2>/dev/null || echo 0)
FAIL_COUNT=$(grep -c '\[FAIL\]' "$LOG" 2>/dev/null || echo 0)
echo
echo "  PASS: $PASS_COUNT / ${#APPS[@]}"
echo "  FAIL: $FAIL_COUNT / ${#APPS[@]}"
