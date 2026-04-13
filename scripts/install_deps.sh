#!/usr/bin/env bash
# Install checkpoint libraries and build tools required by benchmark apps.
#
# Usage:
#   ./scripts/install_deps.sh                     # install all
#   ./scripts/install_deps.sh --fti               # install FTI only
#   ./scripts/install_deps.sh --scr               # install SCR only
#   ./scripts/install_deps.sh --jemalloc          # install jemalloc only
#   ./scripts/install_deps.sh --tools             # install meson/ninja only
#   ./scripts/install_deps.sh --prefix /opt/local # custom prefix
#
# Default install prefix: $HOME/.local
#
# Libraries installed:
#   FTI v1.6      — Fault Tolerance Interface    (needed by: AMG, miniFE, miniVite)
#   SCR v3.1.0    — Scalable Checkpoint/Restart  (needed by: LULESH)
#   jemalloc      — Memory allocator             (needed by: LULESH)
#   meson + ninja — Build tools                  (needed by: SU2)
#
# The script is idempotent — it skips components that are already installed.
# After installation it writes an env.sh that can be sourced to set up paths.
set -euo pipefail

# ── Parse arguments ──────────────────────────────────────────────────────
INSTALL_PREFIX="${HOME}/.local"
DO_ALL=true
DO_FTI=false
DO_SCR=false
DO_JEMALLOC=false
DO_TOOLS=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prefix)     INSTALL_PREFIX="$2"; shift 2 ;;
    --prefix=*)   INSTALL_PREFIX="${1#--prefix=}"; shift ;;
    --fti)        DO_FTI=true; DO_ALL=false; shift ;;
    --scr)        DO_SCR=true; DO_ALL=false; shift ;;
    --jemalloc)   DO_JEMALLOC=true; DO_ALL=false; shift ;;
    --tools)      DO_TOOLS=true; DO_ALL=false; shift ;;
    -h|--help)
      sed -n '2,/^set -euo/{ /^#/s/^# \?//p }' "$0"
      exit 0 ;;
    *)
      echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if $DO_ALL; then
  DO_FTI=true; DO_SCR=true; DO_JEMALLOC=true; DO_TOOLS=true
fi

# Resolve to absolute path
INSTALL_PREFIX="$(mkdir -p "${INSTALL_PREFIX}" && cd "${INSTALL_PREFIX}" && pwd)"
SRC_DIR="${INSTALL_PREFIX}/src"
JOBS="$(nproc 2>/dev/null || echo 2)"
ARCH="$(uname -m)"

echo "============================================================"
echo "  Checkpoint library installation"
echo "  Install prefix : ${INSTALL_PREFIX}"
echo "  Source dir      : ${SRC_DIR}"
echo "  Architecture   : ${ARCH}"
echo "  Parallel jobs  : ${JOBS}"
echo "============================================================"
echo ""

mkdir -p "${SRC_DIR}" "${INSTALL_PREFIX}/lib" "${INSTALL_PREFIX}/include"

# ── Helpers ──────────────────────────────────────────────────────────────
ok()   { echo "[OK]    $*"; }
skip() { echo "[SKIP]  $*"; }
info() { echo "[INFO]  $*"; }
fail() { echo "[FAIL]  $*" >&2; return 1; }

