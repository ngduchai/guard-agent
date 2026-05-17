#!/usr/bin/env bash
# validate_baseline_3tier.sh — Run the OpenCode-only baseline pipeline
# (no guard-agent MCP) for the fast → mid → slow batches, mirroring the
# 3-batch reference workflow.
#
# Designed for unattended overnight / multi-day runs:
#   - default --max-iters 20  (gives weak apps room to converge)
#   - default --continue=true (skips apps that already produced result.json)
#   - --detach auto-launches under nohup; prints PID + log paths and exits
#   - pre-run disk-space gate (aborts if < 10 GB free, warns if < 30 GB)
#   - pre-run /tmp cleanup of stale tmp* dirs > 100 MB (prevents the
#     ENOSPC regression that killed the overnight run)
#   - sentinel file /tmp/baseline_done.sentinel written when finished
#   - timestamped per-tier banners in /tmp/baseline_summary.log
#
# For each tier:
#   1. Iteratively invoke OpenCode against the vanilla source per app
#   2. After each iteration, run the validation framework
#   3. If FAIL, feed the error back to OpenCode and retry (up to --max-iters)
#   4. If PASS, capture metrics and move on
#
# Per-app artifacts:
#   build/tests_baseline/<APP>/                 — OpenCode-injected source
#   build/iterative_logs/<APP>_baseline/        — per-iteration log + result.json
#   build/validation_output/<APP>_baseline/     — validation report
#
# Logs:
#   /tmp/baseline_fast.log
#   /tmp/baseline_mid.log
#   /tmp/baseline_slow.log
#   /tmp/baseline_summary.log                   — aggregated PASS/FAIL across tiers
#   /tmp/baseline_done.sentinel                 — written on completion (success OR failure)
#
# Usage:
#   ./scripts/validate_baseline_3tier.sh                     # all 3 tiers, foreground
#   ./scripts/validate_baseline_3tier.sh --detach            # all 3 tiers, background + nohup
#   ./scripts/validate_baseline_3tier.sh fast                # one tier, foreground
#   ./scripts/validate_baseline_3tier.sh mid slow --detach   # subset, background
#   ./scripts/validate_baseline_3tier.sh --max-iters 10      # cap iterations (default: 20)
#   ./scripts/validate_baseline_3tier.sh --no-continue       # force restart (default skips done apps)
#
# Quick status from another shell:
#   ls -la /tmp/baseline_done.sentinel       # exists? → run finished
#   cat /tmp/baseline_summary.log            # tier-by-tier scoreboard
#   tail -F /tmp/baseline_$(cat /tmp/baseline_current_tier 2>/dev/null).log
#   grep -E "^\s*\[(PASS|FAIL)\]" /tmp/baseline_*.log

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# --- Defaults tuned for unattended runs ---
TIERS=()
MAX_ITERS=20
CONTINUE=true   # default true; --no-continue disables
DETACH=false
MIN_FREE_ABORT_GB=10
MIN_FREE_WARN_GB=30

# --- Parse args ---
while [ $# -gt 0 ]; do
  case "$1" in
    --max-iters)    MAX_ITERS="$2"; shift 2 ;;
    --continue)     CONTINUE=true; shift ;;
    --no-continue)  CONTINUE=false; shift ;;
    --detach)       DETACH=true; shift ;;
    fast|mid|slow)  TIERS+=("$1"); shift ;;
    -h|--help)
      sed -n '2,/^set -e$/{ /^#/s/^# \?//p }' "$0"; exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2
      echo "Use one of: fast | mid | slow | --max-iters N | --[no-]continue | --detach | --help" >&2
      exit 1 ;;
  esac
