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
        # NOTE: We cannot use find_library() here because it may return
        # libmpi.a again (cache variable, or .a preferred on some systems).
        # Instead, glob for libmpi.so* directly in the same directory.
        get_filename_component(_MPI_LIB_DIR "${MPI_CXX_STATIC_LIB}" DIRECTORY)
        file(GLOB _MPI_SHARED_CANDIDATES "${_MPI_LIB_DIR}/libmpi.so*")
        # Filter out libmpicxx.so* and libmpifort.so*
        set(_MPI_SHARED_LIB "")
        foreach(_cand IN LISTS _MPI_SHARED_CANDIDATES)
            get_filename_component(_cname "${_cand}" NAME)
            if(_cname MATCHES "^libmpi\\.so")
                set(_MPI_SHARED_LIB "${_cand}")
                break()
            endif()
        endforeach()
        if(NOT _MPI_SHARED_LIB)
            # Fallback: try the MPI imported target's location
            get_target_property(_MPI_IMPORTED_LOC MPI::MPI_CXX IMPORTED_LOCATION)
            if(_MPI_IMPORTED_LOC AND _MPI_IMPORTED_LOC MATCHES "\\.so")
                set(_MPI_SHARED_LIB "${_MPI_IMPORTED_LOC}")
            endif()
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

        # ---------------------------------------------------------------
        # Strip MPI from HDF5 imported targets' transitive dependencies.
        #
        # On systems where HDF5 is built with parallel (MPI) support,
        # the HDF5 imported targets include libmpi.so in their
        # INTERFACE_LINK_LIBRARIES.  This causes the dynamic libmpi.so
        # to appear on the link line AFTER our static libmpi.a, which
        # makes the final binary dynamically linked against MPI —
        # defeating the purpose of static MPI linking for MANA.
        #
        # The fix: iterate over all HDF5-related imported targets and
        # remove any MPI references from their INTERFACE_LINK_LIBRARIES.
        # This way we can still use HDF5::HDF5 normally, but it won't
        # drag in libmpi.so.
        # ---------------------------------------------------------------

        # Helper function: strip MPI-related entries from a target's
        # INTERFACE_LINK_LIBRARIES.  Uses function() instead of macro()
        # to get proper variable scoping for recursion.
        #
        # NOTE: HDF5's config-mode package wraps MPI in generator
        # expressions like:  $<$<BOOL:ON>:MPI::MPI_C>
        # We must match these as well as plain "MPI::MPI_C" strings.
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

        # Strip MPI from all known HDF5 targets.
        # Different HDF5 installations use different target names, so we
        # try all common variants.
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

        # Now link: use --whole-archive for libmpi.a.
        #
        # We must use LINK_FLAGS (not target_link_libraries) for the
        # --whole-archive wrapper because CMake may reorder libraries
        # specified via target_link_libraries, breaking the archive
        # grouping.  LINK_FLAGS are emitted verbatim at the start of
        # the link line.
        get_target_property(_existing_link_flags art_simple_main LINK_FLAGS)
        if(NOT _existing_link_flags)
            set(_existing_link_flags "")
        endif()
        set_target_properties(art_simple_main PROPERTIES
            LINK_FLAGS "${_existing_link_flags} -Wl,--whole-archive ${MPI_CXX_STATIC_LIB} -Wl,--no-whole-archive")

        # ---------------------------------------------------------------
        # Prefer static HDF5 (libhdf5.a) over shared (libhdf5.so).
        #
        # Even after stripping MPI from HDF5's INTERFACE_LINK_LIBRARIES,
        # the shared libhdf5.so still has libmpi.so in its DT_NEEDED
        # entries.  The dynamic linker will load libmpi.so at runtime,
        # which conflicts with MANA's split-process architecture.
        #
        # Using the static hdf5-static target avoids this entirely.
        # ---------------------------------------------------------------
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
else()
    # Dynamic linking (same as the original build).
    target_link_libraries(art_simple_main HDF5::HDF5 MPI::MPI_CXX)
endif()
