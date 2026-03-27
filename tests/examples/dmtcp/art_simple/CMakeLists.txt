cmake_minimum_required(VERSION 3.10)

# DMTCP/MANA variant of art_simple.
# Same source code as the original; only the build system differs.
# MANA requires statically linked MPI executables.
project(art_simple_main)

find_package(HDF5 REQUIRED)
find_package(MPI REQUIRED)
find_package(Threads REQUIRED)

option(DMTCP_STATIC_MPI "Link MPI statically for MANA compatibility" ON)

add_executable(art_simple_main main.cc art_simple.cc)

if(DMTCP_STATIC_MPI)
    # Static MPI linking for MANA.
    # Use the raw MPI variables instead of the imported target so we can
    # control static vs shared linking.
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

        # Static libmpi.a has many transitive dependencies that vary by
        # platform (PMIx, libfabric, hwloc, Level Zero, etc.).
        #
        # CMake's FindMPI sometimes only populates the imported target
        # MPI::MPI_CXX and leaves MPI_CXX_LIBRARIES empty.  To reliably
        # discover all transitive link dependencies we query the MPI
        # compiler wrapper directly (mpicxx -show) and parse its output.
        # This is the same technique CMake's FindMPI uses internally.

        # --- Step 1: query the MPI compiler wrapper ---
        get_filename_component(_MPI_CXX_DIR "${MPI_CXX_COMPILER}" DIRECTORY)
        find_program(_MPICXX_WRAPPER
            NAMES mpicxx mpic++ mpiCC
            HINTS "${_MPI_CXX_DIR}"
            NO_DEFAULT_PATH)
        if(NOT _MPICXX_WRAPPER)
            find_program(_MPICXX_WRAPPER NAMES mpicxx mpic++ mpiCC)
        endif()

        set(_MPI_WRAPPER_LIBS "")
        set(_MPI_WRAPPER_LIBDIRS "")
        set(_MPI_WRAPPER_RPATHS "")

        if(_MPICXX_WRAPPER)
            execute_process(
                COMMAND "${_MPICXX_WRAPPER}" -show
                OUTPUT_VARIABLE _MPICXX_SHOW_OUTPUT
                OUTPUT_STRIP_TRAILING_WHITESPACE
                ERROR_QUIET
                RESULT_VARIABLE _MPICXX_SHOW_RC)
            if(_MPICXX_SHOW_RC EQUAL 0)
                message(STATUS "DMTCP: mpicxx -show: ${_MPICXX_SHOW_OUTPUT}")

                # Parse -l flags (library names)
                string(REGEX MATCHALL "-l([^ ]+)" _LFLAG_MATCHES "${_MPICXX_SHOW_OUTPUT}")
                foreach(_match IN LISTS _LFLAG_MATCHES)
                    string(REGEX REPLACE "^-l" "" _libname "${_match}")
                    # Skip mpi/mpicxx themselves – we link the static archive
                    if(NOT _libname MATCHES "^mpi(cxx)?$")
                        list(APPEND _MPI_WRAPPER_LIBS "${_libname}")
                    endif()
                endforeach()

                # Parse -L flags (library search paths)
                string(REGEX MATCHALL "-L([^ ]+)" _LDIR_MATCHES "${_MPICXX_SHOW_OUTPUT}")
                foreach(_match IN LISTS _LDIR_MATCHES)
                    string(REGEX REPLACE "^-L" "" _dir "${_match}")
                    list(APPEND _MPI_WRAPPER_LIBDIRS "${_dir}")
                endforeach()

                # Parse -Wl,-rpath flags
                string(REGEX MATCHALL "-Wl,-rpath,([^ ]+)" _RPATH_MATCHES "${_MPICXX_SHOW_OUTPUT}")
                foreach(_match IN LISTS _RPATH_MATCHES)
                    string(REGEX REPLACE "^-Wl,-rpath," "" _rp "${_match}")
                    list(APPEND _MPI_WRAPPER_RPATHS "${_rp}")
                endforeach()
            endif()
        endif()

        message(STATUS "DMTCP: wrapper libs: ${_MPI_WRAPPER_LIBS}")
        message(STATUS "DMTCP: wrapper libdirs: ${_MPI_WRAPPER_LIBDIRS}")

        # --- Step 2: resolve each library name to a full path ---
        set(_MPI_RESOLVED_DEPS "")
        foreach(_libname IN LISTS _MPI_WRAPPER_LIBS)
            find_library(_resolved_${_libname}
                NAMES ${_libname}
                HINTS ${_MPI_WRAPPER_LIBDIRS} ${_MPI_WRAPPER_RPATHS}
                NO_DEFAULT_PATH)
            if(NOT _resolved_${_libname})
                find_library(_resolved_${_libname} NAMES ${_libname})
            endif()
            if(_resolved_${_libname})
                list(APPEND _MPI_RESOLVED_DEPS "${_resolved_${_libname}}")
            else()
                # Fall back to -l flag; the linker will search system paths
                list(APPEND _MPI_RESOLVED_DEPS "${_libname}")
            endif()
        endforeach()

        message(STATUS "DMTCP: resolved transitive deps: ${_MPI_RESOLVED_DEPS}")

        # --- Step 3: apply -L paths as linker search directories ---
        set(_EXTRA_LINK_FLAGS "")
        foreach(_dir IN LISTS _MPI_WRAPPER_LIBDIRS)
            string(APPEND _EXTRA_LINK_FLAGS " -L${_dir}")
        endforeach()
        foreach(_rp IN LISTS _MPI_WRAPPER_RPATHS)
            string(APPEND _EXTRA_LINK_FLAGS " -Wl,-rpath,${_rp}")
        endforeach()
        if(MPI_CXX_LINK_FLAGS)
            string(STRIP "${MPI_CXX_LINK_FLAGS}" _MPI_LINK_FLAGS)
            string(APPEND _EXTRA_LINK_FLAGS " ${_MPI_LINK_FLAGS}")
        endif()
        string(STRIP "${_EXTRA_LINK_FLAGS}" _EXTRA_LINK_FLAGS)
        if(_EXTRA_LINK_FLAGS)
            set_target_properties(art_simple_main PROPERTIES
                LINK_FLAGS "${_EXTRA_LINK_FLAGS}")
        endif()

        target_link_libraries(art_simple_main HDF5::HDF5
            ${MPI_CXX_STATIC_LIB} ${_MPI_RESOLVED_DEPS}
            Threads::Threads ${CMAKE_DL_LIBS} rt)
    else()
        message(WARNING
            "DMTCP: static libmpi.a not found; falling back to dynamic MPI. "
            "MANA may not work correctly. Install a static MPI build or set "
            "-DDMTCP_STATIC_MPI=OFF to silence this warning.")
        target_link_libraries(art_simple_main HDF5::HDF5 MPI::MPI_CXX)
    endif()
else()
    # Dynamic linking (same as the original build).
    target_link_libraries(art_simple_main HDF5::HDF5 MPI::MPI_CXX)
endif()
