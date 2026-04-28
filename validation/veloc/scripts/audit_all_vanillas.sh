#!/usr/bin/env bash
# Audit every vanilla in apps_all.txt (or APPS_FILE) for resilience strip-out.
#
# For each app we invoke run_validate.sh --audit-vanilla, which runs validate.py
# with both --original-codebase and --resilient-codebase pointing at the vanilla
# source.  We expect:
#   * the failure-free run to complete cleanly (vanilla works correctly), and
#   * the failure-injected run's resilience proof to FAIL — meaning the vanilla
#     could not actually recover, only re-do the work from scratch.  That FAIL
#     is the signal that the vanilla is properly stripped of all checkpoint code.
#
# The validate.py exit code is intentionally ignored here: a code-1 exit caused
# by a failed resilience proof is exactly what we want when auditing a vanilla.
# Per-app verdict is computed from the JSON artifacts written under
# build/audit_output/<APP>/correctness/, by audit_aggregate_report.py.
#
# Usage:
#   ./audit_all_vanillas.sh                          # all apps from apps_all.txt
#   APPS_FILE=apps_fast.txt ./audit_all_vanillas.sh  # different list
#   ./audit_all_vanillas.sh CoMD HPCG                # specific apps
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BUILD_DIR="$REPO_ROOT/build"
APPS_FILE="${APPS_FILE:-$REPO_ROOT/validation/veloc/apps_all.txt}"

if [ "$#" -gt 0 ]; then
  apps=("$@")
else
  # Strip inline comments + whole-line comments + blank lines + leading/trailing
  # whitespace. Mirrors run_batch.sh:130-135 so tier files (which use both
  # whole-line `#` headers and inline `# explanation` after each app name)
  # parse identically across the two launchers.
  mapfile -t apps < <(
    sed 's/[[:space:]]*#.*$//' "$APPS_FILE" \
      | grep -v '^[[:space:]]*$' \
      | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
  )
fi

mkdir -p "$BUILD_DIR/audit_output"
LOG_DIR="$BUILD_DIR/audit_output/_logs"
mkdir -p "$LOG_DIR"

echo "════════════════════════════════════════════════════════════════════"
echo "  Vanilla audit: ${#apps[@]} app(s)"
echo "  Logs: $LOG_DIR/<app>.log"
echo "════════════════════════════════════════════════════════════════════"

started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

FORCE="${FORCE:-0}"
for app in "${apps[@]}"; do
  echo ""
  log="$LOG_DIR/${app}.log"
  # Per-app skip: if a prior audit log shows "All stages completed successfully"
  # AND this isn't a forced re-audit, skip.  Audit results are deterministic
  # (vanilla source + audit framework haven't changed), so re-running wastes
  # ~10 min per app for no new information.  Override with FORCE=1.
  if [ -f "$log" ] && grep -q "All stages completed successfully" "$log" 2>/dev/null && [ "$FORCE" != "1" ]; then
    echo "── $app: SKIP (already audited; set FORCE=1 to re-run) ──"
    continue
  fi
  echo "── auditing $app ──"
  # Run the audit; record exit code but never abort the loop on it.  A
  # nonzero exit is expected when the resilience proof fails (the audit
  # success path).  audit_aggregate_report.py is the source of truth.
  if "$SCRIPT_DIR/run_validate.sh" --audit-vanilla "$app" > "$log" 2>&1; then
    rc=0
  else
    rc=$?
  fi
  echo "$app: validate.py exit=$rc (see $log)"
done

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "  Aggregating audit results"
echo "════════════════════════════════════════════════════════════════════"

# Activate venv if available (for yaml/etc.)
if [ -f "$BUILD_DIR/venv/bin/activate" ]; then
  . "$BUILD_DIR/venv/bin/activate"
fi
export PYTHONPATH="$REPO_ROOT"

python3 "$SCRIPT_DIR/audit_aggregate_report.py" \
    --apps "${apps[@]}" \
    --output-root "$BUILD_DIR/audit_output" \
    --started-at "$started_at"
