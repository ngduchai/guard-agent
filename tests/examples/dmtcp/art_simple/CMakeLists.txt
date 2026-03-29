cmake_minimum_required(VERSION 3.10)

# DMTCP/MANA variant of art_simple.
# Same source code as the original; only the build system differs.
#
# Build modes (choose ONE):
#
#   1. MANA mode (recommended for MANA checkpoint/restart):
#      cmake -DDMTCP_USE_MANA_STUB=ON -DMANA_ROOT=/path/to/mana ..
#      Links against libmpistub.so (MANA's MPI stub library).
#      The app uses MPI headers from the system MPI for compilation,
#      but at link time uses MANA's stub.  At runtime, MANA's lower-half
#      provides the real MPI implementation.
#
#   2. Static MPI mode (for plain DMTCP without MANA):
#      cmake -DDMTCP_STATIC_MPI=ON ..
#      Links libmpi.a statically.  NOT compatible with MANA.
#
#   3. Dynamic MPI mode (default, for plain DMTCP or no checkpointing):
#      cmake ..
#      Links libmpi.so dynamically.  Works with plain DMTCP but NOT MANA.
#
project(art_simple_main)

find_package(HDF5 REQUIRED)
find_package(MPI REQUIRED)
find_package(Threads REQUIRED)
find_package(ZLIB REQUIRED)

option(DMTCP_USE_MANA_STUB "Link against MANA's libmpistub.so for MANA checkpoint/restart" OFF)
option(DMTCP_STATIC_MPI "Link MPI statically (for plain DMTCP, NOT compatible with MANA)" OFF)

# MANA_ROOT: path to the MANA installation (contains bin/, lib/, mpi-proxy-split/)
# Auto-detect from common install locations if not specified.
if(DMTCP_USE_MANA_STUB AND NOT MANA_ROOT)
    # Try common locations
    if(EXISTS "$ENV{HOME}/.local/share/guard-agent/dmtcp-src/mana")
        set(MANA_ROOT "$ENV{HOME}/.local/share/guard-agent/dmtcp-src/mana")
    elseif(EXISTS "$ENV{HOME}/.local/lib/dmtcp/libmpistub.so")
        # Installed via make install
        get_filename_component(MANA_ROOT "$ENV{HOME}/.local" ABSOLUTE)
    endif()
endif()

add_executable(art_simple_main main.cc art_simple.cc)

# =====================================================================
# Helper function: strip MPI-related entries from a target's
# INTERFACE_LINK_LIBRARIES.
#
# HDF5's config-mode package wraps MPI in generator expressions like:
#   $<$<BOOL:ON>:MPI::MPI_C>
# We must match these as well as plain "MPI::MPI_C" strings.
# =====================================================================
function(_strip_mpi_from_target _target)
    if(NOT TARGET ${_target})
        return()
    endif()
    get_target_property(_iface_libs ${_target} INTERFACE_LINK_LIBRARIES)
    if(NOT _iface_libs)
        return()
    endif()
    message(STATUS "DMTCP: inspecting ${_target} INTERFACE_LINK_LIBRARIES: ${_iface_libs}")
    set(_filtered_libs "")
    foreach(_lib IN LISTS _iface_libs)
        # Skip MPI imported targets (plain)
        if(_lib MATCHES "^MPI::")
            message(STATUS "DMTCP: stripping ${_lib} from ${_target}")
            continue()
        endif()
        # Skip generator expressions containing MPI targets or libmpi
        # e.g. $<$<BOOL:ON>:MPI::MPI_C>  or  $<...:libmpi.so>
        if(_lib MATCHES "MPI::MPI" OR _lib MATCHES "libmpi[^a-zA-Z]")
            message(STATUS "DMTCP: stripping ${_lib} from ${_target}")
            continue()
        endif()
        # Skip -lmpi or bare "mpi"
        if(_lib STREQUAL "-lmpi" OR _lib STREQUAL "mpi")
            message(STATUS "DMTCP: stripping ${_lib} from ${_target}")
            continue()
        endif()
        # Recurse into sub-targets to strip MPI from them too
        if(TARGET ${_lib})
            _strip_mpi_from_target(${_lib})
        endif()
        list(APPEND _filtered_libs "${_lib}")
    endforeach()
    set_target_properties(${_target} PROPERTIES
        INTERFACE_LINK_LIBRARIES "${_filtered_libs}")
    message(STATUS "DMTCP: ${_target} INTERFACE_LINK_LIBRARIES after filtering: ${_filtered_libs}")
endfunction()

