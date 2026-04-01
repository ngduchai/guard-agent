#!/usr/bin/env bash
# ============================================================================
# rebuild_mana_openmpi.sh – Rebuild MANA against OpenMPI on Aurora
#
# RATIONALE: MANA's split-process MPI interception doesn't work with
# Cray MPICH 5.0 on Aurora (MPI operations become no-ops).  OpenMPI is
# a better match because MANA was originally developed/tested with it.
#
# This script:
#   1. Locates the OpenMPI installation (built from source to ~/.local)
#   2. Unloads Cray PE modules to avoid conflicts
#   3. Patches Makefile_config to use OpenMPI's compilers
#   4. Applies Aurora-specific source patches
#   5. Applies anon_inode patches for writeckpt.cpp & mtcp_restart.c
#   6. Cleans and rebuilds MANA
#   7. Rebuilds the app (art_simple) against OpenMPI
#   8. Runs a quick smoke test
#
# Usage:
#   bash tests/examples/dmtcp/art_simple/rebuild_mana_openmpi.sh
#
# Prerequisites:
#   - OpenMPI built from source at OPENMPI_PREFIX (default: ~/.local)
#   - GCC available (for DMTCP/MANA core — must not use Intel compiler)
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

OPENMPI_PREFIX="${OPENMPI_PREFIX:-${HOME}/.local}"
MANA_ROOT="${MANA_ROOT:-${HOME}/.local/share/guard-agent/dmtcp-src/mana}"
INSTALL_PREFIX="${HOME}/.local"
COORD_PORT="${COORD_PORT:-7907}"

echo "============================================================"
echo "  Rebuild MANA + DMTCP against OpenMPI"
echo "============================================================"
echo ""
echo "MANA_ROOT:       ${MANA_ROOT}"
echo "OPENMPI_PREFIX:  ${OPENMPI_PREFIX}"
echo "INSTALL_PREFIX:  ${INSTALL_PREFIX}"
echo ""

# ── Validate OpenMPI installation ────────────────────────────────────────
OMPI_MPICC="${OPENMPI_PREFIX}/bin/mpicc"
OMPI_MPICXX="${OPENMPI_PREFIX}/bin/mpicxx"
OMPI_MPIFORT="${OPENMPI_PREFIX}/bin/mpifort"
OMPI_MPIRUN="${OPENMPI_PREFIX}/bin/mpirun"

for tool in "${OMPI_MPICC}" "${OMPI_MPICXX}" "${OMPI_MPIRUN}"; do
    if [[ ! -x "${tool}" ]]; then
        echo "ERROR: OpenMPI tool not found: ${tool}" >&2
        echo "       Install OpenMPI first:" >&2
        echo "         cd /tmp && wget https://download.open-mpi.org/release/open-mpi/v4.1/openmpi-4.1.6.tar.gz" >&2
        echo "         tar xf openmpi-4.1.6.tar.gz && cd openmpi-4.1.6" >&2
        echo "         ./configure --prefix=${OPENMPI_PREFIX} --enable-mpi-fortran CC=gcc CXX=g++ FC=gfortran" >&2
        echo "         make -j\$(nproc) && make install" >&2
        exit 1
    fi
done

echo "OpenMPI compilers:"
echo "  mpicc:   ${OMPI_MPICC}"
echo "  mpicxx:  ${OMPI_MPICXX}"
echo "  mpifort: ${OMPI_MPIFORT:-not found}"
echo "  mpirun:  ${OMPI_MPIRUN}"

# Show OpenMPI version and underlying compiler
echo ""
echo "OpenMPI version:"
"${OMPI_MPICC}" --showme:version 2>&1 || true
echo ""
echo "OpenMPI wraps: $("${OMPI_MPICC}" --showme:command 2>&1 || echo 'unknown')"
echo ""

# ── Find GCC ─────────────────────────────────────────────────────────────
_find_gcc() {
    local _cc=""
    for _candidate in gcc /usr/bin/gcc; do
        if command -v "${_candidate}" >/dev/null 2>&1; then
            if "${_candidate}" -v 2>&1 | grep -qi 'gcc version'; then
                _cc="${_candidate}"; break
            fi
        fi
    done
    # Search Aurora/HPC paths
    if [[ -z "${_cc}" ]]; then
        _cc=$(find /opt/aurora -name "gcc" -path "*/gcc-1[0-9]*/bin/gcc" 2>/dev/null | head -1)
    fi
    echo "${_cc}"
}

