#!/bin/bash
# Run Smilei with automatic restart from checkpoint if available.
NPROCS=${1:-4}

# Check if checkpoint dump files exist
DUMP=$(ls -t checkpoints/dump-*-0000000000.h5 2>/dev/null | head -1)

if [ -n "$DUMP" ]; then
    echo "Restarting from checkpoint directory: checkpoints/"
    mpirun -np $NPROCS --oversubscribe ./smilei namelist_minimal.py "Checkpoints.restart_dir='.'"
else
    echo "Starting fresh simulation"
    mpirun -np $NPROCS --oversubscribe ./smilei namelist_minimal.py
fi
