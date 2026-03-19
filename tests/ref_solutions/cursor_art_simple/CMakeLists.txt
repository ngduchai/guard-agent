cmake_minimum_required(VERSION 3.10)

# Set the project name
project(art_simple_main LANGUAGES CXX)

# Find the HDF5 library
find_package(HDF5 REQUIRED)
find_package(MPI REQUIRED)

# ---- VeloC (checkpoint/restart) integration ----
# Default to the VeloC install layout observed on this machine.
set(VELOC_ROOT "" CACHE PATH "Path to VeloC installation (contains include/ and lib/)")
if(NOT VELOC_ROOT)
  message(FATAL_ERROR
    "VeloC installation not found. "
    "Pass -DVELOC_ROOT=<prefix> to cmake (e.g. -DVELOC_ROOT=/usr/local or -DVELOC_ROOT=$HOME/usr)."
  )
endif()

find_path(VELOC_INCLUDE_DIR
  NAMES veloc.h
  PATHS "${VELOC_ROOT}/include"
)

find_library(VELOC_CLIENT_LIBRARY
  NAMES veloc-client
  PATHS "${VELOC_ROOT}/lib"
)

find_library(VELOC_AXL_LIBRARY
  NAMES axl
  PATHS "${VELOC_ROOT}/lib"
)

find_library(VELOC_MODULES_LIBRARY
  NAMES veloc-modules
  PATHS "${VELOC_ROOT}/lib"
)

if (NOT VELOC_INCLUDE_DIR OR NOT VELOC_CLIENT_LIBRARY)
  message(FATAL_ERROR "Could not find VeloC. Set VELOC_ROOT to your VeloC install prefix.")
endif()

# Add an executable
add_executable(art_simple_main main.cc art_simple.cc)

# Link the HDF5 and MPI C++ libraries
target_include_directories(art_simple_main PRIVATE "${VELOC_INCLUDE_DIR}")
target_link_libraries(art_simple_main PRIVATE HDF5::HDF5 MPI::MPI_CXX
  "${VELOC_CLIENT_LIBRARY}" "${VELOC_MODULES_LIBRARY}" "${VELOC_AXL_LIBRARY}"
)

# Ensure the dynamic linker can find VeloC shared libraries at runtime.
set_target_properties(art_simple_main PROPERTIES
  BUILD_RPATH "${VELOC_ROOT}/lib"
  INSTALL_RPATH "${VELOC_ROOT}/lib"
)

# Install binary + default VeloC config.
# This enables `make install` to place `veloc.cfg` next to the executable.
include(GNUInstallDirs)

install(TARGETS art_simple_main
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/veloc.cfg"
  DESTINATION ${CMAKE_INSTALL_BINDIR}
)