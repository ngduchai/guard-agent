#!/usr/bin/env bash
# ============================================================================
# diagnose_and_fix_mana.sh – Comprehensive MANA diagnosis and fix for Aurora
#
# ROOT CAUSE (discovered via strace analysis):
#   MANA crashes with SIGSEGV at address 0x80fff7f8 (the lower-half's stack
#   guard page). The crash is caused by an infinite recursion loop:
#
#   1. libmana.so and libmpistub.so are built with Intel icx/icpx
#   2. They link Intel runtime (libintlc.so.5, libsvml.so, etc.)
#   3. When loaded, Intel runtime initialization calls openat("/proc/self/environ")
#   4. DMTCP wraps openat() via dmtcp_openat
#   5. dmtcp_openat triggers more Intel runtime code → more openat() calls
#   6. Infinite recursion exhausts the stack → SIGSEGV at guard page
#
# FIX STRATEGY:
#   Patch the MANA Makefiles to use GCC for linking libmana.so and
#   libmpistub.so, while keeping mpicc/mpicxx for .o compilation and
#   lower-half linking (which needs implicit -lmpi from mpicc).
#
#   Specifically:
#   - mpi-proxy-split/Makefile: libmana.so link uses ${CXX} → patch to ${MANA_LINK_CXX}
#   - mpi-proxy-split/mpi-wrappers/Makefile: libmpistub.so link uses ${CC} → patch to ${MANA_LINK_CC}
#   - Set MANA_LINK_CXX and MANA_LINK_CC to GCC in Makefile_config
#
#   The lower-half binary is a separate process (not LD_PRELOAD'd), so Intel
#   runtime deps there are harmless.
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
echo "  (Intel runtime infinite recursion fix)"
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
    if readelf -d "${INSTALLED_LIBDMTCP}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"; then
        echo "  *** HAS INTEL RUNTIME DEPS — needs rebuild ***"
        DMTCP_NEEDS_REBUILD=1
    else
        echo "  OK — no Intel runtime deps"
    fi
else
    echo "  NOT FOUND — needs rebuild"
    DMTCP_NEEDS_REBUILD=1
fi
echo ""

echo "--- 1b. Installed libmana.so ---"
INSTALLED_LIBMANA="${INSTALL_PREFIX}/lib/dmtcp/libmana.so"
if [ -f "${INSTALLED_LIBMANA}" ]; then
    if readelf -d "${INSTALLED_LIBMANA}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"; then
        echo "  *** HAS INTEL RUNTIME DEPS — needs fix ***"
        MANA_NEEDS_REBUILD=1
    else
        echo "  OK — no Intel runtime deps"
    fi
else
    echo "  NOT FOUND — needs rebuild"
    MANA_NEEDS_REBUILD=1
fi
echo ""

echo "--- 1c. Installed libmpistub.so ---"
INSTALLED_LIBMPISTUB="${INSTALL_PREFIX}/lib/dmtcp/libmpistub.so"
if [ -f "${INSTALLED_LIBMPISTUB}" ]; then
    if readelf -d "${INSTALLED_LIBMPISTUB}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"; then
        echo "  *** HAS INTEL RUNTIME DEPS — needs fix ***"
        MANA_NEEDS_REBUILD=1
    else
        echo "  OK — no Intel runtime deps"
    fi
else
    echo "  NOT FOUND — needs rebuild"
    MANA_NEEDS_REBUILD=1
fi
echo ""

echo "--- 1d. Build-dir libmana.so ---"
BUILD_LIBMANA="${MANA_ROOT}/lib/dmtcp/libmana.so"
if [ -f "${BUILD_LIBMANA}" ]; then
    if readelf -d "${BUILD_LIBMANA}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"; then
        echo "  *** HAS INTEL RUNTIME DEPS ***"
    else
        echo "  OK — no Intel runtime deps"
    fi
else
    echo "  NOT FOUND"
fi
echo ""

