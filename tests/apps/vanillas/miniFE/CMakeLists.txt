cmake_minimum_required(VERSION 3.10)
project(miniFE LANGUAGES CXX)

# MPI support (required)
find_package(MPI REQUIRED CXX)

# Source files
set(SOURCES
    src/main.cpp
    src/YAML_Doc.cpp
    src/YAML_Element.cpp
    utils/BoxPartition.cpp
    utils/param_utils.cpp
    utils/utils.cpp
    utils/mytimer.cpp
)

# Generate miniFE_info.hpp at build time (mimics generate_info_header script)
# Ensure CXX_FLAGS is non-empty so CMake does not drop the argument.
if(CMAKE_CXX_FLAGS)
    set(_MINIFE_CXX_FLAGS "${CMAKE_CXX_FLAGS}")
else()
    set(_MINIFE_CXX_FLAGS "none")
endif()
add_custom_command(
    OUTPUT ${CMAKE_BINARY_DIR}/miniFE_info.hpp
    COMMAND bash ${CMAKE_SOURCE_DIR}/src/generate_info_header
            "${CMAKE_CXX_COMPILER}"
            "${_MINIFE_CXX_FLAGS}"
            "miniFE"
            "MINIFE"
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
    COMMENT "Generating miniFE_info.hpp"
)
add_custom_target(minife_info_header DEPENDS ${CMAKE_BINARY_DIR}/miniFE_info.hpp)

add_executable(miniFE.x ${SOURCES})
add_dependencies(miniFE.x minife_info_header)

target_include_directories(miniFE.x PRIVATE
    ${CMAKE_BINARY_DIR}
    ${CMAKE_SOURCE_DIR}/src
    ${CMAKE_SOURCE_DIR}/utils
    ${CMAKE_SOURCE_DIR}/fem
)

target_compile_options(miniFE.x PRIVATE -O3 -g)
target_compile_definitions(miniFE.x PRIVATE
    HAVE_MPI
    MPICH_IGNORE_CXX_SEEK
    MINIFE_REPORT_RUSAGE
    MINIFE_SCALAR=double
    MINIFE_LOCAL_ORDINAL=int
    MINIFE_GLOBAL_ORDINAL=int
    MINIFE_CSR_MATRIX
)

target_link_libraries(miniFE.x PRIVATE MPI::MPI_CXX)
