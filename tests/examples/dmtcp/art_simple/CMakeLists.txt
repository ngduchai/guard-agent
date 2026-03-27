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
        #
        # When linking libmpi.a statically, all shared-library dependencies
        # that libmpi.so would normally pull in via DT_NEEDED must be
        # specified explicitly on the link line.
        #
        # Neither MPI_CXX_LIBRARIES nor `mpicxx -show` reliably lists
        # these transitive deps (the wrapper only shows -lmpi/-lmpicxx).
        # Instead, we inspect the actual libmpi.so with `readelf -d` to
        # extract its NEEDED entries, then resolve each to a full path.
        # ---------------------------------------------------------------

        # Find the corresponding shared libmpi.so
        get_filename_component(_MPI_LIB_DIR "${MPI_CXX_STATIC_LIB}" DIRECTORY)
        find_library(_MPI_SHARED_LIB
            NAMES mpi
            HINTS "${_MPI_LIB_DIR}"
            PATH_SUFFIXES lib lib64
            NO_DEFAULT_PATH)
        if(NOT _MPI_SHARED_LIB)
            find_library(_MPI_SHARED_LIB NAMES mpi)
        endif()

        set(_MPI_TRANSITIVE_DEPS "")

        if(_MPI_SHARED_LIB)
            message(STATUS "DMTCP: inspecting shared lib for NEEDED: ${_MPI_SHARED_LIB}")

            # Use readelf to extract DT_NEEDED entries from libmpi.so
            execute_process(
                COMMAND readelf -d "${_MPI_SHARED_LIB}"
                OUTPUT_VARIABLE _READELF_OUTPUT
                OUTPUT_STRIP_TRAILING_WHITESPACE
                ERROR_QUIET
                RESULT_VARIABLE _READELF_RC)

            if(_READELF_RC EQUAL 0)
                # Extract library names from lines like:
                #  0x0000000000000001 (NEEDED)  Shared library: [libpmix.so.2]
                string(REGEX MATCHALL "\\[lib[^\]]+\\.so[^\]]*\\]" _NEEDED_MATCHES "${_READELF_OUTPUT}")

                set(_NEEDED_LIBS "")
                foreach(_match IN LISTS _NEEDED_MATCHES)
                    # Strip brackets: [libfoo.so.2] -> libfoo.so.2
                    string(REGEX REPLACE "^\\[(.*)\\]$" "\\1" _soname "${_match}")
                    # Extract base library name: libfoo.so.2 -> foo
                    string(REGEX REPLACE "^lib(.+)\\.so.*$" "\\1" _libname "${_soname}")
                    # Skip mpi/mpicxx themselves and standard C/C++ runtime
                    if(_libname MATCHES "^(mpi|mpicxx|stdc\\+\\+|gcc_s|c|m|pthread)$")
                        continue()
                    endif()
                    list(APPEND _NEEDED_LIBS "${_libname}")
                endforeach()

                list(REMOVE_DUPLICATES _NEEDED_LIBS)
                message(STATUS "DMTCP: libmpi.so NEEDED libs: ${_NEEDED_LIBS}")

                # Resolve each library name to a full path
                foreach(_libname IN LISTS _NEEDED_LIBS)
                    find_library(_dep_${_libname}
                        NAMES ${_libname}
                        HINTS "${_MPI_LIB_DIR}" "${_MPI_LIB_DIR}/.."
                        PATH_SUFFIXES lib lib64
                    )
                    if(_dep_${_libname})
                        list(APPEND _MPI_TRANSITIVE_DEPS "${_dep_${_libname}}")
                        message(STATUS "DMTCP:   resolved ${_libname} -> ${_dep_${_libname}}")
                    else()
                        # Fall back to -l flag; the linker will search system paths
                        list(APPEND _MPI_TRANSITIVE_DEPS "${_libname}")
                        message(STATUS "DMTCP:   ${_libname} -> using -l fallback")
                    endif()
                endforeach()
            else()
                message(WARNING "DMTCP: readelf failed on ${_MPI_SHARED_LIB}")
            endif()
        else()
            message(WARNING "DMTCP: could not find shared libmpi.so to inspect")
        endif()

        message(STATUS "DMTCP: transitive deps: ${_MPI_TRANSITIVE_DEPS}")

        # Apply any linker flags from FindMPI
        if(MPI_CXX_LINK_FLAGS)
            string(STRIP "${MPI_CXX_LINK_FLAGS}" _MPI_LINK_FLAGS)
            if(_MPI_LINK_FLAGS)
                set_target_properties(art_simple_main PROPERTIES
                    LINK_FLAGS "${_MPI_LINK_FLAGS}")
            endif()
        endif()

        target_link_libraries(art_simple_main HDF5::HDF5
            ${MPI_CXX_STATIC_LIB} ${_MPI_TRANSITIVE_DEPS}
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
