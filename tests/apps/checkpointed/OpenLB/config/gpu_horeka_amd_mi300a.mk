# Example build config for OpenLB using HIP/ROCm for AMD MI300A on HoreKa
#
# Usage:
#  - Copy this file to OpenLB root as `config.mk`
#  - Load modules
#      module purge
#      module use /software/easybuild/modules/all/
#      module load rocm-smi/7.6.0-GCCcore-14.2.0-ROCm-6.4.1  
#  - Run `make clean; make`
#  - Switch to example directory, e.g. `examples/turbulence/nozzle3d`
#  - Run `make`
#  - Launch `./nozzle3d`

#
CXX             := hipcc
CC              := hipcc

CXXFLAGS        := -O3
CXXFLAGS        += -std=c++20

PARALLEL_MODE   := NONE

HIP_PLATFORM	:= amd  
PLATFORMS       := CPU_SISD GPU_HIP

HIP_ARCH	:= gfx942

FLOATING_POINT_TYPE := float

USE_EMBEDDED_DEPENDENCIES := ON
