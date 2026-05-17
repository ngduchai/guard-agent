#!/usr/bin/env bash
set -e

# Wrapper around run_iterative.sh for the 3-D model exploration (5 LLM
# cells x 17 apps).  Adds two flags on top of the base script:
#
#   --model-tag <TAG>          short slug (sonnet46, haiku45, opus47_128k,
#                              gpt55, gemini25pro).  Drives all output paths
#                              so cells run concurrently without clobbering
#                              the un-suffixed Opus 4.7 baseline.
#   --opencode-model <ARGO_ID> full Argo identifier passed through to
#                              opencode --model.  Examples:
#                                argo/claudesonnet46
#                                argo/claudehaiku45
#                                argo/claudeopus47
#                                argo/gpt55
#                                argo/gemini25pro
#
# Path table (when --model-tag <TAG> is set):
#   iter logs         : build/iterative_logs/<APP>_baseline_<TAG>/
#   LLM-modified src  : build/tests_baseline_<TAG>/<APP>/
#   validation output : build/validation_output/<APP>_baseline_<TAG>/
#   trust unit name   : <APP>_baseline_<TAG>
#
# The underlying run_iterative.sh + run_validate.sh recognise MODEL_TAG via
# env var; this wrapper just sets the env + forwards remaining flags.  The
# existing un-suffixed Opus 4.7 paths are never touched when MODEL_TAG is
# set.
#
# Optional env vars passed through (cell-specific):
#   OPENCODE_INPUT_TRUNC_TOKENS=<N>   truncate the iter-loop prompt at file
#                                     boundaries when its token estimate
#                                     exceeds N (Deliverable 2 — cell B1
#                                     128K cap).
#
# Usage:
#   ./run_iterative_for_model.sh --model-tag sonnet46 \
#       --opencode-model argo/claudesonnet46 \
#       --baseline HPCG --max-iters 1
#
# All remaining args after the wrapper's own flags pass through verbatim
# to run_iterative.sh (e.g. --baseline, <app_name>, --max-iters N).

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

MODEL_TAG_ARG=""
OPENCODE_MODEL_ARG=""

# Pop wrapper-only flags; build the forwarded arg list.
FORWARD_ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --model-tag)
      MODEL_TAG_ARG="${2:?--model-tag requires a value}"
      shift 2
      ;;
    --model-tag=*)
      MODEL_TAG_ARG="${1#*=}"
      shift
      ;;
    --opencode-model)
      OPENCODE_MODEL_ARG="${2:?--opencode-model requires a value}"
      shift 2
      ;;
    --opencode-model=*)
      OPENCODE_MODEL_ARG="${1#*=}"
      shift
      ;;
    *)
      FORWARD_ARGS+=("$1")
      shift
      ;;
  esac
done

if [ -z "$MODEL_TAG_ARG" ] || [ -z "$OPENCODE_MODEL_ARG" ]; then
  cat >&2 <<'EOF'
Usage: run_iterative_for_model.sh
         --model-tag <TAG>
         --opencode-model <ARGO_ID>
         [run_iterative.sh args...]

Both --model-tag and --opencode-model are required.
EOF
  exit 2
fi

