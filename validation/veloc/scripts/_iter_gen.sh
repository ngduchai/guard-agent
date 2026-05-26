#!/usr/bin/env bash
# _iter_gen.sh — single-iteration LLM code-generation helper for the
# parallel-queue orchestrator (run_parallel_queue.py).
#
# Responsibility: run ONE OpenCode invocation against an already-built
# prompt, with the same stall watcher and reference-dir hiding behavior
# as the serial run_iterative.sh, and write a single metrics file the
# orchestrator can read.
#
# What this script does NOT do (deliberate scope split):
#   - copy vanilla source              → orchestrator handles, once per loop
#   - build the prompt                 → orchestrator handles
#   - call run_validate.sh             → orchestrator dispatches to executor
#   - clean checkpoints                → orchestrator runs after validation
#   - track iter loops / D3 retry      → orchestrator state machine
#
# Args:
#   $1 APP_NAME    application name (e.g. "Nyx") — used for ref-dir hiding,
#                  sqlite session filter, and progress lines
#   $2 ITER        iteration number (1-based) — names iter_$ITER subdir
#   $3 PROMPT_FILE absolute path to the already-built prompt file
#   $4 APP_DIR     absolute path opencode cd's into (per-app codebase tree)
#   $5 LOG_DIR     absolute path of the iter log root (contains iter_N/...)
#   $6 WORKER_SLOT (optional, default 0) integer 0..N-1 identifying this gen
#                  worker.  Each slot gets its own opencode SQLite DB at
#                  /tmp/opencode_worker_<slot>/.local/share/opencode/opencode.db
#                  via per-call XDG_DATA_HOME so concurrent gen workers never
#                  collide on opencode's shared DB ("Error: database is
#                  locked" silent-rc=0 failure observed under W>1 with
#                  default shared $HOME).  Config (~/.config/opencode) and
#                  vendored packages (~/.cache/opencode) remain shared.
#
# Env (all optional, same defaults as run_iterative.sh):
#   OPENCODE_MODEL        default argo/claudeopus47
#   OPENCODE_TIMEOUT      hard wallclock cap in seconds (default 3600)
#   OPENCODE_STALL_CHECK  stall-watch poll interval (default 600)
#   OPENCODE_STALL_KILL   no-growth threshold to kill after flag (default 1200)
#
# Outputs (written to $LOG_DIR/iter_$ITER/):
#   opencode_stdout.txt
#   opencode_stderr.txt
#   stall_watch.log
#   metrics_gen.json     {gen_wall_s, tokens_input/output/total,
#                         stall_aborted, opencode_exit_code, model, started_at}
#   .opencode_stalled    (flag file present iff stall-watcher killed opencode)
#
# Exit codes:
#   0   opencode completed (regardless of validation outcome — caller decides)
#   2   stall-aborted (watcher killed opencode for inactivity)
#   3   bad args
#   *   any other opencode non-zero exit (e.g. 124/137 = hard-timeout)

set -e

# --- Cleanup helpers ---------------------------------------------------------
_cleanup_children() {
  pkill -9 -P $$ 2>/dev/null || true
}

# Restore the reference dir if we hid it.  Idempotent.
_restore_ref_dir() {
  if [ "${REF_HIDDEN_BY_THIS_ITER:-0}" = 1 ] && [ -d "${REF_HIDDEN_DIR:-/nonexistent}" ]; then
    mv "$REF_HIDDEN_DIR" "$REF_DIR" 2>/dev/null && \
      echo "[gen $APP_NAME iter $ITER] restored reference dir"
    REF_HIDDEN_BY_THIS_ITER=0
  fi
}

_on_exit() {
  _restore_ref_dir
  _cleanup_children
}
trap _on_exit EXIT INT TERM HUP QUIT

# --- Parse args --------------------------------------------------------------
if [ "$#" -lt 5 ] || [ "$#" -gt 6 ]; then
  echo "Usage: _iter_gen.sh APP_NAME ITER PROMPT_FILE APP_DIR LOG_DIR [WORKER_SLOT]" >&2
  exit 3
fi

APP_NAME="$1"
ITER="$2"
PROMPT_FILE="$3"
APP_DIR="$4"
LOG_DIR="$5"
WORKER_SLOT="${6:-0}"

if ! [[ "$WORKER_SLOT" =~ ^[0-9]+$ ]]; then
  echo "ERROR: WORKER_SLOT must be a non-negative integer, got: $WORKER_SLOT" >&2
  exit 3
