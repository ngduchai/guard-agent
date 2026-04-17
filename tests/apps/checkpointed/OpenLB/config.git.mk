# OpenLB build configuration
#
# This file sets up the necessary build flags for compiling OpenLB with
# the GNU C++ compiler and sequential execution. For more complex setups
# edit this file or consult the example configs provided in `config/`.
#
# Basic usage:
#  - Edit variables to fit desired configuration
#  - Run `make clean; make` to clean up any previous artifacts and compile the dependencies
#  - Switch to example directory, e.g. `examples/laminar/poiseuille2d`
#  - Run `make`
#  - Start the simulation using `./poiseuille2d`

# Compiler to use for C++ files, change to `mpic++` when using OpenMPI and GCC
CXX             := g++
# Compiler to use for C files (used for emebedded dependencies)
CC              := gcc

# Suggested optimized build flags for GCC, consult `config/` for further examples
CXXFLAGS        := -O3 -Wall -march=native -mtune=native
# Uncomment to add debug symbols and enable runtime asserts
#CXXFLAGS        += -g -DOLB_DEBUG

# OpenLB requires support for C++20
# works in:
#  * gcc 12 or later     (https://gcc.gnu.org/projects/cxx-status.html#cxx20)
#  * clang 19 or later   (https://clang.llvm.org/cxx_status.html#cxx20)
#  * icx 2024.0 or later (https://www.intel.com/content/www/us/en/developer/articles/technical/c20-features-supported-by-intel-cpp-compiler.html)
CXXFLAGS        += -std=c++20

# optional linker flags
LDFLAGS         :=

# Parallelization mode, must be one of: OFF, MPI, OMP, HYBRID
# Note that for MPI and HYBRID the compiler also needs to be adapted.
# See e.g. `config/cpu_gcc_openmpi.mk`
PARALLEL_MODE   := OFF

# optional MPI and OpenMP flags
MPIFLAGS        :=
OMPFLAGS        := -fopenmp

# Options: CPU_SISD, CPU_SIMD, GPU_CUDA
# Both CPU_SIMD and GPU_CUDA require system-specific adjustment of compiler flags.
# See e.g. `config/cpu_simd_intel_mpi.mk` or `config/gpu_only.mk` for examples.
# CPU_SISD must always be present.
PLATFORMS       := CPU_SISD

# Fundamental arithmetic data type
# Common options are float or double
FLOATING_POINT_TYPE := double

# Any entries are passed to the compiler as `-DFEATURE_*` declarations
# Used to enable some alternative code paths and dependencies
FEATURES        :=

# Set to OFF if libz and tinyxml2 are provided by the system (optional)
USE_EMBEDDED_DEPENDENCIES := ON