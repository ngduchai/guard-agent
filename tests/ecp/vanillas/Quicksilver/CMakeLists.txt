cmake_minimum_required(VERSION 3.12)
project(Quicksilver LANGUAGES NONE)

# ---------------------------------------------------------------------------
# CMake wrapper for the Quicksilver Makefile-based build system.
#
# The validation framework (validation/veloc/runner.py) calls:
#   cmake -S <source_dir> -B <build_dir>
#   cmake --build <build_dir>
#   cmake --install <build_dir> --prefix <build_dir>   (optional)
#
# This wrapper delegates the actual compilation to the Makefile in src/,
# then copies the resulting 'qs' binary into the build directory so that
# runner.py's _find_executable() can locate it.
# ---------------------------------------------------------------------------

include(GNUInstallDirs)

# Resolve the source directory (where this CMakeLists.txt lives).
set(QS_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src")

# The Makefile builds the executable in src/ as 'qs'.
set(QS_EXE_SRC "${QS_SOURCE_DIR}/qs")

# ---------------------------------------------------------------------------
# Custom target: invoke make in src/
# ---------------------------------------------------------------------------
add_custom_target(quicksilver_make ALL
    COMMAND ${CMAKE_MAKE_PROGRAM}
    WORKING_DIRECTORY "${QS_SOURCE_DIR}"
    COMMENT "Building Quicksilver via Makefile in ${QS_SOURCE_DIR}"
    VERBATIM
)

# ---------------------------------------------------------------------------
# Copy the built executable into the CMake build directory so that
# runner.py's _find_executable() can locate it by walking the build tree.
# ---------------------------------------------------------------------------
add_custom_command(
    TARGET quicksilver_make POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${QS_EXE_SRC}"
        "${CMAKE_BINARY_DIR}/qs"
    COMMENT "Copying qs → ${CMAKE_BINARY_DIR}/qs"
    VERBATIM
)

# ---------------------------------------------------------------------------
# Install rule: copy 'qs' to the install prefix bin directory.
# Used when --install-resilient is NOT set (original codebase).
# ---------------------------------------------------------------------------
install(
    PROGRAMS "${QS_EXE_SRC}"
    DESTINATION "${CMAKE_INSTALL_BINDIR}"
)
