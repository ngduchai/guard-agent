cmake_minimum_required(VERSION 3.10)
project(PENNANT CXX)

# ---------- Dependencies ----------
find_package(MPI REQUIRED)
find_package(OpenMP)

# ---------- Sources ----------
set(PENNANT_SOURCES
    src/main.cc
    src/Driver.cc
    src/ExportGold.cc
    src/GenMesh.cc
    src/Hydro.cc
    src/HydroBC.cc
    src/InputFile.cc
    src/Mesh.cc
    src/Parallel.cc
    src/PolyGas.cc
    src/QCS.cc
    src/TTS.cc
    src/WriteXY.cc
)

# ---------- Executable ----------
add_executable(pennant ${PENNANT_SOURCES})

target_compile_definitions(pennant PRIVATE USE_MPI)
target_compile_options(pennant PRIVATE -O3)
target_include_directories(pennant PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(pennant PRIVATE MPI::MPI_CXX)

if(OpenMP_CXX_FOUND)
    target_link_libraries(pennant PRIVATE OpenMP::OpenMP_CXX)
endif()

# ---------- Test data ----------
# Create a symlink so the executable can find test/ relative to the build dir.
add_custom_command(TARGET pennant POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E create_symlink
        ${CMAKE_CURRENT_SOURCE_DIR}/test
        ${CMAKE_CURRENT_BINARY_DIR}/test
    COMMENT "Symlinking test data into build directory"
)

# Install target (optional, for validation framework)
install(TARGETS pennant DESTINATION ${CMAKE_INSTALL_PREFIX})
install(DIRECTORY test/ DESTINATION ${CMAKE_INSTALL_PREFIX}/test)