done
if [ ${#TIERS[@]} -eq 0 ]; then
  TIERS=(fast mid slow)
fi

# --- --detach: re-exec self under nohup, print PID + tails, then exit ---
if $DETACH; then
  # Strip --detach so the child invocation runs normally.
  child_args=()
  for t in "${TIERS[@]}"; do child_args+=("$t"); done
  child_args+=(--max-iters "$MAX_ITERS")
  $CONTINUE && child_args+=(--continue) || child_args+=(--no-continue)
  rm -f /tmp/baseline_done.sentinel
  nohup "$0" "${child_args[@]}" \
    > /tmp/baseline_run.nohup 2>&1 &
  pid=$!
  disown $pid 2>/dev/null || true
  echo "════════════════════════════════════════════════════════════════════"
  echo "  Detached baseline run started"
  echo "════════════════════════════════════════════════════════════════════"
  echo "  PID:           $pid"
  echo "  Tiers:         ${TIERS[*]}"
  echo "  Max iters:     $MAX_ITERS"
  echo "  Continue:      $CONTINUE"
  echo
  echo "  Live log:      tail -F /tmp/baseline_run.nohup"
  echo "  Per-tier logs: /tmp/baseline_{fast,mid,slow}.log"
  echo "  Summary:       /tmp/baseline_summary.log"
  echo "  Sentinel:      /tmp/baseline_done.sentinel  (appears when finished)"
  echo
  echo "  Status check (run anytime):"
  echo "    ls -la /tmp/baseline_done.sentinel      # exists? → done"
  echo "    cat /tmp/baseline_summary.log           # tier-by-tier scoreboard"
  echo "    grep -E '^\\s*\\[(PASS|FAIL)\\]' /tmp/baseline_*.log"
  echo "════════════════════════════════════════════════════════════════════"
  exit 0
fi

# --- Verify environment ---
if [ ! -f .venv/bin/activate ]; then
  echo "ERROR: .venv/bin/activate not found. Run ./setup.sh first." >&2; exit 1
fi
if [ ! -x build/run_batch.sh ]; then
  echo "ERROR: build/run_batch.sh missing. Run ./setup.sh first." >&2; exit 1
fi
for tier in "${TIERS[@]}"; do
  if [ ! -f "validation/veloc/apps_${tier}.txt" ]; then
    echo "ERROR: validation/veloc/apps_${tier}.txt missing." >&2; exit 1
  fi
done

# --- Pre-flight: disk space gate ---
free_gb=$(df --output=avail -BG / | tail -1 | tr -dc '0-9')
if [ -z "$free_gb" ] || [ "$free_gb" -lt "$MIN_FREE_ABORT_GB" ]; then
  echo "ERROR: only ${free_gb:-0} GB free on /. Need at least $MIN_FREE_ABORT_GB GB." >&2
  echo "Try: rm -rf /tmp/sst-* /tmp/tmp[a-zA-Z0-9_]*" >&2
  exit 1
fi
if [ "$free_gb" -lt "$MIN_FREE_WARN_GB" ]; then
  echo "WARNING: only $free_gb GB free on /. Heavy builds (SAMRAI, WarpX) may need more." >&2
fi

# --- Pre-flight: clean stale /tmp/tmp* dirs > 100 MB
# (Same trap that ate disk during the overnight benchmark run.)
for d in /tmp/tmp[a-zA-Z0-9_]*/; do
  [ -d "$d" ] || continue
  sz=$(du -sm "$d" 2>/dev/null | cut -f1)
  if [ -n "$sz" ] && [ "$sz" -gt 100 ]; then
    echo "[preflight] removing stale tmp dir: $d (${sz} MB)"
    rm -rf "$d"
  fi
done

source .venv/bin/activate
export PYTHONPATH="$(pwd)"

SUMMARY_LOG="/tmp/baseline_summary.log"
SENTINEL="/tmp/baseline_done.sentinel"
CURRENT_TIER_FILE="/tmp/baseline_current_tier"
rm -f "$SENTINEL" "$CURRENT_TIER_FILE"
: > "$SUMMARY_LOG"

# Always write the sentinel on exit (covers normal completion AND failures).
_write_sentinel() {
  exit_code=$?
  rm -f "$CURRENT_TIER_FILE"
  {
    echo "finished: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "exit_code: $exit_code"
    echo
    cat "$SUMMARY_LOG" 2>/dev/null
  } > "$SENTINEL"
}
trap _write_sentinel EXIT

# --- Per-tier extra flags forwarded to run_batch.sh ---
EXTRA_FLAGS=()
$CONTINUE && EXTRA_FLAGS+=(--continue)

# --- Run each tier ---
for tier in "${TIERS[@]}"; do
  echo "$tier" > "$CURRENT_TIER_FILE"
  log="/tmp/baseline_${tier}.log"
  apps_file="validation/veloc/apps_${tier}.txt"
  app_count=$(grep -v '^#' "$apps_file" | grep -cv '^[[:space:]]*$' || echo 0)

  banner=$(printf '=%.0s' {1..70})
  {
    echo "$banner"
    echo "  BASELINE tier: $tier  ($app_count apps, max-iters=$MAX_ITERS, continue=$CONTINUE)"
    echo "  apps file: $apps_file"
    echo "  log:       $log"
    echo "  started:   $(date '+%Y-%m-%d %H:%M:%S')"
    echo "  free disk: $(df -h / | awk 'NR==2 {print $4}')"
    echo "$banner"
  } | tee -a "$SUMMARY_LOG"

  # Use --mode iterative --baseline so OpenCode is invoked WITHOUT the
  # guard-agent MCP, then validated, with retry-on-fail up to MAX_ITERS.
  # --continue cascades to the per-app skip-if-result.json marker.
  ./build/run_batch.sh "$apps_file" \
    --mode iterative \
    --baseline \
    --max-iters "$MAX_ITERS" \
    "${EXTRA_FLAGS[@]}" \
    2>&1 | tee "$log"

  # Per-tier scoreboard appended to the rolling summary.
  {
    echo
    echo "--- $tier tier results ---"
    grep -E "^\s*\[(PASS|FAIL)\]" "$log" || echo "  (no [PASS]/[FAIL] markers in log)"
    echo "  finished: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "  free disk: $(df -h / | awk 'NR==2 {print $4}')"
    echo
  } | tee -a "$SUMMARY_LOG"
done

# --- Final aggregated scoreboard ---
banner=$(printf '=%.0s' {1..70})
{
  echo "$banner"
  echo "  BASELINE 3-TIER SUMMARY  ($(date '+%Y-%m-%d %H:%M:%S'))"
  echo "$banner"
  for tier in "${TIERS[@]}"; do
    log="/tmp/baseline_${tier}.log"
    [ -f "$log" ] || continue
    pass=$(grep -c '\[PASS\]' "$log" 2>/dev/null || echo 0)
    fail=$(grep -c '\[FAIL\]' "$log" 2>/dev/null || echo 0)
    printf '  %-5s  PASS: %2d   FAIL: %2d   (log: %s)\n' "$tier" "$pass" "$fail" "$log"
  done
  echo "$banner"
  echo "  Per-tier logs:      /tmp/baseline_{fast,mid,slow}.log"
  echo "  Per-app artifacts:  build/iterative_logs/<APP>_baseline/result.json"
  echo "  Validation reports: build/validation_output/<APP>_baseline/summary_report.md"
  echo "  Sentinel written:   /tmp/baseline_done.sentinel"
  echo "$banner"
} | tee -a "$SUMMARY_LOG"
