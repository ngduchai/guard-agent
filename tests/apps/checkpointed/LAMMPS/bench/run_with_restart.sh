#!/bin/bash
# Run LAMMPS with automatic restart from checkpoint if available.
NPROCS=${1:-4}

# Find the most recent restart file
RST=$(ls -t restart.lj.* 2>/dev/null | head -1)

if [ -n "$RST" ]; then
    echo "Restarting from checkpoint: $RST"
    # Create restart input with the specific file
    cat > /tmp/lammps_restart.in << EOFIN
read_restart    $RST

pair_style      lj/cut 2.5
pair_coeff      1 1 1.0 1.0 2.5

neighbor        0.3 bin
neigh_modify    delay 0 every 20 check no

fix             1 all nve

restart         100 restart.lj

run             2000 upto
EOFIN
    mpirun -np $NPROCS --oversubscribe ./_build/lmp -in /tmp/lammps_restart.in
else
    echo "Starting fresh simulation"
    mpirun -np $NPROCS --oversubscribe ./_build/lmp -in bench/in.lj_ckpt
fi