echo "--- 1e. MPI compiler wrapper ---"
echo "mpicc -show: $(mpicc -show 2>/dev/null || echo 'failed')"
echo ""

echo "=== DIAGNOSIS SUMMARY ==="
echo "  libdmtcp.so needs rebuild: ${DMTCP_NEEDS_REBUILD}"
echo "  libmana.so/libmpistub.so needs fix: ${MANA_NEEDS_REBUILD}"
echo ""

if [ "${DMTCP_NEEDS_REBUILD}" -eq 0 ] && [ "${MANA_NEEDS_REBUILD}" -eq 0 ]; then
    echo "All libraries are clean. Skipping rebuild, going to test phase."
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

    echo "--- 2a. Rebuild standalone DMTCP ---"
    cd "${DMTCP_SRC}"
    make distclean 2>/dev/null || make clean 2>/dev/null || true
    CC="${GCC_CC}" CXX="${GCC_CXX}" ./configure --prefix="${INSTALL_PREFIX}" 2>&1 | tail -3
    make -j"$(nproc)" 2>&1 | tail -5
    make install 2>&1 | tail -3
    echo ""

    if readelf -d "${INSTALL_PREFIX}/lib/dmtcp/libdmtcp.so" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"; then
        echo "  ERROR: Still has Intel deps after rebuild!"
        exit 1
    fi
    echo "  ✓ libdmtcp.so is clean"
    echo ""

    echo "--- 2b. Reconfigure MANA's embedded DMTCP ---"
    MANA_DMTCP="${MANA_ROOT}/dmtcp"
    if [ -d "${MANA_DMTCP}" ]; then
        cd "${MANA_DMTCP}"
        make distclean 2>/dev/null || make clean 2>/dev/null || true
        CC="${GCC_CC}" CXX="${GCC_CXX}" ./configure \
            --prefix="${INSTALL_PREFIX}" \
            --disable-dlsym-wrapper 2>&1 | tail -3
        echo "  ✓ Reconfigured with GCC"
    fi
    echo ""
fi

# ══════════════════════════════════════════════════════════════════════════
# PHASE 3: Fix libmana.so and libmpistub.so
# ══════════════════════════════════════════════════════════════════════════
if [ "${MANA_NEEDS_REBUILD}" -eq 1 ] || [ "${DMTCP_NEEDS_REBUILD}" -eq 1 ]; then
    echo "================================================================"
    echo "  PHASE 3: Fix libmana.so and libmpistub.so"
    echo "================================================================"
    echo ""

    cd "${MANA_ROOT}"

    # 3a. Extract MPI flags
    echo "--- 3a. Extract MPI flags ---"
    MPICC_SHOW=$(mpicc -show 2>/dev/null || echo "")
    MPI_LINK_FLAGS=$(echo "${MPICC_SHOW}" | grep -oP '(\-L\S+|\-l\S+|\-Wl,\S+)' | tr '\n' ' ')
    echo "MPI link flags: ${MPI_LINK_FLAGS}"
    echo ""

    # 3b. Write Makefile_config
    echo "--- 3b. Write Makefile_config ---"
    MAKEFILE_CONFIG="${MANA_ROOT}/mpi-proxy-split/Makefile_config"
    cat > "${MAKEFILE_CONFIG}" << MKEOF
# Aurora (ALCF) – Cray MPICH + Intel GPU
# Auto-generated by diagnose_and_fix_mana.sh
#
# MPICC/MPICXX = mpicc/mpicxx for .o compilation and lower-half linking
# MANA_LINK_CXX/MANA_LINK_CC = GCC for libmana.so/libmpistub.so linking

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

