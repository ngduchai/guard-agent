#!/bin/bash
# Per-rank SST launcher — invoked by mpirun once per rank.
# Each rank runs `sst bench.py` (or restarts from a .sstcpt registry on later
# attempts), then rank 0 prints a stable validation marker so the framework's
# stdout-comparison machinery has something to match.
set -u
script_dir="$(cd "$(dirname "$0")" && pwd)"
SST_BIN="${SST_BIN:-$HOME/.local/sst/bin/sst}"

# Resilient launcher: enables SST's native checkpoint mechanism on every fresh
# run; restarts from the latest .sstcpt registry if a previous attempt left one
# in PWD.  Cadence: --checkpoint-sim-period=4ms (about 4-5 checkpoints over
# the 18ms sim time of bench.py).
: "${SST_CKPT_PERIOD:=4ms}"
: "${SST_CKPT_PREFIX:=ckpt}"
if [ -d "$SST_CKPT_PREFIX" ] && ls "$SST_CKPT_PREFIX"/ckpt_*/ckpt_*.sstcpt >/dev/null 2>&1; then
  latest=$(ls -t "$SST_CKPT_PREFIX"/ckpt_*/ckpt_*.sstcpt | head -1)
  "$SST_BIN" "$latest"
  ec=$?
else
  "$SST_BIN" "$script_dir/bench.py" \
    --checkpoint-sim-period="$SST_CKPT_PERIOD" \
    --checkpoint-prefix="$SST_CKPT_PREFIX" "$@"
  ec=$?
fi

rank="${PMI_RANK:-${OMPI_COMM_WORLD_RANK:-${PMIX_RANK:-0}}}"
if [ "$rank" = "0" ]; then
  if [ "$ec" -eq 0 ]; then
    echo "SST_VALIDATION=PASSED"
  else
    echo "SST_VALIDATION=FAILED"
  fi
fi
exit "$ec"
