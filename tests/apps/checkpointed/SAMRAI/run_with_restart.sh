#!/bin/bash
# Run SAMRAI LinAdv with automatic restart from checkpoint if available.
NPROCS=${1:-4}
INPUT="validation_inputs/linadv.2d.input"

# Find the most recent restart directory
RESTART_DIR=$(ls -td restart_linadv/restore.* 2>/dev/null | head -1)

if [ -n "$RESTART_DIR" ]; then
    RESTORE_NUM=$(basename "$RESTART_DIR" | sed 's/restore\.//' | sed 's/^0*//')
    [ -z "$RESTORE_NUM" ] && RESTORE_NUM=0
    echo "Restarting from checkpoint: $RESTART_DIR (step $RESTORE_NUM)"
    mpirun -np $NPROCS --oversubscribe ./_build/bin/linadv "$INPUT" restart_linadv $RESTORE_NUM
else
    echo "Starting fresh simulation"
    mpirun -np $NPROCS --oversubscribe ./_build/bin/linadv "$INPUT"
fi