GCC_CC="$(_find_gcc)"
if [[ -z "${GCC_CC}" ]]; then
    echo "ERROR: GCC not found. DMTCP/MANA core must be built with GCC." >&2
    exit 1
fi
GCC_CC="$(command -v "${GCC_CC}" 2>/dev/null || echo "${GCC_CC}")"
GCC_CXX="$(echo "${GCC_CC}" | sed 's|/gcc$|/g++|')"
[[ -x "${GCC_CXX}" ]] || GCC_CXX="$(dirname "${GCC_CC}")/g++"
[[ -x "${GCC_CXX}" ]] || GCC_CXX="g++"
echo "GCC: ${GCC_CC} ($(${GCC_CC} --version 2>/dev/null | head -1))"
echo ""

# ── Set up PATH so OpenMPI tools take priority over Cray MPICH ───────────
export PATH="${OPENMPI_PREFIX}/bin:$(dirname "${GCC_CC}"):${PATH}"
export LD_LIBRARY_PATH="${OPENMPI_PREFIX}/lib:${OPENMPI_PREFIX}/lib64:${LD_LIBRARY_PATH:-}"
export PKG_CONFIG_PATH="${OPENMPI_PREFIX}/lib/pkgconfig:${PKG_CONFIG_PATH:-}"

# Verify mpicc is OpenMPI (not Cray)
WHICH_MPICC="$(which mpicc 2>/dev/null || true)"
echo "Active mpicc: ${WHICH_MPICC}"
if [[ "${WHICH_MPICC}" != "${OMPI_MPICC}" ]]; then
    echo "WARNING: mpicc on PATH is not OpenMPI — using explicit paths"
fi
echo ""

if [[ ! -d "${MANA_ROOT}" ]]; then
    echo "ERROR: MANA source not found at ${MANA_ROOT}" >&2
    exit 1
fi

cd "${MANA_ROOT}"

# ── Step 1: Get OpenMPI link flags ──────────────────────────────────────
echo "=== Step 1: Detect OpenMPI configuration ==="
echo ""

# OpenMPI's --showme:libs gives the link flags
OMPI_LIBS="$("${OMPI_MPICC}" --showme:libs 2>/dev/null || echo "-lmpi")"
OMPI_LIBDIRS="$("${OMPI_MPICC}" --showme:libdirs 2>/dev/null || echo "${OPENMPI_PREFIX}/lib")"

# Build MPI_LD_FLAG: -L<libdir> <libs>
MPI_LD_FLAG=""
for d in ${OMPI_LIBDIRS}; do
    MPI_LD_FLAG="${MPI_LD_FLAG} -L${d}"
done
MPI_LD_FLAG="${MPI_LD_FLAG} ${OMPI_LIBS}"
# Add -Wl,-rpath so the lower-half finds OpenMPI at runtime
for d in ${OMPI_LIBDIRS}; do
    MPI_LD_FLAG="${MPI_LD_FLAG} -Wl,-rpath,${d}"
done
MPI_LD_FLAG="$(echo "${MPI_LD_FLAG}" | xargs)"  # trim whitespace

echo "OpenMPI libs:    ${OMPI_LIBS}"
echo "OpenMPI libdirs: ${OMPI_LIBDIRS}"
echo "MPI_LD_FLAG:     ${MPI_LD_FLAG}"
echo ""

# ── Step 2: Write OpenMPI Makefile_config ────────────────────────────────
echo "=== Step 2: Write OpenMPI Makefile_config ==="
echo ""

MAKEFILE_CONFIG="mpi-proxy-split/Makefile_config"

# Backup
if [[ -f "${MAKEFILE_CONFIG}" ]]; then
    cp -v "${MAKEFILE_CONFIG}" "${MAKEFILE_CONFIG}.bak.$(date +%s)"
fi

cat > "${MAKEFILE_CONFIG}" << OPENMPI_EOF
# Makefile_config for Aurora with OpenMPI
# Generated by rebuild_mana_openmpi.sh on $(date)
# OpenMPI ${OPENMPI_PREFIX} + GCC

