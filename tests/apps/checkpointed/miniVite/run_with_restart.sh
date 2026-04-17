#!/bin/bash
# Run miniVite with FTI checkpoint.
# On restart, set failure=1 in FTI config and use latest exec_id.
NPROCS=${1:-4}
FTI_CFG="config.L1.fti"

# Check if FTI checkpoint exists (local/ directory with data)
if [ -d "local" ] && [ "$(ls -A local 2>/dev/null)" ]; then
    echo "FTI checkpoint found, setting failure=1 for restart"
    # Get latest exec_id from meta directory
    EXEC_ID=$(ls -t meta/ 2>/dev/null | head -1)
    if [ -n "$EXEC_ID" ]; then
        sed -i "s/^failure.*/failure                        = 1/" "$FTI_CFG"
        sed -i "s/^exec_id.*/exec_id                        = $EXEC_ID/" "$FTI_CFG"
    fi
fi

LD_LIBRARY_PATH=$HOME/.local/lib:$LD_LIBRARY_PATH mpirun -np $NPROCS --oversubscribe ./miniVite "$FTI_CFG" -n 500000
