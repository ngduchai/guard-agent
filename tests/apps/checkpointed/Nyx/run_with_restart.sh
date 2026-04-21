#!/bin/bash
EXE="./_build/Exec/HydroTests/nyx_HydroTests"
INPUT="Exec/HydroTests/inputs.validation"

# Find latest checkpoint directory
CKPT=$(ls -td chk????? 2>/dev/null | head -1)

if [ -n "$CKPT" ]; then
    echo "Restarting from checkpoint: $CKPT"
    $EXE $INPUT amr.restart=$CKPT
else
    echo "Starting fresh simulation"
    $EXE $INPUT
fi
