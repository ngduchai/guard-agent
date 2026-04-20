#!/bin/bash
NPROCS=${1:-1}
INPUT="inputs/hydro/athinput.blast_ckpt"

RST_FILE=$(ls -t *.rst 2>/dev/null | grep -v 'final' | head -1)

if [ -n "$RST_FILE" ]; then
    echo "Restarting from checkpoint: $RST_FILE"
    ./bin/athena -r "$RST_FILE"
else
    echo "Starting fresh simulation"
    ./bin/athena -i "$INPUT"
fi
