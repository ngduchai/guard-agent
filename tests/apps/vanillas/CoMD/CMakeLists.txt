cmake_minimum_required(VERSION 3.10)
project(CoMD LANGUAGES C)

# MPI support (required)
find_package(MPI REQUIRED C)

# Collect source files from src-mpi/
set(SOURCES
    src-mpi/CoMD.c
    src-mpi/cmdLineParser.c
    src-mpi/decomposition.c
    src-mpi/eam.c
    src-mpi/haloExchange.c
    src-mpi/initAtoms.c
    src-mpi/linkCells.c
    src-mpi/ljForce.c
    src-mpi/mycommand.c
    src-mpi/parallel.c
    src-mpi/performanceTimers.c
    src-mpi/random.c
    src-mpi/timestep.c
    src-mpi/yamlOutput.c
)

# Generate CoMD_info.h at build time (mimics generate_info_header script).
# Generate into the build directory to avoid writing to the source tree.
set(COMD_VARIANT "CoMD-mpi")
add_custom_command(
    OUTPUT ${CMAKE_BINARY_DIR}/CoMD_info.h
    COMMAND bash ${CMAKE_SOURCE_DIR}/src-mpi/generate_info_header
            ${COMD_VARIANT}
            "${CMAKE_C_COMPILER}"
            "${CMAKE_C_FLAGS}"
            "${CMAKE_EXE_LINKER_FLAGS}"
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
    COMMENT "Generating CoMD_info.h"
)
add_custom_target(comd_info_header DEPENDS ${CMAKE_BINARY_DIR}/CoMD_info.h)

add_executable(CoMD-mpi ${SOURCES})
add_dependencies(CoMD-mpi comd_info_header)

# Include build dir first (for generated CoMD_info.h), then source dir for other headers
target_include_directories(CoMD-mpi PRIVATE ${CMAKE_BINARY_DIR} ${CMAKE_SOURCE_DIR}/src-mpi)
target_compile_options(CoMD-mpi PRIVATE -std=c99 -g -O3)
target_compile_definitions(CoMD-mpi PRIVATE DO_MPI DOUBLE)
target_link_libraries(CoMD-mpi PRIVATE MPI::MPI_C m)

# Copy pots directory to build dir so potential files are found at runtime
file(COPY ${CMAKE_SOURCE_DIR}/pots DESTINATION ${CMAKE_BINARY_DIR})
