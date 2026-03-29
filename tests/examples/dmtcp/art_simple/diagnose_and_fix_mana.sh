#!/usr/bin/env bash
# ============================================================================
# diagnose_and_fix_mana.sh – Comprehensive MANA diagnosis and fix for Aurora
#
# ROOT CAUSE (discovered via strace analysis):
#   MANA crashes with SIGSEGV at address 0x80fff7f8 (the lower-half's stack
#   guard page). The crash is caused by an infinite recursion loop:
#
#   1. libmana.so is built with mpicc/mpicxx which wraps Intel icx/icpx
#   2. libmana.so therefore links Intel runtime (libintlc.so.5, libsvml.so, etc.)
#   3. When libmana.so is LD_PRELOAD'd, Intel runtime initialization calls
#      openat("/proc/self/environ") to read environment variables
#   4. DMTCP wraps openat() via dmtcp_openat
#   5. dmtcp_openat triggers more Intel runtime code → more openat() calls
#   6. This creates infinite recursion that exhausts the stack
#   7. Stack overflow hits the PROT_NONE guard page at 0x80fff000 → SIGSEGV
#
#   Evidence: strace showed 8,780 opens of /proc/self/environ without closing,
#   reaching fd 4423, immediately followed by SEGV_ACCERR at 0x80fff7f8.
#
# FIX STRATEGY:
#   The MANA build system has a subtle issue: libmana.so is linked with ${CXX}
#   (from ./configure, which is icpx on Aurora), while the lower-half binary
#   is linked with ${MPICXX} (from Makefile_config). The .o files for both are
#   compiled with ${MPICC}/${MPICXX}.
#
#   We can't simply change MPICC/MPICXX to GCC because:
#   - The lower-half binary needs -lmpi (provided implicitly by mpicc/mpicxx)
#   - The libmana.so link uses ${CXX}, not ${MPICXX}
#
#   APPROACH: Patch the MANA Makefile to use a new variable ${MANA_LINK_CXX}
#   for the libmana.so link rule instead of ${CXX}. Set MANA_LINK_CXX to GCC
#   in Makefile_config. This way:
#   - .o files compile with mpicc/mpicxx (gets MPI headers)
#   - lower-half links with mpicxx (gets -lmpi implicitly)
#   - libmana.so links with g++ (no Intel runtime deps)
#
#   The lower-half binary is a separate process (not LD_PRELOAD'd), so Intel
#   runtime deps there are harmless.
#
# This script:
#   Phase 1: Diagnose current state (Intel runtime deps in loaded libraries)
#   Phase 2: Rebuild DMTCP with GCC (if needed)
#   Phase 3: Patch Makefile + rebuild MANA with GCC linker for libmana.so
#   Phase 4: Verify no Intel runtime deps in LD_PRELOAD'd libraries
#   Phase 5: Test MANA with built-in test
#   Phase 6: Test MANA with strace to verify no /proc/self/environ loop
# ============================================================================

set -euo pipefail

INSTALL_PREFIX="${HOME}/.local"
SRC_DIR="${INSTALL_PREFIX}/share/guard-agent/dmtcp-src"
DMTCP_SRC="${SRC_DIR}/dmtcp"
MANA_ROOT="${SRC_DIR}/mana"
MANA_BIN="${MANA_ROOT}/bin"
MANA_LIB="${MANA_ROOT}/lib/dmtcp"
OUTDIR="${HOME}/diaspora/guard-agent/build/mana_fix_output"

mkdir -p "${OUTDIR}"

export HWLOC_COMPONENTS="-linuxio"

echo "============================================================"
echo "  MANA Diagnosis & Fix for Aurora"
echo "  (Intel runtime infinite recursion in libmana.so)"
echo "============================================================"
echo ""
echo "Date: $(date)"
echo "Host: $(hostname)"
echo ""

# ══════════════════════════════════════════════════════════════════════════
# Find GCC
# ══════════════════════════════════════════════════════════════════════════
_find_gcc() {
    local gcc_path=""
    # Try spack GCC first (Aurora has GCC 13.4.0 via spack)
    gcc_path=$(find /opt/aurora -name "gcc" -path "*/gcc-13*/bin/gcc" 2>/dev/null | head -1)
    if [ -z "${gcc_path}" ]; then
        gcc_path=$(find /opt -name "gcc" -path "*/gcc-1[0-9]*/bin/gcc" 2>/dev/null | head -1)
    fi
    if [ -z "${gcc_path}" ]; then
        gcc_path=$(command -v gcc 2>/dev/null || true)
    fi
    echo "${gcc_path}"
}

GCC_CC=$(_find_gcc)
if [ -z "${GCC_CC}" ]; then
    echo "ERROR: Cannot find GCC"
    exit 1
