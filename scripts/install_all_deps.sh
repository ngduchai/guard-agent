#!/usr/bin/env bash
# install_all_deps.sh — install everything the validation pipeline needs.
#
# This merges what used to live in two separate scripts:
#   1. System packages via apt  (build tools, BLAS/LAPACK, Boost, HDF5-MPI, ...)
#   2. Checkpoint libraries to ~/.local
#        FTI v1.6        (FTI-based apps)
#        SCR v3.1.0      (LULESH)
#        jemalloc 5.3.0  (LULESH persistent-memory variant)
#        pallocator stub (LULESH compile)
#        meson + ninja   (SU2 and friends)
#
# Usage:
#   ./scripts/install_all_deps.sh
#
# The script is idempotent: apt-installed packages are skipped by apt itself,
# and library installs check marker files (e.g. ~/.local/include/fti.h) before
# rebuilding.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_PREFIX="${HOME}/.local"
SRC_DIR="${INSTALL_PREFIX}/src"
JOBS="$(nproc 2>/dev/null || echo 2)"

ok()   { echo "[OK]    $*"; }
skip() { echo "[SKIP]  $*"; }
info() { echo "[INFO]  $*"; }
fail() { echo "[FAIL]  $*" >&2; return 1; }

# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — System packages (apt)
# ─────────────────────────────────────────────────────────────────────────────

install_system_packages() {
  if ! command -v apt-get >/dev/null 2>&1; then
    info "apt-get not found; skipping system-package phase (assume manual install)."
    return 0
  fi

  local sudo_cmd=""
  if [[ $EUID -ne 0 ]]; then
    if ! command -v sudo >/dev/null 2>&1; then
      fail "Need root or sudo to install system packages via apt."
    fi
    sudo_cmd="sudo"
  fi

  info "Installing system packages (apt) ..."
  $sudo_cmd apt-get update -qq
  $sudo_cmd apt-get install -y \
    build-essential \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    liblapacke-dev \
    libboost-all-dev \
    libhdf5-openmpi-dev \
    autoconf automake libtool \
    pkg-config \
    zlib1g-dev \
    libjemalloc-dev \
    cmake \
    git \
    openmpi-bin libopenmpi-dev
  ok "System packages installed."
}

# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Checkpoint libraries (build to $HOME/.local)
# ─────────────────────────────────────────────────────────────────────────────

