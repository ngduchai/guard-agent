#!/bin/bash
# Run SW4lite with automatic restart from checkpoint if available.
NPROCS=${1:-4}
INPUT="tests/validation_test.in"

# Find most recent checkpoint file
CKPT=$(ls -t restart.cycle=*.sw4checkpoint 2>/dev/null | head -1)

if [ -n "$CKPT" ]; then
    echo "Restarting from checkpoint: $CKPT"
    # Create temporary input file with restart line
    cp "$INPUT" /tmp/sw4lite_restart.in
    echo "restart file=$CKPT" >> /tmp/sw4lite_restart.in
    mpirun -np $NPROCS --oversubscribe ./optimize/sw4lite /tmp/sw4lite_restart.in
else
    echo "Starting fresh simulation"
    mpirun -np $NPROCS --oversubscribe ./optimize/sw4lite "$INPUT"
fi
