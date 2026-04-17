# Example build config for OpenLB using Intel C++ and MPI on HoreKa
#
# module load compiler/intel/2025.1_llvm
# module load mpi/impi/2021.11

CXX             := mpicxx
CC              := icx

CXXFLAGS        := -O3 -Wall -std=c++20

PARALLEL_MODE   := MPI

PLATFORMS       := CPU_SISD

USE_EMBEDDED_DEPENDENCIES := ON