# =====================================================================
# MODE 1: MANA stub linking
# =====================================================================
if(DMTCP_USE_MANA_STUB)
    message(STATUS "")
    message(STATUS "============================================================")
    message(STATUS "  DMTCP/MANA stub mode: linking against libmpistub.so")
    message(STATUS "============================================================")

    if(NOT MANA_ROOT)
        message(FATAL_ERROR
            "DMTCP_USE_MANA_STUB=ON but MANA_ROOT not set and auto-detection failed.\n"
            "Set -DMANA_ROOT=/path/to/mana (directory containing lib/dmtcp/libmpistub.so)")
    endif()

    message(STATUS "DMTCP: MANA_ROOT = ${MANA_ROOT}")

    # Find libmpistub.so
    find_library(MANA_MPISTUB_LIB
        NAMES mpistub
        HINTS "${MANA_ROOT}/lib/dmtcp"
              "${MANA_ROOT}/mpi-proxy-split/mpi-wrappers"
              "${MANA_ROOT}/lib"
        NO_DEFAULT_PATH
    )
    if(NOT MANA_MPISTUB_LIB)
        message(FATAL_ERROR
            "Could not find libmpistub.so in MANA_ROOT=${MANA_ROOT}\n"
            "Expected at: ${MANA_ROOT}/lib/dmtcp/libmpistub.so\n"
            "Build MANA first: cd ${MANA_ROOT} && make -j$(nproc)")
    endif()
    message(STATUS "DMTCP: using MANA stub library: ${MANA_MPISTUB_LIB}")

    # Use MPI headers from the system MPI (for compilation only)
    target_include_directories(art_simple_main PRIVATE ${MPI_CXX_INCLUDE_DIRS})
    target_compile_options(art_simple_main PRIVATE ${MPI_CXX_COMPILE_OPTIONS})

    # Strip MPI from all HDF5 targets to prevent libmpi.so from sneaking in
    foreach(_hdf5_target
            HDF5::HDF5
            hdf5-shared
            hdf5-static
            hdf5::hdf5-shared
            hdf5::hdf5-static
            HDF5::HDF5_C
            HDF5::HDF5_CXX)
        _strip_mpi_from_target(${_hdf5_target})
    endforeach()

    # Link against libmpistub.so (NOT libmpi.a or libmpi.so)
    # Use static HDF5 to avoid libhdf5.so pulling in libmpi.so via DT_NEEDED
    if(TARGET hdf5-static)
        message(STATUS "DMTCP: using static HDF5 (hdf5-static) to avoid runtime libmpi.so dependency")
        target_link_libraries(art_simple_main
            hdf5-static
            ${MANA_MPISTUB_LIB}
            Threads::Threads ${CMAKE_DL_LIBS} rt)
    else()
        message(STATUS "DMTCP: hdf5-static not available, falling back to HDF5::HDF5 (shared)")
        message(WARNING
            "Using shared HDF5 with MANA stub mode. If libhdf5.so has libmpi.so "
            "in DT_NEEDED, the app may still load real MPI at runtime, which "
            "conflicts with MANA. Consider installing static HDF5.")
        target_link_libraries(art_simple_main
            HDF5::HDF5
            ${MANA_MPISTUB_LIB}
            Threads::Threads ${CMAKE_DL_LIBS} rt)
    endif()

    message(STATUS "")
    message(STATUS "  Build with: make")
    message(STATUS "  Run with:   mpiexec -np N mana_launch [opts] ./art_simple_main [args]")
    message(STATUS "============================================================")
    message(STATUS "")

