# Example build config for OpenLB using mixed compilation of CUDA with OpenMPI
#
# Adapted for Nvidia HPC SDK 25.3 on the HoreKa supercomputer at KIT
#
# Usage:
#  - Copy this file to OpenLB root as `config.mk`
#  - Load Nvidia HPC toolkit via `module add toolkit/nvidia-hpc-sdk/25.3`
#  - Load CUDA toolkit via `module add devel/cuda/12.4`
#  - Run `make clean; make`
#  - Switch to example directory, e.g. `examples/turbulence/nozzle3d`
#  - Run `make`
#  - Use `mpirun --map-by ppr:2:socket:pe=19 --bind-to core bash -c 'export CUDA_VISIBLE_DEVICES=${OMPI_COMM_WORLD_LOCAL_RANK}; ./nozzle3d' for launch
#  - See example SLURM config script in examples/laminer/cavity3dBenchmark

CXX             := mpicxx
CC              := gcc

CXXFLAGS        := -O3 -Wall -march=native -mtune=native 
CXXFLAGS        += -std=c++20
LDFLAGS += -L/hkfs/home/software/all/toolkit/nvidia_hpc_sdk/25.3/Linux_x86_64/25.3/cuda/12.8/targets/x86_64-linux/lib/stubs/

PARALLEL_MODE   := MPI

PLATFORMS       := CPU_SISD GPU_CUDA

CUDA_CXX        := nvcc
CUDA_CXXFLAGS   := -O3 -std=c++20 -I/hkfs/home/software/all/toolkit/nvidia_hpc_sdk/25.3/Linux_x86_64/25.3/comm_libs/12.8/hpcx/hpcx-2.22.1/ompi/include

CUDA_ARCH       := 80

FLOATING_POINT_TYPE := float

USE_EMBEDDED_DEPENDENCIES := ON
