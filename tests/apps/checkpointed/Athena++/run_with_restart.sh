#!/bin/bash
# Run Athena++ with automatic restart from checkpoint if available.
# This script checks for the most recent .rst file and uses it for restart.

NPROCS=${1:-4}
INPUT="inputs/hydro/athinput.linear_wave1d_ckpt"

# Find the most recent restart file
RST_FILE=$(ls -t LinWave.out3.*.rst 2>/dev/null | head -1)

if [ -n "$RST_FILE" ]; then
    echo "Restarting from checkpoint: $RST_FILE"
    mpirun -np $NPROCS --oversubscribe ./bin/athena -r "$RST_FILE"
else
    echo "Starting fresh simulation"
    mpirun -np $NPROCS --oversubscribe ./bin/athena -i "$INPUT"
fi