fi
GCC_CXX=$(echo "${GCC_CC}" | sed 's|/gcc$|/g++|')
echo "GCC CC:  ${GCC_CC} ($(${GCC_CC} --version 2>/dev/null | head -1))"
echo "GCC CXX: ${GCC_CXX}"
echo ""

# Intel runtime libraries pattern
INTEL_LIBS_PATTERN="libsvml\.so|libirng\.so|libimf\.so|libintlc\.so"

# ══════════════════════════════════════════════════════════════════════════
# PHASE 1: Diagnose current state
# ══════════════════════════════════════════════════════════════════════════
echo "================================================================"
echo "  PHASE 1: Diagnose current state"
echo "================================================================"
echo ""

DMTCP_NEEDS_REBUILD=0
MANA_NEEDS_REBUILD=0

echo "--- 1a. Installed libdmtcp.so ---"
INSTALLED_LIBDMTCP="${INSTALL_PREFIX}/lib/dmtcp/libdmtcp.so"
if [ -f "${INSTALLED_LIBDMTCP}" ]; then
    echo "DT_NEEDED:"
    readelf -d "${INSTALLED_LIBDMTCP}" 2>/dev/null | grep NEEDED || true
    echo ""
    echo "Intel runtime deps:"
    if ldd "${INSTALLED_LIBDMTCP}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"; then
        echo "  *** HAS INTEL RUNTIME DEPS — needs rebuild ***"
        DMTCP_NEEDS_REBUILD=1
    else
        echo "  OK — no Intel runtime deps"
    fi
    echo ""
    echo ".comment section:"
    readelf -p .comment "${INSTALLED_LIBDMTCP}" 2>/dev/null || true
else
    echo "  NOT FOUND — needs rebuild"
    DMTCP_NEEDS_REBUILD=1
fi
echo ""

echo "--- 1b. Installed libmana.so ---"
INSTALLED_LIBMANA="${INSTALL_PREFIX}/lib/dmtcp/libmana.so"
if [ -f "${INSTALLED_LIBMANA}" ]; then
    echo "DT_NEEDED:"
    readelf -d "${INSTALLED_LIBMANA}" 2>/dev/null | grep NEEDED || true
    echo ""
    echo "Intel runtime deps:"
    if readelf -d "${INSTALLED_LIBMANA}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"; then
        echo "  *** HAS INTEL RUNTIME DEPS — needs fix ***"
        MANA_NEEDS_REBUILD=1
    else
        echo "  OK — no Intel runtime deps"
        MANA_NEEDS_REBUILD=0
    fi
else
    echo "  NOT FOUND — needs rebuild"
    MANA_NEEDS_REBUILD=1
fi
echo ""

echo "--- 1c. MANA build-dir libmana.so ---"
BUILD_LIBMANA="${MANA_ROOT}/lib/dmtcp/libmana.so"
if [ -f "${BUILD_LIBMANA}" ]; then
    echo "Intel runtime deps (readelf -d):"
    if readelf -d "${BUILD_LIBMANA}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"; then
        echo "  *** HAS INTEL RUNTIME DEPS ***"
    else
        echo "  OK — no Intel runtime deps"
    fi
fi
echo ""

echo "--- 1d. lower-half binary ---"
LOWER_HALF="${MANA_ROOT}/bin/lower-half"
if [ -f "${LOWER_HALF}" ]; then
    echo "Intel runtime deps:"
    if ldd "${LOWER_HALF}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"; then
        echo "  Has Intel runtime deps (OK for lower-half — it's a separate process)"
    else
        echo "  No Intel runtime deps"
    fi
fi
echo ""

echo "--- 1e. MPI compiler wrapper analysis ---"
echo "mpicc location: $(command -v mpicc 2>/dev/null || echo 'not found')"
echo "mpicc -show:"
mpicc -show 2>/dev/null || echo "  (failed)"
echo ""

echo "--- 1f. Makefile_config ---"
MAKEFILE_CONFIG="${MANA_ROOT}/mpi-proxy-split/Makefile_config"
if [ -f "${MAKEFILE_CONFIG}" ]; then
    cat "${MAKEFILE_CONFIG}"
else
    echo "  NOT FOUND"
fi
echo ""

echo "--- 1g. libmana.so link rule in Makefile ---"
echo "The libmana.so link rule uses \${CXX}, not \${MPICXX}:"
MANA_MAKEFILE="${MANA_ROOT}/mpi-proxy-split/Makefile"
grep -n 'libmana.so:' "${MANA_MAKEFILE}" 2>/dev/null || true
grep -A2 'libmana.so:' "${MANA_MAKEFILE}" 2>/dev/null | head -3 || true
echo ""
echo "CXX from MANA's configure:"
grep '^CXX' "${MANA_ROOT}/Makefile" 2>/dev/null | head -1 || true
echo ""

