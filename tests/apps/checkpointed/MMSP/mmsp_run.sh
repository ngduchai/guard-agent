#!/bin/bash
# Per-rank MMSP launcher (checkpointed variant).
#
# Identical to the vanilla wrapper for stage-in (rank 0 copies the initial
# test.dat from build_dir into per-run cwd), but additionally detects the
# latest test.NNNN.dat output from a prior killed attempt and uses it as
# the input file so the simulation resumes from that checkpoint.
#
# All attempts of one resilient run share the same cwd (cwd-share fix in
# runner.py), so test.NNNN.dat written by attempt 1 is visible to attempt 2.
set -u
script_dir="$(cd "$(dirname "$0")" && pwd)"
SUB="examples/phase_transitions/cahn-hilliard/convex_splitting"
PARALLEL="$script_dir/$SUB/parallel"
SRC_DAT="$script_dir/$SUB/test.dat"

rank="${PMI_RANK:-${OMPI_COMM_WORLD_RANK:-${PMIX_RANK:-0}}}"

if [ ! -f test.dat ] && [ -f "$SRC_DAT" ]; then
  if [ "$rank" = "0" ]; then
    cp "$SRC_DAT" test.dat
  else
    for i in $(seq 1 60); do
      [ -f test.dat ] && break
      sleep 0.5
    done
  fi
fi
[ -f test.dat ] || { echo "test.dat staging failed"; exit 1; }

# Restart detection: pick the latest periodic output file (test.NNNN.dat)
# left behind by a prior killed attempt and use it as the input file.
LATEST=$(ls -t test.[0-9]*.dat 2>/dev/null | head -1)
trap 'kill -TERM "$child" 2>/dev/null' TERM INT
if [ -n "$LATEST" ]; then
  shift  # drop the "test.dat" positional; replace with LATEST
  "$PARALLEL" "$LATEST" "$@" &
else
  "$PARALLEL" "$@" &
fi
child=$!
wait "$child"
exit $?
