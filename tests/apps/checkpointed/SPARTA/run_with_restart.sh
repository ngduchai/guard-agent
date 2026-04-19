#!/bin/bash
NPROCS=${1:-4}
cd examples/free

# Find the most recent restart file (single file, not per-rank)
RST=$(ls -t restart.sparta.* 2>/dev/null | head -1)

if [ -n "$RST" ]; then
    echo "Restarting from checkpoint: $RST"
    cat > /tmp/sparta_restart.in << EOFIN
seed            56789
read_restart    $RST
stats           5000
compute         temp temp
stats_style     step cpu np nattempt ncoll c_temp
restart         2000 restart.sparta
timestep        7.00E-9
run             20000 upto
EOFIN
    mpirun -np $NPROCS --oversubscribe ./spa_mpi -in /tmp/sparta_restart.in
else
    echo "Starting fresh simulation"
    mpirun -np $NPROCS --oversubscribe ./spa_mpi -in in.validation
fi