fi

if ! [[ "$ITER" =~ ^[0-9]+$ ]]; then
  echo "ERROR: ITER must be a positive integer, got: $ITER" >&2
  exit 3
fi

for p in "$PROMPT_FILE" "$APP_DIR" "$LOG_DIR"; do
  if [ ! -e "$p" ]; then
    echo "ERROR: required path does not exist: $p" >&2
    exit 3
  fi
done

ITER_LOG="$LOG_DIR/iter_${ITER}"
mkdir -p "$ITER_LOG"

# --- Resolve repo paths (for REF_DIR hiding) ---------------------------------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BUILD_DIR="$REPO_ROOT/build"

# Activate venv so the inline python sqlite reader has the right interpreter.
if [ -f "$BUILD_DIR/venv/bin/activate" ]; then
  . "$BUILD_DIR/venv/bin/activate"
fi
export PYTHONPATH="${REPO_ROOT}"

# --- Configuration -----------------------------------------------------------
OPENCODE_MODEL="${OPENCODE_MODEL:-argo/claudeopus47}"
OPENCODE_TIMEOUT="${OPENCODE_TIMEOUT:-3600}"
OPENCODE_STALL_CHECK="${OPENCODE_STALL_CHECK:-600}"
OPENCODE_STALL_KILL="${OPENCODE_STALL_KILL:-1200}"

# Per-worker opencode SQLite DB isolation.  Sharing the default
# ~/.local/share/opencode/opencode.db across concurrent `opencode run`
# invocations produces intermittent "Error: database is locked" crashes
# that exit silently with rc=0 (see commit history for the smoke test that
# caught this).  We redirect XDG_DATA_HOME per slot so each worker gets
# its own DB at /tmp/opencode_worker_<slot>/.local/share/opencode/.
# Shared paths (config, vendored language servers under ~/.cache/opencode)
# are unaffected.
WORKER_DATA_ROOT="/tmp/opencode_worker_${WORKER_SLOT}/.local/share"
export XDG_DATA_HOME="$WORKER_DATA_ROOT"
# Per-iter slot wipe: defensive — ensures every iter starts from the same
# clean-DB precondition the orchestrator establishes at startup, not just
# iter_1 of each slot.  Originally hypothesized that a stale opencode.db
# from a prior iter caused 1.5s rc=137 no-ops on SAMRAI+Nyx fresh-vanilla
# (2026-05-26), but that hypothesis is NOT confirmed — many multi-iter
# TRUSTED apps ran fine without this wipe.  Keeping the wipe as cheap
# defense-in-depth while the actual root cause is still under investigation.
rm -rf "$XDG_DATA_HOME/opencode"
mkdir -p "$XDG_DATA_HOME/opencode"
OPENCODE_DB="$XDG_DATA_HOME/opencode/opencode.db"

echo "[gen $APP_NAME iter $ITER] model=$OPENCODE_MODEL slot=$WORKER_SLOT hard_cap=${OPENCODE_TIMEOUT}s stall_check=${OPENCODE_STALL_CHECK}s stall_kill=${OPENCODE_STALL_KILL}s xdg_data=$XDG_DATA_HOME (slot wiped)"

# --- Hide reference dir ------------------------------------------------------
# The LLM must DESIGN VeloC-based resilience independently rather than copy
# from the upstream checkpointed reference.  Each parallel helper uses its
# own $$ PID suffix in the hidden dir name so multiple apps' helpers do not
# collide (they hide DIFFERENT REF_DIRs anyway, but the unique suffix keeps
# the rename target distinct).
REF_DIR="$REPO_ROOT/tests/apps/checkpointed/$APP_NAME"
REF_HIDDEN_DIR="$REPO_ROOT/tests/apps/.hidden_checkpointed_${APP_NAME}_$$"
REF_HIDDEN_BY_THIS_ITER=0
if [ -d "$REF_DIR" ]; then
  if mv "$REF_DIR" "$REF_HIDDEN_DIR" 2>/dev/null; then
    REF_HIDDEN_BY_THIS_ITER=1
    echo "[gen $APP_NAME iter $ITER] hid reference dir"
  else
    echo "[gen $APP_NAME iter $ITER] WARN: failed to hide reference dir $REF_DIR"
  fi
fi

# --- Run OpenCode ------------------------------------------------------------
STALL_LOG="$ITER_LOG/stall_watch.log"
: > "$STALL_LOG"
rm -f "$ITER_LOG/.opencode_stalled"

