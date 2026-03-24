cmake_minimum_required(VERSION 3.10)

project(ExaMiniMD LANGUAGES CXX)

# ---- C++ standard -----------------------------------------------------------
# Kokkos 3.x+ requires C++17; C++14 is the minimum for Kokkos 2.x.
# Setting it here ensures the standard is propagated to all targets.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ---- Default build type -----------------------------------------------------
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
  message(STATUS "No build type specified; defaulting to Release")
endif()

include(GNUInstallDirs)

# ---- Kokkos -----------------------------------------------------------------
# Search common user-local and system install locations automatically.
# Users can override with -DCMAKE_PREFIX_PATH=<kokkos-install-dir>.
list(APPEND CMAKE_PREFIX_PATH
  "$ENV{HOME}/.local"
  "/usr/local"
  "/opt/kokkos"
)

find_package(Kokkos 3.0 REQUIRED)

# ---- MPI (optional) ---------------------------------------------------------
option(USE_MPI "Build with MPI support" ON)

if(USE_MPI)
  find_package(MPI REQUIRED CXX)
else()
  # When building without MPI, check if CUDA backend is active
  kokkos_check(DEVICES Cuda RETURN_VALUE USE_CUDA)
  if(USE_CUDA)
    if(CMAKE_CXX_COMPILER_ID MATCHES "nvcc")
      enable_language(CUDA)
    else()
      message(FATAL_ERROR "Kokkos uses CUDA but compiler is not nvcc")
    endif()
  endif()
endif()

# ---- VeloC (optional) -------------------------------------------------------
option(USE_VELOC "Build with VeloC checkpoint/restart support" ON)

if(USE_VELOC)
  set(VELOC_DIR "/home/ndhai/usr" CACHE PATH "VeloC installation directory")
  if(EXISTS "${VELOC_DIR}/include/veloc.h")
    message(STATUS "VeloC found at ${VELOC_DIR}")
  else()
    message(FATAL_ERROR "VeloC not found at ${VELOC_DIR}/include/veloc.h. Set -DVELOC_DIR=<path>")
  endif()
endif()

# ---- CMake policy -----------------------------------------------------------
# force target_sources to resolve relative paths immediately
if(POLICY CMP0076)
  cmake_policy(SET CMP0076 NEW)
endif()

# ---- Subdirectories ---------------------------------------------------------
add_subdirectory(src)
add_subdirectory(input)