# Summary
echo "=== DIAGNOSIS SUMMARY ==="
echo "  libdmtcp.so needs rebuild: ${DMTCP_NEEDS_REBUILD}"
echo "  libmana.so needs fix:      ${MANA_NEEDS_REBUILD}"
echo ""

if [ "${DMTCP_NEEDS_REBUILD}" -eq 0 ] && [ "${MANA_NEEDS_REBUILD}" -eq 0 ]; then
    echo "Both libraries are clean. Skipping rebuild, going to test phase."
    echo ""
else
    echo "Proceeding with fix..."
    echo ""
fi

# ══════════════════════════════════════════════════════════════════════════
# PHASE 2: Rebuild DMTCP with GCC (if needed)
# ══════════════════════════════════════════════════════════════════════════
if [ "${DMTCP_NEEDS_REBUILD}" -eq 1 ]; then
    echo "================================================================"
    echo "  PHASE 2: Rebuild DMTCP with GCC"
    echo "================================================================"
    echo ""

    # 2a. Standalone DMTCP
    echo "--- 2a. Rebuild standalone DMTCP ---"
    cd "${DMTCP_SRC}"
    make distclean 2>/dev/null || make clean 2>/dev/null || true
    CC="${GCC_CC}" CXX="${GCC_CXX}" ./configure --prefix="${INSTALL_PREFIX}" 2>&1 | tail -3
    make -j"$(nproc)" 2>&1 | tail -5
    make install 2>&1 | tail -3
    echo ""

    echo "Verify standalone libdmtcp.so:"
    if readelf -d "${INSTALL_PREFIX}/lib/dmtcp/libdmtcp.so" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"; then
        echo "  ERROR: Still has Intel deps after rebuild!"
        exit 1
    else
        echo "  OK — clean"
    fi
    echo ""

    # 2b. MANA's embedded DMTCP
    echo "--- 2b. Rebuild MANA's embedded DMTCP ---"
    MANA_DMTCP="${MANA_ROOT}/dmtcp"
    if [ -d "${MANA_DMTCP}" ]; then
        cd "${MANA_DMTCP}"
        make distclean 2>/dev/null || make clean 2>/dev/null || true
        CC="${GCC_CC}" CXX="${GCC_CXX}" ./configure \
            --prefix="${INSTALL_PREFIX}" \
            --disable-dlsym-wrapper 2>&1 | tail -3
        echo "  Reconfigured MANA's embedded DMTCP with GCC"
    fi
    echo ""
fi

# ══════════════════════════════════════════════════════════════════════════
# PHASE 3: Fix libmana.so (patch Makefile + rebuild)
# ══════════════════════════════════════════════════════════════════════════
if [ "${MANA_NEEDS_REBUILD}" -eq 1 ] || [ "${DMTCP_NEEDS_REBUILD}" -eq 1 ]; then
    echo "================================================================"
    echo "  PHASE 3: Fix libmana.so"
    echo "================================================================"
    echo ""

    cd "${MANA_ROOT}"

    # 3a. Extract MPI flags from mpicc -show
    echo "--- 3a. Extract MPI flags ---"
    MPICC_SHOW=$(mpicc -show 2>/dev/null || echo "")
    MPICXX_SHOW=$(mpicxx -show 2>/dev/null || echo "")

    if [ -z "${MPICC_SHOW}" ]; then
        echo "ERROR: mpicc -show failed"
        exit 1
    fi

    # Extract -I flags
    MPI_INCLUDE_FLAGS=$(echo "${MPICC_SHOW}" | grep -oP '\-I\S+' | tr '\n' ' ')
    # Extract -L and -l and -Wl flags
    MPI_LINK_FLAGS=$(echo "${MPICC_SHOW}" | grep -oP '(\-L\S+|\-l\S+|\-Wl,\S+)' | tr '\n' ' ')

    echo "MPI include flags: ${MPI_INCLUDE_FLAGS}"
    echo "MPI link flags:    ${MPI_LINK_FLAGS}"
    echo ""

    # 3b. Write Makefile_config
    # Key: MPICC/MPICXX stay as mpicc/mpicxx for .o compilation and lower-half linking.
    # New variable MANA_LINK_CXX is set to GCC for the libmana.so link step.
    echo "--- 3b. Write Makefile_config ---"
    cat > "${MAKEFILE_CONFIG}" << MKEOF
# Aurora (ALCF) – Cray MPICH + Intel GPU
# Auto-generated by diagnose_and_fix_mana.sh
#
# Strategy:
#   - MPICC/MPICXX = mpicc/mpicxx for .o compilation and lower-half linking
#   - MANA_LINK_CXX = GCC g++ for the libmana.so link step (avoids Intel runtime)
#   - The Makefile is patched to use MANA_LINK_CXX instead of CXX for libmana.so