# GCC linkers for shared libs (avoids Intel runtime deps)
MANA_LINK_CXX = ${GCC_CXX}
MANA_LINK_CC = ${GCC_CC}
MKEOF
    echo "  Written."
    echo ""

    # 3c. Patch mpi-proxy-split/Makefile for libmana.so
    echo "--- 3c. Patch Makefiles ---"
    MANA_MAKEFILE="${MANA_ROOT}/mpi-proxy-split/Makefile"

    # Add MANA_LINK_CXX default
    if ! grep -q 'MANA_LINK_CXX' "${MANA_MAKEFILE}"; then
        sed -i '/^include.*Makefile_config/a \
MANA_LINK_CXX ?= ${CXX}' "${MANA_MAKEFILE}"
        echo "  Added MANA_LINK_CXX default to mpi-proxy-split/Makefile"
    fi

    # Replace ${CXX} with ${MANA_LINK_CXX} in libmana.so link rule
    if grep -q '${CXX} -shared -fPIC' "${MANA_MAKEFILE}"; then
        sed -i 's|\t${CXX} -shared -fPIC|\t${MANA_LINK_CXX} -shared -fPIC|' "${MANA_MAKEFILE}"
        echo "  Patched libmana.so link: \${CXX} → \${MANA_LINK_CXX}"
    elif grep -q '${MANA_LINK_CXX} -shared -fPIC' "${MANA_MAKEFILE}"; then
        echo "  libmana.so link already patched"
    fi

    # Patch mpi-wrappers/Makefile for libmpistub.so
    WRAPPERS_MAKEFILE="${MANA_ROOT}/mpi-proxy-split/mpi-wrappers/Makefile"
    if [ -f "${WRAPPERS_MAKEFILE}" ]; then
        # Add MANA_LINK_CC default
        if ! grep -q 'MANA_LINK_CC' "${WRAPPERS_MAKEFILE}"; then
            if grep -q '^include' "${WRAPPERS_MAKEFILE}"; then
                sed -i '/^include/a \
MANA_LINK_CC ?= ${CC}' "${WRAPPERS_MAKEFILE}"
            else
                sed -i '1i MANA_LINK_CC ?= ${CC}' "${WRAPPERS_MAKEFILE}"
            fi
            echo "  Added MANA_LINK_CC default to mpi-wrappers/Makefile"
        fi

        # Replace ${CC} with ${MANA_LINK_CC} in libmpistub.so link rule
        # The rule is: ${CC} -fPIC $< -shared -o $@
        if grep -q '${CC} -fPIC.*-shared.*libmpistub' "${WRAPPERS_MAKEFILE}" || \
           grep -qP '\$\{CC\} -fPIC \$< -shared' "${WRAPPERS_MAKEFILE}"; then
            sed -i 's|\t${CC} -fPIC $< -shared -o $@|\t${MANA_LINK_CC} -fPIC $< -shared -o $@|' "${WRAPPERS_MAKEFILE}"
            echo "  Patched libmpistub.so link: \${CC} → \${MANA_LINK_CC}"
        elif grep -q '${MANA_LINK_CC} -fPIC' "${WRAPPERS_MAKEFILE}"; then
            echo "  libmpistub.so link already patched"
        else
            echo "  WARNING: Could not find libmpistub.so link rule"
            echo "  Current rule:"
            grep -A2 'libmpistub.so:' "${WRAPPERS_MAKEFILE}" || true
        fi
    fi

    echo ""
    echo "Verify patched rules:"
    echo "  libmana.so:"
    grep -A1 'libmana.so:' "${MANA_MAKEFILE}" | head -2
    echo "  libmpistub.so:"
    grep -A1 'libmpistub.so:' "${WRAPPERS_MAKEFILE}" | head -2
    echo ""

    # 3d. Apply source patches
    echo "--- 3d. Apply source patches ---"

    NEXTFUNC_H="mpi-proxy-split/mpi-wrappers/mpi_nextfunc.h"
    if [ -f "${NEXTFUNC_H}" ] && grep -q '&MPI_##func' "${NEXTFUNC_H}"; then
        sed -i 's/\&MPI_##func/\&PMPI_##func/g' "${NEXTFUNC_H}"
        echo "  Patched ${NEXTFUNC_H}: &MPI_##func → &PMPI_##func"
    fi

    RR_H="mpi-proxy-split/mpi-wrappers/record-replay.h"
    if [ -f "${RR_H}" ] && grep -q '&MPI_##func' "${RR_H}"; then
        sed -i 's/\&MPI_##func/\&PMPI_##func/g' "${RR_H}"
        echo "  Patched ${RR_H}"
    fi

    MANA_INTERNAL_H="mpi-proxy-split/mpi-wrappers/mpi_nextfunc.h"
    if [ -f "${MANA_INTERNAL_H}" ] && ! grep -q 'PMPI_MANA_Internal' "${MANA_INTERNAL_H}"; then
        sed -i '1i #define PMPI_MANA_Internal MPI_MANA_Internal' "${MANA_INTERNAL_H}"
        echo "  Added PMPI_MANA_Internal compat define"
    fi

    SWITCH_CTX="mpi-proxy-split/lower-half/switch-context.cpp"
    if [ -f "${SWITCH_CTX}" ] && grep -q 'rex\.W' "${SWITCH_CTX}"; then
        sed -i 's/rex\.W/.byte 0x48/g' "${SWITCH_CTX}"
        echo "  Patched ${SWITCH_CTX}: rex.W → .byte 0x48"
    fi

    COPY_STACK="mpi-proxy-split/lower-half/copy-stack.c"
    if [ -f "${COPY_STACK}" ] && grep -q 'void \*sp = ' "${COPY_STACK}"; then
        sed -i 's/void \*sp = /char *sp = (char*)/g' "${COPY_STACK}"
        echo "  Patched ${COPY_STACK}: void* → char*"
    fi
    echo ""

    # 3e. Clean and rebuild
    echo "--- 3e. Clean and rebuild MANA ---"
    make clean 2>&1 | tail -3 || true
    echo ""

    echo "Building MANA..."
    if make -j"$(nproc)" 2>&1; then
        echo ""
        echo "✓ MANA build succeeded!"
    else
        echo ""
        echo "Parallel build failed. Trying single-threaded..."
        if make 2>&1; then
            echo "✓ MANA build succeeded (single-threaded)!"
        else
            echo "ERROR: MANA build failed"
            exit 1
        fi
    fi
    echo ""

    # 3f. Verify build-dir libraries
    echo "--- 3f. Verify build-dir libraries ---"
    for lib in libmana.so libmpistub.so; do
        LIB_PATH="${MANA_ROOT}/lib/dmtcp/${lib}"
        if [ -f "${LIB_PATH}" ]; then
            if readelf -d "${LIB_PATH}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"; then
                echo "  ${lib}: *** STILL HAS INTEL DEPS ***"
            else
                echo "  ${lib}: ✓ CLEAN"
            fi
        else
            echo "  ${lib}: NOT FOUND"
        fi
    done
    echo ""

    # 3g. Install — use make install, then manually copy if needed
    echo "--- 3g. Install MANA ---"
    make install 2>&1 | tail -5 || true
    echo ""

    # 3h. Manually ensure critical files are installed
    echo "--- 3h. Ensure critical files are installed ---"
    mkdir -p "${INSTALL_PREFIX}/lib/dmtcp"
    mkdir -p "${INSTALL_PREFIX}/bin"

    for lib in libmana.so libmpistub.so; do
        SRC="${MANA_ROOT}/lib/dmtcp/${lib}"
        DST="${INSTALL_PREFIX}/lib/dmtcp/${lib}"
        if [ -f "${SRC}" ]; then
            cp -f "${SRC}" "${DST}"
            echo "  Copied ${lib} to ${DST}"
        fi
    done

    # Copy symlinks for libmpistub compatibility
    for link in libmpich_intel.so.3.0.1 libmpich_intel.so.3 libmpich_gnu_82.so.3.0.1 libmpich_gnu_82.so.3 libpmi.so.0.5.0 libpmi.so.0; do
        SRC="${MANA_ROOT}/lib/dmtcp/${link}"
        DST="${INSTALL_PREFIX}/lib/dmtcp/${link}"
        if [ -L "${SRC}" ] || [ -f "${SRC}" ]; then
            cp -af "${SRC}" "${DST}" 2>/dev/null || true
        fi
    done

    for bin in lower-half mana_launch mana_start_coordinator mana_restart mana_status mana_p2p_update_logs; do
        SRC="${MANA_ROOT}/bin/${bin}"
        DST="${INSTALL_PREFIX}/bin/${bin}"
        if [ -f "${SRC}" ]; then
            cp -f "${SRC}" "${DST}"
        fi
    done
    echo "  Copied binaries to ${INSTALL_PREFIX}/bin/"
    echo ""

    # 3i. Post-install: ensure libdmtcp.so wasn't overwritten
    echo "--- 3i. Post-install verification ---"
    if readelf -d "${INSTALLED_LIBDMTCP}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"; then
        echo "  WARNING: libdmtcp.so overwritten! Restoring..."
        cd "${DMTCP_SRC}"
        make -j"$(nproc)" 2>&1 | tail -3
        make install 2>&1 | tail -3
    else
        echo "  ✓ libdmtcp.so is clean"
    fi
    echo ""
