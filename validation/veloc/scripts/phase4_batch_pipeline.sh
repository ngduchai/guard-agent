#!/usr/bin/env bash
# Phase 4 driver: per-tier iterative LLM + benchmark pipeline.
#
# For each batch (fast → mid → slow):
#   1. Filter to apps that PASSED the Phase 3 vanilla audit
#   2. Run iterative LLM (run_batch.sh --mode iterative --baseline --max-iters 10)
#      Each iteration validates the LLM-generated code via Validation B
#      (output correct AND ≥1 ckpt file AND ratio < 1.95).
#   3. Run validate (run_batch.sh --mode validate --baseline) on the same list
#      to gather production benchmarks.
#
# Per the user's overnight policy: NO hard stops.  Per-app failures are
# logged via the underlying script's normal return codes; this driver always
# proceeds to the next batch.
#
# Usage:
#   phase4_batch_pipeline.sh                # all 3 batches
#   phase4_batch_pipeline.sh fast mid       # subset
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BUILD_DIR="$REPO_ROOT/build"
AUDIT_SUMMARY="$BUILD_DIR/audit_output/audit_summary.json"

if [ "$#" -gt 0 ]; then
  BATCHES=("$@")
else
  BATCHES=(fast mid slow)
fi

# Activate venv
if [ -f "$BUILD_DIR/venv/bin/activate" ]; then
  . "$BUILD_DIR/venv/bin/activate"
fi
export PYTHONPATH="$REPO_ROOT"

# OpenCode model — propagate through to run_iterative.sh.
# Default: argo/claudeopus47 (highest-quality Anthropic on Argo dev gateway).
# Override with OPENCODE_MODEL env var, e.g.:
#   OPENCODE_MODEL=argo/gemini25pro ./phase4_batch_pipeline.sh fast
export OPENCODE_MODEL="${OPENCODE_MODEL:-argo/claudeopus47}"
echo "[phase4] Using OpenCode model: $OPENCODE_MODEL"

# Resolve cleared-apps list from Phase 3 audit summary.  Falls back to
# treating ALL apps as cleared if the summary doesn't exist (so a fresh
# repo can run Phase 4 standalone for a smoke test).
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
  echo "[phase4] WARNING: no cleared apps found in $AUDIT_SUMMARY"
  echo "[phase4] Falling back to apps_all.txt (all 19 apps)"
  CLEARED_APPS="$(grep -v '^[[:space:]]*$\|^[[:space:]]*#' "$REPO_ROOT/validation/veloc/apps_all.txt")"
fi

echo "════════════════════════════════════════════════════════════════════"
echo "[phase4] Cleared apps from Phase 3: $CLEARED_APPS"
echo "════════════════════════════════════════════════════════════════════"

PHASE4_LOG_DIR="$BUILD_DIR/phase4_logs"
mkdir -p "$PHASE4_LOG_DIR"

for tier in "${BATCHES[@]}"; do
  tier_file="$REPO_ROOT/validation/veloc/apps_${tier}.txt"
  if [ ! -f "$tier_file" ]; then
    echo "[phase4] tier file $tier_file missing; skipping $tier batch"
    continue
  fi
  # Apps in this tier (strip comments + blank lines)
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
    echo "[phase4] tier=$tier: no cleared apps in this batch — skipping"
    continue
  fi

  echo ""
  echo "════════════════════════════════════════════════════════════════════"
  echo "[phase4] tier=$tier  apps=$RUN_APPS"
  echo "════════════════════════════════════════════════════════════════════"

  # Write a temp file with the filtered app list (run_batch.sh expects a file)
  filtered_list="$PHASE4_LOG_DIR/apps_${tier}_cleared.txt"
  for a in $RUN_APPS; do echo "$a"; done > "$filtered_list"

  # Step A — iterative LLM (validates each iter via Validation B)
  echo "[phase4] tier=$tier step=iterative starting at $(date -u +%H:%M:%SZ)"
  bash "$SCRIPT_DIR/run_batch.sh" "$filtered_list" \
       --mode iterative --baseline --max-iters 10 --continue \
       > "$PHASE4_LOG_DIR/${tier}_iterative.log" 2>&1 || true
  echo "[phase4] tier=$tier step=iterative finished at $(date -u +%H:%M:%SZ)"

  # Step B — production validation + benchmarks (LLM baseline)
  echo "[phase4] tier=$tier step=validate starting at $(date -u +%H:%M:%SZ)"
  bash "$SCRIPT_DIR/run_batch.sh" "$filtered_list" \
       --mode validate --baseline --continue \
       > "$PHASE4_LOG_DIR/${tier}_validate.log" 2>&1 || true
  echo "[phase4] tier=$tier step=validate finished at $(date -u +%H:%M:%SZ)"

  # Step C — reference (human-written) benchmarks under the SAME scenarios.
  # Runs serially after Step B so machine load doesn't contaminate the
  # _baseline timings.  Source is tests/apps/checkpointed/<APP>/ (read-only,
  # never REFRESH'd).  Output lands in validation_output/<APP>_reference/.
  echo "[phase4] tier=$tier step=reference starting at $(date -u +%H:%M:%SZ)"
  bash "$SCRIPT_DIR/run_batch.sh" "$filtered_list" \
       --mode validate --reference --continue \
       > "$PHASE4_LOG_DIR/${tier}_reference.log" 2>&1 || true
  echo "[phase4] tier=$tier step=reference finished at $(date -u +%H:%M:%SZ)"
done

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "[phase4] All batches complete.  Per-tier logs in $PHASE4_LOG_DIR"
echo "════════════════════════════════════════════════════════════════════"
