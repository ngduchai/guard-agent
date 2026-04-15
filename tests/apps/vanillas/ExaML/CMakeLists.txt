cmake_minimum_required(VERSION 3.10)
project(XSBench LANGUAGES C)

# MPI support (needed for consistent single-rank output under mpirun)
find_package(MPI REQUIRED C)

# OpenMP support
find_package(OpenMP)

set(SOURCES
    openmp-threading/Main.c
    openmp-threading/io.c
    openmp-threading/Simulation.c
    openmp-threading/GridInit.c
    openmp-threading/XSutils.c
    openmp-threading/Materials.c
)

add_executable(XSBench ${SOURCES})

target_include_directories(XSBench PRIVATE ${CMAKE_SOURCE_DIR}/openmp-threading)
target_compile_options(XSBench PRIVATE -std=gnu99 -Wall -O3)
target_compile_definitions(XSBench PRIVATE MPI)
target_link_libraries(XSBench PRIVATE MPI::MPI_C m)

if(OpenMP_C_FOUND)
    target_compile_definitions(XSBench PRIVATE OPENMP)
    target_link_libraries(XSBench PRIVATE OpenMP::OpenMP_C)
endif()
