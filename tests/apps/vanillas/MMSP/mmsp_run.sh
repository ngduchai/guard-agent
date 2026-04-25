#!/bin/bash
# Per-rank MMSP launcher.
#
# MMSP's run is a two-stage workflow: first invocation creates the initial
# mesh state (./parallel --example 2 test.dat); second invocation runs the
# simulation (./parallel test.dat NSTEPS OUTFREQ).  The validation framework
# does one mpirun per attempt, so this wrapper stages the initial state from
# the build tree into the per-run cwd, then invokes the simulation.
set -u
script_dir="$(cd "$(dirname "$0")" && pwd)"
SUB="examples/phase_transitions/cahn-hilliard/convex_splitting"
PARALLEL="$script_dir/$SUB/parallel"
SRC_DAT="$script_dir/$SUB/test.dat"

rank="${PMI_RANK:-${OMPI_COMM_WORLD_RANK:-${PMIX_RANK:-0}}}"

# Stage test.dat into PWD if missing (rank 0 copies; others poll-wait).
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

trap 'kill -TERM "$child" 2>/dev/null' TERM INT
"$PARALLEL" "$@" &
child=$!
wait "$child"
exit $?