CFLAGS = -g -O2 -std=gnu11
CXXFLAGS = -g -O2
FFLAGS = \${CXXFLAGS} -fallow-argument-mismatch

PLATFORM=\${shell echo \$\$HOST}
HOSTNAME_FULL := \$(shell hostname 2>/dev/null)

# Force OpenMPI (not Cray MPICH)
MPICC = ${OMPI_MPICC}
MPICXX = ${OMPI_MPICXX} -std=c++14
MPIFORTRAN = ${OMPI_MPIFORT}
MPI_LD_FLAG = ${MPI_LD_FLAG}
MPIRUN = ${OMPI_MPIRUN}
MPI_CFLAGS?= -g -O2 -std=gnu11 -g3 -fPIC
MPI_CXXFLAGS?= -g -O2 -g3 -fPIC
MPI_LDFLAGS?=
OPENMPI_EOF

echo "Written ${MAKEFILE_CONFIG}:"
cat "${MAKEFILE_CONFIG}"
echo ""

# ── Step 3: Apply source patches ────────────────────────────────────────
echo "=== Step 3: Apply source patches ==="
echo ""

# --- 3a. procselfmaps.cpp patch (anon_inode:i915.gem) ---
_patch_procselfmaps() {
    local psmap="$1"
    if [[ ! -f "${psmap}" ]]; then return; fi
    if grep -q "data\[dataIdx\] == '/'" "${psmap}" 2>/dev/null; then
        echo "Patching ${psmap} for anon_inode:* support ..."
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
    print('  [OK] Patched successfully')
else:
    print('  [SKIP] Pattern not found (may already be patched)')
" "${psmap}"
    else
        echo "  [SKIP] procselfmaps.cpp already patched: ${psmap}"
    fi
}

# Patch both standalone DMTCP and MANA's embedded copy
_patch_procselfmaps "${MANA_ROOT}/dmtcp/src/procselfmaps.cpp"

# --- 3b. writeckpt.cpp patch (skip anon_inode: device memory) ---
_patch_writeckpt() {
    local wckpt="$1"
    if [[ ! -f "${wckpt}" ]]; then return; fi
    if grep -q 'anon_inode:' "${wckpt}" 2>/dev/null; then
        echo "  [SKIP] writeckpt.cpp already patched: ${wckpt}"
        return
    fi
    echo "Patching ${wckpt} to skip anon_inode: device memory ..."
    python3 -c "
import sys
path = sys.argv[1]
with open(path, 'r') as f:
    content = f.read()

# Find the right location: inside the skip-region logic in writememoryarea()
# We add a check for anon_inode: regions before the existing skip checks
patch_marker = 'Skip anonymous pages that have no backing store'
if patch_marker in content:
    # Insert before the anonymous pages check
    insert_point = content.index(patch_marker)
    # Go back to find the start of the if/comment block
    line_start = content.rfind('\\n', 0, insert_point) + 1
    indent = '      '
    patch_code = '''${indent}// Skip GPU/device memory regions (anon_inode:i915.gem on Aurora)
${indent}if (area.name[0] && strstr(area.name, \"anon_inode:\")) {
${indent}  JTRACE(\"skipping device memory region\")
${indent}    (area.name) ((void*)area.addr) (area.size);
${indent}  skip = 1;
${indent}  break;
${indent}}

'''
    content = content[:line_start] + patch_code + content[line_start:]
    with open(path, 'w') as f:
        f.write(content)
    print('  [OK] Patched writeckpt.cpp')
else:
    print('  [WARN] Could not find insertion point in writeckpt.cpp')
" "${wckpt}"
}

_patch_writeckpt "${MANA_ROOT}/dmtcp/src/writeckpt.cpp"

