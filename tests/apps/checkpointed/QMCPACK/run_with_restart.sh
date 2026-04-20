#!/bin/bash
cd examples/molecules/He

# Find the latest config.h5 file
CKPT=$(ls -t He.s*.config.h5 2>/dev/null | head -1)

if [ -n "$CKPT" ]; then
    SERIES=$(echo "$CKPT" | sed 's/He\.s\([0-9]*\)\.config\.h5/\1/' | sed 's/^0*//')
    [ -z "$SERIES" ] && SERIES=0
    echo "Restarting from checkpoint: $CKPT (series $SERIES)"
    # Create restart XML by adding mcwalkerset to the checkpoint input
    sed "/<\/simulation>/i <mcwalkerset fileroot=\"He\" node=\"-1\"/>" he_simple_opt_ckpt.xml > /tmp/qmc_restart.xml
    ../../../build/bin/qmcpack /tmp/qmc_restart.xml
else
    echo "Starting fresh simulation"
    ../../../build/bin/qmcpack he_simple_opt_ckpt.xml
fi
