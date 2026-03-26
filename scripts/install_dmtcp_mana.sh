#!/usr/bin/env bash
# Install DMTCP and the MANA MPI plugin from source.
#
# Usage:
#   ./scripts/install_dmtcp_mana.sh [--prefix PREFIX]
#
# Default install prefix: $HOME/.local
# ($HOME/.local/bin is typically already on PATH on Linux systems.)
#
# The script is idempotent — it skips steps that are already done.
# After installation, a marker file is written so the validation
# framework can auto-discover DMTCP tools without manual PATH changes.
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

if [ -f "${MANA_LIB}" ]; then
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
  info "Building MANA ..."
  if [ -f configure ]; then
    ./configure --prefix="${INSTALL_PREFIX}"
  fi
  make -j"$(nproc)" || make
  make install 2>/dev/null || \
    cp -v lib/*.so "${INSTALL_PREFIX}/lib/dmtcp/" 2>/dev/null || \
    info "MANA build completed; manual install may be needed"
  ok "MANA built (check ${INSTALL_PREFIX}/lib/dmtcp/ for libmana.so)"
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
