#!/usr/bin/env bash
# Phase 4 driver — per-app end-to-end flow.
#
# For each tier (fast → mid → slow):
#   For each app in tier ∩ Phase-3-cleared:
#     Step 1 — iterative LLM (run_iterative.sh --baseline)
#                 Skipped on resume if result.json already exists.
#     Step 2 — baseline benchmarks (run_validate.sh --baseline)
#                 Runs ONLY if Step 1 produced passed=true.
#                 Skipped on resume if benchmark_results.json already exists.
#     Step 3 — reference benchmarks (run_validate.sh --reference)
#                 Runs UNCONDITIONALLY (reference code is independent of LLM).
#                 Skipped on resume if benchmark_results.json already exists.
#
# Per-app failures are isolated — one app's failure does not stop the rest.
# Per the user's overnight policy: NO hard stops.
#
# Usage:
#   phase4_per_app_pipeline.sh                # all 3 tiers
#   phase4_per_app_pipeline.sh fast mid       # subset
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BUILD_DIR="$REPO_ROOT/build"
AUDIT_SUMMARY="$BUILD_DIR/audit_output/audit_summary.json"

if [ "$#" -gt 0 ]; then
  TIERS=("$@")
else
  TIERS=(fast mid slow)
fi

# Activate venv
if [ -f "$BUILD_DIR/venv/bin/activate" ]; then
  . "$BUILD_DIR/venv/bin/activate"
fi
export PYTHONPATH="$REPO_ROOT"

# OpenCode model — propagate to run_iterative.sh.
export OPENCODE_MODEL="${OPENCODE_MODEL:-argo/claudeopus47}"
echo "[phase4-perapp] Using OpenCode model: $OPENCODE_MODEL"

PHASE4_LOG_DIR="$BUILD_DIR/phase4_logs"
mkdir -p "$PHASE4_LOG_DIR"

# Cleared apps from Phase 3 audit (PASS apps only).
get_cleared_apps() {
  if [ -f "$AUDIT_SUMMARY" ]; then
    python3 -c "
import json
d = json.load(open('$AUDIT_SUMMARY'))
print(' '.join(a['name'] for a in d.get('apps', []) if a.get('status') == 'PASS'))
"
  else
    echo ""
  fi
}

CLEARED_APPS="$(get_cleared_apps)"
if [ -z "$CLEARED_APPS" ]; then
  echo "[phase4-perapp] WARNING: no cleared apps in $AUDIT_SUMMARY" >&2
  echo "[phase4-perapp] Falling back to apps_all.txt" >&2
  CLEARED_APPS="$(grep -v '^[[:space:]]*$\|^[[:space:]]*#' "$REPO_ROOT/validation/veloc/apps_all.txt" | tr '\n' ' ')"
fi

echo "════════════════════════════════════════════════════════════════════"
echo "[phase4-perapp] Cleared apps: $CLEARED_APPS"
echo "════════════════════════════════════════════════════════════════════"

# --- Per-app step helpers -----------------------------------------------
#
# Each helper writes its own log file under PHASE4_LOG_DIR so failures are
# easy to diagnose without grepping a giant tier log.

iter_already_done() {
  # Returns 0 if iter has a result.json (regardless of passed verdict).
  local app="$1"
  [ -f "$BUILD_DIR/iterative_logs/${app}_baseline/result.json" ]
}

iter_passed() {
  # Returns 0 if result.json exists AND passed=true.
  local app="$1"
  local rj="$BUILD_DIR/iterative_logs/${app}_baseline/result.json"
  [ -f "$rj" ] || return 1
  python3 -c "import json,sys; sys.exit(0 if json.load(open('$rj')).get('passed') is True else 1)" 2>/dev/null
}

baseline_bench_done() {
  # benchmark stage writes raw_metrics.json under <output_dir>/benchmarks/
  local app="$1"
  [ -f "$BUILD_DIR/validation_output/${app}_baseline/benchmarks/raw_metrics.json" ]
}

reference_bench_done() {
  local app="$1"
  [ -f "$BUILD_DIR/validation_output/${app}_reference/benchmarks/raw_metrics.json" ]
}

run_iter() {
  local app="$1"
  local log="$PHASE4_LOG_DIR/perapp_${app}_iter.log"
  if iter_already_done "$app"; then
    if iter_passed "$app"; then
      echo "[phase4-perapp]   $app: iter already PASSED (skip) at $(date -u +%H:%M:%SZ)"
    else
      echo "[phase4-perapp]   $app: iter already FAILED (skip — preserved verdict) at $(date -u +%H:%M:%SZ)"
    fi
    return 0
  fi
  echo "[phase4-perapp]   $app: iter starting at $(date -u +%H:%M:%SZ) → $log"
  bash "$SCRIPT_DIR/run_iterative.sh" --baseline "$app" --max-iters 10 \
       > "$log" 2>&1 || true
  echo "[phase4-perapp]   $app: iter finished at $(date -u +%H:%M:%SZ)"
}