CFLAGS = -g -O2 -std=gnu11
CXXFLAGS = -g -O2
FFLAGS = \${CXXFLAGS} -fallow-argument-mismatch

IS_AURORA = 1
MPICC  = mpicc
MPICXX = mpicxx -std=c++14
MPIFORTRAN = mpifort
MPI_LD_FLAG = ${MPI_LINK_FLAGS}
MPIRUN = mpiexec
MPI_CFLAGS  ?= -g -O2 -std=gnu11 -g3 -fPIC
MPI_CXXFLAGS ?= -g -O2 -g3 -fPIC
MPI_LDFLAGS ?= ${MPI_LINK_FLAGS}

# GCC linker for libmana.so (avoids Intel runtime deps)
MANA_LINK_CXX = ${GCC_CXX}
MKEOF

    echo "Written Makefile_config:"
    cat "${MAKEFILE_CONFIG}"
    echo ""

    # 3c. Patch the Makefile to use MANA_LINK_CXX for libmana.so link
    echo "--- 3c. Patch Makefile for libmana.so link rule ---"
    MANA_MAKEFILE="${MANA_ROOT}/mpi-proxy-split/Makefile"

    # Add MANA_LINK_CXX default at the top (after include Makefile_config)
    # If MANA_LINK_CXX is not set in Makefile_config, fall back to ${CXX}
    if ! grep -q 'MANA_LINK_CXX' "${MANA_MAKEFILE}"; then
        # Add default after the include line
        sed -i '/^include.*Makefile_config/a \
# Default MANA_LINK_CXX to CXX if not set in Makefile_config\
MANA_LINK_CXX ?= ${CXX}' "${MANA_MAKEFILE}"
        echo "  Added MANA_LINK_CXX default to Makefile"
    fi

    # Replace ${CXX} with ${MANA_LINK_CXX} in the libmana.so link rule
    # The rule looks like:
    #   libmana.so: ${LIBOBJS} ${WRAPPERS_SRCDIR}/libmpiwrappers.a
    #       ${CXX} -shared -fPIC -g3 -O0 -o $@ ...
    if grep -q '${CXX} -shared -fPIC.*libmana.so' "${MANA_MAKEFILE}" || \
       grep -q '${CXX} -shared -fPIC -g3' "${MANA_MAKEFILE}"; then
        # Only replace the specific line that links libmana.so
        # Match: <tab>${CXX} -shared -fPIC
        sed -i 's|\t${CXX} -shared -fPIC|\t${MANA_LINK_CXX} -shared -fPIC|' "${MANA_MAKEFILE}"
        echo "  Patched libmana.so link rule: \${CXX} → \${MANA_LINK_CXX}"
    else
        echo "  WARNING: Could not find libmana.so link rule to patch"
        echo "  Looking for the pattern..."
        grep -n 'shared.*fPIC' "${MANA_MAKEFILE}" || true
    fi

    echo ""
    echo "Verify patched Makefile (libmana.so rule):"
    grep -A2 'libmana.so:' "${MANA_MAKEFILE}" | head -3
    echo ""

    # 3d. Also patch mpi-wrappers/Makefile for libmpistub.so link
    echo "--- 3d. Patch mpi-wrappers/Makefile for libmpistub.so ---"
    WRAPPERS_MAKEFILE="${MANA_ROOT}/mpi-proxy-split/mpi-wrappers/Makefile"
    if [ -f "${WRAPPERS_MAKEFILE}" ]; then
        # Add MANA_LINK_CXX default
        if ! grep -q 'MANA_LINK_CXX' "${WRAPPERS_MAKEFILE}"; then
            # Check if there's an include line
            if grep -q '^include' "${WRAPPERS_MAKEFILE}"; then
                sed -i '/^include/a \
MANA_LINK_CXX ?= ${CXX}' "${WRAPPERS_MAKEFILE}"
            else
                sed -i '1i MANA_LINK_CXX ?= ${CXX}' "${WRAPPERS_MAKEFILE}"
            fi
        fi

        # Check how libmpistub.so is linked
        echo "  libmpistub.so link rule:"
        grep -A2 'libmpistub' "${WRAPPERS_MAKEFILE}" | head -5 || true

        # Replace CXX/CC with MANA_LINK_CXX for libmpistub.so link
        # The rule might use ${CC} or ${CXX} or a hardcoded compiler
        if grep -q 'libmpistub.so' "${WRAPPERS_MAKEFILE}"; then
            # Replace any icx/icpx/icc references in the link line for libmpistub
            sed -i '/libmpistub\.so/,/^$/s|\ticx |\t${MANA_LINK_CXX} |' "${WRAPPERS_MAKEFILE}"
            sed -i '/libmpistub\.so/,/^$/s|\ticpx |\t${MANA_LINK_CXX} |' "${WRAPPERS_MAKEFILE}"
            sed -i '/libmpistub\.so/,/^$/s|\t${CC} -shared|\t${MANA_LINK_CXX} -shared|' "${WRAPPERS_MAKEFILE}"
            sed -i '/libmpistub\.so/,/^$/s|\t${CXX} -shared|\t${MANA_LINK_CXX} -shared|' "${WRAPPERS_MAKEFILE}"
            echo "  Patched libmpistub.so link rule"
        fi
        echo ""
    fi

    # 3e. Apply source patches
    echo "--- 3e. Apply source patches ---"

    # Patch 1: mpi_nextfunc.h - &MPI_##func → &PMPI_##func
    NEXTFUNC_H="mpi-proxy-split/mpi-wrappers/mpi_nextfunc.h"
    if [ -f "${NEXTFUNC_H}" ] && grep -q '&MPI_##func' "${NEXTFUNC_H}"; then
        sed -i 's/\&MPI_##func/\&PMPI_##func/g' "${NEXTFUNC_H}"
        echo "  Patched ${NEXTFUNC_H}: &MPI_##func → &PMPI_##func"
    fi

    # Patch 2: record-replay.h - same fix
    RR_H="mpi-proxy-split/mpi-wrappers/record-replay.h"
    if [ -f "${RR_H}" ] && grep -q '&MPI_##func' "${RR_H}"; then
        sed -i 's/\&MPI_##func/\&PMPI_##func/g' "${RR_H}"
        echo "  Patched ${RR_H}: &MPI_##func → &PMPI_##func"
    fi

    # Patch 5: PMPI_MANA_Internal compat define
    MANA_INTERNAL_H="mpi-proxy-split/mpi-wrappers/mpi_nextfunc.h"
    if [ -f "${MANA_INTERNAL_H}" ] && ! grep -q 'PMPI_MANA_Internal' "${MANA_INTERNAL_H}"; then
        sed -i '1i #define PMPI_MANA_Internal MPI_MANA_Internal' "${MANA_INTERNAL_H}"
        echo "  Added PMPI_MANA_Internal compat define"
    fi

    # Patch 6: switch-context.cpp rex.W → .byte 0x48
    SWITCH_CTX="mpi-proxy-split/lower-half/switch-context.cpp"
    if [ -f "${SWITCH_CTX}" ] && grep -q 'rex\.W' "${SWITCH_CTX}"; then
        sed -i 's/rex\.W/.byte 0x48/g' "${SWITCH_CTX}"
        echo "  Patched ${SWITCH_CTX}: rex.W → .byte 0x48"
    fi

    # Patch 7: copy-stack.c void* → char* cast
    COPY_STACK="mpi-proxy-split/lower-half/copy-stack.c"
    if [ -f "${COPY_STACK}" ] && grep -q 'void \*sp = ' "${COPY_STACK}"; then
        sed -i 's/void \*sp = /char *sp = (char*)/g' "${COPY_STACK}"
        echo "  Patched ${COPY_STACK}: void* → char*"
    fi

    echo ""

    # 3f. Clean and rebuild MANA
    echo "--- 3f. Clean and rebuild MANA ---"
    make clean 2>&1 | tail -3 || true
    echo ""

    echo "Building MANA (this may take a few minutes)..."
    echo "Note: .o files compile with mpicc/mpicxx, libmana.so links with GCC"
    echo ""
    if make -j"$(nproc)" 2>&1; then
        echo ""
        echo "MANA build succeeded!"
    else
        echo ""
        echo "Build failed with parallel make. Trying single-threaded..."
        if make 2>&1; then
            echo ""
            echo "MANA build succeeded (single-threaded)!"
        else
            echo "ERROR: MANA build failed"
            echo ""
            echo "Checking if the issue is the Makefile patch..."
            echo "libmana.so link rule:"
            grep -A2 'libmana.so:' "${MANA_MAKEFILE}" | head -3
            echo ""
            echo "MANA_LINK_CXX value:"
            grep 'MANA_LINK_CXX' "${MAKEFILE_CONFIG}" || echo "  (not set)"
            exit 1
        fi
    fi
    echo ""

    # 3g. Verify libmana.so is clean
    echo "--- 3g. Verify build-dir libmana.so ---"
    BUILD_LIBMANA="${MANA_ROOT}/lib/dmtcp/libmana.so"
    if [ -f "${BUILD_LIBMANA}" ]; then
        echo "DT_NEEDED:"
        readelf -d "${BUILD_LIBMANA}" 2>/dev/null | grep NEEDED || true
        echo ""
        if readelf -d "${BUILD_LIBMANA}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"; then
            echo "  *** STILL HAS INTEL RUNTIME DEPS ***"
            echo "  The Makefile patch may not have worked."
            echo "  Checking .comment section:"
            readelf -p .comment "${BUILD_LIBMANA}" 2>/dev/null || true
        else
            echo "  ✓ CLEAN — no Intel runtime deps!"
        fi
    else
        echo "  ERROR: libmana.so not found after build"
    fi
    echo ""

    # 3h. Install MANA
    echo "--- 3h. Install MANA ---"
    make install 2>&1 | tail -5 || true
    echo ""

    # 3i. Post-install: ensure GCC-built libdmtcp.so wasn't overwritten
    echo "--- 3i. Post-install verification ---"
    if [ -f "${INSTALLED_LIBDMTCP}" ]; then
        if readelf -d "${INSTALLED_LIBDMTCP}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"; then
            echo "WARNING: MANA install overwrote libdmtcp.so with Intel version!"
            echo "  Rebuilding standalone DMTCP and reinstalling..."
            cd "${DMTCP_SRC}"
            make -j"$(nproc)" 2>&1 | tail -3
            make install 2>&1 | tail -3
            echo "  Done."
        else
            echo "  OK — installed libdmtcp.so is clean"
        fi
    fi
    echo ""
