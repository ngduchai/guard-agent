cmake_minimum_required(VERSION 3.10)
project(miniAMR LANGUAGES C)

# MPI support (required)
find_package(MPI REQUIRED C)

# Collect source files from ref/ subdirectory
set(SOURCES
    ref/block.c
    ref/check_sum.c
    ref/comm_block.c
    ref/comm.c
    ref/comm_parent.c
    ref/comm_refine.c
    ref/comm_util.c
    ref/driver.c
    ref/init.c
    ref/main.c
    ref/move.c
    ref/pack.c
    ref/plot.c
    ref/profile.c
    ref/rcb.c
    ref/refine.c
    ref/sfc.c
    ref/stencil.c
    ref/util.c
)

add_executable(miniAMR.x ${SOURCES})

target_include_directories(miniAMR.x PRIVATE ${CMAKE_SOURCE_DIR}/ref)
target_compile_options(miniAMR.x PRIVATE -O3)
target_link_libraries(miniAMR.x PRIVATE MPI::MPI_C m)
