#!/usr/bin/env bash
set -euo pipefail

# Run resilience validation for art_simple vs veloc_art_simple.
# Baseline:  examples/art_simple
# Resilient: examples/veloc_art_simple
#
# Usage (from repo root):
#   ./validation/run_art_simple_pair_validation.sh

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Optional: use build/venv if it exists (created by ./setup.sh).
if [[ -d "build/venv" ]]; then
  # shellcheck disable=SC1091
  source "build/venv/bin/activate"
fi

export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"

DATA_PATH="${REPO_ROOT}/data/tooth_preprocessed.h5"
COMMON_ARGS="${DATA_PATH} 294.078 5 2 0 4"

RESILIENT_BUILD="build/validation/veloc_art_simple"
RESILIENT_CFG="${REPO_ROOT}/${RESILIENT_BUILD}/veloc.cfg"

python -m validation.run_resilience_validation \
  --baseline-source-dir examples/art_simple \
  --baseline-build-dir build/validation/art_simple_baseline \
  --baseline-executable-name art_simple_main \
  --baseline-args "${COMMON_ARGS}" \
  --resilient-source-dir examples/veloc_art_simple \
  --resilient-build-dir build/validation/veloc_art_simple \
  --resilient-executable-name art_simple_main \
  --resilient-args "${COMMON_ARGS} ${RESILIENT_CFG}" \
  --num-procs 4 \
  --output-dir build/validation_output/art_simple_vs_veloc_art_simple \
  --max-attempts 10 \
  --injection-delay 10.0 \
  --output-file-name recon.h5 \
  --install-resilient