fi

# ══════════════════════════════════════════════════════════════════════════
# PHASE 4: Verify no Intel runtime deps in LD_PRELOAD'd libraries
# ══════════════════════════════════════════════════════════════════════════
echo "================================================================"
echo "  PHASE 4: Verify LD_PRELOAD'd libraries are clean"
echo "================================================================"
echo ""

ALL_CLEAN=1

echo "--- libdmtcp.so ---"
INSTALLED_LIBDMTCP="${INSTALL_PREFIX}/lib/dmtcp/libdmtcp.so"
if [ -f "${INSTALLED_LIBDMTCP}" ]; then
    echo "DT_NEEDED:"
    readelf -d "${INSTALLED_LIBDMTCP}" 2>/dev/null | grep NEEDED || true
    echo ""
    if readelf -d "${INSTALLED_LIBDMTCP}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"; then
        echo "  *** FAIL: Has Intel runtime deps ***"
        ALL_CLEAN=0
    else
        echo "  PASS — no Intel runtime deps"
    fi
fi
echo ""

echo "--- libmana.so (installed) ---"
INSTALLED_LIBMANA="${INSTALL_PREFIX}/lib/dmtcp/libmana.so"
if [ -f "${INSTALLED_LIBMANA}" ]; then
    echo "DT_NEEDED:"
    readelf -d "${INSTALLED_LIBMANA}" 2>/dev/null | grep NEEDED || true
    echo ""
    if readelf -d "${INSTALLED_LIBMANA}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"; then
        echo "  *** FAIL: Has Intel runtime deps ***"
        ALL_CLEAN=0
    else
        echo "  PASS — no Intel runtime deps"
    fi
