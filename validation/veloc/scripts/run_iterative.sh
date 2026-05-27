#!/usr/bin/env bash
set -e

# Clean up child processes on exit to prevent zombies after Ctrl+C / signals.
_cleanup() {
  pkill -9 -P $$ 2>/dev/null || true
  pkill -9 -f "failure_injector.py" 2>/dev/null || true
}

# Signal-trap diagnostics (ISSUES.md #44 fix).  When this wrapper is killed
# (TERM/HUP/INT/QUIT — SIGKILL is uncatchable), capture WHO killed us and
# WHAT state we were in, so the next occurrence is debuggable from the on-
# disk record alone.  Two outputs:
#   1) $LOG_DIR/_signal_termination.log — stamped record of (signal, exit
#      code, parent PID, parent cmd, timestamp, current iteration)
#   2) $LOG_DIR/result.json with `_signal_terminated: true` if no result.json
#      already exists (preserves the iter outcome that would otherwise be
#      lost between validate.py finishing and the wrapper's normal write).
_on_signal() {
  local sig="$1"
  local rc=$?
  local ts ppid pcmd
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  ppid="$(ps -o ppid= -p $$ 2>/dev/null | tr -d ' ' || echo unknown)"
  pcmd="$(ps -o args= -p "$ppid" 2>/dev/null | head -1 || echo unknown)"
  if [ -n "${LOG_DIR:-}" ] && [ -d "$LOG_DIR" ]; then
    {
      echo "ts=$ts signal=$sig exit_code=$rc"
      echo "self_pid=$$  parent_pid=$ppid"
      echo "parent_cmd=$pcmd"
      echo "iteration=${ITER:-pre-loop}  log_dir=$LOG_DIR"
      echo "running_totals: total_elapsed_s=${TOTAL_ELAPSED:-0} total_tokens=${TOTAL_TOKENS:-0}"
    } >> "$LOG_DIR/_signal_termination.log" 2>/dev/null || true
    # Only write a partial result.json if no real one exists — finalized
    # writes (lines ~401, ~498, ~534 below) always come BEFORE a clean exit,
    # so the presence of result.json means the loop completed normally.
    if [ ! -f "$LOG_DIR/result.json" ]; then
      cat > "$LOG_DIR/result.json" 2>/dev/null << EOFSIG || true
{
  "app_name": "${APP_NAME:-unknown}",
  "mode": "${LABEL:-unknown}",
  "passed": false,
  "_signal_terminated": true,
  "_signal": "$sig",
  "_killer_pid": "$ppid",
  "_killer_cmd": "$pcmd",
  "_terminated_at": "$ts",
  "iterations": ${ITER:-0},
  "max_iters": ${MAX_ITERS:-0},
  "total_elapsed_s": ${TOTAL_ELAPSED:-0},
  "total_input_tokens": ${TOTAL_INPUT_TOKENS:-0},
  "total_output_tokens": ${TOTAL_OUTPUT_TOKENS:-0},
  "total_tokens": ${TOTAL_TOKENS:-0},
  "per_iteration": [${ITER_METRICS:-}
  ]
}
EOFSIG
    fi
  fi
  echo "[iter] terminated by signal=$sig exit_code=$rc parent_pid=$ppid parent_cmd=$pcmd" >&2
  _cleanup
  # Re-raise the signal so the parent sees the actual signal exit code.
  trap - "$sig"
  kill -"$sig" $$
}
trap '_on_signal TERM' TERM
trap '_on_signal HUP'  HUP
trap '_on_signal INT'  INT
trap '_on_signal QUIT' QUIT
trap _cleanup EXIT

# Usage: ./run_iterative.sh [--baseline] <app_name> [--max-iters N]
#
# Automated evaluation loop:
#   1. Run OpenCode non-interactively with the app's prompt
#   2. Run correctness validation
#   3. If PASS -> done
#   4. If FAIL -> feed error logs back to OpenCode and repeat
#
# Captures per-iteration metrics: elapsed time, validation result.
# Saves enriched result.json with timing data for comparison.
#
# Modes:
#   ./run_iterative.sh art_simple              # with guard-agent MCP
#   ./run_iterative.sh --baseline art_simple   # without guard-agent (baseline)
#
# Options:
#   --max-iters N    Maximum iterations (default: 30)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BUILD_DIR="$REPO_ROOT/build"

# Activate venv
if [ -f "$BUILD_DIR/venv/bin/activate" ]; then
  . "$BUILD_DIR/venv/bin/activate"
fi
export PYTHONPATH="${REPO_ROOT}"

# --- Parse args ---
USE_BASELINE=false
MAX_ITERS=50
INJECTION_DELAY=""
GROUND_TRUTH_DIR=""

APP_NAME=""
while [ $# -gt 0 ]; do
  case "$1" in
    --baseline)          USE_BASELINE=true; shift ;;
    --max-iters)         MAX_ITERS="$2"; shift 2 ;;
    --injection-delay)   INJECTION_DELAY="$2"; shift 2 ;;
    --ground-truth-dir)  GROUND_TRUTH_DIR="$2"; shift 2 ;;
    -*)                  echo "Unknown option: $1" >&2; exit 1 ;;
    *)                   APP_NAME="$1"; shift ;;
  esac
done

if [ -z "$APP_NAME" ]; then
  echo "Usage: run_iterative.sh [--baseline] <app_name> [--max-iters N]" >&2
  exit 1
fi

# --- Resolve paths ---
# MODEL_TAG env var (set by run_iterative_for_model.sh wrapper for 3-D model
# exploration cells) shards every output path with the LLM tag so multiple
# cells can run concurrently without clobbering each other's data.  When unset
# (default), behavior is exactly as before — the Opus 4.7 baseline lives at
# un-suffixed paths.
MODEL_TAG="${MODEL_TAG:-}"
_TAG_PATH_SUFFIX=""
[ -n "$MODEL_TAG" ] && _TAG_PATH_SUFFIX="_${MODEL_TAG}"

if [ "$USE_BASELINE" = true ]; then
  APP_DIR="$BUILD_DIR/tests_baseline${_TAG_PATH_SUFFIX}/$APP_NAME"
  LABEL="baseline${_TAG_PATH_SUFFIX}"
  VALIDATE_FLAG="--baseline"
else
  APP_DIR="$BUILD_DIR/tests${_TAG_PATH_SUFFIX}/$APP_NAME"
  LABEL="guard-agent${_TAG_PATH_SUFFIX}"
  VALIDATE_FLAG=""
fi

