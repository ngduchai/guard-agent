#!/bin/bash
#MSUB -l nodes=8
#MSUB -l resfailpolicy=ignore
#MSUB -l qos=normal
#MSUB -l gres=ignore
#MSUB -l walltime=00:10:00
# above, tell MOAB / SLURM to not kill job allocation upon a node failure

nprocs=$1 # number of processes
export LD_LIBRARY_PATH=$HOME/local/lib:$LD_LIBRARY_PATH
time srun -l -N$nprocs -n$nprocs ./luleshMPI-perm $2 $3