fi

# ══════════════════════════════════════════════════════════════════════════
# PHASE 4: Verify all libraries
# ══════════════════════════════════════════════════════════════════════════
echo "================================================================"
echo "  PHASE 4: Verify all libraries"
echo "================================================================"
echo ""

ALL_CLEAN=1
for lib in libdmtcp.so libmana.so libmpistub.so; do
    LIB_PATH="${INSTALL_PREFIX}/lib/dmtcp/${lib}"
    if [ -f "${LIB_PATH}" ]; then
        if readelf -d "${LIB_PATH}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"; then
            echo "  ${lib}: *** FAIL — has Intel runtime deps ***"
            ALL_CLEAN=0
        else
            echo "  ${lib}: PASS"
        fi
    else
        echo "  ${lib}: MISSING"
        ALL_CLEAN=0
    fi
done
echo ""

if [ "${ALL_CLEAN}" -eq 1 ]; then
    echo "✓ All libraries are clean!"
else
    echo "*** SOME LIBRARIES HAVE ISSUES ***"
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

pkill -f "dmtcp_coordinator.*${COORD_PORT}" 2>/dev/null || true
sleep 0.5

# 5a. Quick DMTCP test
echo "--- 5a. Quick DMTCP test ---"
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

if timeout 5 env LD_PRELOAD="${INSTALL_PREFIX}/lib/dmtcp/libdmtcp.so" "${OUTDIR}/hello" 2>&1; then
    echo "  PASS"
