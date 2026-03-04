cmake_minimum_required(VERSION 3.10)
project(matrix_mul_mpi)

find_package(MPI REQUIRED)

include_directories(${MPI_INCLUDE_DIRS})

set(SOURCES code.c)

add_executable(matrix_mul_mpi ${SOURCES})
target_link_libraries(matrix_mul_mpi ${MPI_LIBRARIES} veloc)
