#!/bin/bash
NPROCS=${1:-4}
cd examples/ising

DUMP=$(ls -t dump.ising.* 2>/dev/null | head -1)

if [ -n "$DUMP" ]; then
    # Extract sweep number from dump filename (e.g., dump.ising.45 → sweep 4500)
    DUMP_NUM=$(echo "$DUMP" | sed 's/dump\.ising\.//')
    # Each dump is at interval 100 sweeps, so dump number * 100 = sweep count
    SWEEP_DONE=$((DUMP_NUM * 100))
    SWEEP_REMAIN=$((5000 - SWEEP_DONE))
    [ "$SWEEP_REMAIN" -le 0 ] && SWEEP_REMAIN=100
    echo "Restarting from: $DUMP (sweep $SWEEP_DONE, remaining $SWEEP_REMAIN)"
    cat > /tmp/spparks_restart.in << EOFIN
seed         56789
app_style    ising
dimension    2
lattice      sq/4n 1.0
region       box block 0 500 0 500 -0.5 0.5
create_box   box
create_sites box
read_sites   $DUMP
sweep        random
sector       yes
diag_style   energy
temperature  1.0
stats        100.0
dump         1 sites 100.0 dump.ising.* id site
run          ${SWEEP_REMAIN}.0
EOFIN
    mpirun -np $NPROCS --oversubscribe ../../spk_mpi -in /tmp/spparks_restart.in
else
    echo "Starting fresh"
    mpirun -np $NPROCS --oversubscribe ../../spk_mpi -in in.validation
fi