# Re-copy source from original to ensure a clean starting point.
# Prevents stale modifications from a previous interrupted run.
# Also remember the matched vanilla root so D3 retry-on-stall can re-copy
# from the SAME source on each loop attempt (without re-scanning).
VANILLA_SRC_ROOT=""
for _src_root in "$REPO_ROOT/tests/apps/vanillas" "$REPO_ROOT/tests/ecp/vanillas" "$REPO_ROOT/tests/examples/original"; do
  if [ -d "$_src_root/$APP_NAME" ]; then
    echo "[REFRESH] Re-copying $APP_NAME source (clean)"
    # Defensive: a prior run from before the 2026-05-22 editing-scope
    # policy may have left read-only chmod bits on subprojects/_deps.
    # Restore write so rm -rf can clean them up.  Harmless when no
    # locks exist.
    if [ -d "$APP_DIR" ]; then
      chmod -R u+w "$APP_DIR" 2>/dev/null || true
    fi
    rm -rf "$APP_DIR"
    # Ensure parent (build/tests_baseline/ or build/tests/) exists.  Bare
    # `cp` does not create missing parents and earlier overnight cleanup
    # may have removed the parent dir entirely.
    mkdir -p "$(dirname "$APP_DIR")"
    cp -a "$_src_root/$APP_NAME" "$APP_DIR"
    VANILLA_SRC_ROOT="$_src_root"
    break
  fi
done

# Editing-scope policy (2026-05-22, supersedes F-15 vendored lock):
# The LLM is allowed to modify ANY file inside the per-app codebase tree
# ($APP_DIR and everything below it), including embedded/vendored libraries
# (subprojects/, source/<library>/, _deps/, extern/, third_party/). This
# is necessary so the LLM can identify and expose private framework state
# that the application alone cannot reach (e.g. SAMRAI AMR sequencing
# state private to TimeRefinementIntegrator). Shared system libraries
# (MPI install, VeloC install, glibc, compiler runtimes) live OUTSIDE
# $APP_DIR and are off-limits — opencode has no write access to those
# paths anyway. The prompt's HIGHEST-PRIORITY RULE (ANTI_GAMING_DIRECTIVE
# below) communicates this scope to the LLM. Gaming patterns C'/D'/E'
# remain behaviorally forbidden regardless of where the code lives, and
# are caught by the v2.2 recovery_resumed gates + the post-hoc audit.

