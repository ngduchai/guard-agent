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

# Forward everything else to the base script.  exec replaces the wrapper
# process so signals (TERM/INT) reach run_iterative.sh's own trap handlers
# rather than dying in the wrapper layer.
exec "$SCRIPT_DIR/run_iterative.sh" "${FORWARD_ARGS[@]}"