# Validate the tag format.  Letters, digits, underscore, dash only — keeps
# path construction unambiguous (the suffix is appended after _baseline so
# spaces / slashes would break path parsing in downstream tools).
if ! [[ "$MODEL_TAG_ARG" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "ERROR: --model-tag '$MODEL_TAG_ARG' contains illegal chars (allowed: A-Za-z0-9_-)" >&2
  exit 2
fi

export MODEL_TAG="$MODEL_TAG_ARG"
export OPENCODE_MODEL="$OPENCODE_MODEL_ARG"

echo "[run_iterative_for_model] MODEL_TAG=$MODEL_TAG OPENCODE_MODEL=$OPENCODE_MODEL"
echo "[run_iterative_for_model] sharded path table:"
echo "  iter logs : build/iterative_logs/<APP>_baseline_${MODEL_TAG}/"
echo "  src       : build/tests_baseline_${MODEL_TAG}/<APP>/"
echo "  validate  : build/validation_output/<APP>_baseline_${MODEL_TAG}/"
if [ -n "${OPENCODE_INPUT_TRUNC_TOKENS:-}" ]; then
  echo "[run_iterative_for_model] context cap: OPENCODE_INPUT_TRUNC_TOKENS=$OPENCODE_INPUT_TRUNC_TOKENS"
fi

# ---------------------------------------------------------------------------
# Cross-cell read isolation (defense in depth)
#
# When cell N runs after cells 1..N-1, those earlier cells' tagged source
# dirs (build/tests_baseline_<OTHER_TAG>/) sit on disk.  Also the upstream
# reference checkpointed source (tests/apps/checkpointed/<APP>/).  OpenCode's
# read/grep/glob tools have full FS visibility, so cell N's LLM could read
# any of those and crib from them, contaminating the experiment.
#
# Mitigation: move every OTHER cell's tagged dir and the per-app reference
# into a SINGLE isolation folder under /tmp/ (outside the project tree, so
# not discoverable by globbing build/) and chmod 000 the folder so the OS
# itself denies traversal regardless of what OpenCode tries.  Restore on
# any exit (normal, error, signal).  Same effect as the existing per-iter
# reference-hiding in run_iterative.sh, just scaled to cover other-cell
# sources and centralised in one place so the OS perm bit lifts both kinds
# of isolation atomically.
#
# NOT hidden:
#   - This cell's own tests_baseline_${MODEL_TAG}/ (obviously)
#   - The un-suffixed tests_baseline/ (Opus 4.7 1M baseline) — covered by
#     OpenCode permission.read deny at ~/.config/opencode/opencode.json
# ---------------------------------------------------------------------------

REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BUILD_DIR="${BUILD_DIR:-$REPO_ROOT/build}"
ISOLATION_DIR="${ISOLATION_DIR:-/tmp/.cell_iso_${MODEL_TAG}_$$}"
HIDDEN_ENTRIES=()  # entries: "<isolation_path>|<original_path>"

# Pull --baseline <APP> out of the forwarded args so we know which app's
# reference dir to hide.  --baseline may appear as one or two tokens.
APP_FROM_ARGS=""
for ((i=0; i<${#FORWARD_ARGS[@]}; i++)); do
  case "${FORWARD_ARGS[$i]}" in
    --baseline)
      APP_FROM_ARGS="${FORWARD_ARGS[$((i+1))]:-}"
      break
      ;;
    --baseline=*)
      APP_FROM_ARGS="${FORWARD_ARGS[$i]#*=}"
      break
      ;;
  esac
done

mkdir -p "$ISOLATION_DIR"

# Move other cells' tagged source dirs into the isolation folder.
if [ -d "$BUILD_DIR" ]; then
  for d in "$BUILD_DIR"/tests_baseline_*/; do
    [ -d "$d" ] || continue
    base=$(basename "${d%/}")
    tag="${base#tests_baseline_}"
    if [ "$tag" = "$MODEL_TAG" ]; then
      continue
    fi
    target="$ISOLATION_DIR/$base"
    if mv "$d" "$target" 2>/dev/null; then
      HIDDEN_ENTRIES+=("$target|${d%/}")
      echo "[run_iterative_for_model] hid $d → isolation"
    fi
  done
fi

# Move the per-app upstream reference source into the same isolation folder.
# Skip if we couldn't determine the app from --baseline (no harm, run_iterative.sh
# has its own per-iter fallback hiding for the reference dir).
if [ -n "$APP_FROM_ARGS" ]; then
  REF_DIR="$REPO_ROOT/tests/apps/checkpointed/$APP_FROM_ARGS"
  if [ -d "$REF_DIR" ]; then
    target="$ISOLATION_DIR/checkpointed_$APP_FROM_ARGS"
    if mv "$REF_DIR" "$target" 2>/dev/null; then
      HIDDEN_ENTRIES+=("$target|$REF_DIR")
      echo "[run_iterative_for_model] hid reference $REF_DIR → isolation"
    fi
  fi
fi

# OS-level denial: chmod 000 prevents traversal of the isolation folder by
# anyone (including the user the wrapper runs as).  An LLM that somehow
# guesses the isolation path still gets EACCES from the kernel before any
# tool-layer permission check fires.  Wrapper temporarily lifts the mode
# in the restore trap.
chmod 000 "$ISOLATION_DIR" 2>/dev/null

_restore_isolation() {
  # Lift the OS-level deny so we can mv contents back.
  chmod 755 "$ISOLATION_DIR" 2>/dev/null
  local entry iso orig
  for entry in "${HIDDEN_ENTRIES[@]}"; do
    iso="${entry%%|*}"
    orig="${entry##*|}"
    if [ -e "$iso" ]; then
      if mv "$iso" "$orig" 2>/dev/null; then
        echo "[run_iterative_for_model] restored $iso → $orig"
      else
        echo "[run_iterative_for_model] WARN: failed to restore $iso — manual: chmod 755 $ISOLATION_DIR && mv $iso $orig"
      fi
    fi
  done
  # Remove the isolation folder if empty; leave it (warn) if not (something
  # went wrong with restore).
  rmdir "$ISOLATION_DIR" 2>/dev/null || \
    echo "[run_iterative_for_model] WARN: $ISOLATION_DIR not empty after restore — operator cleanup required"
}
trap _restore_isolation EXIT INT TERM

# Forward to the base script.  Run (not exec) so the trap above fires
# after run_iterative.sh exits and the isolation gets lifted before the
# wrapper returns.
"$SCRIPT_DIR/run_iterative.sh" "${FORWARD_ARGS[@]}"
