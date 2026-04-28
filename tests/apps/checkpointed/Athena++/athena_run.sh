#!/bin/bash
# Per-rank Athena++ launcher — invoked by mpirun once per rank.
# Uses the AMR-enabled checkpointed input file (athinput.blast_ckpt) which
# has output3 file_type=rst enabled.  On the first attempt no .rst exists so
# we run with -i; on subsequent attempts (kill+restart) the latest .rst is
# picked up and we run with -r so Athena++ resumes from that checkpoint.
# All ranks see the same shared cwd (cwd-share fix in runner.py), so .rst
# files written by rank 0 are visible to every restart attempt.
set -u
script_dir="$(cd "$(dirname "$0")" && pwd)"
ATHENA="$script_dir/bin/athena"
INPUT="$script_dir/inputs/hydro/athinput.blast_ckpt"

# Don't use `exec` — the failure injector locates ranks by their argv[0]
# (athena_run.sh), so the wrapper process must stay alive as the parent of
# athena.  Forward SIGTERM/SIGINT to the child so the kill propagates.
trap 'kill -TERM "$child" 2>/dev/null' TERM INT
rst=$(ls -t Blast.*.rst 2>/dev/null | grep -v final | head -1)
if [ -n "$rst" ]; then
  "$ATHENA" -r "$rst" &
else
  "$ATHENA" -i "$INPUT" &
fi
child=$!
wait "$child"
exit $?
