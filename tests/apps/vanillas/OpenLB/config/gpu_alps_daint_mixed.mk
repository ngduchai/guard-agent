# Example build config for OpenLB using mixed compilation of CUDA with MPICH
#
# Adapted for the Alps (vCluster Daint) supercomputer at CSCS
#
# uenv image pull prgenv-gnu/24.11:v2
# uenv start --view=default prgenv-gnu/24.11:v2
#
# Update include and linker paths to your local env (probably there is a better option but this works)

CXX             := mpic++
CC              := gcc

CXXFLAGS        := -O3 -Wall -march=native -mtune=native
CXXFLAGS        += -std=c++20 -I/user-environment/env/._default/vprq3bul6vss4mqijq4366vmfpecqpyd/include

PARALLEL_MODE   := MPI

PLATFORMS       := CPU_SISD GPU_CUDA

CUDA_CXX        := nvcc
CUDA_CXXFLAGS   := -O3 -std=c++20 -I/user-environment/env/._default/vprq3bul6vss4mqijq4366vmfpecqpyd/include/

CUDA_LDFLAGS += -L/user-environment/env/._default/vprq3bul6vss4mqijq4366vmfpecqpyd/lib64
CUDA_LDFLAGS += -L/user-environment/env/._default/vprq3bul6vss4mqijq4366vmfpecqpyd/lib64/stubs

CUDA_ARCH       := 90

FLOATING_POINT_TYPE := float

USE_EMBEDDED_DEPENDENCIES := ON

##!/bin/bash
##SBATCH --job-name=test
##SBATCH --nodes=1
##SBATCH --ntasks-per-node=4
##SBATCH --gpus-per-task=1
#
#export MPICH_GPU_SUPPORT_ENABLED=1
#export OLB_NUM_THREADS=4
#export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:.
#
#srun ./cavity3d --size 1150 --steps 1000
