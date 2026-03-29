#!/usr/bin/env bash
# Install DMTCP and the MANA MPI plugin from source.
#
# Usage:
#   ./scripts/install_dmtcp_mana.sh [--prefix PREFIX] [--force-rebuild-mana]
#
# Default install prefix: $HOME/.local
# ($HOME/.local/bin is typically already on PATH on Linux systems.)
#
# If python3 is not on PATH (common on HPC nodes), set PYTHON:
#   PYTHON=/path/to/python3.11 ./scripts/install_dmtcp_mana.sh
#
# The script is idempotent — it skips steps that are already done.
# After installation, a marker file is written so the validation
# framework can auto-discover DMTCP tools without manual PATH changes.
set -euo pipefail

# ── Parse arguments ───────────────────────────────────────────────────────
INSTALL_PREFIX="${HOME}/.local"
FORCE_REBUILD_MANA=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prefix)
      INSTALL_PREFIX="$2"; shift 2 ;;
    --prefix=*)
      INSTALL_PREFIX="${1#--prefix=}"; shift ;;
    --force-rebuild-mana)
      FORCE_REBUILD_MANA=true; shift ;;
    -h|--help)
      echo "Usage: $0 [--prefix PREFIX] [--force-rebuild-mana]"
      echo "  Default prefix: \$HOME/.local"
      echo "  --force-rebuild-mana  Force rebuild even if libmana.so exists"
      exit 0 ;;
    *)
      echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# Resolve to absolute path.
INSTALL_PREFIX="$(cd "$(dirname "${INSTALL_PREFIX}")" 2>/dev/null && pwd)/$(basename "${INSTALL_PREFIX}")"
SRC_DIR="${INSTALL_PREFIX}/share/guard-agent/dmtcp-src"
ARCH="$(uname -m)"

echo "============================================================"
echo "  DMTCP + MANA installation"
echo "  Install prefix : ${INSTALL_PREFIX}"
echo "  Source dir      : ${SRC_DIR}"
echo "============================================================"
echo ""

mkdir -p "${SRC_DIR}"

# ── Helper ────────────────────────────────────────────────────────────────
ok()   { echo "[OK]    $*"; }
skip() { echo "[SKIP]  $*"; }
info() { echo "[INFO]  $*"; }

# ── 1. Build DMTCP ───────────────────────────────────────────────────────
DMTCP_SRC="${SRC_DIR}/dmtcp"
DMTCP_BIN="${INSTALL_PREFIX}/bin/dmtcp_launch"

if [ -x "${DMTCP_BIN}" ]; then
  skip "DMTCP already installed at ${DMTCP_BIN}"
else
  if [ ! -d "${DMTCP_SRC}" ]; then
    info "Cloning DMTCP ..."
    git clone https://github.com/dmtcp/dmtcp.git "${DMTCP_SRC}"
  fi
  info "Building DMTCP ..."
  cd "${DMTCP_SRC}"
  ./configure --prefix="${INSTALL_PREFIX}"
  make -j"$(nproc)"
  make install
  ok "DMTCP installed to ${INSTALL_PREFIX}"
fi

# ── 2. Build MANA (MPI-Agnostic Network-Agnostic checkpoint plugin) ─────
# MANA's MPI proxy-split currently requires x86_64 (uses asm/prctl.h for
# ARCH_SET_FS/ARCH_SET_GS).  On other architectures, DMTCP is installed
# without MANA — MPI-level transparent checkpointing is not available but
# single-process DMTCP checkpointing still works.
MANA_SRC="${SRC_DIR}/mana"
MANA_LIB="${INSTALL_PREFIX}/lib/dmtcp/libmana.so"

