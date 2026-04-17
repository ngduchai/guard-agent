#!/bin/bash
# Run WarpX with automatic restart from checkpoint if available.
NPROCS=${1:-1}
INPUT="test_input/inputs_validation"
EXE=$(ls _build/bin/warpx* 2>/dev/null | head -1)

if [ -z "$EXE" ]; then
    echo "ERROR: WarpX executable not found in _build/bin/"
    exit 1
fi

# Find the most recent checkpoint directory
CKPT=$(ls -td chk????? 2>/dev/null | head -1)

if [ -n "$CKPT" ]; then
    echo "Restarting from checkpoint: $CKPT"
    mpirun -np $NPROCS --oversubscribe $EXE $INPUT amr.restart=$CKPT
else
    echo "Starting fresh simulation"
    mpirun -np $NPROCS --oversubscribe $EXE $INPUT
fi
