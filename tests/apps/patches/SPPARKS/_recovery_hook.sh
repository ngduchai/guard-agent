#!/usr/bin/env bash
# SPPARKS recovery hook for attempt_2.
#
# SPPARKS lacks a native `restart` command, but has the building blocks:
#   - `dump 1 sites N dump.ising.*`  (writes per-site state every N sweeps)
#   - `read_sites <file>`             (loads initial state from a dump)
#
# Pattern (modeled on tests/apps/checkpointed/SPPARKS/run_with_restart.sh):
#   1. Find latest dump.ising.<N> from attempt_1 (cwd is shared)
#   2. Compute sweeps already done = N * 100 (dump interval)
#   3. Compute remaining sweeps = 18800 - done
#   4. Write `in.recovery` with `read_sites <latest_dump>` + adjusted run
# attempt_2's mpirun then uses `-in in.recovery` (via _extra_args_recovery.txt).
set -u

TOTAL_SWEEPS=18800

# Find latest COMPLETE dump (sorted by mtime, newest first; skip if
# truncated by SIGKILL mid-write). Complete dumps for this workload are
# ~2.389 MB; a partial-write file is shorter. Use 2,300,000 bytes as a
# safe threshold (well below the ~2.389M complete size, well above any
# half-written file we've observed at ~2.14M).
MIN_COMPLETE_BYTES=2300000
LATEST=""
for f in $(ls -t dump.ising.[0-9]* 2>/dev/null); do
    SIZE=$(stat -c %s "$f" 2>/dev/null || echo 0)
    if [ "$SIZE" -ge "$MIN_COMPLETE_BYTES" ]; then
        LATEST="$f"
        break
    else
        echo "[spparks-recovery-hook] skipping incomplete dump $f (size=$SIZE < $MIN_COMPLETE_BYTES)" >&2
    fi
done

if [ -z "$LATEST" ]; then
    echo "[spparks-recovery-hook] no dump.ising.* found in cwd; attempt_2 will cold-restart" >&2
    # Write recovery input that just runs full simulation (cold-restart fallback)
    cat > in.recovery <<EOF
seed         56789
app_style    ising
dimension    2
lattice      sq/4n 1.0
region       box block 0 500 0 500 -0.5 0.5
create_box   box
create_sites box
set          site range 1 2
sweep        random
sector       yes
diag_style   energy
temperature  1.0
stats        100.0
dump 1 sites 100.0 dump.ising.* id site
run          ${TOTAL_SWEEPS}.0.0
EOF
    exit 0
fi

# Extract dump number (e.g. dump.ising.45 -> 45).
# SPPARKS dump filenames use a SEQUENCE COUNT (0, 1, 2, ...), not sim time.
# With `dump 1 sites 100.0 ...`, dump #N is at sim time N * 100.
# So sweeps done = N * dump_interval. Matches run_with_restart.sh in the repo.
DUMP_NUM=$(echo "$LATEST" | sed 's/dump\.ising\.//')
DUMP_INTERVAL=100
SWEEP_DONE=$(( DUMP_NUM * DUMP_INTERVAL ))
SWEEP_REMAIN=$(( TOTAL_SWEEPS - SWEEP_DONE ))
if [ "$SWEEP_REMAIN" -le 0 ]; then
    SWEEP_REMAIN=100
fi
echo "[spparks-recovery-hook] resuming from $LATEST (done=${SWEEP_DONE} of ${TOTAL_SWEEPS}, remaining=${SWEEP_REMAIN})"

# Build the restart input script.  `read_sites` replaces `set site range`
# (which assigns initial state).  Other commands match the original
# in.validation so app_style / sweep / dump cadence carry over.
cat > in.recovery <<EOF
seed         56789
app_style    ising
dimension    2
lattice      sq/4n 1.0
region       box block 0 500 0 500 -0.5 0.5
create_box   box
create_sites box
read_sites   ${LATEST}
sweep        random
sector       yes
diag_style   energy
temperature  1.0
stats        100.0
dump 1 sites 100.0 dump.ising.* id site
run          ${SWEEP_REMAIN}.0.0
EOF

echo "[spparks-recovery-hook] wrote in.recovery (SWEEP_REMAIN=${SWEEP_REMAIN})"