fi
echo ""

echo "--- libmana.so (build-dir) ---"
BUILD_LIBMANA="${MANA_ROOT}/lib/dmtcp/libmana.so"
if [ -f "${BUILD_LIBMANA}" ]; then
    echo "DT_NEEDED:"
    readelf -d "${BUILD_LIBMANA}" 2>/dev/null | grep NEEDED || true
    echo ""
    if readelf -d "${BUILD_LIBMANA}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"; then
        echo "  *** FAIL: Has Intel runtime deps ***"
        ALL_CLEAN=0
    else
        echo "  PASS — no Intel runtime deps"
    fi
fi
echo ""

echo "--- libmpistub.so (installed) ---"
INSTALLED_LIBMPISTUB="${INSTALL_PREFIX}/lib/dmtcp/libmpistub.so"
if [ -f "${INSTALLED_LIBMPISTUB}" ]; then
    echo "DT_NEEDED:"
    readelf -d "${INSTALLED_LIBMPISTUB}" 2>/dev/null | grep NEEDED || true
    echo ""
    if readelf -d "${INSTALLED_LIBMPISTUB}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"; then
        echo "  *** FAIL: Has Intel runtime deps ***"
        ALL_CLEAN=0
    else
        echo "  PASS — no Intel runtime deps"
    fi
fi
echo ""

if [ "${ALL_CLEAN}" -eq 0 ]; then
    echo "*** SOME LIBRARIES STILL HAVE INTEL RUNTIME DEPS ***"
    echo "The fix may not work. Proceeding with tests anyway..."
else
    echo "✓ All LD_PRELOAD'd libraries are clean!"
fi
echo ""

# ══════════════════════════════════════════════════════════════════════════
# PHASE 5: Test MANA
# ══════════════════════════════════════════════════════════════════════════
echo "================================================================"
echo "  PHASE 5: Test MANA"
echo "================================================================"
echo ""

