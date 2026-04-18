#!/bin/bash
# Run Smilei with automatic restart from checkpoint if available.
NPROCS=${1:-4}

# Find the most recent dump file
DUMP=$(ls -t dump-*-0000.h5 2>/dev/null | head -1)

if [ -n "$DUMP" ]; then
    DUMP_NUM=$(echo "$DUMP" | sed 's/dump-\([0-9]*\)-.*/\1/')
    echo "Restarting from checkpoint: $DUMP (dump #$DUMP_NUM)"
    mpirun -np $NPROCS --oversubscribe ./smilei namelist.py "Checkpoints.restart_dir='.'"
else
    echo "Starting fresh simulation"
    mpirun -np $NPROCS --oversubscribe ./smilei namelist.py
fi
