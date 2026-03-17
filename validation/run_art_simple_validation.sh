#!/usr/bin/env bash
set -euo pipefail

# Run resilience validation for the art_simple example.
# Usage (from repo root):
#   ./validation/run_matrix_mul_validation.sh

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Optional: use build/venv if it exists (created by ./setup.sh).
if [[ -d "build/venv" ]]; then
  # shellcheck disable=SC1091
  source "build/venv/bin/activate"
fi

export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"

python -m validation.run_validation \
  --source-dir examples/art_simple \
  --build-dir build/validation/art_simple \
  --output-dir build/validation_output/art_simple \
  --executable-name art_simple_main \
  --num-procs 4 \
  --max-attempts 10 \
  --injection-delay 5.0 \
  -- data/tooth_preprocessed.h5 294.078 5 2 0 4

