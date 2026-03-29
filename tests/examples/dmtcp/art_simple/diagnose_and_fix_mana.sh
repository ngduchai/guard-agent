#!/usr/bin/env bash
# ============================================================================
# diagnose_and_fix_mana.sh – Comprehensive MANA diagnosis and fix for Aurora
#
# THREE ROOT CAUSES (all fixed by this script):
#
# ROOT CAUSE #1: libdmtcp.so built with Intel icx
#   - Links libintlc.so.5 whose __intel_cpu_features_init_body calls openat()
#   - DMTCP wraps openat() → triggers Intel runtime init → infinite recursion
#   - FIX: Rebuild DMTCP (standalone + MANA's embedded copy) with GCC
#
# ROOT CAUSE #2: libmana.so and libmpistub.so built with Intel icx/icpx
#   - Same infinite recursion via openat("/proc/self/environ")
#   - Stack overflow → SIGSEGV at guard page 0x80fff000
#   - FIX: Compile ALL MANA .o files with GCC (MPICC=gcc, MPICXX=g++)
#     and link shared libs with GCC (MANA_LINK_CXX, MANA_LINK_CC)
#   - Lower-half needs real MPI → uses LH_MPICC/LH_MPICXX = mpicc/mpicxx
#
# ROOT CAUSE #3: procselfmaps.cpp parser crash on anon_inode:i915.gem
#   - Aurora /proc/self/maps has hundreds of "anon_inode:i915.gem" entries
#   - DMTCP parser only handles names starting with '/', '[', or '('
#   - "anon_inode:" starts with 'a' → parser skips name → JASSERT fails
#   - FIX: Change condition to handle ANY non-newline char as valid name
#
# USAGE:
#   # On Aurora compute node (inside PBS job):
#   bash diagnose_and_fix_mana.sh
#
#   # Force full rebuild even if libraries look clean:
#   bash diagnose_and_fix_mana.sh --force
# ============================================================================

set -euo pipefail

FORCE_REBUILD=0
if [ "${1:-}" = "--force" ]; then
    FORCE_REBUILD=1
fi

INSTALL_PREFIX="${HOME}/.local"
SRC_DIR="${INSTALL_PREFIX}/share/guard-agent/dmtcp-src"
DMTCP_SRC="${SRC_DIR}/dmtcp"
MANA_ROOT="${SRC_DIR}/mana"
MANA_DMTCP="${MANA_ROOT}/dmtcp"
MANA_BIN="${MANA_ROOT}/bin"
MANA_LIB="${MANA_ROOT}/lib/dmtcp"
OUTDIR="${HOME}/diaspora/guard-agent/build/mana_fix_output"

mkdir -p "${OUTDIR}"

export HWLOC_COMPONENTS="-linuxio"

echo "============================================================"
echo "  MANA Diagnosis & Fix for Aurora"
echo "  (All 3 root causes: Intel runtime + procselfmaps parser)"
echo "============================================================"
echo ""
echo "Date: $(date)"
echo "Host: $(hostname)"
echo "Force rebuild: ${FORCE_REBUILD}"
echo ""