PROMPT="$(cat "$PROMPT_FILE")"

OPENCODE_START=$(date +%s.%N)
OPENCODE_START_MS=$(date +%s%3N)

cd "$APP_DIR"

# Hard-timeout-wrapped opencode in the background.
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
          echo "[$(date -u +%H:%M:%SZ)] [stall-watch] stalled ${AGE}s after flag (>=${OPENCODE_STALL_KILL}s) — killing pid $OPENCODE_PID" >> "$STALL_LOG"
          touch "$ITER_LOG/.opencode_stalled"
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

# Wait for opencode (under timeout) to finish.  We TEMPORARILY disable
# `set -e` so a signal-killed child does not exit the helper, but we still
# capture the true exit code into OC_RC.  Historical bug: `wait ... || true`
# masked the exit code so OC_RC was always 0, hiding silent opencode no-ops
# (e.g. rc=1 "You must provide a message", rc=2 prompt-parse errors) behind
# a fake PASS that fed unchanged source into validate.
set +e
wait "$OPENCODE_PID" 2>/dev/null
OC_RC=$?
set -e
# rc=127 from `wait` means "no such job" — opencode already reaped before the
# wait, which can happen on extremely fast (sub-100ms) exits.  Treat as 0;
# the genuine exit code is unrecoverable at that point, but the absence of
# any tokens / stdout will surface via the orchestrator's no-op detector.
[ "$OC_RC" -eq 127 ] && OC_RC=0
kill -TERM "$STALL_WATCHER_PID" 2>/dev/null || true
wait "$STALL_WATCHER_PID" 2>/dev/null || true