# --- 3c. mtcp_restart.c patch (skip anon_inode: during restore) ---
_patch_mtcp_restart() {
    local mrestart="$1"
    if [[ ! -f "${mrestart}" ]]; then return; fi
    if grep -q 'anon_inode:' "${mrestart}" 2>/dev/null; then
        echo "  [SKIP] mtcp_restart.c already patched: ${mrestart}"
        return
    fi
    echo "Patching ${mrestart} to skip anon_inode: device memory ..."
    python3 -c "
import sys
path = sys.argv[1]
with open(path, 'r') as f:
    content = f.read()

# Find restore_memory_region or readmemoryarea function
# Add skip for anon_inode: at the start of the region restore loop
marker = 'DPRINTF(\"Got area'
if marker not in content:
    marker = 'restore_memory_region'
if marker in content:
    idx = content.index(marker)
    # Find the next opening brace of the function or after DPRINTF
    brace_idx = content.index('{', idx)
    after_brace = brace_idx + 1
    # Find the next newline
    nl_idx = content.index('\\n', after_brace)
    indent = '  '
    patch_code = '''
${indent}// Skip GPU/device memory regions (anon_inode:i915.gem on Aurora)
${indent}if (area.name[0] && mtcp_strstr(area.name, \"anon_inode:\")) {
${indent}  DPRINTF(\"Skipping device memory region: %s at %p (%lu bytes)\\\\n\",
${indent}          area.name, area.addr, (unsigned long)area.size);
${indent}  if ((area.properties & DMTCP_ZERO_PAGE) == 0 &&
${indent}      (area.properties & DMTCP_ZERO_PAGE_PARENT_HEADER) == 0) {
${indent}    mtcp_sys_lseek(fd, area.size, SEEK_CUR);
${indent}  }
${indent}  return 0;
${indent}}
'''
    content = content[:nl_idx+1] + patch_code + content[nl_idx+1:]
    with open(path, 'w') as f:
        f.write(content)
    print('  [OK] Patched mtcp_restart.c')
else:
    print('  [WARN] Could not find insertion point in mtcp_restart.c')
" "${mrestart}"
}

_patch_mtcp_restart "${MANA_ROOT}/dmtcp/src/mtcp/mtcp_restart.c"

# --- 3d. Clang/icpx compatibility patches ---
# With OpenMPI + GCC, many of these patches may not be needed.
# But OpenMPI's mpicxx might still use icpx on Aurora if configured wrong.
# Apply them defensively.

OMPI_UNDERLYING="$("${OMPI_MPICXX}" --showme:command 2>/dev/null || echo 'unknown')"
echo ""
echo "OpenMPI mpicxx underlying compiler: ${OMPI_UNDERLYING}"

# Only apply Clang/icpx patches if the underlying compiler is clang/icpx
if echo "${OMPI_UNDERLYING}" | grep -qi 'clang\|icpx\|icx'; then
    echo "Underlying compiler is Clang-based, applying compatibility patches..."

    # Patch 1: NEXT_FUNC macro
    NEXTFUNC_H="mpi-proxy-split/mpi-wrappers/mpi_nextfunc.h"
    if [[ -f "${NEXTFUNC_H}" ]] && grep -q '__typeof__(&MPI_##func)' "${NEXTFUNC_H}"; then
        echo "  Patching ${NEXTFUNC_H}: &MPI_##func -> &PMPI_##func"
        sed -i 's/__typeof__(&MPI_##func)/__typeof__(\&PMPI_##func)/g' "${NEXTFUNC_H}"
    fi

    # Patch 2: record-replay.h
    RECORD_REPLAY_H="mpi-proxy-split/record-replay.h"
    if [[ -f "${RECORD_REPLAY_H}" ]] && grep -q '&MPI_##FNC' "${RECORD_REPLAY_H}"; then
        echo "  Patching ${RECORD_REPLAY_H}: &MPI_##FNC -> &PMPI_##FNC"
        sed -i 's/&MPI_##FNC/\&PMPI_##FNC/g' "${RECORD_REPLAY_H}"
    fi

    # Patch 3: wrapper .cpp files
    WRAPPERS_DIR="mpi-proxy-split/mpi-wrappers"
    if [[ -d "${WRAPPERS_DIR}" ]]; then
        for f in "${WRAPPERS_DIR}"/*.cpp; do
            [[ -f "$f" ]] || continue
            if grep -q 'PMPI_LOGGING' "$f"; then
                sed -i 's/PMPI_LOGGING/MPI_LOGGING/g' "$f"
            fi
        done
        for f in "${WRAPPERS_DIR}"/*.cpp; do
            [[ -f "$f" ]] || continue
            if grep -q '#pragma weak' "$f"; then
                sed -i -E \
                    -e '/^#pragma weak/! s/([^_A-Za-z0-9])MPI_([A-Z][a-z][A-Za-z0-9_]*)\(/\1PMPI_\2(/g' \
                    -e '/^#pragma weak/! s/^MPI_([A-Z][a-z][A-Za-z0-9_]*)\(/PMPI_\1(/g' \
                    "$f"
            fi
        done
        echo "  Patched wrapper .cpp files"
    fi

    # Patch 4: VLA initializer
    REQ_WRAPPERS="mpi-proxy-split/mpi-wrappers/mpi_request_wrappers.cpp"
    if [[ -f "${REQ_WRAPPERS}" ]] && grep -q 'was_null\[count\] = {0}' "${REQ_WRAPPERS}"; then
        sed -i 's/int was_null\[count\] = {0};/int was_null[count];/' "${REQ_WRAPPERS}"
        echo "  Patched VLA initializer"
    fi

    # Patch 5: PMPI_MANA_Internal compat
    MPI_WRAPPERS="mpi-proxy-split/mpi-wrappers/mpi_wrappers.cpp"
    if [[ -f "${MPI_WRAPPERS}" ]] && grep -q 'MANA_Internal' "${MPI_WRAPPERS}" \
       && ! grep -q '#define PMPI_MANA_Internal' "${MPI_WRAPPERS}"; then
        sed -i '1i\/* Clang/icpx compat: MANA_Internal has no PMPI variant */\
