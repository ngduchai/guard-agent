#!/bin/bash
NPROCS=${1:-4}
cd examples/ising

DUMP=$(ls -t dump.ising.* 2>/dev/null | head -1)

if [ -n "$DUMP" ]; then
    echo "Restarting from: $DUMP"
    sed "s|RESTART_FILE|$DUMP|" in.restart > /tmp/spparks_restart.in
    mpirun -np $NPROCS --oversubscribe ../../spk_mpi -in /tmp/spparks_restart.in
else
    echo "Starting fresh"
    mpirun -np $NPROCS --oversubscribe ../../spk_mpi -in in.validation
fi