check_lib_prereq() {
  local missing=()
  command -v cmake  >/dev/null 2>&1 || missing+=(cmake)
  command -v make   >/dev/null 2>&1 || missing+=(make)
  command -v mpicc  >/dev/null 2>&1 || missing+=(mpicc)
  command -v mpicxx >/dev/null 2>&1 || missing+=(mpicxx)
  command -v gcc    >/dev/null 2>&1 || missing+=(gcc)
  command -v git    >/dev/null 2>&1 || missing+=(git)
  if [[ ${#missing[@]} -gt 0 ]]; then
    fail "Missing prerequisites for library build: ${missing[*]}"
  fi
  ok "Library-build prerequisites present (cmake, make, mpicc, mpicxx, gcc, git)."
}

install_fti() {
  local marker="${INSTALL_PREFIX}/include/fti.h"
  if [[ -f "${marker}" ]]; then skip "FTI already installed"; return 0; fi

  info "Installing FTI v1.6 ..."
  local src="${SRC_DIR}/fti"
  [[ -d "${src}" ]] || git clone --depth 1 --branch v1.6 https://github.com/leobago/fti.git "${src}"
  local build="${src}/build"
  rm -rf "${build}"; mkdir -p "${build}"
  ( cd "${build}" && cmake .. \
      -DCMAKE_INSTALL_PREFIX="${INSTALL_PREFIX}" \
      -DCMAKE_C_COMPILER=mpicc \
      -DENABLE_FORTRAN=OFF -DENABLE_HDF5=OFF -DENABLE_SIONLIB=OFF \
      -DENABLE_IME_NATIVE=OFF -DENABLE_LUSTRE=OFF \
      -DENABLE_EXAMPLES=OFF -DENABLE_TESTS=OFF \
      -DCMAKE_BUILD_TYPE=Release && \
    make -j"${JOBS}" && make install )
  if [[ -d "${INSTALL_PREFIX}/lib64" && ! -L "${INSTALL_PREFIX}/lib64" ]]; then
    cp -rn "${INSTALL_PREFIX}/lib64/"* "${INSTALL_PREFIX}/lib/" 2>/dev/null || true
  fi
  ok "FTI v1.6 installed."
}

install_scr() {
  local marker="${INSTALL_PREFIX}/include/scr.h"
  if [[ -f "${marker}" ]]; then skip "SCR already installed"; return 0; fi

  info "Installing SCR v3.1.0 ..."
  local src="${SRC_DIR}/scr"
  [[ -d "${src}" ]] || git clone --depth 1 --branch v3.1.0 https://github.com/LLNL/scr.git "${src}"
  ( cd "${src}" && \
    if [[ ! -f install/lib/libkvtree.so && ! -f install/lib/libkvtree.a ]]; then
      bash bootstrap.sh --tag --opt --clean
    fi
  )
  local build="${src}/build"
  rm -rf "${build}"; mkdir -p "${build}"
  ( cd "${build}" && cmake .. \
      -DCMAKE_INSTALL_PREFIX="${INSTALL_PREFIX}" \
      -DCMAKE_PREFIX_PATH="${src}/install" \
      -DCMAKE_C_COMPILER=mpicc -DCMAKE_CXX_COMPILER=mpicxx \
      -DSCR_RESOURCE_MANAGER=NONE \
      -DSCR_CNTL_BASE=/tmp -DSCR_CACHE_BASE=/tmp \
      -DENABLE_FORTRAN=OFF -DENABLE_EXAMPLES=OFF -DENABLE_TESTS=OFF \
      -DBUILD_SHARED_LIBS=ON \
      -DCMAKE_BUILD_TYPE=Release && \
    make -j"${JOBS}" && make install )
  cp -n "${src}/install"/lib/lib*.so* "${INSTALL_PREFIX}/lib/" 2>/dev/null || true
  cp -n "${src}/install"/lib/lib*.a   "${INSTALL_PREFIX}/lib/" 2>/dev/null || true
  cp -rn "${src}/install"/include/*   "${INSTALL_PREFIX}/include/" 2>/dev/null || true
  ok "SCR v3.1.0 installed."
}

install_jemalloc() {
  if [[ -f "${INSTALL_PREFIX}/lib/libjemalloc.so" || -f "${INSTALL_PREFIX}/lib/libjemalloc.a" ]]; then
    skip "jemalloc already installed"; return 0
  fi
  info "Installing jemalloc 5.3.0 ..."
  local src="${SRC_DIR}/jemalloc"
  [[ -d "${src}" ]] || git clone --depth 1 --branch 5.3.0 https://github.com/jemalloc/jemalloc.git "${src}"
  ( cd "${src}" && ./autogen.sh && ./configure --prefix="${INSTALL_PREFIX}" && \
    make -j"${JOBS}" && make install )
  ok "jemalloc installed."
}

install_pallocator_stub() {
  local marker="${INSTALL_PREFIX}/include/jemalloc/pallocator.h"
  if [[ -f "${marker}" ]]; then skip "pallocator.h stub already installed"; return 0; fi
  mkdir -p "${INSTALL_PREFIX}/include/jemalloc"
  cp "${SCRIPT_DIR}/pallocator_stub.h" "${marker}" 2>/dev/null || \
    info "(pallocator stub source not vendored; LULESH may need manual fix)"
  [[ -f "${marker}" ]] && ok "pallocator.h stub installed." || true
}

install_tools() {
  if command -v meson >/dev/null 2>&1 && command -v ninja >/dev/null 2>&1; then
    skip "meson + ninja already available"; return 0
  fi
  info "Installing meson + ninja via pip --user ..."
  local pip="python3 -m pip"
  ${pip} install --user --quiet meson ninja || \
    fail "Could not install meson/ninja. Install manually: python3 -m pip install --user meson ninja"
  ok "meson + ninja installed."
}

write_env_sh() {
  local env_file="${INSTALL_PREFIX}/env.sh"
  cat > "${env_file}" << ENVEOF
# Source this file to set up paths for the checkpoint libraries.
# Usage: source ${env_file}
export PATH="${INSTALL_PREFIX}/bin:\${PATH}"
export LD_LIBRARY_PATH="${INSTALL_PREFIX}/lib:\${LD_LIBRARY_PATH:-}"
export LIBRARY_PATH="${INSTALL_PREFIX}/lib:\${LIBRARY_PATH:-}"
export C_INCLUDE_PATH="${INSTALL_PREFIX}/include:\${C_INCLUDE_PATH:-}"
export CPLUS_INCLUDE_PATH="${INSTALL_PREFIX}/include:\${CPLUS_INCLUDE_PATH:-}"
export PKG_CONFIG_PATH="${INSTALL_PREFIX}/lib/pkgconfig:\${PKG_CONFIG_PATH:-}"
export CMAKE_PREFIX_PATH="${INSTALL_PREFIX}:\${CMAKE_PREFIX_PATH:-}"
ENVEOF
  ok "Environment file written: ${env_file}"
}

install_libraries() {
  mkdir -p "${SRC_DIR}" "${INSTALL_PREFIX}/lib" "${INSTALL_PREFIX}/include"
  check_lib_prereq
  install_fti
  install_scr
  install_jemalloc
  install_pallocator_stub
  install_tools
  write_env_sh
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

main() {
  echo "========================================================="
  echo "  guard-agent — install all validation dependencies"
  echo "  Install prefix: ${INSTALL_PREFIX}"
  echo "  Parallel jobs:  ${JOBS}"
  echo "========================================================="
  install_system_packages
  echo ""
  install_libraries
  echo ""
  echo "[done] All dependencies installed."
  echo "       Activate environment: source ${INSTALL_PREFIX}/env.sh"
}

main "$@"