# Post-validation checkpoint cleanup (2026-05-21, issue: Nyx disk-full from
# multi-GB AMReX chk dirs accumulating across iters).
#
# Run AFTER each iter's validate.py exits.  Removes the BULKY checkpoint
# artefacts this iter wrote, so the next iter starts with a clean
# checkpoint state and the disk does not fill across many iters.
#
# What's removed (bulk only):
#   1. build/validation_output/<APP>_<LABEL>/correctness/resilient*/**/chk* /plt* /restart_*
#      AMReX, Nyx, SAMRAI native checkpoint dirs that the binary wrote during this iter.
#      stdout.txt/stderr.txt and the dir structure are PRESERVED so the next iter's
#      prompt builder (which reads these at lines 367-374) sees the prior iter's logs.
#   2. /tmp/*<app_lower>*{veloc,persistent,scratch,chk,restart,ckpt}*
#      VeloC + native ckpt dirs declared by the LLM's veloc.cfg / written by app to /tmp.
#   3. $APP_DIR/chk* + plt* + restart_* + *.veloc + validation_output.bin
#      In-tree ckpts AMReX or Nyx-style write to cwd of the binary inside tests_baseline tree.
#
# What's preserved:
#   - $APP_DIR/_build/                                       build artefacts (fast rebuild)
#   - $APP_DIR/<source files>                                LLM's accumulated source mods
#   - build/baseline_cache/<APP>/                            cross-experiment baseline (paper)
#   - build/validation_output/<APP>_<LABEL>/benchmarks/      bench data (paper)
#   - correctness/resilient*/{stdout,stderr}.txt             needed by next iter's prompt
#   - correctness/resilient*/attempt_*/                       dir scaffolding (logs inside)
#
# Cleanup is best-effort: any rm failure is silenced (|| true) so a stuck
# inotify handle or stale lock cannot abort the iter loop.
_clean_iter_checkpoints() {
  local app_dir="$1"
  local app_name="$2"
  local label="$3"
  local app_lower
  app_lower=$(echo "$app_name" | tr '[:upper:]' '[:lower:]')

  # (1) Bulky ckpt dirs INSIDE correctness/resilient*/ — preserves stdout.txt/stderr.txt
  # that the next iter's prompt builder reads, only removes the multi-GB ckpt payload.
  local correctness_dir="$BUILD_DIR/validation_output/${app_name}_${label}/correctness"
  if [ -d "$correctness_dir" ]; then
    local bytes_before bytes_after
    bytes_before=$(du -sb "$correctness_dir" 2>/dev/null | awk '{print $1}')
    # AMReX/Nyx: chk?????? and plt?????? (6-digit pad).  SAMRAI: restore.* + chkpt.*
    # Generic VeloC: *.veloc.  These are the typical multi-MB-to-multi-GB writes.
    find "$correctness_dir" \
      \( -type d \( -name 'chk??????' -o -name 'plt??????' -o -name 'restart_*' -o -name 'chkpt*' -o -name 'restore.*' \) \
         -o -type f \( -name '*.veloc' -o -name 'validation_output.bin' -o -name '*.chk' -o -name '*.h5' -o -name '*.hdf5' -o -name 'restart.*' \) \) \
      -prune -exec rm -rf {} + 2>/dev/null || true
    bytes_after=$(du -sb "$correctness_dir" 2>/dev/null | awk '{print $1}')
    if [ -n "$bytes_before" ] && [ -n "$bytes_after" ] && [ "$bytes_before" != "$bytes_after" ]; then
      echo "[ckpt-clean] correctness/: $(numfmt --to=iec "$bytes_before" 2>/dev/null || echo "${bytes_before}B") -> $(numfmt --to=iec "$bytes_after" 2>/dev/null || echo "${bytes_after}B")"
    fi
  fi

  # (2) /tmp dirs — match app-name-lower or veloc-cfg-declared paths.
  # Conservative: only match dirs whose name CONTAINS app_lower AND looks ckpt-like.
  local tmp_removed=""
  for d in /tmp/*"${app_lower}"* /tmp/"${app_lower}"_*; do
    [ -d "$d" ] || continue
    case "$(basename "$d")" in
      *veloc*|*persistent*|*scratch*|*chk*|*restart*|*ckpt*|*backup*)
        rm -rf "$d" 2>/dev/null && tmp_removed="$tmp_removed $(basename "$d")"
        ;;
    esac
  done
  [ -n "$tmp_removed" ] && echo "[ckpt-clean] removed /tmp:${tmp_removed}"

  # (3) In-tree ckpt files written by the binary to APP_DIR's cwd.
  # Matches AMReX-style (chk*, plt*), Nyx-style (restart*), generic (*.veloc).
  # Restricted to top-level APP_DIR (maxdepth 1) to avoid nuking source files
  # named similarly inside src/ or subprojects/.
  if [ -d "$app_dir" ]; then
    local intree_removed=""
    for f in "$app_dir"/chk?????? "$app_dir"/plt?????? "$app_dir"/restart_* "$app_dir"/*.veloc "$app_dir"/validation_output.bin; do
      [ -e "$f" ] || continue
      rm -rf "$f" 2>/dev/null && intree_removed="$intree_removed $(basename "$f")"
    done
    [ -n "$intree_removed" ] && echo "[ckpt-clean] removed in-tree:${intree_removed}"
  fi
}

if [ ! -d "$APP_DIR" ]; then
  echo "ERROR: App directory not found: $APP_DIR" >&2
  exit 1
fi

PROMPT_FILE="$APP_DIR/prompt.txt"
if [ ! -f "$PROMPT_FILE" ]; then
  echo "ERROR: No prompt.txt found in $APP_DIR" >&2
  exit 1
fi

INITIAL_PROMPT="$(cat "$PROMPT_FILE")"

# Highest-priority anti-gaming directive prepended to every iter prompt
# (iter 1 and iter 2+).  Goal: frame the LLM's task as "implement honest
# checkpoint/restart", NOT "make the validator say PASS".  The validator
# catches gaming after the fact, but only after consuming compute and
# tokens producing a gamed solution; this directive aims to prevent
# gaming from being attempted in the first place.  Single-quoted so
# bash performs no interpolation on the text.
ANTI_GAMING_DIRECTIVE='================================================================================
TASK
================================================================================
This application has no checkpoint/restart support. Add one, using the
VeloC runtime library (libveloc) for persistence.

================================================================================
YOU MAY
================================================================================
- Modify any file inside this codebase directory tree (the current
  working directory and everything under it).
- Call into libveloc.
- Use read, list, glob, grep, edit, write tools directly.
- Read (read-only) any file under this external directory — it holds
  the previous attempt(s) validator output and your build logs, and you
  MUST consult it to understand exactly how/why the previous attempt
  was rejected before you start editing code:
    * /home/ndhai/diaspora/guard-agent/build/iterative_logs/
      (per-iter prompt.txt, build_output.txt, opencode_stdout.txt,
       validate_stdout.txt, validate_stderr.txt, metrics.json — the
       validator stderr at the previous iter dir contains the exact
       gate / fatal that rejected the previous attempt; read it first.)

================================================================================
YOU MAY NOT
================================================================================
- Modify any file outside this codebase directory tree.
- Delegate work to sub-agents.
- Take any action whose purpose is to make a validator gate pass
  without performing real state capture on checkpoint and real state
  load on restart.

================================================================================
REQUIRED RUNTIME CONFIG FILE (infrastructure, not the resilience task)
================================================================================
The VeloC runtime needs a `veloc.cfg` text file in the SOURCE TREE ROOT
(your current working directory) BEFORE the binary is launched.  The
validator parses this file BEFORE invoking mpirun to know which
directories to poll for checkpoint files.  If the file is absent, or
its scratch/persistent values are NOT absolute filesystem paths, the
validator immediately FATALs with "No VeloC checkpoint directories
resolved from veloc.cfg" and you get zero credit for the iteration.

Create it as a STATIC FILE in the tree at iteration start.  DO NOT
generate it at runtime from inside the binary (e.g. via a
`writeVelocConfig()` function called from main() before VELOC_Init):
that approach cannot pass this validator because the cfg is parsed
before mpirun launches the binary.

Concrete requirements:
  Path:          ./veloc.cfg   (in your current working directory)
  Required keys: scratch, persistent, mode
  Path rule:     scratch and persistent MUST be absolute /tmp paths
                 and MUST differ from each other.

Working example (substitute <app> with a short lowercase identifier;
the exact subdirectory names are unconstrained as long as the two
absolute paths differ):

  scratch = /tmp/<app>_veloc_scratch
  persistent = /tmp/<app>_veloc_persistent
  mode = sync

This is plumbing, not part of the resilience challenge.  Get it in
place on iteration 1 and spend your iteration budget on actual
checkpoint state capture and recovery logic instead.
================================================================================'

LOG_DIR="$BUILD_DIR/iterative_logs/${APP_NAME}_${LABEL}"
mkdir -p "$LOG_DIR"

echo "════════════════════════════════════════════════════════════════════"
echo "  Iterative evaluation: $APP_NAME ($LABEL)"
echo "════════════════════════════════════════════════════════════════════"
echo "  App directory: $APP_DIR"
echo "  Max iterations: $MAX_ITERS"
echo "  Logs: $LOG_DIR"
echo ""

# --- D3 retry-loop config (2026-05-03) ---
# When OpenCode hangs (stall-killed) OR the iter loop runs out of MAX_ITERS
# without converging, we wipe build/tests_baseline/<APP>/, re-copy fresh
# vanilla, and restart the iter loop from iter 1.  This avoids retrying on
# top of partially-modified (potentially broken) code from the failed
# attempt.  Per-iter history is wiped per loop attempt; aggregate summary
# of failed attempts is preserved in PRIOR_LOOP_ATTEMPTS for reporting.
OPENCODE_RETRIES="${OPENCODE_RETRIES:-2}"
MAX_LOOP_ATTEMPTS=$((1 + OPENCODE_RETRIES))
PRIOR_LOOP_ATTEMPTS=""  # JSON array entries for failed prior attempts
LOOP_STALL_COUNT=0
LOOP_MAX_ITERS_COUNT=0

# Outer wallclock start measured ONCE — covers all loop attempts.
EVAL_START=$(date +%s.%N)

LOOP_ATTEMPT=1
while [ "$LOOP_ATTEMPT" -le "$MAX_LOOP_ATTEMPTS" ]; do
  echo ""
  echo "════════════════════════════════════════════════════════════════════"
  echo "  Loop attempt $LOOP_ATTEMPT / $MAX_LOOP_ATTEMPTS"
  echo "════════════════════════════════════════════════════════════════════"

  # On retry attempts (>1), wipe the modified source and re-copy vanilla.
  # First attempt already used the fresh copy from the [REFRESH] step above.
  if [ "$LOOP_ATTEMPT" -gt 1 ]; then
    if [ -z "$VANILLA_SRC_ROOT" ]; then
      echo "ERROR: VANILLA_SRC_ROOT not set; cannot re-copy for retry" >&2
      exit 3
    fi
    echo "[REFRESH] Re-copying $APP_NAME source (clean) for loop attempt $LOOP_ATTEMPT"
    rm -rf "$APP_DIR"
    mkdir -p "$(dirname "$APP_DIR")"
    cp -a "$VANILLA_SRC_ROOT/$APP_NAME" "$APP_DIR"
  fi

  # --- Per-attempt metrics accumulators (Q1: wiped each retry) ---
  TOTAL_ELAPSED="0.0"
  TOTAL_OPENCODE_ELAPSED="0.0"
  TOTAL_VALIDATION_ELAPSED="0.0"
  TOTAL_INPUT_TOKENS=0
  TOTAL_OUTPUT_TOKENS=0
  TOTAL_TOKENS=0
  ITER_METRICS=""  # will be built as JSON array entries
  LOOP_OUTCOME=""  # set to "stall" or "max_iters" if the iter loop exits abnormally
  STALL_ITERATION=0
  LAST_ITER=0

  # --- Iteration loop ---
  for ITER in $(seq 1 "$MAX_ITERS"); do
    LAST_ITER=$ITER
  echo ""
  echo "╔══════════════════════════════════════════════════════════════════╗"
  echo "║  Iteration $ITER / $MAX_ITERS"
  echo "╚══════════════════════════════════════════════════════════════════╝"
  echo ""

  ITER_LOG="$LOG_DIR/iter_${ITER}"
  mkdir -p "$ITER_LOG"

  # --- Step 1: Build the prompt ---
  if [ "$ITER" -eq 1 ]; then
    PROMPT="${ANTI_GAMING_DIRECTIVE}

${INITIAL_PROMPT}"
  else
    # Feed back the validation error from the previous iteration.
    # The fallback prompt deliberately ships only the raw artefacts (the
    # validator output and the build output) plus the failure-analysis
    # discipline from the original prompt.txt.  We do NOT include a checklist
    # of what to do (initialise X, register Y, finalise Z, link library W) —
    # the whole point of the experiment is to measure whether the agent can
    # diagnose its own failure and decide for itself what to change.  Listing
    # API steps here would short-circuit that judgment and contaminate every
    # iteration past the first.  See ISSUES.md issue #18.
    PREV_LOG="$LOG_DIR/iter_$((ITER - 1))"
    PROMPT="${ANTI_GAMING_DIRECTIVE}

Your previous attempt was rejected by the validation pipeline. Inspect
the artifacts under this directory and fix the code:

  $PREV_LOG

It contains validate_stderr.txt (the exact gate / fatal that rejected
the previous attempt — read it first), validate_stdout.txt,
build_output.txt, opencode_stdout.txt, and metrics.json."
  fi

  # --- Optional context-cap (Deliverable 2, cell B1 enabler) ---
  # OPENCODE_INPUT_TRUNC_TOKENS env var: cap the prompt at roughly N
  # tokens (chars/4 approx) by dropping oldest stdout/stderr lines first
  # and then whole least-informative sections.  ANTI_GAMING_DIRECTIVE
  # is NEVER trimmed.  Used by cell B1 to simulate a 128K-context Opus
  # 4.7 run against the existing 1M baseline.  When unset, behavior is
  # unchanged.
  if [ -n "${OPENCODE_INPUT_TRUNC_TOKENS:-}" ]; then
    _TRUNC_META="$ITER_LOG/prompt_truncation.json"
    PROMPT_CAPPED=$(printf '%s\n' "$PROMPT" | \
        OPENCODE_INPUT_TRUNC_TOKENS="$OPENCODE_INPUT_TRUNC_TOKENS" \
        python3 -m validation.veloc.prompt_truncator 2>"$_TRUNC_META")
    PROMPT="$PROMPT_CAPPED"
    # Surface a one-line summary so the iter log shows what the cap did.
    echo "[iter $ITER] context cap: $(cat "$_TRUNC_META" 2>/dev/null)"
  fi

  # Save the prompt for debugging
  printf '%s\n' "$PROMPT" > "$ITER_LOG/prompt.txt"

  # --- Step 2: Run OpenCode (timed) ---
  echo "[iter $ITER] Running OpenCode ($LABEL)..."
  OPENCODE_START=$(date +%s.%N)
  OPENCODE_START_MS=$(date +%s%3N)
  cd "$APP_DIR"

  # Two-tier safety: stall watcher + hard cap.
  #
  # Hard cap (OPENCODE_TIMEOUT, default 3600s/1h): absolute wallclock kill,
  # safety net in case the watcher itself fails.  Productive iters typically
  # finish in 5–30 min; complex iter-1 explorations (multi-MB context,
  # 40+ tool calls) can exceed 30 min.  The 1h cap is generous enough that
  # only a truly runaway session hits it.
  #
  # Stall watcher (OPENCODE_STALL_CHECK / OPENCODE_STALL_KILL):
  #   - Every OPENCODE_STALL_CHECK seconds (default 600s/10min), check whether
  #     opencode_stdout.txt has grown since last check.
  #   - If no growth → set a "stalled" flag with the current timestamp.
  #   - On subsequent checks: if growth resumes, clear the flag.  If no growth
  #     and the flag has been set for ≥ OPENCODE_STALL_KILL seconds (default
  #     1200s/20min), kill opencode, mark .opencode_stalled, and break out of
  #     the per-app iter loop (move to next app; record investigation entry).
  #   - Worst case: ~30 min of zero stdout activity before kill.
  #   - Productive runs are unaffected — any stdout write resets the flag.
  OPENCODE_TIMEOUT="${OPENCODE_TIMEOUT:-3600}"
  OPENCODE_STALL_CHECK="${OPENCODE_STALL_CHECK:-600}"
  OPENCODE_STALL_KILL="${OPENCODE_STALL_KILL:-1200}"
  # --dangerously-skip-permissions is paired with a strict deny-list in
  # ~/.config/opencode/opencode.json's "permission" block:
  #   - edit/write/patch: ALLOW only under build/tests_baseline/** and
  #     build/tests/**; DENY everywhere else
  #   - bash: DENY (the iterative loop runs all builds externally)
  #   - webfetch/websearch/external_directory: DENY
  # With those denies in place, --dangerously-skip-permissions only auto-
  # approves the *safe* operations (read/list/grep/glob anywhere, edits
  # within the per-app codebase) and explicit denies still apply.
  #
  # Model selection: OPENCODE_MODEL env var (default: argo/claudeopus47).
  # Available models from opencode.json (Argo dev gateway):
  #   argo/claudeopus47    Claude Opus 4.7 (default — highest-quality Anthropic)
  #   argo/claudeopus46    Claude Opus 4.6
  #   argo/claudesonnet46  Claude Sonnet 4.6   (3-D cell A1)
  #   argo/claudehaiku45   Claude Haiku 4.5    (3-D cell A2)
  #   argo/gpt55           GPT-5.5             (3-D cell C1)
  #   argo/gpt54           GPT-5.4
  #   argo/gemini25pro     Gemini 2.5 Pro      (3-D cell C2)
  # The wrapper run_iterative_for_model.sh sets OPENCODE_MODEL + MODEL_TAG
  # together to drive sharded multi-cell runs.
  OPENCODE_MODEL="${OPENCODE_MODEL:-argo/claudeopus47}"
  echo "[iter $ITER] OpenCode model: $OPENCODE_MODEL"
  echo "[iter $ITER] Hard cap: ${OPENCODE_TIMEOUT}s.  Stall watch: check every ${OPENCODE_STALL_CHECK}s, kill if stalled ≥${OPENCODE_STALL_KILL}s after flag."

  STALL_LOG="$ITER_LOG/stall_watch.log"
  : > "$STALL_LOG"
  rm -f "$ITER_LOG/.opencode_stalled"

  # Hide the upstream reference checkpointed source from the LLM during
  # this OpenCode invocation.  Otherwise the LLM may grep / read
  # tests/apps/checkpointed/<APP>/ for the upstream's RestartManager-
  # based resilience code and transcribe it into the LLM-modified
  # vanilla — which is gaming (the experiment tests whether the LLM
  # can DESIGN VeloC-based resilience independently, not whether it
  # can copy the upstream's HDF5-based one).  The validator's
  # subsequent Validation A step still needs the reference at the
  # original path, so we restore it after OpenCode exits.
  REF_DIR="$REPO_ROOT/tests/apps/checkpointed/$APP_NAME"
  REF_HIDDEN_DIR="$REPO_ROOT/tests/apps/.hidden_checkpointed_${APP_NAME}_$$"
  REF_HIDDEN_BY_THIS_ITER=0
  if [ -d "$REF_DIR" ]; then
    if mv "$REF_DIR" "$REF_HIDDEN_DIR" 2>/dev/null; then
      REF_HIDDEN_BY_THIS_ITER=1
      echo "[iter $ITER] hid reference dir ($REF_DIR → $REF_HIDDEN_DIR)"
    else
      echo "[iter $ITER] WARN: failed to hide reference dir $REF_DIR — LLM may read it"
    fi
  fi
  # Restore on any exit (normal, error, signal).  Use a unique trap
  # name so we don't clobber the script-level _batch_cleanup trap.
  _restore_ref_dir() {
    if [ "$REF_HIDDEN_BY_THIS_ITER" = 1 ] && [ -d "$REF_HIDDEN_DIR" ]; then
      mv "$REF_HIDDEN_DIR" "$REF_DIR" 2>/dev/null && \
        echo "[iter $ITER] restored reference dir ($REF_HIDDEN_DIR → $REF_DIR)"
    fi
  }
  trap _restore_ref_dir EXIT INT TERM

  # Launch opencode in the background under the hard wallclock cap.
  timeout --kill-after=10 "$OPENCODE_TIMEOUT" \
    opencode run --dangerously-skip-permissions --model "$OPENCODE_MODEL" "$PROMPT" \
    > "$ITER_LOG/opencode_stdout.txt" 2> "$ITER_LOG/opencode_stderr.txt" &
  OPENCODE_PID=$!

  # Stall watcher: side-by-side, monitors stdout growth.
  (
    STALL_FLAG_TIME=0
    LAST_SIZE=0
    while sleep "$OPENCODE_STALL_CHECK"; do
      kill -0 "$OPENCODE_PID" 2>/dev/null || exit 0
      CUR_SIZE=$(stat -c %s "$ITER_LOG/opencode_stdout.txt" 2>/dev/null || echo 0)
      NOW=$(date +%s)
      if [ "$CUR_SIZE" -ne "$LAST_SIZE" ]; then
        if [ "$STALL_FLAG_TIME" -ne 0 ]; then
          echo "[$(date -u +%H:%M:%SZ)] [stall-watch] progress resumed at ${CUR_SIZE} bytes — clearing flag" >> "$STALL_LOG"
        fi
        LAST_SIZE=$CUR_SIZE
        STALL_FLAG_TIME=0
      else
        if [ "$STALL_FLAG_TIME" -eq 0 ]; then
          STALL_FLAG_TIME=$NOW
          echo "[$(date -u +%H:%M:%SZ)] [stall-watch] no stdout growth in last ${OPENCODE_STALL_CHECK}s (size=${CUR_SIZE}) — flagged" >> "$STALL_LOG"
        else
          AGE=$(( NOW - STALL_FLAG_TIME ))
          if [ "$AGE" -ge "$OPENCODE_STALL_KILL" ]; then
            echo "[$(date -u +%H:%M:%SZ)] [stall-watch] stalled ${AGE}s after flag (≥${OPENCODE_STALL_KILL}s) — killing pid $OPENCODE_PID" >> "$STALL_LOG"
            touch "$ITER_LOG/.opencode_stalled"
            # Kill the timeout process; descendants (opencode + helpers) cascade via SIGTERM/SIGKILL.
            kill -TERM "$OPENCODE_PID" 2>/dev/null
            sleep 5
            kill -KILL "$OPENCODE_PID" 2>/dev/null
            pkill -KILL -P "$OPENCODE_PID" 2>/dev/null
            exit 0
          fi
        fi
      fi
    done
  ) &
  STALL_WATCHER_PID=$!

  # Wait for opencode (timeout-wrapped) to exit, then stop the watcher.
  # CRITICAL: `|| true` is REQUIRED because `set -e` is active and `wait`
  # returns non-zero when the awaited process was signal-killed (e.g.
  # SIGTERM/SIGKILL from the stall watcher).  Without `|| true`, the
  # script would exit here before reaching the .opencode_stalled check
  # and the D3 retry-loop logic, which is what crashed the
  # 2026-05-03 cleanup_v2 chain on HyPar iter.
  wait "$OPENCODE_PID" 2>/dev/null || true
  OC_RC=$?
  kill -TERM "$STALL_WATCHER_PID" 2>/dev/null || true
  wait "$STALL_WATCHER_PID" 2>/dev/null || true
  # Restore the reference dir before validate.py runs (it needs the
  # path for Validation A).  Idempotent with the EXIT trap.
  _restore_ref_dir
  trap - EXIT INT TERM

  STALL_ABORTED=0
  if [ -f "$ITER_LOG/.opencode_stalled" ]; then
    STALL_ABORTED=1
    echo "[iter $ITER] OpenCode killed by stall watcher (no stdout growth ≥${OPENCODE_STALL_KILL}s after flag)" \
      | tee -a "$ITER_LOG/opencode_stderr.txt"
    # Append to the global investigation log (acts as the "todo to investigate").
    mkdir -p "$REPO_ROOT/build/run_logs"
    printf "%s\tapp=%s\titer=%s\treason=stalled\tlog=%s\n" \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$APP_NAME" "$ITER" "$ITER_LOG" \
      >> "$REPO_ROOT/build/run_logs/_stall_investigations.log"
  elif [ "$OC_RC" = 124 ] || [ "$OC_RC" = 137 ]; then
    echo "[iter $ITER] OpenCode hit ${OPENCODE_TIMEOUT}s hard cap — treating as iteration failure" \
      | tee -a "$ITER_LOG/opencode_stderr.txt"
  fi

  cd "$REPO_ROOT"
  OPENCODE_END=$(date +%s.%N)
  # awk emits a leading 0 for fractions (unlike bc which would write
  # ".865" instead of "0.865" — invalid JSON when interpolated below).
  OPENCODE_ELAPSED=$(awk "BEGIN { printf \"%.9f\", $OPENCODE_END - $OPENCODE_START }" 2>/dev/null || echo "0")
  TOTAL_OPENCODE_ELAPSED=$(awk "BEGIN { printf \"%.9f\", $TOTAL_OPENCODE_ELAPSED + $OPENCODE_ELAPSED }" 2>/dev/null || echo "0")
  echo "[iter $ITER] OpenCode finished in ${OPENCODE_ELAPSED}s"

  # --- Per-iter inspection: pull tool-call breakdown + file-change stats ---
  # Writes inspection.json + inspection.md into the iter dir so a later
  # human / agent can quickly see WHAT OpenCode did this iteration without
  # re-querying the SQLite DB.  Best-effort — failures here do not affect
  # the iterative loop.
  python3 -m validation.veloc.scripts.inspect_iter "$ITER_LOG" --write \
    >> "$ITER_LOG/inspection.run.log" 2>&1 || true

  # --- Extract token usage from OpenCode's SQLite DB ---
  OPENCODE_DB="$HOME/.local/share/opencode/opencode.db"
  ITER_INPUT_TOKENS=0
  ITER_OUTPUT_TOKENS=0
  ITER_TOTAL_TOKENS=0
  if [ -f "$OPENCODE_DB" ]; then
    TOKENS_JSON=$(python3 -c "
import sqlite3, json, sys
try:
    db = sqlite3.connect('$OPENCODE_DB')
    c = db.cursor()
    c.execute('''
        SELECT m.session_id,
               COALESCE(SUM(json_extract(m.data, \"$.tokens.input\")), 0),
               COALESCE(SUM(json_extract(m.data, \"$.tokens.output\")), 0),
               COALESCE(SUM(json_extract(m.data, \"$.tokens.total\")), 0)
        FROM message m
        JOIN session s ON m.session_id = s.id
        WHERE s.directory = '$APP_DIR'
          AND json_extract(m.data, \"$.role\") = \"assistant\"
          AND json_extract(m.data, \"$.tokens.total\") IS NOT NULL
          AND s.time_created >= $OPENCODE_START_MS
        GROUP BY m.session_id
        ORDER BY s.time_created DESC
        LIMIT 1
    ''')
    row = c.fetchone()
    db.close()
    if row:
        print(json.dumps({'input': int(row[1]), 'output': int(row[2]), 'total': int(row[3])}))
    else:
        print(json.dumps({'input': 0, 'output': 0, 'total': 0}))
except Exception as e:
    print(json.dumps({'input': 0, 'output': 0, 'total': 0, 'error': str(e)}), file=sys.stderr)
    print(json.dumps({'input': 0, 'output': 0, 'total': 0}))
" 2>/dev/null)
    ITER_INPUT_TOKENS=$(echo "$TOKENS_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('input',0))" 2>/dev/null || echo "0")
    ITER_OUTPUT_TOKENS=$(echo "$TOKENS_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('output',0))" 2>/dev/null || echo "0")
    ITER_TOTAL_TOKENS=$(echo "$TOKENS_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo "0")
    echo "[iter $ITER] Tokens: input=$ITER_INPUT_TOKENS output=$ITER_OUTPUT_TOKENS total=$ITER_TOTAL_TOKENS"
  fi

  # --- Stall: record this iter as stall_aborted, break loop for D3 retry. ---
  # When the watcher killed opencode for inactivity, validating now would
  # waste 5–15 min on stale source.  D3 retry-loop semantics: abandon this
  # loop attempt, record outcome, let the outer while decide to retry from
  # a fresh vanilla copy or give up after MAX_LOOP_ATTEMPTS.
  if [ "$STALL_ABORTED" = 1 ]; then
    ITER_ELAPSED="$OPENCODE_ELAPSED"
    TOTAL_ELAPSED=$(awk "BEGIN { printf \"%.9f\", $TOTAL_ELAPSED + $ITER_ELAPSED }" 2>/dev/null || echo "0")
    TOTAL_INPUT_TOKENS=$((TOTAL_INPUT_TOKENS + ITER_INPUT_TOKENS))
    TOTAL_OUTPUT_TOKENS=$((TOTAL_OUTPUT_TOKENS + ITER_OUTPUT_TOKENS))
    TOTAL_TOKENS=$((TOTAL_TOKENS + ITER_TOTAL_TOKENS))
    cat > "$ITER_LOG/metrics.json" << EOFMETRICS
{
  "iter": $ITER,
  "opencode_elapsed_s": $OPENCODE_ELAPSED,
  "validation_elapsed_s": 0,
  "total_elapsed_s": $ITER_ELAPSED,
  "validation_passed": false,
  "stall_aborted": true,
  "input_tokens": $ITER_INPUT_TOKENS,
  "output_tokens": $ITER_OUTPUT_TOKENS,
  "total_tokens": $ITER_TOTAL_TOKENS
}
EOFMETRICS
    [ -n "$ITER_METRICS" ] && ITER_METRICS="${ITER_METRICS},"
    ITER_METRICS="${ITER_METRICS}
    {\"iter\": $ITER, \"opencode_elapsed_s\": $OPENCODE_ELAPSED, \"validation_elapsed_s\": 0, \"total_elapsed_s\": $ITER_ELAPSED, \"validation_passed\": false, \"stall_aborted\": true, \"input_tokens\": $ITER_INPUT_TOKENS, \"output_tokens\": $ITER_OUTPUT_TOKENS, \"total_tokens\": $ITER_TOTAL_TOKENS}"
    LOOP_OUTCOME="stall"
    STALL_ITERATION=$ITER
    LAST_ITER=$ITER
    echo ""
    echo "[loop attempt $LOOP_ATTEMPT/$MAX_LOOP_ATTEMPTS] STALL at iter $ITER — breaking iter loop"
    break  # Break out of for-iter; outer while decides retry vs final-fail
  fi

  # --- Step 3: Run correctness validation (timed) ---
  echo "[iter $ITER] Running correctness validation..."
  VALIDATE_START=$(date +%s.%N)

  # Build extra flags for validate.sh
  EXTRA_VALIDATE_FLAGS=""
  [ -n "$INJECTION_DELAY" ] && EXTRA_VALIDATE_FLAGS="$EXTRA_VALIDATE_FLAGS --injection-delay $INJECTION_DELAY"
  [ -n "$GROUND_TRUTH_DIR" ] && EXTRA_VALIDATE_FLAGS="$EXTRA_VALIDATE_FLAGS --ground-truth-dir $GROUND_TRUTH_DIR"

  set +e
  # --label routes the validation output cell to validation_output/<APP>_<LABEL>/
  # instead of always landing in <APP>_baseline/.  When LABEL is the default
  # "baseline${_TAG_PATH_SUFFIX}" with no MODEL_TAG, behavior is unchanged.
  "$SCRIPT_DIR/run_validate.sh" $VALIDATE_FLAG "$APP_NAME" \
    --label "$LABEL" \
    --skip-benchmarks --skip-report \
    $EXTRA_VALIDATE_FLAGS \
    > "$ITER_LOG/validate_stdout.txt" 2> "$ITER_LOG/validate_stderr.txt"
  VALIDATE_EXIT=$?
  set -e

  VALIDATE_END=$(date +%s.%N)
  # awk preserves leading zero for fractions; bc would strip it (".865"
  # → invalid JSON).  Same fix applied to OPENCODE_ELAPSED + ITER_ELAPSED
  # + TOTAL_ELAPSED below for consistency across all four float fields.
  VALIDATE_ELAPSED=$(awk "BEGIN { printf \"%.9f\", $VALIDATE_END - $VALIDATE_START }" 2>/dev/null || echo "0")
  TOTAL_VALIDATION_ELAPSED=$(awk "BEGIN { printf \"%.9f\", $TOTAL_VALIDATION_ELAPSED + $VALIDATE_ELAPSED }" 2>/dev/null || echo "0")
  ITER_ELAPSED=$(awk "BEGIN { printf \"%.9f\", $OPENCODE_ELAPSED + $VALIDATE_ELAPSED }" 2>/dev/null || echo "0")
  TOTAL_ELAPSED=$(awk "BEGIN { printf \"%.9f\", $TOTAL_ELAPSED + $ITER_ELAPSED }" 2>/dev/null || echo "0")

  # Post-validation checkpoint cleanup: remove this iter's ckpt artefacts
  # (correctness/resilient*/ + /tmp/<app>* + in-tree chk*/plt*/restart*) so
  # the next iter starts with a clean checkpoint state.  Preserves _build/
  # (no rebuild penalty), source files (LLM's accumulated changes), and the
  # sibling benchmarks/ tree (paper-grade data).
  _clean_iter_checkpoints "$APP_DIR" "$APP_NAME" "$LABEL" || true

  # Extract build output for feedback (if build failed)
  grep -A 20 "Build failed\|CMake Error\|make.*Error\|error:" \
    "$ITER_LOG/validate_stdout.txt" "$ITER_LOG/validate_stderr.txt" \
    > "$ITER_LOG/build_output.txt" 2>/dev/null || true

  # Record per-iteration metrics
  ITER_PASSED="false"
  [ "$VALIDATE_EXIT" -eq 0 ] && ITER_PASSED="true"

  # Accumulate token counts
  TOTAL_INPUT_TOKENS=$((TOTAL_INPUT_TOKENS + ITER_INPUT_TOKENS))
  TOTAL_OUTPUT_TOKENS=$((TOTAL_OUTPUT_TOKENS + ITER_OUTPUT_TOKENS))
  TOTAL_TOKENS=$((TOTAL_TOKENS + ITER_TOTAL_TOKENS))

  # Save per-iteration metrics
  cat > "$ITER_LOG/metrics.json" << EOFMETRICS
{
  "iter": $ITER,
  "opencode_elapsed_s": $OPENCODE_ELAPSED,
  "validation_elapsed_s": $VALIDATE_ELAPSED,
  "total_elapsed_s": $ITER_ELAPSED,
  "validation_passed": $ITER_PASSED,
  "input_tokens": $ITER_INPUT_TOKENS,
  "output_tokens": $ITER_OUTPUT_TOKENS,
  "total_tokens": $ITER_TOTAL_TOKENS
}
EOFMETRICS

  # Append to JSON array string
  [ -n "$ITER_METRICS" ] && ITER_METRICS="${ITER_METRICS},"
  ITER_METRICS="${ITER_METRICS}
    {\"iter\": $ITER, \"opencode_elapsed_s\": $OPENCODE_ELAPSED, \"validation_elapsed_s\": $VALIDATE_ELAPSED, \"total_elapsed_s\": $ITER_ELAPSED, \"validation_passed\": $ITER_PASSED, \"input_tokens\": $ITER_INPUT_TOKENS, \"output_tokens\": $ITER_OUTPUT_TOKENS, \"total_tokens\": $ITER_TOTAL_TOKENS}"

  # --- Step 4: Check result ---
  if [ "$VALIDATE_EXIT" -eq 0 ]; then
    EVAL_END=$(date +%s.%N)
    WALL_ELAPSED=$(awk "BEGIN { printf \"%.9f\", $EVAL_END - $EVAL_START }" 2>/dev/null || echo "0")

    echo ""
    echo "════════════════════════════════════════════════════════════════════"
    echo "  PASS — Correctness validation passed on iteration $ITER"
    echo "  Total OpenCode+validation time: ${TOTAL_ELAPSED}s"
    echo "  Wall-clock time: ${WALL_ELAPSED}s"
    echo "  Total tokens: ${TOTAL_TOKENS} (input: ${TOTAL_INPUT_TOKENS}, output: ${TOTAL_OUTPUT_TOKENS})"
    echo "════════════════════════════════════════════════════════════════════"

    # CRIT-3 / F-* result.json provenance: _passed_via records WHERE the
    # top-level `passed` verdict came from.  "iter_loop" = normal exit
    # path (VALIDATE_EXIT==0 in the iter loop above).  Any later manual
    # reconstruction that needs to flip `passed` to true via an external
    # validate.py run MUST set _passed_via to "external_validate" or
    # "manual_reconstruction" instead, so downstream consumers can decide
    # whether to trust the verdict.  Schema version bumped in lockstep.
    cat > "$LOG_DIR/result.json" << EOFRESULT
{
  "app_name": "$APP_NAME",
  "mode": "$LABEL",
  "schema_version": 2,
  "passed": true,
  "_passed_via": "iter_loop",
  "iterations": $ITER,
  "max_iters": $MAX_ITERS,
  "total_elapsed_s": $TOTAL_ELAPSED,
  "wall_elapsed_s": $WALL_ELAPSED,
  "total_opencode_elapsed_s": $TOTAL_OPENCODE_ELAPSED,
  "total_validation_elapsed_s": $TOTAL_VALIDATION_ELAPSED,
  "total_input_tokens": $TOTAL_INPUT_TOKENS,
  "total_output_tokens": $TOTAL_OUTPUT_TOKENS,
  "total_tokens": $TOTAL_TOKENS,
  "per_iteration": [$ITER_METRICS
  ],
  "loop_attempt_final": $LOOP_ATTEMPT,
  "loop_attempts_total": $LOOP_ATTEMPT,
  "loop_stall_count": $LOOP_STALL_COUNT,
  "loop_max_iters_count": $LOOP_MAX_ITERS_COUNT,
  "prior_loop_attempts": [$PRIOR_LOOP_ATTEMPTS
  ]
}
EOFRESULT
    exit 0
  else
    echo "[iter $ITER] FAIL — Validation failed (${ITER_ELAPSED}s). $([ "$ITER" -lt "$MAX_ITERS" ] && echo "Retrying..." || echo "Max iterations reached.")"
    grep -E "FATAL|FAIL|Error|error:" "$ITER_LOG/validate_stderr.txt" 2>/dev/null | head -5
  fi
  done  # END for ITER

  # --- D3: decide whether this loop attempt's outcome is retry or final ---
  if [ -z "$LOOP_OUTCOME" ]; then
    # for-loop fell through naturally → max iters exhausted without stall
    LOOP_OUTCOME="max_iters"
    LAST_ITER=$MAX_ITERS
  fi

  # Tally outcome counters for the report.
  if [ "$LOOP_OUTCOME" = "stall" ]; then
    LOOP_STALL_COUNT=$((LOOP_STALL_COUNT + 1))
  elif [ "$LOOP_OUTCOME" = "max_iters" ]; then
    LOOP_MAX_ITERS_COUNT=$((LOOP_MAX_ITERS_COUNT + 1))
  fi

  # Append summary of this failed attempt to PRIOR_LOOP_ATTEMPTS JSON.
  [ -n "$PRIOR_LOOP_ATTEMPTS" ] && PRIOR_LOOP_ATTEMPTS="${PRIOR_LOOP_ATTEMPTS},"
  PRIOR_LOOP_ATTEMPTS="${PRIOR_LOOP_ATTEMPTS}
    {\"attempt\": $LOOP_ATTEMPT, \"outcome\": \"$LOOP_OUTCOME\", \"iters_run\": $LAST_ITER, \"stall_iteration\": $STALL_ITERATION, \"total_elapsed_s\": $TOTAL_ELAPSED, \"total_tokens\": $TOTAL_TOKENS, \"total_input_tokens\": $TOTAL_INPUT_TOKENS, \"total_output_tokens\": $TOTAL_OUTPUT_TOKENS}"

  echo ""
  echo "[loop attempt $LOOP_ATTEMPT/$MAX_LOOP_ATTEMPTS] outcome=$LOOP_OUTCOME (iters_run=$LAST_ITER, total_tokens=$TOTAL_TOKENS)"

  # Either retry (re-copy vanilla, restart for-iter) or fall through to
  # the final fail-result writer below.
  if [ "$LOOP_ATTEMPT" -lt "$MAX_LOOP_ATTEMPTS" ]; then
    LOOP_ATTEMPT=$((LOOP_ATTEMPT + 1))
    continue  # outer while → wipe + recopy + restart for-iter
  fi
  break  # budget exhausted → fall through to final fail
done  # END while LOOP_ATTEMPT

# --- All loop attempts exhausted; final fail result ---
EVAL_END=$(date +%s.%N)
WALL_ELAPSED=$(awk "BEGIN { printf \"%.9f\", $EVAL_END - $EVAL_START }" 2>/dev/null || echo "0")

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "  FAIL — Did not pass after $LOOP_ATTEMPT loop attempt(s) (stalls=$LOOP_STALL_COUNT, max_iters=$LOOP_MAX_ITERS_COUNT)"
echo "  Last attempt: $LOOP_OUTCOME at iter $LAST_ITER"
echo "  Wall-clock time: ${WALL_ELAPSED}s (across all attempts)"
echo "  Last attempt tokens: ${TOTAL_TOKENS} (input: ${TOTAL_INPUT_TOKENS}, output: ${TOTAL_OUTPUT_TOKENS})"
echo "════════════════════════════════════════════════════════════════════"
echo "  Logs: $LOG_DIR"

cat > "$LOG_DIR/result.json" << EOFRESULT
{
  "app_name": "$APP_NAME",
  "mode": "$LABEL",
  "schema_version": 2,
  "passed": false,
  "_passed_via": "iter_loop",
  "stall_aborted": $([ "$LOOP_OUTCOME" = "stall" ] && echo "true" || echo "false"),
  "stall_iteration": $STALL_ITERATION,
  "iterations": $LAST_ITER,
  "max_iters": $MAX_ITERS,
  "total_elapsed_s": $TOTAL_ELAPSED,
  "wall_elapsed_s": $WALL_ELAPSED,
  "total_opencode_elapsed_s": $TOTAL_OPENCODE_ELAPSED,
  "total_validation_elapsed_s": $TOTAL_VALIDATION_ELAPSED,
  "total_input_tokens": $TOTAL_INPUT_TOKENS,
  "total_output_tokens": $TOTAL_OUTPUT_TOKENS,
  "total_tokens": $TOTAL_TOKENS,
  "per_iteration": [$ITER_METRICS
  ],
  "loop_attempt_final": $LOOP_ATTEMPT,
  "loop_attempts_total": $LOOP_ATTEMPT,
  "loop_stall_count": $LOOP_STALL_COUNT,
  "loop_max_iters_count": $LOOP_MAX_ITERS_COUNT,
  "prior_loop_attempts": [$PRIOR_LOOP_ATTEMPTS
  ]
}
EOFRESULT
exit $([ "$LOOP_OUTCOME" = "stall" ] && echo "2" || echo "1")
