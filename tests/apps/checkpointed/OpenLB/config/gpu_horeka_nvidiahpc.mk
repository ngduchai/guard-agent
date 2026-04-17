# Example build config for OpenLB using mixed compilation of CUDA with OpenMPI
#
# Adapted for Nvidia HPC SDK 22.3 on the HoreKa supercomputer at KIT
#
# Usage:
#  - Copy this file to OpenLB root as `config.mk`
#  - Load Nvidia HPC toolkit via `module load toolkit/nvidia-hpc-sdk/25.3`
#  - Run `make clean; make`
#  - Switch to example directory, e.g. `examples/turbulence/nozzle3d`
#  - Run `make`
#  - Use `mpirun --map-by ppr:2:socket:pe=19 --bind-to core bash -c 'export CUDA_VISIBLE_DEVICES=${OMPI_COMM_WORLD_LOCAL_RANK}; ./nozzle3d' for launch
#  - See example SLURM config script in examples/laminer/cavity3dBenchmark
CXX             := nvcc
CC              := nvcc
CXXFLAGS        := -O3  -std=c++20 -march=native -mtune=native
CXXFLAGS        += -I/hkfs/home/software/all/toolkit/nvidia_hpc_sdk/25.3/Linux_x86_64/25.3/comm_libs/12.8/hpcx/hpcx-2.22.1/ompi/include
LDFLAGS         := -L/hkfs/home/software/all/toolkit/nvidia_hpc_sdk/25.3/Linux_x86_64/25.3/comm_libs/12.8/hpcx/hpcx-2.22.1/ompi/lib

PARALLEL_MODE   := MPI
MPIFLAGS        := -lmpi
PLATFORMS       := CPU_SISD GPU_CUDA
CUDA_ARCH       := 90
