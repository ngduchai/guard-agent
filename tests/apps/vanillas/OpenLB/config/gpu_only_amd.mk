# Example build config for OpenLB using ROCm on single GPU systems
#
# Tested using:
#  - ROCm runtime version 1.18
#  - GPU: AMD RX 7800 XT
#  - OS: CachyOS (Based on Arch Linux)
#
# Dependencies:
#  - Refer to the ROCm documentation for information on how to install and configure ROCm for your system
#
# Usage:
#  - Copy this file to OpenLB root as `config.mk`
#  - Run `make clean; make`
#  - Switch to example directory, e.g. `examples/laminar/cavity3dBenchmark`
#  - Run `make`
#  - Start the simulation using `./cavity3d`

CXX             := hipcc
CC              := hipcc

CXXFLAGS        := -O3
CXXFLAGS        += -std=c++20

PARALLEL_MODE   := NONE

HIP_PLATFORM	:= amd  

PLATFORMS       := CPU_SISD GPU_HIP

# HIP_ARCH=native automatically find your amd gpu
HIP_ARCH		:= gfx942


FLOATING_POINT_TYPE := float

USE_EMBEDDED_DEPENDENCIES := ON
