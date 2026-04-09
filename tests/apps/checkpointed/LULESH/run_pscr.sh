#!/bin/bash
#MSUB -l nodes=10
#MSUB -l resfailpolicy=ignore
#MSUB -l qos=normal
#MSUB -l gres=ignore
#MSUB -l walltime=00:10:00
# above, tell MOAB / SLURM to not kill job allocation upon a node failure

# add the scr commands to the job environment
. /usr/local/tools/dotkit/init.sh; use scr-1.1

export SCR_LOG_ENABLE=0
export SCR_JOB_NAME=lulesh

# specify global path where checkpoint directories should be written
#export SCR_PREFIX=/p/lscratchb/username/run1/checkpoints
export SCR_FETCH=0
export SCR_FLUSH=0

# specify the node local path for checkpoints
export SCR_CACHE_BASE=$TMP

export SCR_COPY_TYPE=LOCAL
export SCR_RUNS=3

nprocs=$1 # number of processes
export LD_LIBRARY_PATH=$HOME/local/lib:$LD_LIBRARY_PATH
time scr_srun -l -N$nprocs -n$nprocs ./luleshMPI-pscr
