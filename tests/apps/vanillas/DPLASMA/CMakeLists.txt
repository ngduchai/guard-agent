cmake_minimum_required(VERSION 3.12)
project(HPCCG LANGUAGES CXX)

# Find MPI
find_package(MPI REQUIRED CXX)

set(SOURCES
    main.cpp
    generate_matrix.cpp
    read_HPC_row.cpp
    compute_residual.cpp
    mytimer.cpp
    dump_matlab_matrix.cpp
    HPC_sparsemv.cpp
    HPCCG.cpp
    waxpby.cpp
    ddot.cpp
    make_local_matrix.cpp
    exchange_externals.cpp
    YAML_Element.cpp
    YAML_Doc.cpp
    HPC_Sparse_Matrix.cpp
)

add_executable(test_HPCCG ${SOURCES})

target_compile_definitions(test_HPCCG PRIVATE USING_MPI)
target_compile_options(test_HPCCG PRIVATE -O3)
target_link_libraries(test_HPCCG PRIVATE MPI::MPI_CXX m)