# =====================================================================
# MODE 2: Static MPI linking (for plain DMTCP, NOT MANA)
# =====================================================================
elseif(DMTCP_STATIC_MPI)
    message(STATUS "")
    message(STATUS "============================================================")
    message(STATUS "  DMTCP static MPI mode: linking libmpi.a")
    message(STATUS "  NOTE: NOT compatible with MANA. Use -DDMTCP_USE_MANA_STUB=ON for MANA.")
    message(STATUS "============================================================")

    target_include_directories(art_simple_main PRIVATE ${MPI_CXX_INCLUDE_DIRS})
    target_compile_options(art_simple_main PRIVATE ${MPI_CXX_COMPILE_OPTIONS})

    # Prefer libmpi.a if available; fall back to whatever CMake found.
    find_library(MPI_CXX_STATIC_LIB
        NAMES libmpi.a mpi
        HINTS ${MPI_CXX_LIBRARY_DIRS}
              ENV MPI_HOME
        PATH_SUFFIXES lib lib64
    )
    if(MPI_CXX_STATIC_LIB AND MPI_CXX_STATIC_LIB MATCHES "\\.a$")
        message(STATUS "DMTCP: using static MPI library: ${MPI_CXX_STATIC_LIB}")

        # ---------------------------------------------------------------
        # Discover transitive dependencies of libmpi.so.
        # ---------------------------------------------------------------
        get_filename_component(_MPI_LIB_DIR "${MPI_CXX_STATIC_LIB}" DIRECTORY)
        file(GLOB _MPI_SHARED_CANDIDATES "${_MPI_LIB_DIR}/libmpi.so*")
        set(_MPI_SHARED_LIB "")
        foreach(_cand IN LISTS _MPI_SHARED_CANDIDATES)
            get_filename_component(_cname "${_cand}" NAME)
            if(_cname MATCHES "^libmpi\\.so")
                set(_MPI_SHARED_LIB "${_cand}")
                break()
            endif()
        endforeach()
        if(NOT _MPI_SHARED_LIB)
            get_target_property(_MPI_IMPORTED_LOC MPI::MPI_CXX IMPORTED_LOCATION)
            if(_MPI_IMPORTED_LOC AND _MPI_IMPORTED_LOC MATCHES "\\.so")
                set(_MPI_SHARED_LIB "${_MPI_IMPORTED_LOC}")
            endif()
        endif()

        set(_MPI_TRANSITIVE_DEPS "")

        if(_MPI_SHARED_LIB)
            message(STATUS "DMTCP: inspecting shared lib with ldd: ${_MPI_SHARED_LIB}")

            execute_process(
                COMMAND ldd "${_MPI_SHARED_LIB}"
                OUTPUT_VARIABLE _LDD_OUTPUT
                OUTPUT_STRIP_TRAILING_WHITESPACE
                ERROR_QUIET
                RESULT_VARIABLE _LDD_RC)

            if(_LDD_RC EQUAL 0)
                string(REPLACE "\n" ";" _LDD_LINES "${_LDD_OUTPUT}")

                foreach(_line IN LISTS _LDD_LINES)
                    if(_line MATCHES "=>[ \t]+(/[^ \t]+)")
                        set(_resolved_path "${CMAKE_MATCH_1}")
                        get_filename_component(_fname "${_resolved_path}" NAME)
                        if(_fname MATCHES "^lib(mpi|mpicxx|stdc\\+\\+|gcc_s|c|m|pthread|dl|rt)\\.")
                            continue()
                        endif()
                        if(_fname MATCHES "^ld-linux" OR _fname MATCHES "^linux-vdso")
                            continue()
                        endif()
                        list(APPEND _MPI_TRANSITIVE_DEPS "${_resolved_path}")
                    endif()
                endforeach()

                list(REMOVE_DUPLICATES _MPI_TRANSITIVE_DEPS)
                message(STATUS "DMTCP: ldd resolved deps (${_MPI_SHARED_LIB}):")
                foreach(_dep IN LISTS _MPI_TRANSITIVE_DEPS)
                    message(STATUS "DMTCP:   ${_dep}")
                endforeach()
            else()
                message(WARNING "DMTCP: ldd failed on ${_MPI_SHARED_LIB}")
            endif()
        else()
            message(WARNING "DMTCP: could not find shared libmpi.so to inspect")
        endif()

        message(STATUS "DMTCP: total transitive deps: ${_MPI_TRANSITIVE_DEPS}")

        # Apply any linker flags from FindMPI
        if(MPI_CXX_LINK_FLAGS)
            string(STRIP "${MPI_CXX_LINK_FLAGS}" _MPI_LINK_FLAGS)
            if(_MPI_LINK_FLAGS)
                set_target_properties(art_simple_main PROPERTIES
                    LINK_FLAGS "${_MPI_LINK_FLAGS}")
            endif()
        endif()

        # Strip MPI from HDF5 targets
        foreach(_hdf5_target
                HDF5::HDF5
                hdf5-shared
                hdf5-static
                hdf5::hdf5-shared
                hdf5::hdf5-static
                HDF5::HDF5_C
                HDF5::HDF5_CXX)
            _strip_mpi_from_target(${_hdf5_target})
        endforeach()

        # Link with --whole-archive for libmpi.a
        get_target_property(_existing_link_flags art_simple_main LINK_FLAGS)
        if(NOT _existing_link_flags)
            set(_existing_link_flags "")
        endif()
        set_target_properties(art_simple_main PROPERTIES
            LINK_FLAGS "${_existing_link_flags} -Wl,--whole-archive ${MPI_CXX_STATIC_LIB} -Wl,--no-whole-archive")

        # Prefer static HDF5 to avoid libhdf5.so DT_NEEDED pulling in libmpi.so
        if(TARGET hdf5-static)
            message(STATUS "DMTCP: using static HDF5 (hdf5-static) to avoid runtime libmpi.so dependency")
            target_link_libraries(art_simple_main
                hdf5-static
                ${_MPI_TRANSITIVE_DEPS}
                Threads::Threads ${CMAKE_DL_LIBS} rt)
        else()
            message(STATUS "DMTCP: hdf5-static not available, falling back to HDF5::HDF5 (shared)")
            target_link_libraries(art_simple_main
                HDF5::HDF5
                ${_MPI_TRANSITIVE_DEPS}
                Threads::Threads ${CMAKE_DL_LIBS} rt)
        endif()
    else()
        message(WARNING
            "DMTCP: static libmpi.a not found; falling back to dynamic MPI. "
            "MANA may not work correctly. Install a static MPI build or set "
            "-DDMTCP_STATIC_MPI=OFF to silence this warning.")
        target_link_libraries(art_simple_main HDF5::HDF5 MPI::MPI_CXX)
    endif()

# =====================================================================
# MODE 3: Dynamic MPI linking (default)
# =====================================================================
else()
    # Dynamic linking (same as the original build).
    target_link_libraries(art_simple_main HDF5::HDF5 MPI::MPI_CXX)
endif()