COORD_PORT=7920
COORD_HOST="$(hostname)"
CKPT_DIR="${OUTDIR}/ckpt"
mkdir -p "${CKPT_DIR}"

# Kill any stale coordinators
pkill -f "dmtcp_coordinator.*${COORD_PORT}" 2>/dev/null || true
sleep 0.5

# 5a. Quick DMTCP test (non-MPI)
echo "--- 5a. Quick DMTCP test (non-MPI) ---"
cat > "${OUTDIR}/hello.c" << 'EOF'
#include <stdio.h>
#include <unistd.h>
int main() {
    printf("Hello from DMTCP test (pid=%d)\n", getpid());
    fflush(stdout);
    return 0;
}
EOF

${GCC_CC} -o "${OUTDIR}/hello" "${OUTDIR}/hello.c" 2>&1

echo "Test: LD_PRELOAD=libdmtcp.so hello"
if timeout 5 env LD_PRELOAD="${INSTALL_PREFIX}/lib/dmtcp/libdmtcp.so" "${OUTDIR}/hello" 2>&1; then
    echo "  PASS"
else
    RC=$?
    echo "  Exit code: ${RC}"
    if [ "${RC}" -eq 124 ]; then
        echo "  FAIL: Process timed out (DMTCP still hanging!)"
        echo "  Cannot proceed — DMTCP itself is broken."
        exit 1
    fi
fi
echo ""

# 5b. Start coordinator
echo "--- 5b. Start coordinator ---"
"${INSTALL_PREFIX}/bin/dmtcp_coordinator" --exit-on-last -q --daemon \
    --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1 || true
sleep 1

# Verify coordinator
if "${INSTALL_PREFIX}/bin/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" -s 2>/dev/null; then
    echo "  Coordinator running on ${COORD_HOST}:${COORD_PORT}"
else
    echo "  WARNING: Could not verify coordinator"
fi
echo ""

# 5c. DMTCP launch test (non-MPI)
echo "--- 5c. dmtcp_launch test (non-MPI) ---"
if timeout 10 "${INSTALL_PREFIX}/bin/dmtcp_launch" \
    -h "${COORD_HOST}" -p "${COORD_PORT}" \
    --no-gzip --join-coordinator \
    "${OUTDIR}/hello" 2>&1; then
    echo "  PASS"
else
    RC=$?
    echo "  Exit code: ${RC}"
    if [ "${RC}" -eq 124 ]; then
        echo "  FAIL: dmtcp_launch timed out"
    fi
fi
echo ""

# 5d. MANA test with built-in test binary
echo "--- 5d. MANA test with built-in test binary ---"

# Restart coordinator (it may have exited with --exit-on-last)
pkill -f "dmtcp_coordinator.*${COORD_PORT}" 2>/dev/null || true
sleep 0.5
"${INSTALL_PREFIX}/bin/dmtcp_coordinator" --exit-on-last -q --daemon \
    --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1 || true
sleep 1

MANA_TEST=$(find "${MANA_ROOT}/mpi-proxy-split/test" -name "*.mana.exe" -type f 2>/dev/null | head -1)
if [ -z "${MANA_TEST}" ]; then
    MANA_TEST=$(find "${MANA_ROOT}" -name "*.mana.exe" -type f 2>/dev/null | head -1)
fi

MANA_EXIT=1
if [ -n "${MANA_TEST}" ]; then
    echo "Test binary: ${MANA_TEST}"
    echo "Linkage:"
    readelf -d "${MANA_TEST}" 2>/dev/null | grep NEEDED || true
    echo ""

    echo "Running: mpiexec -np 1 mana_launch ${MANA_TEST}"
    timeout 30 mpiexec -np 1 \
        "${MANA_BIN}/mana_launch" --verbose \
        --coord-host "${COORD_HOST}" --coord-port "${COORD_PORT}" \
        --ckptdir "${CKPT_DIR}" --no-gzip \
        "${MANA_TEST}" \
        > "${OUTDIR}/test_mana_stdout.txt" \
        2> "${OUTDIR}/test_mana_stderr.txt"
    MANA_EXIT=$?

    echo ""
    echo "Exit code: ${MANA_EXIT}"
    echo "--- stdout ---"
    cat "${OUTDIR}/test_mana_stdout.txt" 2>/dev/null || echo "  (empty)"
    echo "--- stderr (last 30 lines) ---"
    tail -30 "${OUTDIR}/test_mana_stderr.txt" 2>/dev/null || echo "  (empty)"
    echo ""

    if [ "${MANA_EXIT}" -eq 0 ]; then
        echo "✓ MANA TEST PASSED!"
    elif [ "${MANA_EXIT}" -eq 139 ] || [ "${MANA_EXIT}" -eq 11 ]; then
        echo "✗ MANA TEST SIGSEGV — proceeding to strace diagnosis"
    else
        echo "✗ MANA TEST FAILED (exit=${MANA_EXIT})"
    fi
