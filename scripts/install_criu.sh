#!/usr/bin/env bash
# Install CRIU (Checkpoint/Restore In Userspace) from source.
#
# Usage:
#   ./scripts/install_criu.sh [--prefix PREFIX]
#
# Default install prefix: $HOME/.local
#
# CRIU requires:
#   - protobuf-c (built from source if not available)
#   - Kernel with CONFIG_CHECKPOINT_RESTORE=y
#   - GCC (not Intel compiler)
#
# The script is idempotent — it skips steps that are already done.
set -euo pipefail

# ── Parse arguments ───────────────────────────────────────────────────────
INSTALL_PREFIX="${HOME}/.local"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prefix)
      INSTALL_PREFIX="$2"; shift 2 ;;
    --prefix=*)
      INSTALL_PREFIX="${1#--prefix=}"; shift ;;
    -h|--help)
      echo "Usage: $0 [--prefix PREFIX]"
      echo "  Default prefix: \$HOME/.local"
      exit 0 ;;
    *)
      echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

INSTALL_PREFIX="$(cd "$(dirname "${INSTALL_PREFIX}")" 2>/dev/null && pwd)/$(basename "${INSTALL_PREFIX}")"
SRC_DIR="${INSTALL_PREFIX}/share/guard-agent/criu-src"

echo "============================================================"
echo "  CRIU installation"
echo "  Install prefix : ${INSTALL_PREFIX}"
echo "  Source dir      : ${SRC_DIR}"
echo "============================================================"
echo ""

mkdir -p "${SRC_DIR}"

ok()   { echo "[OK]    $*"; }
skip() { echo "[SKIP]  $*"; }
info() { echo "[INFO]  $*"; }

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
  if [ -z "${_cc}" ]; then
    _cc=$(find /opt/aurora -name "gcc" -path "*/gcc-1[0-9]*/bin/gcc" 2>/dev/null | head -1)
  fi
  echo "${_cc}"
}

GCC_CC="$(_find_gcc)"
if [ -z "${GCC_CC}" ]; then
  echo "[ERROR] GCC not found. CRIU requires GCC to build." >&2
  exit 1
fi
GCC_CXX="$(echo "${GCC_CC}" | sed 's|/gcc$|/g++|')"
GCC_DIR="$(dirname "${GCC_CC}")"
info "Using GCC: ${GCC_CC} ($(${GCC_CC} --version 2>/dev/null | head -1))"

# Put GCC first on PATH so make uses it
export PATH="${GCC_DIR}:${PATH}"
export CC="${GCC_CC}"
export CXX="${GCC_CXX}"

# ── Check kernel support ─────────────────────────────────────────────────
if zcat /proc/config.gz 2>/dev/null | grep -q 'CONFIG_CHECKPOINT_RESTORE=y'; then
  ok "Kernel supports CONFIG_CHECKPOINT_RESTORE"
else
  echo "[WARN]  Cannot verify CONFIG_CHECKPOINT_RESTORE=y in kernel config."
  echo "        CRIU may not work on this kernel."
fi

# ── 1. Build protobuf-c ──────────────────────────────────────────────────
PROTOC_SRC="${SRC_DIR}/protobuf-c"
PROTOC_LIB="${INSTALL_PREFIX}/lib/libprotobuf-c.so"

if [ -f "${PROTOC_LIB}" ]; then
  skip "protobuf-c already installed at ${PROTOC_LIB}"
