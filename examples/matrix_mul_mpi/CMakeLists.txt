cmake_minimum_required(VERSION 3.16)
project(matrix_mul_mpi C)

find_package(MPI REQUIRED)

add_executable(matrix_mul_mpi code.c)
target_link_libraries(matrix_mul_mpi PRIVATE MPI::MPI_C)