else
    echo "No .mana.exe test binary found. Skipping."
    MANA_EXIT=1
fi
echo ""

# ══════════════════════════════════════════════════════════════════════════
# PHASE 6: Strace diagnosis (if MANA test failed)
# ══════════════════════════════════════════════════════════════════════════
if [ "${MANA_EXIT:-1}" -ne 0 ] && [ -n "${MANA_TEST:-}" ]; then
    echo "================================================================"
    echo "  PHASE 6: Strace diagnosis"
    echo "================================================================"
    echo ""

    # Restart coordinator
    pkill -f "dmtcp_coordinator.*${COORD_PORT}" 2>/dev/null || true
    sleep 0.5
    "${INSTALL_PREFIX}/bin/dmtcp_coordinator" --exit-on-last -q --daemon \
        --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1 || true
    sleep 1

    STRACE_LOG="${OUTDIR}/mana_strace.log"
    echo "Running MANA test under strace..."
    echo "Strace log: ${STRACE_LOG}"
    echo ""

    timeout 30 strace -ff -o "${STRACE_LOG}" \
        mpiexec -np 1 \
        "${MANA_BIN}/mana_launch" --verbose \
        --coord-host "${COORD_HOST}" --coord-port "${COORD_PORT}" \
        --ckptdir "${CKPT_DIR}" --no-gzip \
        "${MANA_TEST}" 2>&1 || true

    echo ""
    echo "--- Strace analysis ---"

    # Find the PID that crashed
    CRASH_PID=""
    for f in ${STRACE_LOG}.*; do
        if [ -f "$f" ] && grep -q 'SIGSEGV' "$f" 2>/dev/null; then
            CRASH_PID=$(basename "$f" | sed "s/.*\\.//")
            echo "Crash found in PID ${CRASH_PID} (file: $f)"
            break
        fi
    done

    if [ -n "${CRASH_PID}" ]; then
        CRASH_FILE="${STRACE_LOG}.${CRASH_PID}"

        echo ""
        echo "SIGSEGV details:"
        grep 'SIGSEGV' "${CRASH_FILE}" 2>/dev/null || true
        echo ""

        echo "/proc/self/environ opens:"
        ENVIRON_COUNT=$(grep -c 'proc/self/environ' "${CRASH_FILE}" 2>/dev/null || echo 0)
        echo "  Count: ${ENVIRON_COUNT}"
        if [ "${ENVIRON_COUNT}" -gt 100 ]; then
            echo "  *** INFINITE LOOP STILL PRESENT — Intel runtime recursion ***"
            echo "  This means libmana.so or another LD_PRELOAD'd library"
            echo "  still has Intel runtime dependencies."
            echo ""
            echo "  Check which library has Intel deps:"
            echo "  readelf -d ${INSTALLED_LIBMANA}"
            readelf -d "${INSTALLED_LIBMANA}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}" || echo "    (none)"
            echo "  readelf -d ${INSTALLED_LIBDMTCP}"
            readelf -d "${INSTALLED_LIBDMTCP}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}" || echo "    (none)"
        else
            echo "  OK — no infinite loop (Intel runtime fix worked!)"
            echo "  The crash is from a different cause."
        fi
        echo ""

        echo "Last 15 strace lines before crash:"
        tail -15 "${CRASH_FILE}" 2>/dev/null || true
        echo ""

        echo "mmap/mprotect calls near crash:"
        grep -E 'mmap|mprotect' "${CRASH_FILE}" 2>/dev/null | tail -10 || true
    else
        echo "No SIGSEGV found in strace logs."
        echo "Strace files:"
        ls -la ${STRACE_LOG}.* 2>/dev/null || echo "  (none)"
    fi
    echo ""
fi

# ══════════════════════════════════════════════════════════════════════════
# Cleanup
# ══════════════════════════════════════════════════════════════════════════
pkill -f "dmtcp_coordinator.*${COORD_PORT}" 2>/dev/null || true

echo "================================================================"
echo "  COMPLETE"
echo "================================================================"
echo ""
echo "Output directory: ${OUTDIR}"
echo ""
if [ "${MANA_EXIT:-1}" -eq 0 ]; then
    echo "RESULT: SUCCESS — MANA is working!"
    echo ""
    echo "Next steps:"
    echo "  1. Build your app with MANA stub mode (link against libmpistub.so)"
    echo "  2. Run with: mpiexec -np N mana_launch --coord-host HOST --coord-port PORT your_app"
else
    echo "RESULT: MANA test did not pass."
    echo ""
    echo "Check the output above for details."
    echo "If the /proc/self/environ loop is gone but there's a different crash,"
    echo "the Intel runtime fix worked but there may be another MANA issue."
fi
