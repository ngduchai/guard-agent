#!/usr/bin/env bash
# =============================================================================
# install_deps.sh — Install dependencies for ExaMiniMD
#
# Dependencies:
#   - Kokkos (C++ performance portability library) — built from source
#   - MPI (OpenMPI or MPICH) — installed via system package manager
#   - CMake >= 3.10
#   - C++11-capable compiler (g++ >= 5 or clang++ >= 3.4)
#
# Usage:
#   ./install_deps.sh [OPTIONS]
#
# Options:
#   --prefix DIR        Installation prefix for Kokkos
#                       (default: ~/.local, no sudo required)
#   --kokkos-version V  Kokkos version to install (default: 4.3.01)
#   --no-mpi            Skip MPI installation check
#   --serial-only       Build Kokkos with Serial backend only (no OpenMP)
#   --system-prefix     Install to /usr/local (requires sudo)
#   -h, --help          Show this help message
#
# After running this script, build ExaMiniMD with:
#   mkdir build && cd build
#   cmake .. -DCMAKE_PREFIX_PATH=~/.local
#   cmake --build . --parallel
# =============================================================================

set -euo pipefail

# ---- Defaults ----------------------------------------------------------------
INSTALL_PREFIX="${HOME}/.local"
KOKKOS_VERSION="4.3.01"
INSTALL_MPI=true
KOKKOS_DEVICES="OpenMP"
USE_SUDO=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---- Argument parsing --------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prefix)
      INSTALL_PREFIX="$2"; shift 2 ;;
    --kokkos-version)
      KOKKOS_VERSION="$2"; shift 2 ;;
    --no-mpi)
      INSTALL_MPI=false; shift ;;
    --serial-only)
      KOKKOS_DEVICES="Serial"; shift ;;
    --system-prefix)
      INSTALL_PREFIX="/usr/local"; USE_SUDO=true; shift ;;
    -h|--help)
      sed -n '2,25p' "$0"; exit 0 ;;
    *)
      echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ---- Helpers -----------------------------------------------------------------
info()  { echo "[INFO]  $*"; }
warn()  { echo "[WARN]  $*" >&2; }
error() { echo "[ERROR] $*" >&2; exit 1; }

maybe_sudo() {
  if $USE_SUDO; then
    sudo "$@"
  else
    "$@"
  fi
}

require_cmd() {
  command -v "$1" &>/dev/null || error "Required command '$1' not found. Please install it first."
}

# ---- Detect OS / package manager ---------------------------------------------
detect_pkg_manager() {
  if command -v apt-get &>/dev/null; then
    echo "apt"
  elif command -v dnf &>/dev/null; then
    echo "dnf"
  elif command -v yum &>/dev/null; then
    echo "yum"
  elif command -v brew &>/dev/null; then
    echo "brew"
  else
    echo "unknown"
  fi
}

PKG_MGR=$(detect_pkg_manager)

install_pkg() {
  local pkg="$1"
  info "Installing system package: $pkg"
  case "$PKG_MGR" in
    apt)   sudo apt-get install -y "$pkg" ;;
    dnf)   sudo dnf install -y "$pkg" ;;
    yum)   sudo yum install -y "$pkg" ;;
    brew)  brew install "$pkg" ;;
    *)     warn "Cannot auto-install '$pkg': unknown package manager. Please install it manually." ;;
  esac
}

# ---- Check / install system prerequisites ------------------------------------
info "=== Checking system prerequisites ==="

require_cmd cmake
CMAKE_VERSION=$(cmake --version | head -1 | awk '{print $3}')
info "CMake found: $CMAKE_VERSION"

require_cmd g++
GXX_VERSION=$(g++ --version | head -1)
info "C++ compiler: $GXX_VERSION"

# MPI
if $INSTALL_MPI; then
  if command -v mpicxx &>/dev/null; then
    info "MPI C++ compiler found: $(mpicxx --version 2>&1 | head -1)"
  else
    info "MPI not found — attempting to install..."
    case "$PKG_MGR" in
      apt)
        install_pkg "libopenmpi-dev"
        install_pkg "openmpi-bin"
        ;;
      dnf|yum)
        install_pkg "openmpi-devel"
        ;;
      brew)
        install_pkg "open-mpi"
        ;;
      *)
        warn "Please install OpenMPI or MPICH manually (e.g., libopenmpi-dev on Debian/Ubuntu)."
        ;;
    esac
  fi
fi

# Build tools
for tool in make git wget; do
  if ! command -v "$tool" &>/dev/null; then
    info "Installing missing tool: $tool"
    install_pkg "$tool"
  fi
done

# ---- Check if Kokkos is already installed ------------------------------------
info "=== Checking for Kokkos ==="

