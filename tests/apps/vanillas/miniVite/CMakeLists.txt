cmake_minimum_required(VERSION 3.10)
project(miniVite CXX)

find_package(MPI REQUIRED)
find_package(OpenMP REQUIRED)

add_executable(miniVite main.cpp)

target_compile_features(miniVite PRIVATE cxx_std_11)
target_compile_options(miniVite PRIVATE -O3)
target_compile_definitions(miniVite PRIVATE PRINT_DIST_STATS)
target_link_libraries(miniVite PRIVATE MPI::MPI_CXX OpenMP::OpenMP_CXX)
