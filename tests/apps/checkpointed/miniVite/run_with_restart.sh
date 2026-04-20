#!/bin/bash
NPROCS=${1:-4}

# Check if checkpoint files exist
if ls miniVite_ckpt_*.bin 1>/dev/null 2>&1; then
    echo "Checkpoint files found, restarting..."
    mpirun -np $NPROCS --oversubscribe ./miniVite -n 500000
else
    echo "Starting fresh simulation"
    mpirun -np $NPROCS --oversubscribe ./miniVite -n 500000
fi
