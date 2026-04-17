#!/bin/bash

NCORES=${SLURM_CPUS_ON_NODE:-4}

module purge
module load compiler/intel/2024.0_llvm
icpx -v

cp config/cpu_horeka_intel.mk config.mk

# Removal of possible leftovers since we use the shell executor and I don't trust the gitlab-runner's cleanup
make clean-all

echo "Running make with $NCORES cores."

make -j$NCORES && \
make -j$NCORES samples FEATURES=CIPIPELINE
