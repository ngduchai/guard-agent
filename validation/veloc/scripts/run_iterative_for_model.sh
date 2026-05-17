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
# Inter-tag read isolation (defense-in-depth against cross-cell leakage)
#
# When cell N runs after cells 1..N-1, those earlier cells' tagged source
# dirs (build/tests_baseline_<OTHER_TAG>/) sit on disk. OpenCode's read/
# grep/glob tools have full FS visibility, so cell N's LLM could read
# those earlier solutions and crib from them, contaminating the experiment.
#
# Mitigation: temporarily mv every OTHER cell's tagged dir to a .hidden_*
# sibling before run_iterative.sh launches, restore on any exit (normal,
# error, signal). Mirrors the existing reference-hiding pattern at
# run_iterative.sh:474-493 for tests/apps/checkpointed/.
#
# NOT hidden:
#   - This cell's own tests_baseline_${MODEL_TAG}/ (obviously)
#   - The un-suffixed tests_baseline/ (Opus 4.7 1M baseline) — covered by
#     OpenCode permission.read deny at ~/.config/opencode/opencode.json
#     so defense-in-depth is via the config, not by hiding
# ---------------------------------------------------------------------------

REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BUILD_DIR="${BUILD_DIR:-$REPO_ROOT/build}"
HIDDEN_DIRS=()  # entries: "<hidden_path>|<original_path>"

if [ -d "$BUILD_DIR" ]; then
  for d in "$BUILD_DIR"/tests_baseline_*/; do
    [ -d "$d" ] || continue
    base=$(basename "${d%/}")
    tag="${base#tests_baseline_}"
    # Skip this cell's own dir and any pre-existing .hidden_* (left over
    # from a crashed prior run that didn't restore — we ignore those, the
    # operator can clean up manually).
    if [ "$tag" = "$MODEL_TAG" ] || [[ "$tag" == .hidden_* ]]; then
      continue
    fi
    hidden="${BUILD_DIR}/.hidden_tests_baseline_${tag}_$$"
    if mv "$d" "$hidden" 2>/dev/null; then
      HIDDEN_DIRS+=("$hidden|$d")
      echo "[run_iterative_for_model] hid other-cell dir (${d%/} → $hidden)"
    else
      echo "[run_iterative_for_model] WARN: failed to hide ${d%/} — cell may read it"
    fi
  done
fi

_restore_hidden_dirs() {
  local entry hidden orig
  for entry in "${HIDDEN_DIRS[@]}"; do
    hidden="${entry%%|*}"
    orig="${entry##*|}"
    if [ -d "$hidden" ]; then
      if mv "$hidden" "$orig" 2>/dev/null; then
        echo "[run_iterative_for_model] restored other-cell dir ($hidden → $orig)"
      else
        echo "[run_iterative_for_model] WARN: failed to restore $hidden — manual: mv $hidden $orig"
      fi
    fi
  done
}
trap _restore_hidden_dirs EXIT INT TERM

# Forward everything else to the base script.  Run (not exec) so the
# trap above fires after run_iterative.sh exits and the hidden dirs get
# restored before the wrapper returns.
"$SCRIPT_DIR/run_iterative.sh" "${FORWARD_ARGS[@]}"
