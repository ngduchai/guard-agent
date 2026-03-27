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

        # Static libmpi.a has transitive dependencies on PMIx, fabric, hwloc,
        # etc.  Discover them so the linker can resolve all symbols.
        set(_MPI_TRANSITIVE_DEPS "")

        # PMIx – required by MPICH for process management.
        find_library(_PMIX_LIB NAMES pmix
            HINTS ${MPI_CXX_LIBRARY_DIRS} ENV MPI_HOME
            PATH_SUFFIXES lib lib64)
        if(_PMIX_LIB)
            list(APPEND _MPI_TRANSITIVE_DEPS ${_PMIX_LIB})
            message(STATUS "DMTCP: found PMIx: ${_PMIX_LIB}")
        endif()

        # PMI2 – some MPICH builds also need libpmi2.
        find_library(_PMI2_LIB NAMES pmi2
            HINTS ${MPI_CXX_LIBRARY_DIRS} ENV MPI_HOME
            PATH_SUFFIXES lib lib64)
        if(_PMI2_LIB)
            list(APPEND _MPI_TRANSITIVE_DEPS ${_PMI2_LIB})
            message(STATUS "DMTCP: found PMI2: ${_PMI2_LIB}")
        endif()

        # libfabric (OFI) – network transport used by MPICH on many HPC systems.
        find_library(_FABRIC_LIB NAMES fabric
            HINTS ${MPI_CXX_LIBRARY_DIRS} ENV MPI_HOME
            PATH_SUFFIXES lib lib64)
        if(_FABRIC_LIB)
            list(APPEND _MPI_TRANSITIVE_DEPS ${_FABRIC_LIB})
            message(STATUS "DMTCP: found libfabric: ${_FABRIC_LIB}")
        endif()

        # hwloc – hardware locality, often a transitive dep of MPICH.
        find_library(_HWLOC_LIB NAMES hwloc
            HINTS ${MPI_CXX_LIBRARY_DIRS} ENV MPI_HOME
            PATH_SUFFIXES lib lib64)
        if(_HWLOC_LIB)
            list(APPEND _MPI_TRANSITIVE_DEPS ${_HWLOC_LIB})
            message(STATUS "DMTCP: found hwloc: ${_HWLOC_LIB}")
        endif()

        # System libraries required by static MPICH: pthreads, dl, rt.
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
