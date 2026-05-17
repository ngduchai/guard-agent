#!/usr/bin/env bash
# baseline_full_pipeline.sh — End-to-end overnight orchestrator.
#
# Per tier (fast → mid → slow):
#   STAGE 1.  Iterative-baseline (OpenCode + iterative build/validate/fix loop)
#             for every app in the tier.  Resumes via --continue on apps that
#             already have iterative_logs/<APP>_baseline/result.json.
#   STAGE 2.  For every app that PASSed Stage 1: run the full validation
#             pipeline on the agent-generated code (correctness + benchmarks
#             + report).  Captures checkpoint_metrics.json (size + per-dir
#             breakdown), benchmarks/raw_metrics.json (timing, memory,
#             checkpoint_size_bytes via the new POSIX-fallback path), and
#             summary_report.md.
#   STAGE 3.  For every app in the tier (regardless of baseline outcome):
#             ensure the human-reference build has a complete validation
#             record.  Audits build/validation_output/<APP>_reference/ for
#             missing test_results.json / raw_metrics.json / checkpoint
#             measurements; re-runs validate.py to gap-fill what's missing.
#   STAGE 4.  Append a per-tier summary to /tmp/baseline_full_pipeline.log.
#
# Designed to run unattended for many hours.  Logs each stage to its own
# file so you can spot-check from another shell:
#
#   /tmp/baseline_full_pipeline.log              — orchestrator banners + per-tier scoreboard
#   /tmp/baseline_iter_<tier>.log                — Stage 1 iterative baseline
#   /tmp/baseline_bench_<tier>_<app>.log         — Stage 2 per-app benchmark
#   /tmp/baseline_ref_<tier>_<app>.log           — Stage 3 per-app reference re-run
#   /tmp/baseline_full_pipeline.sentinel         — written when finished
#   /tmp/baseline_full_pipeline.nohup            — wrapper stdout when --detach is used
#
# Usage:
#   ./scripts/baseline_full_pipeline.sh                          # all 3 tiers, foreground
#   ./scripts/baseline_full_pipeline.sh --detach                 # all 3 tiers, background
#   ./scripts/baseline_full_pipeline.sh fast                     # one tier
#   ./scripts/baseline_full_pipeline.sh --max-iters 10           # cap iterations (default 20)
#   ./scripts/baseline_full_pipeline.sh --reference-only         # skip Stage 1+2, just gap-fill ref
#   ./scripts/baseline_full_pipeline.sh --no-continue            # force restart of Stage 1 per app
#
# Quick status from another shell:
#   ls -la /tmp/baseline_full_pipeline.sentinel    # exists? → done
#   cat /tmp/baseline_full_pipeline.log            # tier-by-tier scoreboard
#   tail -F /tmp/baseline_full_pipeline.log

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

TIERS=()
MAX_ITERS=20
CONTINUE=true
DETACH=false
REFERENCE_ONLY=false
MIN_FREE_GB_ABORT=10
MIN_FREE_GB_WARN=30

while [ $# -gt 0 ]; do
  case "$1" in
    --max-iters)        MAX_ITERS="$2"; shift 2 ;;
    --continue)         CONTINUE=true; shift ;;
    --no-continue)      CONTINUE=false; shift ;;
    --detach)           DETACH=true; shift ;;
    --reference-only)   REFERENCE_ONLY=true; shift ;;
    fast|mid|slow)      TIERS+=("$1"); shift ;;
    -h|--help)
      sed -n '2,/^set -e$/{ /^#/s/^# \?//p }' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done
