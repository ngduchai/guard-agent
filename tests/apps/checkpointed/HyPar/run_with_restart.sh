#!/bin/bash
NPROCS=${1:-1}
EXAMPLE="Examples/1D/FPDoubleWell"
cd "$EXAMPLE"

# Find the latest output file (op_00010.txt, op_00020.txt, etc.)
LAST_OP=$(ls -t op_*.txt 2>/dev/null | head -1)

if [ -n "$LAST_OP" ]; then
    # Extract iteration number from filename (op_00010.txt → 10000)
    OP_NUM=$(echo "$LAST_OP" | sed 's/op_//;s/\.txt//;s/^0*//')
    RESTART_ITER=$((OP_NUM * 1000))
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
