#!/bin/bash
INPUT="test_input/inputs_validation"
EXE=$(ls _build/bin/warpx* 2>/dev/null | head -1)
[ -z "$EXE" ] && echo "ERROR: WarpX not found" && exit 1

# Find latest checkpoint directory (diags/chkpointNNNNNN)
CKPT=$(ls -td diags/chkpoint?????? 2>/dev/null | head -1)

if [ -n "$CKPT" ]; then
    echo "Restarting from checkpoint: $CKPT"
    $EXE $INPUT amr.restart=$CKPT
else
    echo "Starting fresh simulation"
    $EXE $INPUT
fi