[ ${#TIERS[@]} -eq 0 ] && TIERS=(fast mid slow)

if $DETACH; then
  child_args=()
  for t in "${TIERS[@]}"; do child_args+=("$t"); done
  child_args+=(--max-iters "$MAX_ITERS")
  $CONTINUE && child_args+=(--continue) || child_args+=(--no-continue)
  $REFERENCE_ONLY && child_args+=(--reference-only)
  rm -f /tmp/baseline_full_pipeline.sentinel
  nohup "$0" "${child_args[@]}" > /tmp/baseline_full_pipeline.nohup 2>&1 &
  pid=$!
  disown $pid 2>/dev/null || true
  echo "════════════════════════════════════════════════════════════════════"
  echo "  baseline_full_pipeline detached"
  echo "════════════════════════════════════════════════════════════════════"
  echo "  PID:        $pid"
  echo "  Tiers:      ${TIERS[*]}"
  echo "  Max iters:  $MAX_ITERS"
  echo "  Continue:   $CONTINUE"
  echo "  Ref-only:   $REFERENCE_ONLY"
  echo
  echo "  Live log:   tail -F /tmp/baseline_full_pipeline.log"
  echo "  Sentinel:   ls /tmp/baseline_full_pipeline.sentinel"
  echo "════════════════════════════════════════════════════════════════════"
  exit 0
fi

# --- Pre-flight ---
[ -f .venv/bin/activate ] || { echo "ERROR: .venv missing"; exit 1; }
[ -x build/run_batch.sh ] || { echo "ERROR: build/run_batch.sh missing"; exit 1; }
[ -x build/run_validate.sh ] || { echo "ERROR: build/run_validate.sh missing"; exit 1; }

free_gb=$(df --output=avail -BG / | tail -1 | tr -dc '0-9')
[ "${free_gb:-0}" -lt "$MIN_FREE_GB_ABORT" ] && { echo "ERROR: only ${free_gb} GB free"; exit 1; }
[ "${free_gb:-0}" -lt "$MIN_FREE_GB_WARN" ] && echo "WARN: only ${free_gb} GB free"

# Pre-clean stale /tmp dirs > 100 MB
for d in /tmp/tmp[a-zA-Z0-9_]*/; do
  [ -d "$d" ] || continue
  sz=$(du -sm "$d" 2>/dev/null | cut -f1)
  [ -n "$sz" ] && [ "$sz" -gt 100 ] && { echo "[preflight] removing $d (${sz}MB)"; rm -rf "$d"; }
done

source .venv/bin/activate
export PYTHONPATH="$(pwd)"

LOG=/tmp/baseline_full_pipeline.log
SENTINEL=/tmp/baseline_full_pipeline.sentinel
CURRENT_TIER_FILE=/tmp/baseline_full_pipeline_tier
rm -f "$SENTINEL" "$CURRENT_TIER_FILE"
: > "$LOG"

_write_sentinel() {
  ec=$?
  rm -f "$CURRENT_TIER_FILE"
  {
    echo "finished: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "exit_code: $ec"
    echo
    cat "$LOG" 2>/dev/null
  } > "$SENTINEL"
}
trap _write_sentinel EXIT

banner() { local b; b=$(printf '=%.0s' {1..70}); echo "$b"; echo "  $*"; echo "$b"; }

# Read app list (strips comments + blanks)
read_apps() {
  sed 's/[[:space:]]*#.*$//' "$1" | grep -v '^[[:space:]]*$' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

# Did this app PASS Stage 1 (iterative baseline)?
iter_baseline_passed() {
  local app="$1"
  local rj="build/iterative_logs/${app}_baseline/result.json"
  [ -f "$rj" ] && python3 -c "import json; d=json.load(open('$rj')); raise SystemExit(0 if d.get('passed') else 1)" 2>/dev/null
}

# Does this implementation have a complete validation record?
metrics_complete() {
  local app="$1" impl="$2"   # impl = baseline | reference
  local out="build/validation_output/${app}_${impl}"
  [ -d "$out" ] || return 1
  [ -f "$out/correctness/test_results.json" ] || return 1
  [ -f "$out/benchmarks/raw_metrics.json" ] || return 1
  [ -f "$out/summary_report.md" ] || return 1
  # Verify benchmark has both scenarios × both codebases × non-null elapsed_s
  python3 - <<EOF || return 1
import json
d = json.load(open("$out/benchmarks/raw_metrics.json"))
need = {("small-nofail","original"),("small-nofail","resilient"),
        ("small-low","original"),("small-low","resilient")}
seen = {(r["scenario_name"], r["codebase"]) for r in d.get("runs",[]) if r.get("elapsed_s")}
import sys
sys.exit(0 if need.issubset(seen) else 1)
EOF
  return 0
}

# Run validate.py for one app/impl, with --resume to skip already-done stages.
run_validation() {
  local app="$1" impl="$2" log="$3"
  local flag="--$impl"
  echo "[orchestrator] validate ($impl): $app  → $log" | tee -a "$LOG"
  ./build/run_validate.sh "$flag" "$app" --resume 2>&1 | tee "$log" \
    | grep --line-buffered -E "^\s*\[(PASS|FAIL)\]|FATAL|STAGE [0-9]" \
    >> "$LOG" || true
}

# ==============================================================
# Per-tier loop
# ==============================================================
for tier in "${TIERS[@]}"; do
  echo "$tier" > "$CURRENT_TIER_FILE"
  apps_file="validation/veloc/apps_${tier}.txt"
  [ -f "$apps_file" ] || { echo "ERROR: $apps_file missing" >&2; continue; }
  mapfile -t apps < <(read_apps "$apps_file")

  banner "TIER $tier — $(date '+%H:%M:%S') — apps: ${apps[*]}" | tee -a "$LOG"

  # ---------- STAGE 1: Iterative baseline ----------
  if ! $REFERENCE_ONLY; then
    iter_log="/tmp/baseline_iter_${tier}.log"
    banner "$tier STAGE 1 — iterative baseline ($MAX_ITERS iters max) → $iter_log" | tee -a "$LOG"
    EXTRA=()
    $CONTINUE && EXTRA+=(--continue)
    ./build/run_batch.sh "$apps_file" \
      --mode iterative --baseline --max-iters "$MAX_ITERS" \
      "${EXTRA[@]}" 2>&1 | tee "$iter_log" \
      | grep --line-buffered -E "^\s*\[(PASS|FAIL)\] [A-Za-z0-9_+]+" \
      >> "$LOG" || true
    echo "[orchestrator] $tier Stage 1 done at $(date '+%H:%M:%S')" | tee -a "$LOG"
  fi

  # ---------- STAGE 2: Baseline benchmark for PASS apps ----------
  if ! $REFERENCE_ONLY; then
    banner "$tier STAGE 2 — baseline benchmark for PASS apps" | tee -a "$LOG"
    for app in "${apps[@]}"; do
      if iter_baseline_passed "$app"; then
        bench_log="/tmp/baseline_bench_${tier}_${app}.log"
        run_validation "$app" "baseline" "$bench_log"
      else
        echo "[orchestrator] skip baseline-benchmark $app (Stage 1 did not pass)" | tee -a "$LOG"
      fi
    done
  fi

  # ---------- STAGE 3: Reference gap-fill ----------
  banner "$tier STAGE 3 — reference validation completeness" | tee -a "$LOG"
  for app in "${apps[@]}"; do
    if metrics_complete "$app" "reference"; then
      echo "[orchestrator] reference $app already complete" | tee -a "$LOG"
      continue
    fi
    ref_log="/tmp/baseline_ref_${tier}_${app}.log"
    run_validation "$app" "reference" "$ref_log"
  done

  # ---------- STAGE 4: Tier summary ----------
  echo | tee -a "$LOG"
  banner "$tier SUMMARY — $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG"
  printf "%-15s %-10s %-10s %-10s\n" "app" "iter_b" "bench_b" "bench_ref" | tee -a "$LOG"
  for app in "${apps[@]}"; do
    ib="?"; bb="?"; br="?"
    iter_baseline_passed "$app" && ib="PASS" || ib="FAIL"
    metrics_complete "$app" "baseline"   && bb="OK"   || bb="MISS"
    metrics_complete "$app" "reference"  && br="OK"   || br="MISS"
    printf "%-15s %-10s %-10s %-10s\n" "$app" "$ib" "$bb" "$br" | tee -a "$LOG"
  done
done

banner "ALL TIERS DONE — $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG"
