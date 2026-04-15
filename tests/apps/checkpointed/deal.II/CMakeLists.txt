cmake_minimum_required(VERSION 3.12)
project(XSBench LANGUAGES C)

# Find MPI (required)
find_package(MPI REQUIRED C)

# Find OpenMP
find_package(OpenMP REQUIRED C)

# Find HDF5 (required for output file comparison)
set(HDF5_PREFER_PARALLEL FALSE)
find_package(HDF5 REQUIRED COMPONENTS C)

# Source files from openmp-threading subdirectory
set(SOURCES
    openmp-threading/Main.c
    openmp-threading/io.c
    openmp-threading/Simulation.c
    openmp-threading/GridInit.c
    openmp-threading/XSutils.c
    openmp-threading/Materials.c
)

add_executable(XSBench ${SOURCES})

# Include the header directory
target_include_directories(XSBench PRIVATE ${CMAKE_SOURCE_DIR}/openmp-threading)

# Compile definitions
target_compile_definitions(XSBench PRIVATE MPI OPENMP)

# Compile options
target_compile_options(XSBench PRIVATE -std=gnu99 -Wall -O3)

# Link libraries
target_link_libraries(XSBench PRIVATE
    MPI::MPI_C
    OpenMP::OpenMP_C
    ${HDF5_C_LIBRARIES}
    m
)

# HDF5 include directories
target_include_directories(XSBench PRIVATE ${HDF5_C_INCLUDE_DIRS})

# Install the binary
install(TARGETS XSBench RUNTIME DESTINATION .)
