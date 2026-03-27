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
        # platform (PMIx, libfabric, hwloc, Level Zero, etc.).  Rather than
        # enumerating them one by one, we extract the shared libraries that
        # CMake's FindMPI discovered from the MPI compiler wrapper and link
        # them alongside the static archive.  This ensures all symbols
        # referenced by libmpi.a are resolved regardless of the platform.
        set(_MPI_SHARED_DEPS "")
        foreach(_lib IN LISTS MPI_CXX_LIBRARIES)
            # Skip the shared libmpi.so / libmpicxx.so themselves – we are
            # replacing them with the static archive.
            if(_lib MATCHES "libmpi(cxx)?\\.(so|dylib)")
                continue()
            endif()
            list(APPEND _MPI_SHARED_DEPS "${_lib}")
        endforeach()
        message(STATUS "DMTCP: MPI transitive deps: ${_MPI_SHARED_DEPS}")

        # Also pull in any linker flags FindMPI extracted (e.g. -L paths).
        if(MPI_CXX_LINK_FLAGS)
            string(STRIP "${MPI_CXX_LINK_FLAGS}" _MPI_LINK_FLAGS)
            if(_MPI_LINK_FLAGS)
                set_target_properties(art_simple_main PROPERTIES
                    LINK_FLAGS "${_MPI_LINK_FLAGS}")
            endif()
        endif()

        target_link_libraries(art_simple_main HDF5::HDF5
            ${MPI_CXX_STATIC_LIB} ${_MPI_SHARED_DEPS}
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