check_prereq() {
  local missing=()
  command -v cmake  >/dev/null 2>&1 || missing+=(cmake)
  command -v make   >/dev/null 2>&1 || missing+=(make)
  command -v mpicc  >/dev/null 2>&1 || missing+=(mpicc)
  command -v mpicxx >/dev/null 2>&1 || missing+=(mpicxx)
  command -v gcc    >/dev/null 2>&1 || missing+=(gcc)
  command -v git    >/dev/null 2>&1 || missing+=(git)
  if [[ ${#missing[@]} -gt 0 ]]; then
    fail "Missing prerequisites: ${missing[*]}"
  fi
  ok "Prerequisites satisfied (cmake, make, mpicc, mpicxx, gcc, git)"
}

# ── 1. FTI ───────────────────────────────────────────────────────────────
install_fti() {
  local marker="${INSTALL_PREFIX}/include/fti.h"
  if [[ -f "${marker}" ]]; then
    skip "FTI already installed (${marker} exists)"
    return 0
  fi

  info "Installing FTI v1.6 ..."
  local src="${SRC_DIR}/fti"
  if [[ ! -d "${src}" ]]; then
    git clone --depth 1 --branch v1.6 https://github.com/leobago/fti.git "${src}"
  fi

  local build="${src}/build"
  rm -rf "${build}"
  mkdir -p "${build}"
  cd "${build}"

  cmake .. \
    -DCMAKE_INSTALL_PREFIX="${INSTALL_PREFIX}" \
    -DCMAKE_C_COMPILER=mpicc \
    -DENABLE_FORTRAN=OFF \
    -DENABLE_HDF5=OFF \
    -DENABLE_SIONLIB=OFF \
    -DENABLE_IME_NATIVE=OFF \
    -DENABLE_LUSTRE=OFF \
    -DENABLE_EXAMPLES=OFF \
    -DENABLE_TESTS=OFF \
    -DCMAKE_BUILD_TYPE=Release

  make -j"${JOBS}"
  make install

  # FTI sometimes installs to lib64 — symlink if needed
  if [[ -d "${INSTALL_PREFIX}/lib64" ]] && [[ ! -L "${INSTALL_PREFIX}/lib64" ]]; then
    # Merge lib64 into lib
    cp -rn "${INSTALL_PREFIX}/lib64/"* "${INSTALL_PREFIX}/lib/" 2>/dev/null || true
  fi

  ok "FTI v1.6 installed to ${INSTALL_PREFIX}"
}

# ── 2. SCR ───────────────────────────────────────────────────────────────
install_scr() {
  local marker="${INSTALL_PREFIX}/include/scr.h"
  if [[ -f "${marker}" ]]; then
    skip "SCR already installed (${marker} exists)"
    return 0
  fi

  info "Installing SCR v3.1.0 (with bootstrap for sub-dependencies) ..."
  local src="${SRC_DIR}/scr"
  if [[ ! -d "${src}" ]]; then
    git clone --depth 1 --branch v3.1.0 https://github.com/LLNL/scr.git "${src}"
  fi

  cd "${src}"

  # SCR ships a bootstrap.sh that downloads+builds all 9 sub-dependencies
  # (lwgrp, dtcmp, kvtree, AXL, spath, rankstr, redset, shuffile, er)
  # into scr/install/. We run it, then build SCR itself pointing there.
  if [[ ! -f install/lib/libkvtree.so ]] && [[ ! -f install/lib/libkvtree.a ]]; then
    info "Running bootstrap.sh to build SCR sub-dependencies ..."
    bash bootstrap.sh --tag --opt --clean
  else
    info "SCR sub-dependencies already built (skipping bootstrap)"
  fi

  local dep_dir="${src}/install"

  local build="${src}/build"
  rm -rf "${build}"
  mkdir -p "${build}"
  cd "${build}"

  cmake .. \
    -DCMAKE_INSTALL_PREFIX="${INSTALL_PREFIX}" \
    -DCMAKE_PREFIX_PATH="${dep_dir}" \
    -DCMAKE_C_COMPILER=mpicc \
    -DCMAKE_CXX_COMPILER=mpicxx \
    -DSCR_RESOURCE_MANAGER=NONE \
    -DSCR_CNTL_BASE=/tmp \
    -DSCR_CACHE_BASE=/tmp \
    -DENABLE_FORTRAN=OFF \
    -DENABLE_EXAMPLES=OFF \
    -DENABLE_TESTS=OFF \
    -DBUILD_SHARED_LIBS=ON \
    -DCMAKE_BUILD_TYPE=Release

  make -j"${JOBS}"
  make install

  # Also copy sub-dependency libs so LULESH can link at runtime
  cp -n "${dep_dir}"/lib/lib*.so* "${INSTALL_PREFIX}/lib/" 2>/dev/null || true
  cp -n "${dep_dir}"/lib/lib*.a   "${INSTALL_PREFIX}/lib/" 2>/dev/null || true
  cp -rn "${dep_dir}"/include/*   "${INSTALL_PREFIX}/include/" 2>/dev/null || true

  ok "SCR v3.1.0 installed to ${INSTALL_PREFIX}"
}

# ── 3. jemalloc ──────────────────────────────────────────────────────────
install_jemalloc() {
  local marker="${INSTALL_PREFIX}/lib/libjemalloc.so"
  # Also check .a for static builds
  if [[ -f "${marker}" ]] || [[ -f "${INSTALL_PREFIX}/lib/libjemalloc.a" ]]; then
    skip "jemalloc already installed"
    return 0
  fi

  info "Installing jemalloc ..."
  local src="${SRC_DIR}/jemalloc"
  if [[ ! -d "${src}" ]]; then
    git clone --depth 1 --branch 5.3.0 https://github.com/jemalloc/jemalloc.git "${src}"
  fi

  cd "${src}"

  # Check for autotools
  if ! command -v autoconf >/dev/null 2>&1; then
    info "autoconf not found — trying to install jemalloc with existing configure"
    if [[ ! -f configure ]]; then
      fail "jemalloc needs autoconf to generate configure script"
    fi
  else
    ./autogen.sh
  fi

  ./configure --prefix="${INSTALL_PREFIX}"
  make -j"${JOBS}"
  make install

  ok "jemalloc installed to ${INSTALL_PREFIX}"
}

# ── 4. Pallocator stub ──────────────────────────────────────────────────
install_pallocator_stub() {
  local marker="${INSTALL_PREFIX}/include/jemalloc/pallocator.h"
  if [[ -f "${marker}" ]]; then
    skip "pallocator.h stub already exists"
    return 0
  fi

  info "Creating pallocator.h stub for LULESH persistent-memory emulation ..."
  mkdir -p "${INSTALL_PREFIX}/include/jemalloc"
  cat > "${marker}" << 'HEADER_EOF'
/*
 * pallocator.h — Stub for jemalloc persistent-memory allocator (PerMA).
 *
 * This stub emulates the pallocator API using standard malloc/free and
 * file-backed mmap, allowing LULESH's persistent-SCR variant to compile
 * and run without the full PerMA/NVRAM infrastructure.
 *
 * Provides: PERM_NEW, JEMALLOC_P, perm, mopen, mclose, PermCheckpoint,
 *           PermRestart macros/functions.
 */
#ifndef JEMALLOC_PALLOCATOR_H
#define JEMALLOC_PALLOCATOR_H

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

/* ── Persistent allocation (falls back to standard malloc) ───────────── */
#define JEMALLOC_P(fn) fn

#ifdef __cplusplus
/* C++ array-syntax support: PERM_NEW(Real_t[N]) → malloc(sizeof(Real_t)*N) */
#define PERM_NEW(expr) (decltype(new expr))(malloc(sizeof(expr)))
#else
#define PERM_NEW(type) ((type *)malloc(sizeof(type)))
#endif

#ifdef __cplusplus
extern "C" {
#endif

/* ── Memory-mapped file support ──────────────────────────────────────── */

/* File extension for mmap backing files */
#define MMAP_EXT ".mmap"

static void *_perm_mmap_base = NULL;
static size_t _perm_mmap_size = 0;
static int _perm_mmap_fd = -1;
static char _perm_mmap_path[4096] = {0};
static void **_perm_root_ptr = NULL;
static size_t _perm_root_size = 0;

static inline void perm(void *root, size_t size) {
  _perm_root_ptr = (void **)root;
  _perm_root_size = size;
}

static inline void mopen(const char *path, const char *mode, size_t size) {
  (void)mode;
  strncpy(_perm_mmap_path, path, sizeof(_perm_mmap_path) - 1);
  _perm_mmap_size = size;

  int flags = O_RDWR | O_CREAT;
  _perm_mmap_fd = open(path, flags, 0644);
  if (_perm_mmap_fd < 0) {
    perror("pallocator: mopen failed");
    return;
  }
  if (ftruncate(_perm_mmap_fd, (off_t)size) != 0) {
    perror("pallocator: ftruncate failed");
  }
  _perm_mmap_base = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED,
                          _perm_mmap_fd, 0);
  if (_perm_mmap_base == MAP_FAILED) {
    _perm_mmap_base = NULL;
    perror("pallocator: mmap failed");
  }
}

static inline void mclose(void) {
  if (_perm_mmap_base && _perm_mmap_base != MAP_FAILED) {
    munmap(_perm_mmap_base, _perm_mmap_size);
  }
  if (_perm_mmap_fd >= 0) {
    close(_perm_mmap_fd);
    _perm_mmap_fd = -1;
  }
  _perm_mmap_base = NULL;
}

/* ── Binary file checkpoint/restore (bopen/bclose/backup/restore) ───── */
/* In the stub, these are no-ops that always succeed (return 0). */

static int _perm_bfd = -1;

static inline int bopen(const char *file, const char *mode) {
  (void)file; (void)mode;
  return 0;
}

static inline int bclose(void) {
  return 0;
}

static inline int backup(void) {
  return 0;
}

static inline int restore(void) {
  return 0;
}

/* ── Checkpoint/Restart helpers ──────────────────────────────────────── */
/* Only provide defaults if the application does not define its own.
 * LULESH defines PermCheckpoint/PermRestart in the source file;
 * use PALLOCATOR_NO_DEFAULT_PERM_FUNCS to suppress these stubs. */
#ifndef PALLOCATOR_NO_DEFAULT_PERM_FUNCS

static inline void _pallocator_default_PermCheckpoint(int force) {
  (void)force;
  if (_perm_mmap_base) msync(_perm_mmap_base, _perm_mmap_size, MS_SYNC);
}

static inline void _pallocator_default_PermRestart(int *init) {
  *init = 1;
}

#endif /* PALLOCATOR_NO_DEFAULT_PERM_FUNCS */

#ifdef __cplusplus
}
#endif

#endif /* JEMALLOC_PALLOCATOR_H */
HEADER_EOF

  ok "pallocator.h stub created at ${marker}"
}

# ── 5. Build tools ──────────────────────────────────────────────────────
install_tools() {
  if command -v meson >/dev/null 2>&1 && command -v ninja >/dev/null 2>&1; then
    skip "meson and ninja already available"
    return 0
  fi

  info "Installing meson and ninja via pip ..."
  local pip=""
  if command -v pip3 >/dev/null 2>&1; then
    pip=pip3
  elif command -v pip >/dev/null 2>&1; then
    pip=pip
  else
    # Try python -m pip
    pip="python3 -m pip"
  fi

  ${pip} install --user meson ninja 2>/dev/null || \
    ${pip} install --prefix="${INSTALL_PREFIX}" meson ninja 2>/dev/null || \
    fail "Could not install meson/ninja. Install manually: pip install --user meson ninja"

  ok "meson and ninja installed"
}

# ── 6. Write env.sh ─────────────────────────────────────────────────────
write_env_sh() {
  local env_file="${INSTALL_PREFIX}/env.sh"
  cat > "${env_file}" << ENVEOF
# Source this file to set up paths for checkpoint libraries.
# Usage: source ${env_file}

export PATH="${INSTALL_PREFIX}/bin:\${PATH}"
export LD_LIBRARY_PATH="${INSTALL_PREFIX}/lib:\${LD_LIBRARY_PATH:-}"
export LIBRARY_PATH="${INSTALL_PREFIX}/lib:\${LIBRARY_PATH:-}"
export C_INCLUDE_PATH="${INSTALL_PREFIX}/include:\${C_INCLUDE_PATH:-}"
export CPLUS_INCLUDE_PATH="${INSTALL_PREFIX}/include:\${CPLUS_INCLUDE_PATH:-}"
export PKG_CONFIG_PATH="${INSTALL_PREFIX}/lib/pkgconfig:\${PKG_CONFIG_PATH:-}"
export CMAKE_PREFIX_PATH="${INSTALL_PREFIX}:\${CMAKE_PREFIX_PATH:-}"
ENVEOF

  ok "Environment file written to ${env_file}"
  echo ""
  echo "  To activate: source ${env_file}"
}

# ── Main ─────────────────────────────────────────────────────────────────
main() {
  check_prereq

  echo ""
  if $DO_FTI;      then install_fti; echo ""; fi
  if $DO_SCR;      then install_scr; echo ""; fi
  if $DO_JEMALLOC; then install_jemalloc; echo ""; fi
  if $DO_JEMALLOC || $DO_ALL; then install_pallocator_stub; echo ""; fi
  if $DO_TOOLS;    then install_tools; echo ""; fi

  write_env_sh

  echo ""
  echo "============================================================"
  echo "  Installation complete."
  echo ""
  echo "  Installed to: ${INSTALL_PREFIX}"
  echo ""
  local installed=()
  [[ -f "${INSTALL_PREFIX}/include/fti.h" ]]    && installed+=("FTI")
  [[ -f "${INSTALL_PREFIX}/include/scr.h" ]]    && installed+=("SCR")
  [[ -f "${INSTALL_PREFIX}/lib/libjemalloc.so" || -f "${INSTALL_PREFIX}/lib/libjemalloc.a" ]] && installed+=("jemalloc")
  command -v meson >/dev/null 2>&1               && installed+=("meson")
  command -v ninja >/dev/null 2>&1               && installed+=("ninja")
  echo "  Libraries: ${installed[*]:-none}"
  echo ""
  echo "  Next: source ${INSTALL_PREFIX}/env.sh"
  echo "        ./setup.sh --clean"
  echo "        ./build/run_validate_apps.sh"
  echo "============================================================"
}

main