run_baseline_bench() {
  local app="$1"
  local log="$PHASE4_LOG_DIR/perapp_${app}_baseline.log"
  if ! iter_passed "$app"; then
    echo "[phase4-perapp]   $app: baseline-bench skipped (iter did not pass)"
    return 0
  fi
  if baseline_bench_done "$app"; then
    echo "[phase4-perapp]   $app: baseline-bench already done (skip)"
    return 0
  fi
  echo "[phase4-perapp]   $app: baseline-bench starting at $(date -u +%H:%M:%SZ) → $log"
  # --resume so the per-app validator picks up at the next un-done trial.
  bash "$SCRIPT_DIR/run_validate.sh" --baseline "$app" --resume \
       > "$log" 2>&1 || true
  echo "[phase4-perapp]   $app: baseline-bench finished at $(date -u +%H:%M:%SZ)"
}

run_reference_bench() {
  local app="$1"
  local log="$PHASE4_LOG_DIR/perapp_${app}_reference.log"
  if reference_bench_done "$app"; then
    echo "[phase4-perapp]   $app: reference-bench already done (skip)"
    return 0
  fi
  if [ ! -d "$REPO_ROOT/tests/apps/checkpointed/$app" ]; then
    echo "[phase4-perapp]   $app: reference-bench skipped (no tests/apps/checkpointed/$app)"
    return 0
  fi
  echo "[phase4-perapp]   $app: reference-bench starting at $(date -u +%H:%M:%SZ) → $log"
  # --skip-correctness: reference apps don't ship veloc.cfg, so the
  # checkpoint-observed correctness stage would FATAL on missing scratch
  # paths.  We only need stage 2 metrics (timing + checkpoint size) for
  # the reference comparison.  --reference-input-priority is added
  # automatically by run_validate.sh when --reference is set.
  bash "$SCRIPT_DIR/run_validate.sh" --reference "$app" --resume --skip-correctness \
       > "$log" 2>&1 || true
  echo "[phase4-perapp]   $app: reference-bench finished at $(date -u +%H:%M:%SZ)"
}

# --- Tier loop -----------------------------------------------------------

for tier in "${TIERS[@]}"; do
  tier_file="$REPO_ROOT/validation/veloc/apps_${tier}.txt"
  if [ ! -f "$tier_file" ]; then
    echo "[phase4-perapp] tier file $tier_file missing; skipping $tier"
    continue
  fi

  TIER_APPS=$(sed 's/[[:space:]]*#.*$//' "$tier_file" | grep -v '^[[:space:]]*$' | tr '\n' ' ')

  # Intersection: tier ∩ cleared
  RUN_APPS=""
  for a in $TIER_APPS; do
    for c in $CLEARED_APPS; do
      if [ "$a" = "$c" ]; then
        RUN_APPS="$RUN_APPS $a"
        break
      fi
    done
  done
  RUN_APPS="$(echo $RUN_APPS | xargs)"

  if [ -z "$RUN_APPS" ]; then
    echo "[phase4-perapp] tier=$tier: no cleared apps; skipping"
    continue
  fi

  echo ""
  echo "════════════════════════════════════════════════════════════════════"
  echo "[phase4-perapp] tier=$tier  apps=$RUN_APPS"
  echo "[phase4-perapp] tier=$tier starting at $(date -u +%H:%M:%SZ)"
  echo "════════════════════════════════════════════════════════════════════"

  for app in $RUN_APPS; do
    echo ""
    echo "──────────────────────────────────────────────────────────────────"
    echo "[phase4-perapp] tier=$tier  app=$app  starting at $(date -u +%H:%M:%SZ)"
    echo "──────────────────────────────────────────────────────────────────"

    # Kill any stray processes from a previous app.
    pkill -9 -f "mpirun|mpiexec|orted|failure_injector.py" 2>/dev/null || true

    run_iter "$app"
    run_baseline_bench "$app"
    run_reference_bench "$app"

    echo "[phase4-perapp] tier=$tier  app=$app  done at $(date -u +%H:%M:%SZ)"
  done

  echo ""
  echo "════════════════════════════════════════════════════════════════════"
  echo "[phase4-perapp] tier=$tier finished at $(date -u +%H:%M:%SZ)"
  echo "════════════════════════════════════════════════════════════════════"
done

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "[phase4-perapp] All tiers complete.  Per-app logs in $PHASE4_LOG_DIR/perapp_*"
echo "[phase4-perapp] Per-app pairs: build/validation_output/<APP>_{baseline,reference}/"
echo "════════════════════════════════════════════════════════════════════"