# ══════════════════════════════════════════════════════════════════════════
# Find GCC
# ══════════════════════════════════════════════════════════════════════════
_find_gcc() {
    local gcc_path=""
    # Try GCC 13 first, then any GCC 10+
    gcc_path=$(find /opt/aurora -name "gcc" -path "*/gcc-13*/bin/gcc" 2>/dev/null | head -1)
    if [ -z "${gcc_path}" ]; then
        gcc_path=$(find /opt/aurora -name "gcc" -path "*/gcc-12*/bin/gcc" 2>/dev/null | head -1)
    fi
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
    echo "ERROR: Cannot find GCC on this system"
    exit 1
fi
GCC_CXX=$(echo "${GCC_CC}" | sed 's|/gcc$|/g++|')
GCC_DIR=$(dirname "${GCC_CC}")

echo "GCC CC:  ${GCC_CC}"
echo "GCC CXX: ${GCC_CXX}"
echo "GCC version: $(${GCC_CC} --version 2>/dev/null | head -1)"
echo ""

# Verify g++ exists
if [ ! -x "${GCC_CXX}" ]; then
    echo "ERROR: g++ not found at ${GCC_CXX}"
    exit 1
fi

INTEL_LIBS_PATTERN="libsvml\.so|libirng\.so|libimf\.so|libintlc\.so"

# ══════════════════════════════════════════════════════════════════════════
# Extract MPI flags from mpicc -show
# ══════════════════════════════════════════════════════════════════════════
echo "--- MPI compiler info ---"
MPICC_SHOW=$(mpicc -show 2>/dev/null || echo "")
echo "mpicc -show: ${MPICC_SHOW}"

# Extract include flags (-I...)
MPI_INC_FLAGS=$(echo "${MPICC_SHOW}" | grep -oP '\-I\S+' | tr '\n' ' ')
# Extract link flags (-L..., -l..., -Wl,...)
MPI_LINK_FLAGS=$(echo "${MPICC_SHOW}" | grep -oP '(\-L\S+|\-l\S+|\-Wl,\S+)' | tr '\n' ' ')

echo "MPI include flags: ${MPI_INC_FLAGS}"
echo "MPI link flags: ${MPI_LINK_FLAGS}"
echo ""

# ══════════════════════════════════════════════════════════════════════════
# PHASE 1: Diagnose current state
# ══════════════════════════════════════════════════════════════════════════
echo "================================================================"
echo "  PHASE 1: Diagnose current state"
echo "================================================================"
echo ""

DMTCP_NEEDS_REBUILD=0
MANA_NEEDS_REBUILD=0
PROCSELFMAPS_NEEDS_PATCH=0

echo "--- 1a. Installed libdmtcp.so ---"
INSTALLED_LIBDMTCP="${INSTALL_PREFIX}/lib/dmtcp/libdmtcp.so"
if [ -f "${INSTALLED_LIBDMTCP}" ]; then
    if readelf -d "${INSTALLED_LIBDMTCP}" 2>/dev/null | grep -qE "${INTEL_LIBS_PATTERN}"; then
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
    if readelf -d "${INSTALLED_LIBMANA}" 2>/dev/null | grep -qE "${INTEL_LIBS_PATTERN}"; then
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
    if readelf -d "${INSTALLED_LIBMPISTUB}" 2>/dev/null | grep -qE "${INTEL_LIBS_PATTERN}"; then
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

echo "--- 1d. procselfmaps.cpp parser ---"
# Check both DMTCP copies for the parser bug
for PSMAP in "${MANA_DMTCP}/src/procselfmaps.cpp" "${DMTCP_SRC}/src/procselfmaps.cpp"; do
    if [ -f "${PSMAP}" ]; then
        if grep -q "data\[dataIdx\] == '/'" "${PSMAP}" 2>/dev/null; then
            echo "  ${PSMAP}:"
            echo "    *** NEEDS PATCH — only handles '/', '[', '(' names ***"
            PROCSELFMAPS_NEEDS_PATCH=1
        else
            echo "  ${PSMAP}: OK — already patched"
        fi
    else
        echo "  ${PSMAP}: NOT FOUND"
    fi
done
echo ""

echo "=== DIAGNOSIS SUMMARY ==="
echo "  DMTCP needs rebuild (Intel deps):     ${DMTCP_NEEDS_REBUILD}"
echo "  MANA needs rebuild (Intel deps):      ${MANA_NEEDS_REBUILD}"
echo "  procselfmaps.cpp needs patch:         ${PROCSELFMAPS_NEEDS_PATCH}"
echo "  Force rebuild:                        ${FORCE_REBUILD}"
echo ""

# Determine if we need to do anything
NEEDS_WORK=0
if [ "${DMTCP_NEEDS_REBUILD}" -eq 1 ] || [ "${MANA_NEEDS_REBUILD}" -eq 1 ] || \
   [ "${PROCSELFMAPS_NEEDS_PATCH}" -eq 1 ] || [ "${FORCE_REBUILD}" -eq 1 ]; then
    NEEDS_WORK=1
fi

if [ "${NEEDS_WORK}" -eq 0 ]; then
    echo "All libraries are clean and patched. Skipping to test phase."
    echo ""
fi

# ══════════════════════════════════════════════════════════════════════════
# PHASE 2: Patch procselfmaps.cpp (ROOT CAUSE #3)
# ══════════════════════════════════════════════════════════════════════════
if [ "${PROCSELFMAPS_NEEDS_PATCH}" -eq 1 ] || [ "${FORCE_REBUILD}" -eq 1 ]; then
    echo "================================================================"
    echo "  PHASE 2: Patch procselfmaps.cpp (ROOT CAUSE #3)"
    echo "================================================================"
    echo ""
    echo "  Aurora /proc/self/maps contains 'anon_inode:i915.gem' entries."
    echo "  DMTCP's parser only handles names starting with '/', '[', '('."
    echo "  Fix: accept ANY non-newline character as start of a name."
    echo ""

    for PSMAP in "${MANA_DMTCP}/src/procselfmaps.cpp" "${DMTCP_SRC}/src/procselfmaps.cpp"; do
        if [ ! -f "${PSMAP}" ]; then
            echo "  SKIP: ${PSMAP} not found"
            continue
        fi

        echo "  Patching: ${PSMAP}"
        echo "  Before:"
        grep -n "data\[dataIdx\] == '/'" "${PSMAP}" 2>/dev/null | head -3 || echo "    (pattern not found)"

        # The original line is:
        #   if (data[dataIdx] == '/' || data[dataIdx] == '[' || data[dataIdx] == '(') {
        # Replace with:
        #   if (data[dataIdx] != '\n') {
        #
        # Use a Python one-liner for reliable replacement (sed quoting is fragile here)
        python3 -c "
import sys
path = sys.argv[1]
with open(path, 'r') as f:
    content = f.read()
old = \"if (data[dataIdx] == '/' || data[dataIdx] == '[' || data[dataIdx] == '(') {\"
new = \"if (data[dataIdx] != '\\\\n') { // patched: handle anon_inode:* and other non-standard names\"
if old in content:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print('  Patched successfully')
else:
    print('  Pattern not found (may already be patched)')
" "${PSMAP}"

        echo "  After:"
        grep -n "data\[dataIdx\]" "${PSMAP}" | grep -E "!= |== '/'" | head -3 || echo "    (check manually)"
        echo ""
    done
fi

# ══════════════════════════════════════════════════════════════════════════
# PHASE 3: Rebuild DMTCP with GCC (ROOT CAUSE #1)
# ══════════════════════════════════════════════════════════════════════════
if [ "${DMTCP_NEEDS_REBUILD}" -eq 1 ] || [ "${PROCSELFMAPS_NEEDS_PATCH}" -eq 1 ] || [ "${FORCE_REBUILD}" -eq 1 ]; then
    echo "================================================================"
    echo "  PHASE 3: Rebuild DMTCP with GCC"
    echo "================================================================"
    echo ""

    echo "--- 3a. Rebuild standalone DMTCP ---"
    cd "${DMTCP_SRC}"
    make distclean 2>/dev/null || make clean 2>/dev/null || true
    CC="${GCC_CC}" CXX="${GCC_CXX}" ./configure --prefix="${INSTALL_PREFIX}" 2>&1 | tail -5
    make -j"$(nproc)" 2>&1 | tail -5
    echo "  Build exit: $?"
    make install 2>&1 | tail -3
    echo ""

    if readelf -d "${INSTALL_PREFIX}/lib/dmtcp/libdmtcp.so" 2>/dev/null | grep -qE "${INTEL_LIBS_PATTERN}"; then
        echo "  ERROR: libdmtcp.so still has Intel deps after rebuild!"
        exit 1
    fi
    echo "  ✓ Standalone libdmtcp.so is clean"
    echo ""

    echo "--- 3b. Reconfigure MANA's embedded DMTCP ---"
    if [ -d "${MANA_DMTCP}" ]; then
        cd "${MANA_DMTCP}"
        make distclean 2>/dev/null || make clean 2>/dev/null || true
        CC="${GCC_CC}" CXX="${GCC_CXX}" ./configure \
            --prefix="${INSTALL_PREFIX}" \
            --disable-dlsym-wrapper 2>&1 | tail -5
        make -j"$(nproc)" 2>&1 | tail -5
        echo "  Build exit: $?"
        echo "  ✓ Embedded DMTCP reconfigured and rebuilt with GCC"
    fi
    echo ""
fi

# ══════════════════════════════════════════════════════════════════════════
# PHASE 4: Fix MANA build (ROOT CAUSE #2)
# ══════════════════════════════════════════════════════════════════════════
if [ "${MANA_NEEDS_REBUILD}" -eq 1 ] || [ "${PROCSELFMAPS_NEEDS_PATCH}" -eq 1 ] || [ "${FORCE_REBUILD}" -eq 1 ]; then
    echo "================================================================"
    echo "  PHASE 4: Fix MANA build (GCC compilation + linking)"
    echo "================================================================"
    echo ""

    cd "${MANA_ROOT}"

    # 4a. Write Makefile_config with GCC for compilation AND linking
    echo "--- 4a. Write Makefile_config ---"
    MAKEFILE_CONFIG="${MANA_ROOT}/mpi-proxy-split/Makefile_config"
    cat > "${MAKEFILE_CONFIG}" << MKEOF
# Aurora (ALCF) – Cray MPICH + Intel GPU
# Auto-generated by diagnose_and_fix_mana.sh
#
# KEY DESIGN:
#   MPICC/MPICXX = GCC + MPI include flags (for .o compilation)
#   LH_MPICC/LH_MPICXX = real mpicc/mpicxx (for lower-half, needs -lmpi)
#   MANA_LINK_CXX/MANA_LINK_CC = GCC (for libmana.so/libmpistub.so linking)
#
# This avoids Intel runtime (libintlc.so.5) being linked into any
# LD_PRELOAD'd library, preventing the openat() infinite recursion.

CFLAGS = -g -O2 -std=gnu11
CXXFLAGS = -g -O2
FFLAGS = \${CXXFLAGS} -fallow-argument-mismatch

IS_AURORA = 1

# GCC with MPI headers for compiling .o files
# (avoids _intel_fast_memcpy and other Intel runtime symbols)
MPICC  = ${GCC_CC} ${MPI_INC_FLAGS}
MPICXX = ${GCC_CXX} -std=c++14 ${MPI_INC_FLAGS}
MPIFORTRAN = mpifort

# Real MPI compiler wrappers for lower-half (needs implicit -lmpi)
LH_MPICC  = mpicc
LH_MPICXX = mpicxx -std=c++14

MPI_LD_FLAG = ${MPI_LINK_FLAGS}
MPIRUN = mpiexec

MPI_CFLAGS  ?= -g -O2 -std=gnu11 -g3 -fPIC
MPI_CXXFLAGS ?= -g -O2 -g3 -fPIC
MPI_LDFLAGS ?= ${MPI_LINK_FLAGS}

# GCC linkers for shared libs (avoids Intel runtime deps)
MANA_LINK_CXX = ${GCC_CXX}
MANA_LINK_CC = ${GCC_CC}
MKEOF
    echo "  Written: ${MAKEFILE_CONFIG}"
    echo ""

    # 4b. Patch mpi-proxy-split/Makefile for libmana.so
    echo "--- 4b. Patch mpi-proxy-split/Makefile ---"
    MANA_MAKEFILE="${MANA_ROOT}/mpi-proxy-split/Makefile"

    # Add MANA_LINK_CXX default after include
    if ! grep -q 'MANA_LINK_CXX' "${MANA_MAKEFILE}"; then
        sed -i '/^include.*Makefile_config/a \
MANA_LINK_CXX ?= ${CXX}' "${MANA_MAKEFILE}"
        echo "  Added MANA_LINK_CXX default"
    fi

    # Replace ${CXX} with ${MANA_LINK_CXX} in libmana.so link rule
    if grep -q '${CXX} -shared -fPIC' "${MANA_MAKEFILE}"; then
        sed -i 's|\t${CXX} -shared -fPIC|\t${MANA_LINK_CXX} -shared -fPIC|' "${MANA_MAKEFILE}"
        echo "  Patched libmana.so link: \${CXX} → \${MANA_LINK_CXX}"
    elif grep -q '${MANA_LINK_CXX} -shared -fPIC' "${MANA_MAKEFILE}"; then
        echo "  libmana.so link already patched"
    fi

    # 4c. Patch mpi-wrappers/Makefile for libmpistub.so
    echo "--- 4c. Patch mpi-wrappers/Makefile ---"
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
            echo "  Added MANA_LINK_CC default"
        fi

        # Replace ${CC} with ${MANA_LINK_CC} in libmpistub.so link rule
        if grep -q '${CC} -fPIC.*-shared' "${WRAPPERS_MAKEFILE}" || \
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

    # 4d. Patch lower-half/Makefile for LH_MPICXX/LH_MPICC
    echo "--- 4d. Patch lower-half/Makefile ---"
    LH_MAKEFILE="${MANA_ROOT}/mpi-proxy-split/lower-half/Makefile"
    if [ -f "${LH_MAKEFILE}" ]; then
        # Add LH_MPICXX/LH_MPICC defaults after include
        if ! grep -q 'LH_MPICXX' "${LH_MAKEFILE}"; then
            sed -i '/^include.*Makefile_config/a \
LH_MPICXX ?= ${MPICXX}\
LH_MPICC ?= ${MPICC}' "${LH_MAKEFILE}"
            echo "  Added LH_MPICXX/LH_MPICC defaults"
        fi

        # Replace ${MPICXX} with ${LH_MPICXX} in compile/link rules
        # (but NOT in the include line or variable definitions)
        if grep -q '${MPICXX}' "${LH_MAKEFILE}"; then
            # Only replace in recipe lines (starting with tab)
            sed -i '/^\t/s|\${MPICXX}|\${LH_MPICXX}|g' "${LH_MAKEFILE}"
            echo "  Patched lower-half: \${MPICXX} → \${LH_MPICXX} in recipes"
        fi
        if grep -q '${MPICC}' "${LH_MAKEFILE}"; then
            sed -i '/^\t/s|\${MPICC}|\${LH_MPICC}|g' "${LH_MAKEFILE}"
            echo "  Patched lower-half: \${MPICC} → \${LH_MPICC} in recipes"
        fi
    fi
    echo ""

    echo "Verify patched rules:"
    echo "  libmana.so link:"
    grep -A1 'libmana.so:' "${MANA_MAKEFILE}" 2>/dev/null | head -2
    echo "  libmpistub.so link:"
    grep -A1 'libmpistub.so:' "${WRAPPERS_MAKEFILE}" 2>/dev/null | head -2
    echo "  lower-half compile (first recipe line):"
    grep -m1 'LH_MPICXX\|MPICXX' "${LH_MAKEFILE}" 2>/dev/null | head -1
    echo ""

    # 4e. Apply MANA source patches
    echo "--- 4e. Apply MANA source patches ---"

    # Patch 1: mpi_nextfunc.h — &MPI_##func → &PMPI_##func
    NEXTFUNC_H="mpi-proxy-split/mpi-wrappers/mpi_nextfunc.h"
    if [ -f "${NEXTFUNC_H}" ] && grep -q '&MPI_##func' "${NEXTFUNC_H}"; then
        sed -i 's/\&MPI_##func/\&PMPI_##func/g' "${NEXTFUNC_H}"
        echo "  Patched ${NEXTFUNC_H}: &MPI_##func → &PMPI_##func"
    fi

    # Patch 2: record-replay.h — same
    RR_H="mpi-proxy-split/mpi-wrappers/record-replay.h"
    if [ -f "${RR_H}" ] && grep -q '&MPI_##func' "${RR_H}"; then
        sed -i 's/\&MPI_##func/\&PMPI_##func/g' "${RR_H}"
        echo "  Patched ${RR_H}"
    fi

    # Patch 3: PMPI_MANA_Internal compat define
    MANA_INTERNAL_H="mpi-proxy-split/mpi-wrappers/mpi_nextfunc.h"
    if [ -f "${MANA_INTERNAL_H}" ] && ! grep -q 'PMPI_MANA_Internal' "${MANA_INTERNAL_H}"; then
        sed -i '1i #define PMPI_MANA_Internal MPI_MANA_Internal' "${MANA_INTERNAL_H}"
        echo "  Added PMPI_MANA_Internal compat define"
    fi

    # Patch 4: switch-context.cpp — rex.W → .byte 0x48
    SWITCH_CTX="mpi-proxy-split/lower-half/switch-context.cpp"
    if [ -f "${SWITCH_CTX}" ] && grep -q 'rex\.W' "${SWITCH_CTX}"; then
        sed -i 's/rex\.W/.byte 0x48/g' "${SWITCH_CTX}"
        echo "  Patched ${SWITCH_CTX}: rex.W → .byte 0x48"
    fi

    # Patch 5: copy-stack.c — void* → char* for pointer arithmetic
    COPY_STACK="mpi-proxy-split/lower-half/copy-stack.c"
    if [ -f "${COPY_STACK}" ] && grep -q 'void \*sp = ' "${COPY_STACK}"; then
        sed -i 's/void \*sp = /char *sp = (char*)/g' "${COPY_STACK}"
        echo "  Patched ${COPY_STACK}: void* → char*"
    fi

    # Patch 6: Fix VLA with initializer in wrapper .cpp files
    for f in $(find mpi-proxy-split/mpi-wrappers -name "*.cpp" 2>/dev/null); do
        if grep -q 'int counts\[' "$f" 2>/dev/null; then
            # Check for VLA with initializer like: int counts[n] = {0};
            if grep -qP 'int counts\[\w+\]\s*=\s*\{' "$f" 2>/dev/null; then
                sed -i 's/int counts\[\([^]]*\)\] = {0};/int counts[\1]; memset(counts, 0, sizeof(counts));/' "$f"
                echo "  Patched VLA initializer in $f"
            fi
        fi
    done
    echo ""

    # 4f. Clean and rebuild MANA
    echo "--- 4f. Clean and rebuild MANA ---"
    cd "${MANA_ROOT}"
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
            echo ""
            echo "Check build output above for errors."
            echo "Common issues:"
            echo "  - _intel_fast_memcpy: MPICC still using Intel compiler"
            echo "  - Missing MPI symbols in lower-half: LH_MPICXX not set"
            exit 1
        fi
    fi
    echo ""

    # 4g. Belt-and-suspenders: manually rebuild libmpistub.so with GCC
    echo "--- 4g. Manually rebuild libmpistub.so with GCC ---"
    MPISTUB_SRC="${MANA_ROOT}/mpi-proxy-split/mpi-wrappers"
    MPISTUB_C=$(find "${MPISTUB_SRC}" -name "mpistub.c" -o -name "mpi_stub.c" 2>/dev/null | head -1)
    if [ -z "${MPISTUB_C}" ]; then
        # Try to find the source file used for libmpistub.so
        MPISTUB_C=$(grep -A2 'libmpistub.so:' "${WRAPPERS_MAKEFILE}" 2>/dev/null | grep -oP '\S+\.c' | head -1)
        if [ -n "${MPISTUB_C}" ] && [ ! -f "${MPISTUB_C}" ]; then
            MPISTUB_C="${MPISTUB_SRC}/${MPISTUB_C}"
        fi
    fi

    if [ -n "${MPISTUB_C}" ] && [ -f "${MPISTUB_C}" ]; then
        echo "  Source: ${MPISTUB_C}"
        ${GCC_CC} -fPIC "${MPISTUB_C}" -shared -o "${MANA_LIB}/libmpistub.so" 2>&1
        echo "  ✓ Rebuilt libmpistub.so with GCC"
    else
        echo "  Could not find mpistub source file"
        echo "  Checking if build-dir libmpistub.so is clean..."
        if [ -f "${MANA_LIB}/libmpistub.so" ]; then
            if readelf -d "${MANA_LIB}/libmpistub.so" 2>/dev/null | grep -qE "${INTEL_LIBS_PATTERN}"; then
                echo "  *** WARNING: libmpistub.so still has Intel deps ***"
            else
                echo "  OK — libmpistub.so is clean"
            fi
        fi
    fi
    echo ""

    # 4h. Verify build-dir libraries
    echo "--- 4h. Verify build-dir libraries ---"
    for lib in libmana.so libmpistub.so; do
        LIB_PATH="${MANA_LIB}/${lib}"
        if [ -f "${LIB_PATH}" ]; then
            if readelf -d "${LIB_PATH}" 2>/dev/null | grep -qE "${INTEL_LIBS_PATTERN}"; then
                echo "  ${lib}: *** STILL HAS INTEL DEPS ***"
                readelf -d "${LIB_PATH}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"
            else
                echo "  ${lib}: ✓ CLEAN"
            fi
        else
            echo "  ${lib}: NOT FOUND"
        fi
    done
    echo ""

    # 4i. Install — manually copy critical files
    echo "--- 4i. Install MANA ---"
    # Try make install first (may have errors on Aurora, that's OK)
    make install 2>&1 | tail -5 || true
    echo ""

    # Manually ensure critical files are installed
    echo "--- 4j. Ensure critical files are installed ---"
    mkdir -p "${INSTALL_PREFIX}/lib/dmtcp"
    mkdir -p "${INSTALL_PREFIX}/bin"

    for lib in libmana.so libmpistub.so; do
        SRC="${MANA_LIB}/${lib}"
        DST="${INSTALL_PREFIX}/lib/dmtcp/${lib}"
        if [ -f "${SRC}" ]; then
            cp -f "${SRC}" "${DST}"
            echo "  Copied ${lib}"
        fi
    done

    # Copy symlinks for libmpistub compatibility
    for link in libmpich_intel.so.3.0.1 libmpich_intel.so.3 libmpich_gnu_82.so.3.0.1 libmpich_gnu_82.so.3 libpmi.so.0.5.0 libpmi.so.0; do
        SRC="${MANA_LIB}/${link}"
        DST="${INSTALL_PREFIX}/lib/dmtcp/${link}"
        if [ -L "${SRC}" ] || [ -f "${SRC}" ]; then
            cp -af "${SRC}" "${DST}" 2>/dev/null || true
        fi
    done

    for bin in lower-half mana_launch mana_start_coordinator mana_restart mana_status mana_p2p_update_logs; do
        SRC="${MANA_BIN}/${bin}"
        DST="${INSTALL_PREFIX}/bin/${bin}"
        if [ -f "${SRC}" ]; then
            cp -f "${SRC}" "${DST}"
        fi
    done
    echo "  Copied binaries to ${INSTALL_PREFIX}/bin/"
    echo ""

    # 4k. Post-install: ensure libdmtcp.so wasn't overwritten by MANA's make install
    echo "--- 4k. Post-install verification ---"
    if readelf -d "${INSTALLED_LIBDMTCP}" 2>/dev/null | grep -qE "${INTEL_LIBS_PATTERN}"; then
        echo "  WARNING: libdmtcp.so was overwritten by MANA install! Restoring..."
        cd "${DMTCP_SRC}"
        make install 2>&1 | tail -3
        echo "  Restored standalone libdmtcp.so"
    else
        echo "  ✓ libdmtcp.so is clean"
    fi
    echo ""
fi

# ══════════════════════════════════════════════════════════════════════════
# PHASE 5: Verify all libraries
# ══════════════════════════════════════════════════════════════════════════
echo "================================================================"
echo "  PHASE 5: Verify all libraries"
echo "================================================================"
echo ""

ALL_CLEAN=1
for lib in libdmtcp.so libmana.so libmpistub.so; do
    LIB_PATH="${INSTALL_PREFIX}/lib/dmtcp/${lib}"
    if [ -f "${LIB_PATH}" ]; then
        if readelf -d "${LIB_PATH}" 2>/dev/null | grep -qE "${INTEL_LIBS_PATTERN}"; then
            echo "  ${lib}: *** FAIL — has Intel runtime deps ***"
            readelf -d "${LIB_PATH}" 2>/dev/null | grep -E "${INTEL_LIBS_PATTERN}"
            ALL_CLEAN=0
        else
            echo "  ${lib}: ✓ PASS"
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
# PHASE 6: Test MANA
# ══════════════════════════════════════════════════════════════════════════
echo "================================================================"
echo "  PHASE 6: Test MANA"
echo "================================================================"
echo ""

COORD_PORT=7920
COORD_HOST="$(hostname)"
CKPT_DIR="${OUTDIR}/ckpt"
mkdir -p "${CKPT_DIR}"

pkill -f "dmtcp_coordinator.*${COORD_PORT}" 2>/dev/null || true
sleep 0.5

# 6a. Quick DMTCP test (LD_PRELOAD libdmtcp.so)
echo "--- 6a. Quick DMTCP test ---"
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
    echo "  ✓ PASS"
else
    RC=$?
    if [ "${RC}" -eq 124 ]; then
        echo "  ✗ FAIL: Timed out — DMTCP is broken (Intel runtime loop?)"
        exit 1
    fi
    echo "  Exit code: ${RC} (non-zero but not timeout)"
fi
echo ""

# 6b. Start coordinator
echo "--- 6b. Start coordinator ---"
"${INSTALL_PREFIX}/bin/dmtcp_coordinator" --exit-on-last -q --daemon \
    --coord-port "${COORD_PORT}" --ckptdir "${CKPT_DIR}" 2>&1 || true
sleep 1
"${INSTALL_PREFIX}/bin/dmtcp_command" -h "${COORD_HOST}" --port "${COORD_PORT}" -s 2>/dev/null || true
echo ""

# 6c. dmtcp_launch test
echo "--- 6c. dmtcp_launch test ---"
if timeout 10 "${INSTALL_PREFIX}/bin/dmtcp_launch" \
    -h "${COORD_HOST}" -p "${COORD_PORT}" \
    --no-gzip --join-coordinator \
    "${OUTDIR}/hello" 2>&1; then
    echo "  ✓ PASS"
else
    echo "  Exit code: $?"
fi
echo ""

# 6d. MANA test
echo "--- 6d. MANA test ---"
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

    # Check if test binary links Intel runtime
    if ldd "${MANA_TEST}" 2>/dev/null | grep -qE "${INTEL_LIBS_PATTERN}"; then
        echo "WARNING: Test binary has Intel runtime deps via its dependencies."
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
    elif [ "${MANA_EXIT}" -eq 99 ]; then
        echo "✗ MANA TEST EXIT 99 (DMTCP JASSERT failure)"
        echo "  Check JASSERT logs: ls /tmp/dmtcp-${USER}@$(hostname)/jassertlog.*"
        echo "  Latest JASSERT log:"
        ls -lt /tmp/dmtcp-${USER}@$(hostname)/jassertlog.* 2>/dev/null | head -3
        echo ""
        LATEST_JASSERT=$(ls -t /tmp/dmtcp-${USER}@$(hostname)/jassertlog.* 2>/dev/null | head -1)
        if [ -n "${LATEST_JASSERT}" ]; then
            echo "  Content (last 20 lines):"
            tail -20 "${LATEST_JASSERT}" 2>/dev/null
        fi
    else
        echo "✗ MANA TEST FAILED (exit=${MANA_EXIT})"
    fi
else
    echo "No .mana.exe test binary found."
fi
echo ""

# ══════════════════════════════════════════════════════════════════════════
# PHASE 7: Strace diagnosis (if MANA test failed)
# ══════════════════════════════════════════════════════════════════════════
if [ "${MANA_EXIT:-1}" -ne 0 ] && [ -n "${MANA_TEST:-}" ]; then
    echo "================================================================"
    echo "  PHASE 7: Strace diagnosis"
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
            echo "  *** INFINITE LOOP STILL PRESENT — Intel runtime fix didn't work ***"
        else
            echo "  OK — no infinite loop (Intel runtime fix worked!)"
            echo "  The crash is from a different cause."
        fi
        echo ""

        echo "Last 15 strace lines:"
        tail -15 "${CRASH_FILE}" 2>/dev/null || true
    else
        echo "No SIGSEGV found in strace logs."

        # Check for JASSERT failures (exit code 99)
        for f in ${STRACE_LOG}.*; do
            if [ -f "$f" ] && grep -q 'procselfmaps' "$f" 2>/dev/null; then
                echo "Found procselfmaps reference in PID $(basename "$f" | sed 's/.*\.//'):"
                grep 'procselfmaps' "$f" 2>/dev/null | head -5
                echo ""
            fi
        done

        ls -la ${STRACE_LOG}.* 2>/dev/null | head -10 || echo "  (no strace files)"
    fi
    echo ""

    # Check JASSERT logs
    echo "--- JASSERT logs ---"
    JASSERT_DIR="/tmp/dmtcp-${USER}@$(hostname)"
    if [ -d "${JASSERT_DIR}" ]; then
        echo "JASSERT log directory: ${JASSERT_DIR}"
        ls -lt "${JASSERT_DIR}"/jassertlog.* 2>/dev/null | head -5
        echo ""
        LATEST_JASSERT=$(ls -t "${JASSERT_DIR}"/jassertlog.* 2>/dev/null | head -1)
        if [ -n "${LATEST_JASSERT}" ]; then
            echo "Latest JASSERT log (${LATEST_JASSERT}):"
            echo "--- last 30 lines ---"
            tail -30 "${LATEST_JASSERT}" 2>/dev/null
        fi
    else
        echo "No JASSERT log directory found"
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
    echo "Next steps:"
    echo "  1. Build your app with MANA stub mode:"
    echo "     cmake -DDMTCP_USE_MANA_STUB=ON ..."
    echo "  2. Run with mana_launch:"
    echo "     mana_start_coordinator --coord-port 7920 --ckptdir /tmp/ckpt"
    echo "     mpiexec -np N mana_launch --coord-host \$(hostname) --coord-port 7920 ./your_app"
else
    echo "RESULT: MANA test did not pass (exit=${MANA_EXIT:-unknown})"
    echo ""
    echo "Diagnostics to check:"
    echo "  - Output files: ${OUTDIR}/"
    echo "  - JASSERT logs: /tmp/dmtcp-${USER}@$(hostname)/jassertlog.*"
    echo "  - Strace logs: ${OUTDIR}/mana_strace.log.*"
    echo ""
    echo "If exit=99 and JASSERT mentions procselfmaps:"
    echo "  The procselfmaps.cpp patch may not have been applied correctly."
    echo "  Check: grep 'dataIdx' ${MANA_DMTCP}/src/procselfmaps.cpp | head -5"
fi