else
    RC=$?
    if [ "${RC}" -eq 124 ]; then
        echo "  FAIL: Timed out — DMTCP is broken"
        exit 1
    fi
    echo "  Exit code: ${RC} (non-zero but not timeout)"
fi
echo ""

# 5b. Start coordinator
echo "--- 5b. Start coordinator ---"
"${INSTALL_PREFIX}/bin/dmtcp_coordinator" --exit-on-last -q --daemon \
    --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1 || true
sleep 1
"${INSTALL_PREFIX}/bin/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" -s 2>/dev/null || true
echo ""

# 5c. dmtcp_launch test
echo "--- 5c. dmtcp_launch test ---"
if timeout 10 "${INSTALL_PREFIX}/bin/dmtcp_launch" \
    -h "${COORD_HOST}" -p "${COORD_PORT}" \
    --no-gzip --join-coordinator \
    "${OUTDIR}/hello" 2>&1; then
    echo "  PASS"
else
    echo "  Exit code: $?"
fi
echo ""

# 5d. MANA test
echo "--- 5d. MANA test ---"
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
    echo "DT_NEEDED:"
    readelf -d "${MANA_TEST}" 2>/dev/null | grep NEEDED || true
    echo ""

    # Check if test binary links libmpistub.so
    if ldd "${MANA_TEST}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"; then
        echo "WARNING: Test binary has Intel runtime deps via its dependencies."
        echo "This may cause the same infinite recursion."
        echo "The test binary may need to be rebuilt."
    fi
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
        echo "✗ MANA TEST SIGSEGV"
    elif [ "${MANA_EXIT}" -eq 124 ]; then
        echo "✗ MANA TEST TIMED OUT"
    else
        echo "✗ MANA TEST FAILED (exit=${MANA_EXIT})"
    fi
