cmake_minimum_required(VERSION 3.12)
project(ResilientQuicksilver LANGUAGES NONE)

# ---------------------------------------------------------------------------
# CMake wrapper for the VeloC-resilient Quicksilver Makefile-based build.
#
# This wrapper delegates the actual compilation to the modified Makefile
# in src/ (which includes VeloC flags), then copies the resulting 'qs'
# binary into the CMake build directory.
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
    COMMENT "Building resilient Quicksilver via Makefile in ${QS_SOURCE_DIR}"
    VERBATIM
)

# ---------------------------------------------------------------------------
# Copy the built executable into the CMake build directory.
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
# Install rule
# ---------------------------------------------------------------------------
install(
    PROGRAMS "${QS_EXE_SRC}"
    DESTINATION "${CMAKE_INSTALL_BINDIR}"
)
