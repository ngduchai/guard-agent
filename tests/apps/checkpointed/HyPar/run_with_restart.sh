#!/bin/bash
NPROCS=${1:-1}
EXAMPLE="Examples/1D/FPDoubleWell"
cd "$EXAMPLE"

# Find the latest output file (op_00010.txt, op_00020.txt, etc.)
LAST_OP=$(ls -t op_*.dat 2>/dev/null | head -1)

if [ -n "$LAST_OP" ]; then
    # Extract iteration number from filename (op_00010.txt → 10000)
    OP_NUM=$(echo "$LAST_OP" | sed 's/op_//;s/\.dat//;s/^0*//')
    [ -z "$OP_NUM" ] && OP_NUM=0
    FILE_OP_ITER=$(grep 'file_op_iter' solver.inp | awk '{print $2}')
    RESTART_ITER=$((OP_NUM * FILE_OP_ITER))
    echo "Restarting from: $LAST_OP (iteration $RESTART_ITER)"
    # Copy output as initial condition
    cp "$LAST_OP" initial.inp
    # Update solver.inp with restart_iter
    sed -i "s/^end/  restart_iter      $RESTART_ITER\nend/" solver.inp
    mpirun -np $NPROCS --oversubscribe ../../../build/src/HyPar
    # Revert solver.inp
    sed -i '/restart_iter/d' solver.inp
else
    echo "Starting fresh simulation"
    mpirun -np $NPROCS --oversubscribe ../../../build/src/HyPar
fi