KOKKOS_FOUND=false
for search_dir in "$INSTALL_PREFIX" /usr /usr/local /opt/kokkos "${HOME}/.local"; do
  if [[ -f "$search_dir/lib/cmake/Kokkos/KokkosConfig.cmake" ]] || \
     [[ -f "$search_dir/lib64/cmake/Kokkos/KokkosConfig.cmake" ]]; then
    KOKKOS_FOUND=true
    info "Kokkos already installed at: $search_dir"
    break
  fi
done

if $KOKKOS_FOUND; then
  info "Kokkos is already installed. Skipping Kokkos build."
  info "If you want to reinstall, remove the existing installation first."
else
  # ---- Download and build Kokkos -------------------------------------------
  info "=== Installing Kokkos $KOKKOS_VERSION ==="
  info "Installation prefix: $INSTALL_PREFIX"

  KOKKOS_TARBALL="kokkos-${KOKKOS_VERSION}.tar.gz"
  KOKKOS_URL="https://github.com/kokkos/kokkos/archive/refs/tags/${KOKKOS_VERSION}.tar.gz"
  KOKKOS_SRC_DIR="/tmp/kokkos-${KOKKOS_VERSION}"
  KOKKOS_BUILD_DIR="/tmp/kokkos-build-${KOKKOS_VERSION}"

  # Download
  if [[ ! -f "/tmp/${KOKKOS_TARBALL}" ]]; then
    info "Downloading Kokkos from $KOKKOS_URL ..."
    wget -q --show-progress -O "/tmp/${KOKKOS_TARBALL}" "$KOKKOS_URL" || \
      error "Failed to download Kokkos. Check your internet connection."
  else
    info "Kokkos tarball already downloaded at /tmp/${KOKKOS_TARBALL}."
  fi

  # Extract
  if [[ ! -d "$KOKKOS_SRC_DIR" ]]; then
    info "Extracting Kokkos..."
    tar -xzf "/tmp/${KOKKOS_TARBALL}" -C /tmp/
    # The extracted directory may be named kokkos-<version>
    if [[ ! -d "$KOKKOS_SRC_DIR" ]]; then
      EXTRACTED=$(tar -tzf "/tmp/${KOKKOS_TARBALL}" | head -1 | cut -d/ -f1)
      mv "/tmp/${EXTRACTED}" "$KOKKOS_SRC_DIR"
    fi
  else
    info "Kokkos source already extracted at $KOKKOS_SRC_DIR."
  fi

  # Configure
  OPENMP_FLAG=$([ "$KOKKOS_DEVICES" = "OpenMP" ] && echo "ON" || echo "OFF")
  info "Configuring Kokkos (devices: $KOKKOS_DEVICES, prefix: $INSTALL_PREFIX)..."
  rm -rf "$KOKKOS_BUILD_DIR"
  mkdir -p "$KOKKOS_BUILD_DIR"

  cmake -S "$KOKKOS_SRC_DIR" -B "$KOKKOS_BUILD_DIR" \
    -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX" \
    -DCMAKE_BUILD_TYPE=Release \
    -DKokkos_ENABLE_SERIAL=ON \
    -DKokkos_ENABLE_OPENMP="${OPENMP_FLAG}" \
    -DCMAKE_CXX_STANDARD=17

  # Build
  NPROC=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
  info "Building Kokkos with $NPROC parallel jobs..."
  cmake --build "$KOKKOS_BUILD_DIR" --parallel "$NPROC"

  # Install (no sudo needed for user-local prefix)
  info "Installing Kokkos to $INSTALL_PREFIX ..."
  maybe_sudo cmake --install "$KOKKOS_BUILD_DIR"

  info "Kokkos $KOKKOS_VERSION installed successfully."

  # Cleanup build directory
  rm -rf "$KOKKOS_BUILD_DIR"
  info "Build directory cleaned up."
fi

# ---- Summary -----------------------------------------------------------------
info ""
info "=== Dependency installation complete ==="
info ""
info "Installed / verified:"
info "  - CMake:  $(cmake --version | head -1)"
info "  - C++:    $(g++ --version | head -1)"
if command -v mpicxx &>/dev/null; then
  info "  - MPI:    $(mpicxx --version 2>&1 | head -1)"
fi
info "  - Kokkos: $KOKKOS_VERSION (prefix: $INSTALL_PREFIX)"
info ""
info "You can now build ExaMiniMD:"
SCRIPT_REL=$(realpath --relative-to="$(pwd)" "$SCRIPT_DIR" 2>/dev/null || echo "$SCRIPT_DIR")
info "  cd $SCRIPT_REL"
info "  mkdir build && cd build"
info "  cmake .. -DCMAKE_PREFIX_PATH=$INSTALL_PREFIX"
info "  cmake --build . --parallel"
info ""
info "To run ExaMiniMD (serial mode):"
info "  OMP_PROC_BIND=false ./build/src/ExaMiniMD -il input/in.lj --comm-type Serial --kokkos-threads=1"
info ""
info "To run ExaMiniMD with MPI (2 processes):"
info "  mpirun -np 2 ./build/src/ExaMiniMD -il input/in.lj --comm-type MPI --kokkos-threads=1"
