cmake_minimum_required(VERSION 3.10)
project(HPCCG LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(GNUInstallDirs)

find_package(MPI REQUIRED)

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
)

add_executable(test_HPCCG ${SOURCES})

target_compile_definitions(test_HPCCG PRIVATE USING_MPI)
target_link_libraries(test_HPCCG PRIVATE MPI::MPI_CXX)

install(TARGETS test_HPCCG DESTINATION ${CMAKE_INSTALL_BINDIR})
