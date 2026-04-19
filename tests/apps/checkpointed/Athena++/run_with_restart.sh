#!/bin/bash
NPROCS=${1:-4}
INPUT="inputs/hydro/athinput.blast_ckpt"

RST_FILE=$(ls -t Blast.out3.*.rst 2>/dev/null | head -1)

if [ -n "$RST_FILE" ]; then
    echo "Restarting from checkpoint: $RST_FILE"
    mpirun -np $NPROCS --oversubscribe ./bin/athena -r "$RST_FILE"
else
    echo "Starting fresh simulation"
    mpirun -np $NPROCS --oversubscribe ./bin/athena -i "$INPUT"
fi