else
  if [ ! -d "${PROTOC_SRC}" ]; then
    info "Cloning protobuf-c ..."
    git clone --depth 1 https://github.com/protobuf-c/protobuf-c.git "${PROTOC_SRC}"
  fi
  info "Building protobuf-c ..."
  cd "${PROTOC_SRC}"
  # protobuf-c needs protobuf (protoc). Check if available.
  if ! command -v protoc &>/dev/null; then
    # Try to find protoc in common locations
    PROTOC_BIN=""
    for p in /usr/bin/protoc /usr/local/bin/protoc; do
      if [ -x "$p" ]; then PROTOC_BIN="$p"; break; fi
    done
    if [ -z "${PROTOC_BIN}" ]; then
      echo "[WARN]  protoc not found. Building protobuf from source first..."
      # Build protobuf (Google's protobuf) as a dependency
      PROTOBUF_SRC="${SRC_DIR}/protobuf"
      if [ ! -d "${PROTOBUF_SRC}" ]; then
        git clone --depth 1 --branch v3.21.12 https://github.com/protocolbuffers/protobuf.git "${PROTOBUF_SRC}"
      fi
      cd "${PROTOBUF_SRC}"
      if [ -f configure ]; then
        ./configure --prefix="${INSTALL_PREFIX}"
      else
        git submodule update --init --recursive 2>/dev/null || true
        mkdir -p build_dir && cd build_dir
        cmake .. -DCMAKE_INSTALL_PREFIX="${INSTALL_PREFIX}" \
          -DCMAKE_C_COMPILER="${GCC_CC}" \
          -DCMAKE_CXX_COMPILER="${GCC_CXX}" \
          -Dprotobuf_BUILD_TESTS=OFF -DCMAKE_POSITION_INDEPENDENT_CODE=ON
        make -j"$(nproc)"
        make install
        cd ..
      fi
      export PATH="${INSTALL_PREFIX}/bin:${PATH}"
      export PKG_CONFIG_PATH="${INSTALL_PREFIX}/lib/pkgconfig:${INSTALL_PREFIX}/lib64/pkgconfig:${PKG_CONFIG_PATH:-}"
      export LD_LIBRARY_PATH="${INSTALL_PREFIX}/lib:${INSTALL_PREFIX}/lib64:${LD_LIBRARY_PATH:-}"
      cd "${PROTOC_SRC}"
    fi
  fi
  # Build protobuf-c
  if [ -f autogen.sh ]; then
    ./autogen.sh
  fi
  if [ -f configure ]; then
    PKG_CONFIG_PATH="${INSTALL_PREFIX}/lib/pkgconfig:${INSTALL_PREFIX}/lib64/pkgconfig:${PKG_CONFIG_PATH:-}" \
      ./configure --prefix="${INSTALL_PREFIX}"
    make -j"$(nproc)"
    make install
  else
    mkdir -p build_dir && cd build_dir
    cmake .. -DCMAKE_INSTALL_PREFIX="${INSTALL_PREFIX}" \
      -DCMAKE_PREFIX_PATH="${INSTALL_PREFIX}"
    make -j"$(nproc)"
    make install
    cd ..
  fi
  ok "protobuf-c installed to ${INSTALL_PREFIX}"
fi

export PKG_CONFIG_PATH="${INSTALL_PREFIX}/lib/pkgconfig:${INSTALL_PREFIX}/lib64/pkgconfig:${PKG_CONFIG_PATH:-}"
export LD_LIBRARY_PATH="${INSTALL_PREFIX}/lib:${INSTALL_PREFIX}/lib64:${LD_LIBRARY_PATH:-}"

# ── 2. Build CRIU ────────────────────────────────────────────────────────
CRIU_SRC="${SRC_DIR}/criu"
CRIU_BIN="${INSTALL_PREFIX}/sbin/criu"

if [ -x "${CRIU_BIN}" ]; then
  skip "CRIU already installed at ${CRIU_BIN}"
else
  if [ ! -d "${CRIU_SRC}" ]; then
    info "Cloning CRIU ..."
    git clone --depth 1 https://github.com/checkpoint-restore/criu.git "${CRIU_SRC}"
  fi
  info "Building CRIU ..."
  cd "${CRIU_SRC}"
  make clean 2>/dev/null || true
  make -j"$(nproc)" \
    PREFIX="${INSTALL_PREFIX}" \
    DESTDIR="" \
    CC="${GCC_CC}" \
    LD="${GCC_CC}" \
    USERCFLAGS="-I${INSTALL_PREFIX}/include" \
    USERLDFLAGS="-L${INSTALL_PREFIX}/lib -L${INSTALL_PREFIX}/lib64"
  make install PREFIX="${INSTALL_PREFIX}" DESTDIR=""
  ok "CRIU installed to ${INSTALL_PREFIX}"
fi

# ── 3. Verify ────────────────────────────────────────────────────────────
echo ""
echo "Verifying installation ..."
export PATH="${INSTALL_PREFIX}/sbin:${INSTALL_PREFIX}/bin:${PATH}"

if command -v criu &>/dev/null; then
  ok "criu found at $(command -v criu)"
  criu --version 2>/dev/null || true
else
  echo "[FAIL]  criu not found in PATH"
  echo "        Add to your shell profile:"
  echo "          export PATH=\"${INSTALL_PREFIX}/sbin:\${PATH}\""
  exit 1
fi

# Quick sanity check
if criu check 2>/dev/null; then
  ok "criu check passed — kernel is compatible"
else
  echo "[WARN]  'criu check' failed. Some features may not work."
  echo "        This is common on HPC systems with restricted kernels."
  echo "        Checkpoint/restore of simple processes may still work."
fi

# Write marker file for auto-discovery
MARKER_DIR="${HOME}/.local/share/guard-agent"
MARKER_FILE="${MARKER_DIR}/criu_prefix"
mkdir -p "${MARKER_DIR}"
echo "${INSTALL_PREFIX}" > "${MARKER_FILE}"
ok "Install prefix recorded in ${MARKER_FILE}"

echo ""
echo "============================================================"
echo "  CRIU installation complete."
echo ""
echo "  Add to your shell profile:"
echo "    export PATH=\"${INSTALL_PREFIX}/sbin:\${PATH}\""
echo "============================================================"
