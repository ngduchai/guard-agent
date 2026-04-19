#!/bin/bash
# Run SPARTA with automatic restart from checkpoint if available.
NPROCS=${1:-4}
cd examples/free

# Find the most recent restart file (for rank 0)
RST=$(ls -t restart.sparta.*.0 2>/dev/null | head -1)

if [ -n "$RST" ]; then
    # Extract base name (e.g., restart.sparta.4000)
    BASE=$(echo "$RST" | sed 's/\.[0-9]*$//')
    echo "Restarting from checkpoint: $BASE"
    cat > /tmp/sparta_restart.in << EOFIN
read_restart    ${BASE}.*
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