# --- OpenCode forensic dump (always written) --------------------------------
# Every iter writes opencode_diagnostic.txt so when the silent-no-op signature
# fires (or any other surprise: 0-byte stdout, non-zero rc, fast exit), we
# have enough state to root-cause without having to re-run.  Cost is ~5-10 KB
# per iter — negligible vs. the time wasted by a no-op iter going undetected.
DIAG="$ITER_LOG/opencode_diagnostic.txt"
{
  echo "=== OpenCode iter diagnostic — $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo "app=$APP_NAME iter=$ITER slot=$WORKER_SLOT"
  echo "OC_RC=$OC_RC"
  STDOUT_SIZE=$(stat -c %s "$ITER_LOG/opencode_stdout.txt" 2>/dev/null || echo NA)
  STDERR_SIZE=$(stat -c %s "$ITER_LOG/opencode_stderr.txt" 2>/dev/null || echo NA)
  echo "stdout_size_bytes=$STDOUT_SIZE"
  echo "stderr_size_bytes=$STDERR_SIZE"
  echo "prompt_file=$PROMPT_FILE prompt_size_bytes=$(stat -c %s "$PROMPT_FILE" 2>/dev/null || echo NA)"
  echo
  echo "--- env (relevant) ---"
  echo "HOME=$HOME"
  echo "USER=${USER:-}"
  echo "XDG_DATA_HOME=$XDG_DATA_HOME"
  echo "OPENCODE_DB=$OPENCODE_DB"
  echo "PWD=$(pwd)"
  echo "OPENCODE_MODEL=$OPENCODE_MODEL OPENCODE_TIMEOUT=$OPENCODE_TIMEOUT"
  echo
  echo "--- opencode --version ---"
  opencode --version 2>&1 || echo "(opencode --version FAILED rc=$?)"
  echo
  echo "--- $XDG_DATA_HOME/opencode tree (du -sh top-level) ---"
  if [ -d "$XDG_DATA_HOME/opencode" ]; then
    du -sh "$XDG_DATA_HOME/opencode"/* 2>/dev/null | head -20
  else
    echo "(missing — opencode dir was not created)"
  fi
  echo
  echo "--- SQLite session/message counts (slot DB) ---"
  if [ -f "$OPENCODE_DB" ]; then
    echo "db_size_bytes=$(stat -c %s "$OPENCODE_DB" 2>/dev/null)"
    python3 - "$OPENCODE_DB" "$APP_DIR" "$OPENCODE_START_MS" <<'PYEOF' 2>&1
import sqlite3, sys
db_path, app_dir, start_ms = sys.argv[1], sys.argv[2], int(sys.argv[3])
try:
    db = sqlite3.connect(db_path, timeout=5.0)
    c = db.cursor()
    n_sess = c.execute("SELECT COUNT(*) FROM session").fetchone()[0]
    n_msg = c.execute("SELECT COUNT(*) FROM message").fetchone()[0]
    n_this = c.execute(
        "SELECT COUNT(*) FROM session WHERE directory=? AND time_created>=?",
        (app_dir, start_ms),
    ).fetchone()[0]
    print(f"sessions_total={n_sess} messages_total={n_msg} sessions_this_iter={n_this}")
    recent = c.execute(
        "SELECT id, directory, time_created FROM session "
        "ORDER BY time_created DESC LIMIT 3"
    ).fetchall()
    for sid, sdir, stc in recent:
        marker = " <- this iter" if stc >= start_ms and sdir == app_dir else ""
        print(f"  recent: id={sid[:24]}... dir={sdir} created={stc}{marker}")
    db.close()
except Exception as e:
    print(f"(DB query failed: {e})")
PYEOF
  else
    echo "(no DB at $OPENCODE_DB)"
  fi
  echo
  echo "--- newest opencode log tail (50 lines) ---"
  LATEST_LOG=$(ls -t "$XDG_DATA_HOME/opencode/log/"*.log 2>/dev/null | head -1)
  if [ -n "$LATEST_LOG" ]; then
    echo "log_file=$LATEST_LOG log_size_bytes=$(stat -c %s "$LATEST_LOG" 2>/dev/null)"
    tail -50 "$LATEST_LOG" 2>/dev/null
  else
    echo "(no log files under $XDG_DATA_HOME/opencode/log/)"
  fi
  echo
  echo "--- opencode_stdout.txt last 30 lines ---"
  tail -30 "$ITER_LOG/opencode_stdout.txt" 2>/dev/null
  echo
  echo "--- opencode_stderr.txt last 30 lines ---"
  tail -30 "$ITER_LOG/opencode_stderr.txt" 2>/dev/null
} > "$DIAG" 2>&1

# Restore ref dir before we extract tokens or return — the validator (called
# later by the orchestrator on the executor side) needs the original path.
_restore_ref_dir
# Re-arm the EXIT trap to be safe in case anything raises between here and exit.
# (no-op if already restored)

STALL_ABORTED=0
if [ -f "$ITER_LOG/.opencode_stalled" ]; then
  STALL_ABORTED=1
  echo "[gen $APP_NAME iter $ITER] OpenCode killed by stall watcher (no stdout growth >=${OPENCODE_STALL_KILL}s after flag)" \
    | tee -a "$ITER_LOG/opencode_stderr.txt"
  mkdir -p "$REPO_ROOT/build/run_logs"
  # Single short POSIX-atomic append (<PIPE_BUF=4096 bytes).
  printf "%s\tapp=%s\titer=%s\treason=stalled\tlog=%s\n" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$APP_NAME" "$ITER" "$ITER_LOG" \
    >> "$REPO_ROOT/build/run_logs/_stall_investigations.log"
elif [ "$OC_RC" = 124 ] || [ "$OC_RC" = 137 ]; then
  echo "[gen $APP_NAME iter $ITER] OpenCode hit ${OPENCODE_TIMEOUT}s hard cap" \
    | tee -a "$ITER_LOG/opencode_stderr.txt"
fi

cd "$REPO_ROOT"
OPENCODE_END=$(date +%s.%N)
GEN_WALL=$(awk "BEGIN { printf \"%.9f\", $OPENCODE_END - $OPENCODE_START }" 2>/dev/null || echo "0")
echo "[gen $APP_NAME iter $ITER] OpenCode finished in ${GEN_WALL}s (rc=$OC_RC stall=$STALL_ABORTED)"

# --- Per-iter inspection (best-effort, identical to run_iterative.sh) --------
python3 -m validation.veloc.scripts.inspect_iter "$ITER_LOG" --write \
  >> "$ITER_LOG/inspection.run.log" 2>&1 || true

# --- Token extraction from OpenCode's SQLite DB ------------------------------
# Per-slot DB at $OPENCODE_DB (set above via XDG_DATA_HOME).  No cross-worker
# contention by construction.  Session filter by directory + time_created
# is still useful to skip historical sessions in the same slot DB across
# repeated iters of one app.
ITER_INPUT_TOKENS=0
ITER_OUTPUT_TOKENS=0
ITER_TOTAL_TOKENS=0
if [ -f "$OPENCODE_DB" ]; then
  TOKENS_JSON=$(APP_DIR="$APP_DIR" OPENCODE_START_MS="$OPENCODE_START_MS" OPENCODE_DB="$OPENCODE_DB" \
    python3 -c '
import os, sqlite3, json, sys, time

db_path = os.environ["OPENCODE_DB"]
app_dir = os.environ["APP_DIR"]
start_ms = int(os.environ["OPENCODE_START_MS"])

# Retry-on-lock: WAL still serializes the checkpoint operation, so a brief
# busy timeout absorbs the rare contention spike when several helpers query
# at the same instant.
for attempt in range(5):
    try:
        db = sqlite3.connect(db_path, timeout=10.0)
        c = db.cursor()
        c.execute("""
            SELECT m.session_id,
                   COALESCE(SUM(json_extract(m.data, "$.tokens.input")), 0),
                   COALESCE(SUM(json_extract(m.data, "$.tokens.output")), 0),
                   COALESCE(SUM(json_extract(m.data, "$.tokens.total")), 0)
            FROM message m
            JOIN session s ON m.session_id = s.id
            WHERE s.directory = ?
              AND json_extract(m.data, "$.role") = "assistant"
              AND json_extract(m.data, "$.tokens.total") IS NOT NULL
              AND s.time_created >= ?
            GROUP BY m.session_id
            ORDER BY s.time_created DESC
            LIMIT 1
        """, (app_dir, start_ms))
        row = c.fetchone()
        db.close()
        if row:
            print(json.dumps({"input": int(row[1]), "output": int(row[2]), "total": int(row[3])}))
        else:
            print(json.dumps({"input": 0, "output": 0, "total": 0}))
        break
    except sqlite3.OperationalError as e:
        if attempt == 4:
            print(json.dumps({"input": 0, "output": 0, "total": 0, "error": str(e)}), file=sys.stderr)
            print(json.dumps({"input": 0, "output": 0, "total": 0}))
            break
        time.sleep(0.5 * (attempt + 1))
    except Exception as e:
        print(json.dumps({"input": 0, "output": 0, "total": 0, "error": str(e)}), file=sys.stderr)
        print(json.dumps({"input": 0, "output": 0, "total": 0}))
        break
' 2>/dev/null)
  ITER_INPUT_TOKENS=$(echo "$TOKENS_JSON"  | python3 -c "import sys,json; print(json.load(sys.stdin).get('input',0))"  2>/dev/null || echo "0")
  ITER_OUTPUT_TOKENS=$(echo "$TOKENS_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('output',0))" 2>/dev/null || echo "0")
  ITER_TOTAL_TOKENS=$(echo "$TOKENS_JSON"  | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))"  2>/dev/null || echo "0")
  echo "[gen $APP_NAME iter $ITER] tokens input=$ITER_INPUT_TOKENS output=$ITER_OUTPUT_TOKENS total=$ITER_TOTAL_TOKENS"
fi

# --- Write metrics_gen.json (atomic via tmp+rename) --------------------------
STARTED_AT=$(date -u -d "@$(printf '%.0f' "$OPENCODE_START")" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)
STALL_BOOL=$([ "$STALL_ABORTED" = 1 ] && echo "true" || echo "false")

TMP_METRICS="$ITER_LOG/metrics_gen.json.tmp.$$"
cat > "$TMP_METRICS" << EOFMETRICS
{
  "schema": "iter_gen_v1",
  "app_name": "$APP_NAME",
  "iter": $ITER,
  "model": "$OPENCODE_MODEL",
  "started_at": "$STARTED_AT",
  "gen_wall_s": $GEN_WALL,
  "tokens_input": $ITER_INPUT_TOKENS,
  "tokens_output": $ITER_OUTPUT_TOKENS,
  "tokens_total": $ITER_TOTAL_TOKENS,
  "stall_aborted": $STALL_BOOL,
  "opencode_exit_code": $OC_RC,
  "opencode_timeout_s": $OPENCODE_TIMEOUT,
  "stall_check_s": $OPENCODE_STALL_CHECK,
  "stall_kill_s": $OPENCODE_STALL_KILL
}
EOFMETRICS
mv -f "$TMP_METRICS" "$ITER_LOG/metrics_gen.json"

# --- Exit code reflects gen outcome only (validation comes later) ------------
if [ "$STALL_ABORTED" = 1 ]; then
  exit 2
fi
exit "$OC_RC"