# Check if MANA needs a rebuild for the current platform.
# If libmana.so exists but Makefile_config doesn't match the current platform,
# we need to rebuild.  This handles the case where MANA was installed before
# platform-specific patches were added to this script.
MANA_NEEDS_REBUILD=false
if [ -f "${MANA_LIB}" ] && [ -d "${MANA_SRC}" ]; then
  _MAKEFILE_CFG="${MANA_SRC}/mpi-proxy-split/Makefile_config"
  if [ -f "${_MAKEFILE_CFG}" ]; then
    _CUR_HOST="$(hostname 2>/dev/null || echo unknown)"
    _ON_AURORA=false
    if [[ "${_CUR_HOST}" =~ ^x[0-9]+c[0-9]+s[0-9]+b[0-9]+n[0-9]+ ]] || \
       [[ "${_CUR_HOST}" =~ ^aurora-uan- ]] || \
       [[ -n "${CRAY_MPICH_DIR:-}" ]]; then
      _ON_AURORA=true
    fi
    if [[ "${_ON_AURORA}" == "true" ]] && ! grep -q 'IS_AURORA' "${_MAKEFILE_CFG}"; then
      info "MANA installed but Makefile_config missing Aurora config — will rebuild"
      MANA_NEEDS_REBUILD=true
    fi
  fi
fi

if $FORCE_REBUILD_MANA && [ -d "${MANA_SRC}" ]; then
  info "Forced MANA rebuild requested"
  MANA_NEEDS_REBUILD=true
fi

if [ -f "${MANA_LIB}" ] && ! $MANA_NEEDS_REBUILD; then
  skip "MANA already installed at ${MANA_LIB}"
elif [[ "${ARCH}" != "x86_64" ]]; then
  echo ""
  echo "[WARN]  MANA MPI plugin is not supported on ${ARCH} (requires x86_64)."
  echo "        DMTCP is installed and works for single-process checkpointing."
  echo "        MPI-level transparent checkpointing via MANA is not available"
  echo "        on this architecture."
  echo ""