#define PMPI_MANA_Internal MPI_MANA_Internal' "${MPI_WRAPPERS}"
        echo "  Patched PMPI_MANA_Internal"
    fi

    # Patch 6: rex.W -> .byte 0x48
    SWITCH_CTX="mpi-proxy-split/lower-half/switch-context.cpp"
    if [[ -f "${SWITCH_CTX}" ]] && grep -q 'rex\.W' "${SWITCH_CTX}"; then
        sed -i 's/rex\.W\\n rdfsbase/.byte 0x48; rdfsbase/g; s/rex\.W\\n wrfsbase/.byte 0x48; wrfsbase/g' "${SWITCH_CTX}"
        echo "  Patched rex.W"
    fi

    # Patch 7: void* arithmetic in copy-stack.c
    COPY_STACK="mpi-proxy-split/lower-half/copy-stack.c"
    if [[ -f "${COPY_STACK}" ]] && grep -q 'rc2 + dest_mem_len' "${COPY_STACK}"; then
        sed -i 's/rc2 + dest_mem_len/(char *)rc2 + dest_mem_len/g' "${COPY_STACK}"
        echo "  Patched void* arithmetic"
    fi
else
    echo "Underlying compiler is GCC-based, Clang patches not needed."
fi

echo ""

# ── Step 4: Rebuild MANA's embedded DMTCP first ─────────────────────────
echo "=== Step 4: Rebuild embedded DMTCP ==="
echo ""

# MANA has its own DMTCP submodule that must be built with GCC
cd "${MANA_ROOT}"
if [[ -d "dmtcp" ]] && [[ -f "dmtcp/configure" ]]; then
    cd dmtcp
    echo "Rebuilding MANA's embedded DMTCP with GCC..."
    if [[ ! -f Makefile ]]; then
        CC="${GCC_CC}" CXX="${GCC_CXX}" ./configure --prefix="${INSTALL_PREFIX}"
    else
        # If already configured, just rebuild
        make clean 2>/dev/null || true
    fi
    CC="${GCC_CC}" CXX="${GCC_CXX}" make -j"$(nproc)"
    make install
    echo "[OK] DMTCP rebuilt with GCC"
    cd "${MANA_ROOT}"
else
    echo "No embedded DMTCP found (using standalone)"
fi
echo ""

# ── Step 5: Clean and rebuild MANA ──────────────────────────────────────
echo "=== Step 5: Clean and rebuild MANA ==="
echo ""

cd "${MANA_ROOT}"

# Clean previous build
make -C mpi-proxy-split clean 2>/dev/null || true
make -C mpi-proxy-split/mpi-wrappers clean 2>/dev/null || true
make -C mpi-proxy-split/lower-half clean 2>/dev/null || true
make clean 2>/dev/null || true

echo "Building MANA against OpenMPI (this may take a few minutes)..."
echo ""

# Set CC/CXX for the non-MPI parts of MANA (must use GCC)
export CC="${GCC_CC}"
export CXX="${GCC_CXX}"

