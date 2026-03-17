cmake_minimum_required(VERSION 3.9)
project(matrix_mul_mpi C)

find_package(MPI REQUIRED)
find_package(veloc REQUIRED)

add_executable(matrix_mul_mpi code.c)
target_link_libraries(matrix_mul_mpi veloc-client PRIVATE MPI::MPI_C)