else
  if [ ! -d "${MANA_SRC}" ]; then
    info "Cloning MANA (with --recursive for DMTCP submodule) ..."
    git clone --recursive https://github.com/mpickpt/mana.git "${MANA_SRC}"
  fi
  cd "${MANA_SRC}"
  # MANA expects DMTCP as a git submodule under mana/dmtcp/.
  # Ensure the submodule is initialized (handles shallow clones or missed --recursive).
  if [ ! -f dmtcp/configure ] && [ -f .gitmodules ]; then
    info "Initializing DMTCP submodule inside MANA ..."
    git submodule init && git submodule update
  fi
  # If submodule still missing (e.g., tarball download), symlink our DMTCP source.
  if [ ! -f dmtcp/configure ] && [ -d "${DMTCP_SRC}" ]; then
    info "Symlinking DMTCP source into MANA ..."
    rm -rf dmtcp
    ln -sf "${DMTCP_SRC}" dmtcp
  fi
  # MANA requires Python 3.7+.  On HPC systems python3 may not be on
  # PATH but versioned binaries (python3.9, python3.11, …) or module-
  # loaded interpreters often exist.  Search broadly before giving up.
  #
  # If auto-discovery fails, the user can set PYTHON to the full path:
  #   PYTHON=/path/to/python3.11 ./scripts/install_dmtcp_mana.sh
  PYTHON3=""
  _find_python3() {
    # 0. Honour the PYTHON env var if set by the user.
    if [[ -n "${PYTHON:-}" ]]; then
      if [[ -x "${PYTHON}" ]]; then
        echo "${PYTHON}"; return
      elif command -v "${PYTHON}" &>/dev/null; then
        command -v "${PYTHON}"; return
      else
        echo "[WARN]  PYTHON='${PYTHON}' is not executable, ignoring." >&2
      fi
    fi
    # 1. Try plain python3.
    if command -v python3 &>/dev/null; then
      echo "python3"; return
    fi
    # 2. Try versioned names (python3.7 … python3.13), highest first.
    local v
    for v in 13 12 11 10 9 8 7; do
      if command -v "python3.${v}" &>/dev/null; then
        echo "python3.${v}"; return
      fi
    done
    # 3. Try plain python and verify it's 3.x.
    if command -v python &>/dev/null; then
      local maj
      maj="$(python -c 'import sys; print(sys.version_info.major)' 2>/dev/null || true)"
      if [[ "${maj}" == "3" ]]; then
        echo "python"; return
      fi
    fi
    # 4. Search common HPC/spack/conda prefix paths.
    local search_dirs=(
      /usr/bin /usr/local/bin
      /opt/*/bin
      "${HOME}/.conda/bin" "${HOME}/miniconda3/bin" "${HOME}/anaconda3/bin"
    )
    local d candidate
    for d in "${search_dirs[@]}"; do
      for v in 13 12 11 10 9 8 7; do
        candidate="${d}/python3.${v}"
        if [[ -x "${candidate}" ]]; then
          echo "${candidate}"; return
        fi
      done
      candidate="${d}/python3"
      if [[ -x "${candidate}" ]]; then
        echo "${candidate}"; return
      fi
    done
    # 5. On module-based systems, try loading a python module.
    if type module &>/dev/null 2>&1; then
      local mod
      for mod in python python3 anaconda; do
        if module load "${mod}" 2>/dev/null; then
          if command -v python3 &>/dev/null; then
            echo "python3"; return
          fi
        fi
      done
    fi
    return 1
  }

  if PYTHON3="$(_find_python3)"; then
    PY_VER="$("${PYTHON3}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    PY_MAJ="$("${PYTHON3}" -c 'import sys; print(sys.version_info.major)')"
    PY_MIN="$("${PYTHON3}" -c 'import sys; print(sys.version_info.minor)')"
    if [[ "${PY_MAJ}" -lt 3 ]] || { [[ "${PY_MAJ}" -eq 3 ]] && [[ "${PY_MIN}" -lt 7 ]]; }; then
      echo ""
      echo "[ERROR] Found ${PYTHON3} (${PY_VER}) but MANA requires Python >= 3.7."
      echo "        Specify a newer interpreter:"
      echo "          PYTHON=/path/to/python3.x ./scripts/install_dmtcp_mana.sh"
      echo ""
      exit 1
    fi
    info "Found ${PYTHON3} (${PY_VER})"
    # Make sure configure can find it — put its directory first on PATH
    # and create a temporary "python3" symlink if needed.
    PYTHON3_ABS="$(command -v "${PYTHON3}" 2>/dev/null || echo "${PYTHON3}")"
    PYTHON3_DIR="$(dirname "${PYTHON3_ABS}")"
    export PATH="${PYTHON3_DIR}:${PATH}"
    # Create a temporary "python3" symlink if python3 is missing OR if it
    # resolves to a different binary than the one we selected (e.g. the
    # system python3 is 3.6 but the user asked for python3.10).
    SYSTEM_PY3="$(command -v python3 2>/dev/null || true)"
    SYSTEM_PY3_REAL="$(readlink -f "${SYSTEM_PY3}" 2>/dev/null || true)"
    PYTHON3_ABS_REAL="$(readlink -f "${PYTHON3_ABS}" 2>/dev/null || echo "${PYTHON3_ABS}")"
    if [[ -z "${SYSTEM_PY3}" ]] || [[ "${SYSTEM_PY3_REAL}" != "${PYTHON3_ABS_REAL}" ]]; then
      TMPBIN="$(mktemp -d)"
      ln -sf "${PYTHON3_ABS}" "${TMPBIN}/python3"
      export PATH="${TMPBIN}:${PATH}"
      info "Created temporary python3 symlink at ${TMPBIN}/python3 -> ${PYTHON3_ABS}"
    fi
  else
    echo ""
    echo "[ERROR] Python 3.7+ not found anywhere.  MANA requires it."
    echo "        Searched: python3, python3.{7..13}, python, common HPC paths."
    echo ""
    echo "        Set the PYTHON env var to the full path of your interpreter:"
    echo "          PYTHON=/path/to/python3.x ./scripts/install_dmtcp_mana.sh"
    echo ""
    echo "        Or on module-based systems:"
    echo "          module load python && ./scripts/install_dmtcp_mana.sh"
    echo ""
    exit 1
  fi

  info "Building MANA ..."

  MANA_BUILD_OK=true
  if [ -f configure ] && ! ./configure --prefix="${INSTALL_PREFIX}"; then
    MANA_BUILD_OK=false
  fi

  # ── Aurora (ALCF) platform detection for Makefile_config ───────────
  # MANA's Makefile_config only has platform detection for Perlmutter.
  # On Aurora (Cray MPICH 5.0 + Intel oneAPI), we need to set the
  # correct MPI compiler wrappers and library flags.
  #
  # Aurora hostnames:
  #   Compute nodes: x4NNNcNsNbNnN (e.g. x4310c5s0b0n0)
  #   Login nodes:   aurora-uan-NNNN (e.g. aurora-uan-0011)
  MAKEFILE_CONFIG="mpi-proxy-split/Makefile_config"
  if [ -f "${MAKEFILE_CONFIG}" ] && ! grep -q 'IS_AURORA' "${MAKEFILE_CONFIG}"; then
    _HOSTNAME="$(hostname 2>/dev/null || echo unknown)"
    IS_AURORA=false
    if [[ "${_HOSTNAME}" =~ ^x[0-9]+c[0-9]+s[0-9]+b[0-9]+n[0-9]+ ]] || \
       [[ "${_HOSTNAME}" =~ ^aurora-uan- ]]; then
      IS_AURORA=true
    fi
    # Also check for Cray MPICH environment (works even if hostname pattern changes)
    if [[ "${IS_AURORA}" != "true" ]] && [[ -n "${CRAY_MPICH_DIR:-}" ]]; then
      IS_AURORA=true
    fi

    if [[ "${IS_AURORA}" == "true" ]]; then
      info "Detected Aurora (ALCF) platform, patching Makefile_config ..."
      # Determine MPI library path from Cray MPICH
      _MPI_LIB_DIR=""
      if [[ -n "${CRAY_MPICH_DIR:-}" ]]; then
        _MPI_LIB_DIR="${CRAY_MPICH_DIR}/lib"
      elif [[ -d "/opt/cray/pe/mpich" ]]; then
        # Find the latest MPICH version
        _MPI_LIB_DIR="$(find /opt/cray/pe/mpich -name 'libmpi.so' -exec dirname {} \; 2>/dev/null | head -1)"
      fi
      # Get MPI link flags from the compiler wrapper
      _MPI_LINK_FLAGS=""
      if command -v mpicxx &>/dev/null; then
        # Cray mpicxx --cray-print-opts=libs gives the link flags
        _MPI_LINK_FLAGS="$(mpicxx --cray-print-opts=libs 2>/dev/null || true)"
      fi
      if [[ -z "${_MPI_LINK_FLAGS}" ]] && [[ -n "${_MPI_LIB_DIR}" ]]; then
        _MPI_LINK_FLAGS="-L${_MPI_LIB_DIR} -lmpi"
      fi
      if [[ -z "${_MPI_LINK_FLAGS}" ]]; then
        _MPI_LINK_FLAGS="-lmpi"
      fi

      # Insert Aurora detection block before the 'else' clause
      # We add it after the Perlmutter block
      sed -i '/^ifeq (\${IS_PERLMUTTER}, 1)/i\
# Mark the platform as Aurora for ALCF Aurora compute/login nodes.\
AURORA_HOST := $(shell hostname 2>/dev/null)\
ifneq ($(findstring aurora-uan,$(AURORA_HOST)),)\
IS_AURORA = 1\
endif\
# Aurora compute nodes: x4NNNcNsNbNnN pattern\
ifneq ($(shell echo $(AURORA_HOST) | grep -c "^x[0-9]"),0)\
IS_AURORA = 1\
endif\
# Also detect via CRAY_MPICH_DIR environment variable\
ifdef CRAY_MPICH_DIR\
IS_AURORA = 1\
endif\
' "${MAKEFILE_CONFIG}"

      # Now add the Aurora-specific settings block
      sed -i '/^ifeq (\${IS_PERLMUTTER}, 1)/i\
ifeq (${IS_AURORA}, 1)\
  MPICC = mpicc\
  MPICXX = mpicxx -std=c++14\
  MPIFORTRAN = mpifort\
  MPI_LD_FLAG = '"${_MPI_LINK_FLAGS}"'\
  MPIRUN = mpiexec\
  MPI_CFLAGS?= -g -O2 -std=gnu11 -g3 -fPIC\
  MPI_CXXFLAGS?= -g -O2 -g3 -fPIC\
  MPI_LDFLAGS?=\
default2: default\
else\
' "${MAKEFILE_CONFIG}"

      # Close the Aurora else block by adding 'endif' before the Perlmutter block
      # Actually, we need to restructure: Aurora if/else wraps the Perlmutter block
      # Let's use a simpler approach: just add an endif after the Perlmutter endif
      # Wait, this is getting complex with nested ifeq. Let me use a different approach.

      # Revert the above sed attempts and use a clean rewrite approach
      git checkout -- "${MAKEFILE_CONFIG}" 2>/dev/null || true

      # Write a new Makefile_config with Aurora support
      cat > "${MAKEFILE_CONFIG}" << 'AURORA_MAKEFILE_CONFIG_EOF'
CFLAGS = -g -O2 -std=gnu11
CXXFLAGS = -g -O2
FFLAGS = ${CXXFLAGS}  -fallow-argument-mismatch

PLATFORM=${shell echo $$HOST}
HOSTNAME_FULL := $(shell hostname 2>/dev/null)

# ── Platform detection ──────────────────────────────────────────────
# Aurora (ALCF): compute nodes x4NNNcNsNbNnN, login nodes aurora-uan-NNNN
ifneq ($(findstring aurora-uan,$(HOSTNAME_FULL)),)
IS_AURORA = 1
endif
ifneq ($(shell echo $(HOSTNAME_FULL) | grep -c "^x[0-9]"),0)
IS_AURORA = 1
endif
ifdef CRAY_MPICH_DIR
IS_AURORA = 1
endif

# Perlmutter (NERSC): compute nodes nid0XXXXX, login nodes loginNN
ifeq ($(findstring nid0,$(PLATFORM)),nid0)
IS_PERLMUTTER = 1
endif
ifeq ($(findstring login,$(PLATFORM)),login)
IS_PERLMUTTER = 1
endif

# ── Platform-specific settings ──────────────────────────────────────
ifeq (${IS_AURORA}, 1)
  MPICC = mpicc
  MPICXX = mpicxx -std=c++14
  MPIFORTRAN = mpifort
AURORA_MAKEFILE_CONFIG_EOF

      # Add the MPI_LD_FLAG with the detected link flags
      echo "  MPI_LD_FLAG = ${_MPI_LINK_FLAGS}" >> "${MAKEFILE_CONFIG}"

      cat >> "${MAKEFILE_CONFIG}" << 'AURORA_MAKEFILE_CONFIG_EOF2'
  MPIRUN = mpiexec
  MPI_CFLAGS?= -g -O2 -std=gnu11 -g3 -fPIC
  MPI_CXXFLAGS?= -g -O2 -g3 -fPIC
  MPI_LDFLAGS?=
default2: default
else
ifeq (${IS_PERLMUTTER}, 1)
  MPICC = cc
  MPICXX = CC -std=c++14
  MPIFORTRAN = ftn
  MPI_LD_FLAG = -lmpich
  MPIRUN = srun
  MPI_CFLAGS?= -g -O2 -std=gnu11 -g3 -fPIC
  MPI_CXXFLAGS?= -g -O2 -g3 -fPIC
  MPI_LDFLAGS?= -dynamic
default2: default
else
  MPICC = mpicc
  MPICXX = mpic++ -std=c++14
  MPIFORTRAN = mpifort
  MPIRUN = mpirun
  MPI_LD_FLAG = -L$$HOME/mpich-static/usr/lib64 -lmpi -L$$HOME/local_install/lib -llzma -lz -lm -lxml2
  MPI_CFLAGS?= -g -O2 -std=gnu11 -g3 -fPIC
  MPI_CXXFLAGS?= -g -O2 -g3 -fPIC
  MPI_FFLAGS =  -fallow-argument-mismatch -g3
  MPI_LDFLAGS?=
endif
endif
AURORA_MAKEFILE_CONFIG_EOF2

      ok "Makefile_config patched for Aurora"
    fi
  fi

  # ── Clang / icpx compatibility for #pragma weak ambiguity ─────────
  # On Clang-based compilers (icpx, clang++), #pragma weak MPI_Send =
  # PMPI_Send creates a second declaration of MPI_Send in the same
  # translation unit.  Combined with the declaration from mpi_proto.h,
  # this makes &MPI_Send ambiguous (two candidates with the same
  # signature).  GCC does not have this problem.
  #
  # This breaks two things in MANA:
  #   1. NEXT_FUNC macro (mpi_nextfunc.h) uses __typeof__(&MPI_##func)
  #   2. Direct calls like MPI_Isend(...) in wrapper code are ambiguous
  #
  # Fix: patch the source files to use PMPI_##func instead of MPI_##func
  # where the ambiguity occurs.  PMPI_##func always has a single
  # unambiguous declaration and the exact same signature.
  if $MANA_BUILD_OK; then
    info "Applying Clang/icpx compatibility patches ..."

    # 1. Patch NEXT_FUNC macro: __typeof__(&MPI_##func) -> __typeof__(&PMPI_##func)
    NEXTFUNC_H="mpi-proxy-split/mpi-wrappers/mpi_nextfunc.h"
    if [ -f "${NEXTFUNC_H}" ] && grep -q '__typeof__(&MPI_##func)' "${NEXTFUNC_H}"; then
      info "Patching ${NEXTFUNC_H}: &MPI_##func -> &PMPI_##func ..."
      sed -i 's/__typeof__(&MPI_##func)/__typeof__(\&PMPI_##func)/g' "${NEXTFUNC_H}"
    fi

    # 2. Patch record-replay.h GENERATE_FNC_PTR macro: &MPI_##FNC -> &PMPI_##FNC
    #    The macro is: #define GENERATE_FNC_PTR(FNC)  &MPI_##FNC
    #    Used by LOG_CALL and FNC_CALL macros.  With Clang, &MPI_Xxx is
    #    ambiguous due to #pragma weak aliases; &PMPI_Xxx is unambiguous.
    RECORD_REPLAY_H="mpi-proxy-split/record-replay.h"
    if [ -f "${RECORD_REPLAY_H}" ] && grep -q '&MPI_##FNC' "${RECORD_REPLAY_H}"; then
      info "Patching ${RECORD_REPLAY_H}: &MPI_##FNC -> &PMPI_##FNC ..."
      sed -i 's/&MPI_##FNC/\&PMPI_##FNC/g' "${RECORD_REPLAY_H}"
    fi

    # 3. Patch direct MPI_Xxx calls in wrapper .cpp files that are
    #    ambiguous due to #pragma weak.  These are calls where the
    #    wrapper itself calls MPI_Isend/MPI_Irecv (not via NEXT_FUNC).
    #    Replace with PMPI_Isend/PMPI_Irecv to avoid the ambiguity.
    #
    #    Pattern: MPI_[A-Z][a-z] matches MPI API functions (MPI_Isend,
    #    MPI_Recv, MPI_Type_size, MPI_Allreduce, etc.) but NOT
    #    all-caps macros (MPI_LOGGING, MPI_SUCCESS, MPI_COMM_WORLD)
    #    and NOT MANA-internal functions like MPI_MANA_Internal.
    WRAPPERS_DIR="mpi-proxy-split/mpi-wrappers"
    if [ -d "${WRAPPERS_DIR}" ]; then
      # First, revert any incorrectly-patched all-caps MANA macros
      # from a previous run (e.g. PMPI_LOGGING -> MPI_LOGGING).
      for f in "${WRAPPERS_DIR}"/*.cpp; do
        [ -f "$f" ] || continue
        if grep -q 'PMPI_LOGGING' "$f"; then
          sed -i 's/PMPI_LOGGING/MPI_LOGGING/g' "$f"
        fi
      done
      # Now apply the correct patch.
      for f in "${WRAPPERS_DIR}"/*.cpp; do
        [ -f "$f" ] || continue
        if grep -q '#pragma weak' "$f"; then
          sed -i -E \
            -e '/^#pragma weak/! s/([^_A-Za-z0-9])MPI_([A-Z][a-z][A-Za-z0-9_]*)\(/\1PMPI_\2(/g' \
            -e '/^#pragma weak/! s/^MPI_([A-Z][a-z][A-Za-z0-9_]*)\(/PMPI_\1(/g' \
            "$f"
        fi
      done
    fi

    # 4. Fix VLA (variable-length array) with initializer in
    #    mpi_request_wrappers.cpp.  Clang rejects "int arr[n] = {0};"
    #    when n is not a compile-time constant.  The subsequent loop
    #    fills every element, so the initializer is unnecessary.
    REQ_WRAPPERS="mpi-proxy-split/mpi-wrappers/mpi_request_wrappers.cpp"
    if [ -f "${REQ_WRAPPERS}" ] && grep -q 'was_null\[count\] = {0}' "${REQ_WRAPPERS}"; then
      info "Patching ${REQ_WRAPPERS}: removing VLA initializer ..."
      sed -i 's/int was_null\[count\] = {0};/int was_null[count];/' "${REQ_WRAPPERS}"
    fi

    # 5. MPI_MANA_Internal is a MANA-internal function (not part of the
    #    MPI standard) that has no PMPI_ counterpart.  After Patch 1
    #    changes &MPI_##func to &PMPI_##func in NEXT_FUNC, the expansion
    #    NEXT_FUNC(MANA_Internal) would reference the non-existent
    #    PMPI_MANA_Internal.  Add a compatibility define so the compiler
    #    resolves it back to the real function.
    MPI_WRAPPERS="mpi-proxy-split/mpi-wrappers/mpi_wrappers.cpp"
    if [ -f "${MPI_WRAPPERS}" ] && grep -q 'MANA_Internal' "${MPI_WRAPPERS}" \
       && ! grep -q '#define PMPI_MANA_Internal' "${MPI_WRAPPERS}"; then
      info "Patching ${MPI_WRAPPERS}: adding PMPI_MANA_Internal compat define ..."
      sed -i '1i\/* Clang/icpx compat: MANA_Internal has no PMPI variant */\
#define PMPI_MANA_Internal MPI_MANA_Internal' "${MPI_WRAPPERS}"
    fi

    # 6. lower-half/switch-context.cpp uses "rex.W\n rdfsbase" and
    #    "rex.W\n wrfsbase" inline assembly.  The Intel Clang integrated
    #    assembler does not recognise "rex.W" as a standalone mnemonic.
    #    Replace with the equivalent ".byte 0x48" REX.W prefix encoding.
    SWITCH_CTX="mpi-proxy-split/lower-half/switch-context.cpp"
    if [ -f "${SWITCH_CTX}" ] && grep -q 'rex\.W' "${SWITCH_CTX}"; then
      info "Patching ${SWITCH_CTX}: rex.W -> .byte 0x48 for icpx asm ..."
      sed -i 's/rex\.W\\n rdfsbase/.byte 0x48; rdfsbase/g; s/rex\.W\\n wrfsbase/.byte 0x48; wrfsbase/g' "${SWITCH_CTX}"
    fi

    # 7. lower-half/copy-stack.c is compiled by mpic++ (icpx) which treats
    #    .c files as C++.  In C++ mode, arithmetic on void* is illegal.
    #    Cast the void* to char* so the pointer arithmetic compiles.
    COPY_STACK="mpi-proxy-split/lower-half/copy-stack.c"
    if [ -f "${COPY_STACK}" ] && grep -q 'rc2 + dest_mem_len' "${COPY_STACK}"; then
      info "Patching ${COPY_STACK}: void* arithmetic -> char* cast ..."
      sed -i 's/rc2 + dest_mem_len/(char *)rc2 + dest_mem_len/g' "${COPY_STACK}"
    fi

    info "Patches applied."
  fi

  # Clean any previous failed build artifacts before retrying.
  if [ -d mpi-proxy-split ]; then
    make -C mpi-proxy-split clean 2>/dev/null || true
    make -C mpi-proxy-split/mpi-wrappers clean 2>/dev/null || true
  fi

  if $MANA_BUILD_OK && ! { make -j"$(nproc)" || make; }; then
    MANA_BUILD_OK=false
    echo ""
    echo "[WARN]  MANA build failed.  This is typically caused by an"
    echo "        incompatibility between MANA and the system MPI library"
    echo "        (e.g. Clang/icpx #pragma weak ambiguity or MPICH >= 5.0"
    echo "        overloaded declarations)."
    echo "        DMTCP is still installed and works for single-process"
    echo "        checkpointing.  MPI-level transparent checkpointing via"
    echo "        MANA is not available until MANA upstream adds support"
    echo "        for this compiler/MPI combination."
    echo ""
  fi
  if $MANA_BUILD_OK; then
    make install 2>/dev/null || \
      cp -v lib/*.so "${INSTALL_PREFIX}/lib/dmtcp/" 2>/dev/null || \
      info "MANA build completed; manual install may be needed"
    ok "MANA built (check ${INSTALL_PREFIX}/lib/dmtcp/ for libmana.so)"
  fi
fi

# ── 3. Verify ────────────────────────────────────────────────────────────
echo ""
echo "Verifying installation ..."
export PATH="${INSTALL_PREFIX}/bin:${PATH}"

MISSING=()
for tool in dmtcp_launch dmtcp_coordinator dmtcp_command dmtcp_restart; do
  if command -v "${tool}" &>/dev/null; then
    ok "${tool} found at $(command -v "${tool}")"
  else
    MISSING+=("${tool}")
    echo "[FAIL]  ${tool} not found"
  fi
done

echo ""
if [ ${#MISSING[@]} -eq 0 ]; then
  # ── 4. Write install-prefix marker for auto-discovery ─────────────────
  MARKER_DIR="${HOME}/.local/share/guard-agent"
  MARKER_FILE="${MARKER_DIR}/dmtcp_prefix"
  mkdir -p "${MARKER_DIR}"
  echo "${INSTALL_PREFIX}" > "${MARKER_FILE}"
  ok "Install prefix recorded in ${MARKER_FILE}"

  echo ""
  echo "============================================================"
  echo "  All DMTCP tools verified."
  echo ""
  if [[ "${INSTALL_PREFIX}" == "${HOME}/.local" ]]; then
    echo "  \$HOME/.local/bin is typically already on PATH."
    echo "  If not, add to your shell profile:"
  else
    echo "  Add the following to your shell profile:"
  fi
  echo ""
  echo "    export PATH=\"${INSTALL_PREFIX}/bin:\${PATH}\""
  echo "    export LD_LIBRARY_PATH=\"${INSTALL_PREFIX}/lib:\${LD_LIBRARY_PATH:-}\""
  echo ""
  echo "  The validation framework will auto-discover DMTCP tools"
  echo "  via the marker file at: ${MARKER_FILE}"
  echo "============================================================"
else
  echo "============================================================"
  echo "  WARNING: ${#MISSING[@]} tool(s) missing: ${MISSING[*]}"
  echo "  Check the build output above for errors."
  echo "============================================================"
  exit 1
fi