else
    echo "No .mana.exe test binary found."
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

    pkill -f "dmtcp_coordinator.*${COORD_PORT}" 2>/dev/null || true
    sleep 0.5
    "${INSTALL_PREFIX}/bin/dmtcp_coordinator" --exit-on-last -q --daemon \
        --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1 || true
    sleep 1

    STRACE_LOG="${OUTDIR}/mana_strace.log"
    echo "Running MANA test under strace..."

    timeout 30 strace -ff -o "${STRACE_LOG}" \
        mpiexec -np 1 \
        "${MANA_BIN}/mana_launch" --verbose \
        --coord-host "${COORD_HOST}" --coord-port "${COORD_PORT}" \
        --ckptdir "${CKPT_DIR}" --no-gzip \
        "${MANA_TEST}" 2>&1 || true

    echo ""
    echo "--- Strace analysis ---"

    CRASH_PID=""
    for f in ${STRACE_LOG}.*; do
        if [ -f "$f" ] && grep -q 'SIGSEGV' "$f" 2>/dev/null; then
            CRASH_PID=$(basename "$f" | sed "s/.*\\.//")
            echo "Crash in PID ${CRASH_PID}"
            break
        fi
    done

    if [ -n "${CRASH_PID}" ]; then
        CRASH_FILE="${STRACE_LOG}.${CRASH_PID}"

        echo "SIGSEGV details:"
        grep 'SIGSEGV' "${CRASH_FILE}" 2>/dev/null || true
        echo ""

        ENVIRON_COUNT=$(grep -c 'proc/self/environ' "${CRASH_FILE}" 2>/dev/null || echo 0)
        echo "/proc/self/environ opens: ${ENVIRON_COUNT}"
        if [ "${ENVIRON_COUNT}" -gt 100 ]; then
            echo "  *** INFINITE LOOP STILL PRESENT ***"
        else
            echo "  OK — no infinite loop (Intel runtime fix worked!)"
            echo "  The crash is from a different cause."
        fi
        echo ""

        echo "Last 15 strace lines:"
        tail -15 "${CRASH_FILE}" 2>/dev/null || true
    else
        echo "No SIGSEGV found in strace logs."
        ls -la ${STRACE_LOG}.* 2>/dev/null || echo "  (no strace files)"
    fi
    echo ""
fi

# ══════════════════════════════════════════════════════════════════════════
# Cleanup & Summary
# ══════════════════════════════════════════════════════════════════════════
pkill -f "dmtcp_coordinator.*${COORD_PORT}" 2>/dev/null || true

echo "================================================================"
echo "  COMPLETE"
echo "================================================================"
echo ""
echo "Output: ${OUTDIR}"
echo ""
if [ "${MANA_EXIT:-1}" -eq 0 ]; then
    echo "RESULT: ✓ SUCCESS — MANA is working!"
    echo ""
    echo "Next: build your app with MANA stub mode and run with mana_launch"
else
    echo "RESULT: MANA test did not pass (exit=${MANA_EXIT:-unknown})"
    echo ""
    echo "If /proc/self/environ loop is gone, the Intel fix worked"
    echo "but there may be another MANA issue."
fi
