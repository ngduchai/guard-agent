#!/bin/bash
# Per-rank SST launcher — invoked by mpirun once per rank.
# Runs `sst bench.py`; rank 0 emits a stable validation marker on success
# so the framework's stdout-comparison machinery has something to match.
set -u
script_dir="$(cd "$(dirname "$0")" && pwd)"
SST_BIN="${SST_BIN:-$HOME/.local/sst/bin/sst}"

"$SST_BIN" "$script_dir/bench.py" "$@"
ec=$?

rank="${PMI_RANK:-${OMPI_COMM_WORLD_RANK:-${PMIX_RANK:-0}}}"
if [ "$rank" = "0" ]; then
  if [ "$ec" -eq 0 ]; then
    echo "SST_VALIDATION=PASSED"
  else
    echo "SST_VALIDATION=FAILED"
  fi
fi
exit "$ec"