if make -j"$(nproc)" 2>&1; then
    echo ""
    echo "[OK] MANA build succeeded!"
else
    echo ""
    echo "[WARN] Parallel build failed. Trying single-threaded..."
    if make 2>&1; then
        echo "[OK] MANA build succeeded (single-threaded)!"
    else
        echo "[FAIL] MANA build failed!"
        echo ""
        echo "Check the output above for errors."
        echo "Common issues:"
        echo "  - OpenMPI not compiled with Fortran (need --enable-mpi-fortran)"
        echo "  - Missing MPI headers (check OPENMPI_PREFIX/include/mpi.h)"
        exit 1
    fi
fi
echo ""

# Install MANA tools and libraries
echo "Installing MANA..."
make install 2>/dev/null || \
    cp -v lib/dmtcp/*.so "${INSTALL_PREFIX}/lib/dmtcp/" 2>/dev/null || true

# Copy MANA binaries to the install prefix
for tool in mana_launch mana_restart mana_start_coordinator; do
    if [[ -x "bin/${tool}" ]]; then
        cp -v "bin/${tool}" "${INSTALL_PREFIX}/bin/" 2>/dev/null || true
    fi
done
echo ""

# ── Step 6: Verify build ────────────────────────────────────────────────
echo "=== Step 6: Verify build ==="
echo ""

MANA_BIN="${MANA_ROOT}/bin"
MANA_LIB="${MANA_ROOT}/lib/dmtcp"
LOWER_HALF="${MANA_BIN}/lower-half"
LIBMANA="${MANA_LIB}/libmana.so"
LIBMPISTUB="${MANA_LIB}/libmpistub.so"

for comp in "${LIBMANA}:libmana.so" "${LOWER_HALF}:lower-half" "${LIBMPISTUB}:libmpistub.so"; do
    path="${comp%%:*}"
    name="${comp##*:}"
    if [[ -e "${path}" ]]; then
        echo "[OK] ${name}: $(file "${path}" 2>/dev/null | cut -d: -f2)"
    else
        echo "[FAIL] ${name}: MISSING"
    fi
done
echo ""

echo "lower-half ldd | grep mpi:"
ldd "${LOWER_HALF}" 2>/dev/null | grep -i mpi || echo "  (none)"
echo ""

echo "lower-half ldd | grep openmpi:"
ldd "${LOWER_HALF}" 2>/dev/null | grep -i open || echo "  (none)"
echo ""

# Verify it links to OpenMPI (not Cray MPICH)
if ldd "${LOWER_HALF}" 2>/dev/null | grep -q "${OPENMPI_PREFIX}"; then
    echo "[OK] lower-half links to OpenMPI at ${OPENMPI_PREFIX}"
elif ldd "${LOWER_HALF}" 2>/dev/null | grep -q 'libmpi'; then
    echo "[WARN] lower-half links to libmpi but not from ${OPENMPI_PREFIX}"
    echo "       May still be using Cray MPICH. Check ldd output above."
else
    echo "[WARN] lower-half does not appear to link to any MPI library"
fi
echo ""

# ── Step 7: Rebuild the app against OpenMPI ─────────────────────────────
echo "=== Step 7: Rebuild art_simple against OpenMPI ==="
echo ""

APP_SRC="${REPO_ROOT}/build/example_refs/dmtcp/art_simple"
APP_BUILD="${REPO_ROOT}/build/example_refs/dmtcp/art_simple/build_openmpi"

if [[ -d "${APP_SRC}" ]] && [[ -f "${APP_SRC}/CMakeLists.txt" ]]; then
    mkdir -p "${APP_BUILD}"
    cd "${APP_BUILD}"

    echo "Configuring with OpenMPI compilers..."
    cmake "${APP_SRC}" \
        -DCMAKE_C_COMPILER="${OMPI_MPICC}" \
        -DCMAKE_CXX_COMPILER="${OMPI_MPICXX}" \
        -DCMAKE_PREFIX_PATH="${OPENMPI_PREFIX}" \
        2>&1

    echo ""
    echo "Building..."
    make -j"$(nproc)" 2>&1

    # Find the built executable
    APP_EXE="$(find "${APP_BUILD}" -name 'art_simple' -type f -executable 2>/dev/null | head -1)"
    if [[ -n "${APP_EXE}" ]]; then
        echo "[OK] Built: ${APP_EXE}"
        echo "     ldd | grep mpi:"
        ldd "${APP_EXE}" 2>/dev/null | grep -i mpi || echo "  (none)"
    else
        echo "[WARN] Could not find art_simple executable after build"
    fi
else
    echo "[SKIP] App source not found at ${APP_SRC}"
    APP_EXE=""
fi
echo ""

# ── Step 8: Quick smoke test (MANA + OpenMPI) ───────────────────────────
echo "=== Step 8: Quick MANA + OpenMPI smoke test ==="
echo ""

export HWLOC_COMPONENTS="-linuxio"

COORD_HOST="$(hostname)"
MANA_LAUNCH="${MANA_BIN}/mana_launch"
DMTCP_COMMAND="${MANA_BIN}/dmtcp_command"
DMTCP_COORD="${MANA_BIN}/dmtcp_coordinator"
CKPT_DIR="${REPO_ROOT}/build/test_mana_openmpi/ckpt"
RUN_DIR="${REPO_ROOT}/build/test_mana_openmpi/run"
mkdir -p "${CKPT_DIR}" "${RUN_DIR}"

# Kill any existing coordinator
"${DMTCP_COMMAND}" -h "${COORD_HOST}" --coord-port "${COORD_PORT}" --quit 2>/dev/null || true
sleep 0.5

# Start coordinator directly (not via mana_start_coordinator) WITHOUT --exit-on-last
echo "Starting coordinator on port ${COORD_PORT} ..."
"${DMTCP_COORD}" --daemon --coord-port "${COORD_PORT}" \
    --ckptdir "${CKPT_DIR}" -q -q
sleep 1

# Write .mana.rc
cat > "${HOME}/.mana.rc" << MANARC
Host: ${COORD_HOST}
Port: ${COORD_PORT}

MANARC
echo "Wrote ~/.mana.rc"

# Test with art_simple if available, otherwise use a MANA test binary
TEST_EXE=""
if [[ -n "${APP_EXE:-}" ]] && [[ -x "${APP_EXE}" ]]; then
    DATA_PATH="${REPO_ROOT}/build/data/tooth_preprocessed.h5"
    if [[ -f "${DATA_PATH}" ]]; then
        TEST_EXE="${APP_EXE}"
        TEST_ARGS=("${DATA_PATH}" "294.078" "5" "2" "0" "4")
        echo "Testing with art_simple (5 outer iterations for quick test)"
    fi
fi

if [[ -z "${TEST_EXE}" ]]; then
    # Fall back to MANA test binary
    TEST_EXE=$(find "${MANA_ROOT}/mpi-proxy-split/test" -name "*.mana.exe" -type f 2>/dev/null | head -1)
    if [[ -n "${TEST_EXE}" ]]; then
        TEST_ARGS=()
        echo "Testing with MANA test binary: ${TEST_EXE}"
    fi
fi

if [[ -n "${TEST_EXE}" ]]; then
    # Write argv override config for MANA (in case of argv corruption)
    if [[ ${#TEST_ARGS[@]} -ge 5 ]]; then
        cat > "${RUN_DIR}/mana_argv_override.conf" << ARGVEOF
center=${TEST_ARGS[1]}
num_outer_iter=${TEST_ARGS[2]}
num_iter=${TEST_ARGS[3]}
beg_index=${TEST_ARGS[4]}
nslices=${TEST_ARGS[5]:-4}
ARGVEOF
        echo "Wrote mana_argv_override.conf"
    fi

    echo ""
    echo "Launching under MANA: mpirun -np 1 mana_launch ${TEST_EXE} ${TEST_ARGS[*]:-}"
    echo ""

    timeout 120 "${OMPI_MPIRUN}" -np 1 \
        "${MANA_LAUNCH}" --verbose \
        --coord-host "${COORD_HOST}" --coord-port "${COORD_PORT}" \
        --ckptdir "${CKPT_DIR}" --no-gzip \
        "${TEST_EXE}" "${TEST_ARGS[@]}" \
        2>&1
    TEST_EXIT=$?

    echo ""
    if [[ "${TEST_EXIT}" -eq 0 ]]; then
        echo "[OK] MANA + OpenMPI smoke test PASSED!"

        # Try a checkpoint
        echo ""
        echo "=== Bonus: checkpoint test ==="
        echo ""
        echo "Launching again (longer run) for checkpoint test..."

        # Restart coordinator
        "${DMTCP_COMMAND}" -h "${COORD_HOST}" --coord-port "${COORD_PORT}" --quit 2>/dev/null || true
        sleep 0.5
        "${DMTCP_COORD}" --daemon --coord-port "${COORD_PORT}" \
            --ckptdir "${CKPT_DIR}" -q -q
        sleep 0.5

        if [[ ${#TEST_ARGS[@]} -ge 3 ]]; then
            # Use more iterations so we have time to checkpoint
            TEST_ARGS[2]="30"
            cat > "${RUN_DIR}/mana_argv_override.conf" << ARGVEOF2
center=${TEST_ARGS[1]}
num_outer_iter=${TEST_ARGS[2]}
num_iter=${TEST_ARGS[3]}
beg_index=${TEST_ARGS[4]}
nslices=${TEST_ARGS[5]:-4}
ARGVEOF2
        fi

        rm -f "${CKPT_DIR}"/ckpt_*.dmtcp

        # Launch in background
        "${OMPI_MPIRUN}" -np 2 \
            "${MANA_LAUNCH}" \
            --coord-host "${COORD_HOST}" --coord-port "${COORD_PORT}" \
            --ckptdir "${CKPT_DIR}" --no-gzip \
            "${TEST_EXE}" "${TEST_ARGS[@]}" \
            > "${RUN_DIR}/stdout_ckpt.txt" 2> "${RUN_DIR}/stderr_ckpt.txt" &
        MPI_PID=$!
        echo "Launched with PID ${MPI_PID}"

        # Wait for app to initialize
        echo "Waiting 10s for app to start..."
        sleep 10

        if kill -0 "${MPI_PID}" 2>/dev/null; then
            echo "App still running. Triggering checkpoint..."
            "${DMTCP_COMMAND}" -h "${COORD_HOST}" --coord-port "${COORD_PORT}" --checkpoint 2>&1
            sleep 5

            CKPT_FILES=$(find "${CKPT_DIR}" -name "ckpt_*.dmtcp" -type f 2>/dev/null)
            if [[ -n "${CKPT_FILES}" ]]; then
                CKPT_COUNT=$(echo "${CKPT_FILES}" | wc -l)
                CKPT_SIZE=$(du -sh "${CKPT_DIR}" 2>/dev/null | cut -f1)
                echo "[OK] Checkpoint created: ${CKPT_COUNT} file(s), total ${CKPT_SIZE}"
                echo "Files:"
                echo "${CKPT_FILES}" | head -5
            else
                echo "[FAIL] No checkpoint files created"
            fi

            # Kill the app
            kill "${MPI_PID}" 2>/dev/null || true
            wait "${MPI_PID}" 2>/dev/null || true
        else
            echo "App already exited before checkpoint could be taken"
            wait "${MPI_PID}" 2>/dev/null || true
        fi
    elif [[ "${TEST_EXIT}" -eq 124 ]]; then
        echo "[FAIL] MANA test TIMED OUT (120s)"
    elif [[ "${TEST_EXIT}" -eq 139 ]]; then
        echo "[FAIL] MANA test SIGSEGV (signal 11)"
    else
        echo "[FAIL] MANA test failed (exit=${TEST_EXIT})"
    fi
else
    echo "[SKIP] No test binary available"
fi

# Cleanup coordinator
"${DMTCP_COMMAND}" -h "${COORD_HOST}" --coord-port "${COORD_PORT}" --quit 2>/dev/null || true

echo ""
echo "============================================================"
echo "  Rebuild complete."
echo ""
echo "  Next steps:"
echo "    1. If smoke test passed, run the full validation:"
echo "       cd ${REPO_ROOT}"
echo "       rm -rf build/validation_output/art_simple"
echo "       ./validation/veloc/run_art_simple_validation.sh --skip-benchmark --skip-report"
echo ""
echo "    2. Ensure OpenMPI is on PATH when running validation:"
echo "       export PATH=${OPENMPI_PREFIX}/bin:\${PATH}"
echo "       export LD_LIBRARY_PATH=${OPENMPI_PREFIX}/lib:\${LD_LIBRARY_PATH:-}"
echo "============================================================"
