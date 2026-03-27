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
        # We use `ldd` on the shared libmpi.so to get fully-resolved paths
        # to all transitive dependencies, then link them alongside the
        # static archive.
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
            message(STATUS "DMTCP: inspecting shared lib with ldd: ${_MPI_SHARED_LIB}")

            # Use ldd to get fully-resolved paths to all dependencies
            execute_process(
                COMMAND ldd "${_MPI_SHARED_LIB}"
                OUTPUT_VARIABLE _LDD_OUTPUT
                OUTPUT_STRIP_TRAILING_WHITESPACE
                ERROR_QUIET
                RESULT_VARIABLE _LDD_RC)

            if(_LDD_RC EQUAL 0)
                # ldd output lines look like:
                #   libpmix.so.2 => /usr/lib64/libpmix.so.2 (0x00007f...)
                #   /lib64/ld-linux-x86-64.so.2 (0x00007f...)
                #   linux-vdso.so.1 (0x00007f...)
                string(REPLACE "\n" ";" _LDD_LINES "${_LDD_OUTPUT}")

                foreach(_line IN LISTS _LDD_LINES)
                    # Match lines with "=> /path/to/lib.so"
                    if(_line MATCHES "=>[ \t]+(/[^ \t]+)")
                        set(_resolved_path "${CMAKE_MATCH_1}")
                        # Extract library base name for filtering
                        get_filename_component(_fname "${_resolved_path}" NAME)
                        # Skip mpi/mpicxx, standard C/C++ runtime, linker, vdso
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
                message(WARNING "DMTCP: ldd failed on ${_MPI_SHARED_LIB}, "
                    "falling back to readelf approach")

                # Fallback: use readelf -d to extract NEEDED entries
                execute_process(
                    COMMAND readelf -d "${_MPI_SHARED_LIB}"
                    OUTPUT_VARIABLE _READELF_OUTPUT
                    OUTPUT_STRIP_TRAILING_WHITESPACE
                    ERROR_QUIET
                    RESULT_VARIABLE _READELF_RC)

                if(_READELF_RC EQUAL 0)
                    string(REGEX MATCHALL "\\[lib[^\]]+\\.so[^\]]*\\]"
                        _NEEDED_MATCHES "${_READELF_OUTPUT}")
                    foreach(_match IN LISTS _NEEDED_MATCHES)
                        string(REGEX REPLACE "^\\[(.*)\\]$" "\\1" _soname "${_match}")
                        string(REGEX REPLACE "^lib(.+)\\.so.*$" "\\1" _libname "${_soname}")
                        if(_libname MATCHES "^(mpi|mpicxx|stdc\\+\\+|gcc_s|c|m|pthread)$")
                            continue()
                        endif()
                        find_library(_dep_${_libname} NAMES ${_libname}
                            HINTS "${_MPI_LIB_DIR}")
                        if(_dep_${_libname})
                            list(APPEND _MPI_TRANSITIVE_DEPS "${_dep_${_libname}}")
                        else()
                            list(APPEND _MPI_TRANSITIVE_DEPS "${_libname}")
                        endif()
                    endforeach()
                endif()
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
